# communication

batman-adv mesh, mavlink-router, and the 868 MHz safety link.

## Built

### `safety_link/` — abort and recall

The wire format that makes `/api/safety/abort` real. Built to the three
constraints in [`../docs/implementation-plan.md`](../docs/implementation-plan.md) §4:

1. **Off the mesh.** The reason to abort is often that the mesh failed, so this
   runs on the separate 865-867 MHz radio.
2. **Framed, sequenced, acknowledged per aircraft.** LoRa is lossy; a single
   unacknowledged packet is a hope, not a command. The operator sees *which*
   aircraft accepted - "abort sent" and "abort received" are different claims.
3. **Secondary to a hardware path.** The primary abort is the safety receiver
   driving `RC7_OPTION=4` (RTL) straight into the flight controller, which works
   with a hung companion. This layer adds addressing and an audit trail.

12-byte CRC-16/CCITT frames, ~60 ms of airtime at SF7. Tested against single-bit
flips at 14 positions, truncation, replay, stale frames, partial acknowledgement,
and a full exchange with **60 % packet loss in both directions** - where the
abort still reaches all three aircraft.

> The GCS endpoint still sets a flag that nothing reads. This is the wire
> format, not the wiring. The UI must keep saying **NOT IMPLEMENTED** until the
> radio is connected.

## Not built

`mesh/` (batman-adv config and link monitoring) and `mavlink-router/` config.
