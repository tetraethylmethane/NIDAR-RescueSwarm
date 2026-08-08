"""Safety-link tests — written against how a lossy radio actually fails.

Abort and recall are safety functions. A protocol test that only checks the
happy path proves nothing useful, so most of these are corruption, truncation,
replay, loss and partial acknowledgement.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "communication"))
from safety_link.protocol import (  # noqa: E402
    BROADCAST, FRAME_LEN, Command, Frame, ProtocolError, Receiver, Sender,
    crc16, decode,
)


def test_round_trip():
    f = Frame(Command.ABORT, target=2, seq=42, t=1_723_459_200)
    g = decode(f.encode())
    assert g == f


def test_frame_is_short_enough_for_lora():
    """At SF7/125 kHz this is ~60 ms of airtime, so it can repeat at 2 Hz for
    ten seconds and still leave the band nearly idle."""
    assert len(Frame(Command.ABORT).encode()) == FRAME_LEN == 12


@pytest.mark.parametrize("bit", range(0, 96, 7))
def test_single_bit_flip_is_always_caught(bit):
    """The failure mode of a noisy radio. A checksum would miss some of these;
    CRC-16/CCITT does not."""
    data = bytearray(Frame(Command.ABORT, 1, 7, 1_723_459_200).encode())
    data[bit // 8] ^= 1 << (bit % 8)
    with pytest.raises(ProtocolError):
        decode(bytes(data))


@pytest.mark.parametrize("payload", [
    b"", b"\xa5", b"\xa5\x01", b"\x00" * 12, b"\xa5\x01" + b"\x00" * 20,
    b"garbage-from-another-system",
])
def test_malformed_frames_rejected(payload):
    with pytest.raises(ProtocolError):
        decode(payload)


def test_unknown_command_rejected():
    body = bytearray(Frame(Command.ABORT).encode())
    body[2] = 0x7F                       # not a Command
    body[10:12] = crc16(bytes(body[:10])).to_bytes(2, "big")
    with pytest.raises(ProtocolError):
        decode(bytes(body))


def test_wrong_version_rejected():
    body = bytearray(Frame(Command.ABORT).encode())
    body[1] = 0x02
    body[10:12] = crc16(bytes(body[:10])).to_bytes(2, "big")
    with pytest.raises(ProtocolError):
        decode(bytes(body))


# ------------------------------------------------------------------ receiver
def test_receiver_acts_and_acknowledges():
    r = Receiver(2)
    frame = Frame(Command.RECALL, BROADCAST, 5, 1000).encode()
    action, ack = r.on_receive(frame, now=1000)
    assert action is Command.RECALL
    a = decode(ack)
    assert a.command is Command.ACK and a.target == 2 and a.seq == 5


def test_repeats_are_acknowledged_but_acted_on_once():
    """The sender repeats for ten seconds. The aircraft must not re-trigger on
    every repeat, but must keep acknowledging in case the earlier ack was the
    packet that got lost."""
    r = Receiver(1)
    frame = Frame(Command.ABORT, BROADCAST, 9, 1000).encode()
    first, ack1 = r.on_receive(frame, now=1000)
    assert first is Command.ABORT and ack1
    for _ in range(20):
        again, ack = r.on_receive(frame, now=1001)
        assert again is None, "repeat re-triggered the action"
        assert ack is not None, "repeat was not acknowledged"


def test_stale_frame_rejected():
    """A repeater or a delayed packet must not abort a mission minutes after
    the operator cleared it."""
    r = Receiver(1)
    old = Frame(Command.ABORT, BROADCAST, 3, 1000).encode()
    action, ack = r.on_receive(old, now=1000 + 120)
    assert action is None and ack is None
    assert r.rejected == 1


def test_frame_addressed_to_another_aircraft_is_ignored():
    r = Receiver(3)
    action, ack = r.on_receive(Frame(Command.ABORT, 1, 1, 1000).encode(), now=1000)
    assert action is None and ack is None


def test_ack_frames_do_not_trigger_actions():
    r = Receiver(1)
    action, _ = r.on_receive(Frame(Command.ACK, 2, 1, 1000).encode(), now=1000)
    assert action is None


# -------------------------------------------------------------------- sender
def test_sender_tracks_which_aircraft_have_accepted():
    """'Abort sent' and 'abort received' are different statements, and the
    operator must be shown the second."""
    s = Sender((1, 2, 3))
    first = s.begin(Command.ABORT, now=1000)
    seq = decode(first).seq

    assert s.missing == (1, 2, 3)
    assert not s.complete

    s.on_receive(Frame(Command.ACK, 1, seq, 1000).encode())
    s.on_receive(Frame(Command.ACK, 3, seq, 1000).encode())
    assert s.missing == (2,), "operator must see drone 2 has not accepted"
    assert not s.complete

    s.on_receive(Frame(Command.ACK, 2, seq, 1000).encode())
    assert s.complete and s.missing == ()
    assert s.frame(now=1001) is None, "stop transmitting once all acked"


def test_stale_acks_from_a_previous_command_are_ignored():
    s = Sender((1, 2))
    s.begin(Command.ABORT, now=1000)
    old_seq = s._seq
    s.begin(Command.RECALL, now=1010)              # new command, new sequence
    assert s.on_receive(Frame(Command.ACK, 1, old_seq, 1010).encode()) is None
    assert s.missing == (1, 2)


def test_sender_stops_repeating_after_the_window():
    s = Sender((1,), repeat_s=10.0)
    s.begin(Command.ABORT, now=1000)
    assert s.frame(now=1005) is not None
    assert s.frame(now=1011) is None


def test_only_abort_and_recall_may_be_sent():
    s = Sender()
    for bad in (Command.ACK, Command.HEARTBEAT):
        with pytest.raises(ProtocolError):
            s.begin(bad)


# --------------------------------------------------------------- end to end
def test_full_exchange_over_a_lossy_link():
    """Drop 60 % of packets in both directions and require the abort to land on
    all three aircraft anyway. This is what the repeat window is for."""
    import random

    rng = random.Random(20260808)
    s = Sender((1, 2, 3), repeat_s=10.0)
    rx = {i: Receiver(i) for i in (1, 2, 3)}

    now = 1000.0
    data = s.begin(Command.ABORT, now=now)
    acted: set[int] = set()

    for _ in range(40):
        if data is not None:
            for i, r in rx.items():
                if rng.random() < 0.4:                   # 60 % loss uplink
                    action, ack = r.on_receive(data, now=now)
                    if action is Command.ABORT:
                        acted.add(i)
                    if ack and rng.random() < 0.4:       # 60 % loss downlink
                        s.on_receive(ack)
        now += 0.5
        data = s.frame(now=now)
        if s.complete:
            break

    assert acted == {1, 2, 3}, f"aircraft that never acted: {{1,2,3}} - {acted}"
    assert s.complete, f"never confirmed: {s.missing}"
    for r in rx.values():
        assert r.action is Command.ABORT
