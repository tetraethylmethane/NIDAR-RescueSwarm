#!/usr/bin/env python3
"""Tests for the cascade geometry and economics.

These run without torch, without cv2 and without the 13 GB dataset, because
everything they check is arithmetic. The gate's real recall is NOT testable
here -- that needs SeaDronesSee and a GPU, and nothing in this file pretends
otherwise. What is testable here is whether the tiling covers the frame, whether
a target that straddles a boundary is counted correctly, and whether the
break-even and recall models behave at their limits.
"""
from __future__ import annotations

import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from perception.cascade import economics as E  # noqa: E402
from perception.cascade import geometry as G  # noqa: E402


# ------------------------------------------------------------------ geometry
def test_tile_grid_covers_every_pixel():
    """No gaps. A survivor in an uncovered strip is invisible by construction."""
    w, h = 4056, 3040
    tiles = G.tile_grid(w, h, 640, 0.20)
    covered = [[False] * 64 for _ in range(48)]      # coarse 64 px sampling
    for t in tiles:
        for gy in range(48):
            for gx in range(64):
                px, py = gx * 64 + 32, gy * 64 + 32
                if px < w and py < h and t.x0 <= px < t.x1 and t.y0 <= py < t.y1:
                    covered[gy][gx] = True
    for gy in range(48):
        for gx in range(64):
            if gx * 64 + 32 < w and gy * 64 + 32 < h:
                assert covered[gy][gx], f"gap at grid ({gx},{gy})"


def test_tile_count_matches_the_documented_figure():
    """48 at 20 % overlap. The whole cost model is built on this number."""
    assert len(G.tile_grid(4056, 3040, 640, 0.20)) == 48
    assert len(G.tile_grid(2028, 1520, 640, 0.20)) == 12      # after 2x downsample
    # SAHI's alternative 25 % recommendation. 54, not 63: the naive
    # ceil(H/stride) overcounts because the LAST tile covers a full `tile`, not
    # a stride. The correct count is ceil((H-tile)/stride)+1, and getting this
    # wrong inflates the cost of extra overlap by more than a factor of two.
    assert len(G.tile_grid(4056, 3040, 640, 0.25)) == 54
    assert 54 / 48 == pytest.approx(1.125, abs=0.001)   # +12.5 %, not +31 %


def test_all_tiles_are_full_size():
    """Edge tiles are pulled flush, never padded -- a detector trained on 640
    crops should never be handed a partly black one."""
    for t in G.tile_grid(4056, 3040, 640, 0.20):
        assert t.w == 640 and t.h == 640
        assert 0 <= t.x0 and t.x1 <= 4056
        assert 0 <= t.y0 and t.y1 <= 3040


def test_target_always_appears_whole_somewhere():
    """The property the tiling rests on: 128 px of shared margin against a
    39 px target means no survivor can be sliced by every tile touching them."""
    tiles = G.tile_grid(4056, 3040, 640, 0.20)
    assert G.overlap_covers_target(640, 0.20, 38.7)
    side = 39
    for cx in range(20, 4056 - 20, 97):        # 97 to land on boundaries too
        for cy in range(20, 3040 - 20, 101):
            box = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
            assert G.tiles_for_box(tiles, box), f"target at ({cx},{cy}) sliced by every tile"


def test_a_target_wider_than_the_overlap_can_be_lost():
    """The failure mode, asserted so it cannot be argued away.

    This is why a 96 px tiling with 19 px of margin was rejected: an 82 px
    target genuinely has positions where no tile holds 80 % of it.
    """
    assert not G.overlap_covers_target(96, 0.20, 82.0)
    tiles = G.tile_grid(1000, 1000, 96, 0.20)
    lost = 0
    for cx in range(60, 940, 7):
        box = (cx - 41, 500 - 41, cx + 41, 500 + 41)
        if not G.tiles_for_box(tiles, box):
            lost += 1
    assert lost > 0, "expected some positions to be unrecoverable"


def test_scale_matching_is_a_ratio():
    """Borrowed data is rescaled so its targets are OUR size in pixels."""
    assert G.scale_to_match(20.0, 40.0) == pytest.approx(2.0)
    assert G.scale_to_match(80.0, 40.0) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        G.scale_to_match(0.0, 40.0)


def test_gsd_and_target_px_agree_with_the_sizing_model():
    """1.55 um, 6 mm, 40 m -> 1.03 cm/px, and a 0.4 m target -> ~39 px."""
    assert G.gsd_m(40.0, 1.55, 6.0) * 100 == pytest.approx(1.033, abs=0.01)
    assert G.target_px(0.4, 40.0, 1.55, 6.0) == pytest.approx(38.7, abs=0.5)


def test_partially_visible_target_is_not_a_positive():
    """A sliver is not a training example."""
    tiles = [G.Tile(0, 0, 640, 640)]
    assert G.tiles_for_box(tiles, (600, 300, 700, 340)) == []      # 40 % in
    assert G.tiles_for_box(tiles, (560, 300, 620, 340)) == [0]     # fully in


# ----------------------------------------------------------------- economics
def test_break_even_is_insensitive_to_gate_cost():
    """The result that decides the design: the detector dominates so completely
    that a 16x more expensive gate costs only ~5 points of rejection. There is
    therefore no reason to cripple the gate's input resolution to save compute,
    which is what the MCU-class proposal was doing."""
    be = {g: E.break_even_rejection(E.DOWNSAMPLED, E.cascade_at(g))
          for g in (160, 320, 640)}
    assert 0.74 < be[160] < 0.77
    assert 0.79 < be[640] < 0.82
    assert be[640] - be[160] < 0.06


def test_cascade_at_break_even_costs_the_baseline():
    for g in (160, 320, 640):
        c = E.cascade_at(g)
        be = E.break_even_rejection(E.DOWNSAMPLED, c)
        assert c.cost_gflop(be) == pytest.approx(E.DOWNSAMPLED.cost_gflop(), rel=1e-9)


def test_native_tiling_doubles_pixels_on_target():
    assert E.NATIVE.target_px / E.DOWNSAMPLED.target_px == pytest.approx(2.0, abs=0.02)


def test_correlated_failure_destroys_the_benefit_of_fusion():
    """Twelve independent looks at 50 % recall find everything; twelve
    correlated looks at 50 % recall find half. The gap IS the risk."""
    assert E.per_target_recall(0.5, 12, correlation=0.0) > 0.999
    assert E.per_target_recall(0.5, 12, correlation=1.0) == pytest.approx(0.5)


def test_required_per_look_inverts_per_target_recall():
    for corr in (0.0, 0.5, 1.0):
        p = E.required_per_look(0.90, 12, corr)
        assert E.per_target_recall(p, 12, corr) == pytest.approx(0.90, abs=1e-3)


def test_verdict_requires_both_cost_and_recall():
    c = E.cascade_at(320)
    be = E.break_even_rejection(E.DOWNSAMPLED, c)
    # cheap enough but unsafe
    v = E.verdict(rejection=be + 0.05, gate_recall=0.60, baseline=E.DOWNSAMPLED,
                  cascade=c)
    assert v["cost_ok"] and not v["recall_ok"] and not v["adopt"]
    # safe but too expensive
    v = E.verdict(rejection=be - 0.20, gate_recall=0.99, baseline=E.DOWNSAMPLED,
                  cascade=c)
    assert not v["cost_ok"] and v["recall_ok"] and not v["adopt"]
    # both
    v = E.verdict(rejection=be + 0.05, gate_recall=0.99, baseline=E.DOWNSAMPLED,
                  cascade=c)
    assert v["adopt"]


def test_verdict_judges_recall_on_the_correlated_case():
    """A gate at 92 % per-look passes only because we refuse to assume
    independence. If we assumed independence, 50 % would 'pass'."""
    c = E.cascade_at(320)
    be = E.break_even_rejection(E.DOWNSAMPLED, c)
    v = E.verdict(be + 0.01, gate_recall=0.50, baseline=E.DOWNSAMPLED, cascade=c)
    assert v["per_target_recall_if_independent"] > 0.999
    assert not v["adopt"], "independence assumption must not be able to pass a bad gate"


# ------------------------------------------------------------------- dataset
# Synthetic COCO, so the selection logic is exercised before the 13 GB arrives.
from perception.cascade import dataset as D  # noqa: E402


def _coco(images, annotations, cats=(("swimmer", 1),)):
    return {"categories": [{"id": i, "name": n} for n, i in cats],
            "images": images, "annotations": annotations}


def _img(i, pitch, w=3840, h=2160, alt=40.0):
    return {"id": i, "file_name": f"{i}.jpg", "width": w, "height": h,
            "altitude": alt, "gimbal_pitch": pitch}


def _ann(i, x, y, w, h, cat=1):
    return {"image_id": i, "category_id": cat, "bbox": [x, y, w, h], "iscrowd": 0}


def test_pitch_convention_is_inferred_once_per_dataset():
    """Per-value guessing is ambiguous across [-90, 0] and silently deletes the
    oblique frames, which are the hard ones."""
    assert D.infer_pitch_convention([{"gimbal_pitch": -90.0},
                                     {"gimbal_pitch": -45.0}]) == "nadir_at_-90"
    assert D.infer_pitch_convention([{"gimbal_pitch": 0.0},
                                     {"gimbal_pitch": 45.0}]) == "nadir_at_0"
    assert D.infer_pitch_convention([{"gimbal_yaw": 3.0}]) == "unknown"


def test_off_nadir_under_each_convention():
    assert D._off_nadir({"gimbal_pitch": -90.0}, "nadir_at_-90") == pytest.approx(0.0)
    assert D._off_nadir({"gimbal_pitch": -70.0}, "nadir_at_-90") == pytest.approx(20.0)
    # the value that used to fall between the two ranges and return None
    assert D._off_nadir({"gimbal_pitch": -45.0}, "nadir_at_-90") == pytest.approx(45.0)
    assert D._off_nadir({"gimbal_pitch": 45.0}, "nadir_at_0") == pytest.approx(45.0)
    assert D._off_nadir({"gimbal_yaw": 3.0}, "nadir_at_-90") is None


def test_oblique_frames_are_excluded(tmp_path):
    """Our geolocation is near-nadir only, so oblique frames would flatter the
    result on a problem we do not have."""
    coco = _coco([_img(1, -90.0), _img(2, -45.0)],
                 [_ann(1, 10, 10, 30, 30), _ann(2, 10, 10, 30, 30)])
    p = tmp_path / "a.json"
    p.write_text(json.dumps(coco), encoding="utf-8")
    kept, reasons = D.select(D.load_split(str(p)))
    assert [f.image_id for f in kept] == [1]
    assert any("oblique" in k for k in reasons)


def test_frames_without_people_or_metadata_are_dropped(tmp_path):
    coco = _coco([_img(1, -90.0), _img(2, -90.0), _img(3, None)],
                 [_ann(1, 10, 10, 30, 30), _ann(3, 10, 10, 30, 30)])
    p = tmp_path / "a.json"
    p.write_text(json.dumps(coco), encoding="utf-8")
    kept, reasons = D.select(D.load_split(str(p)))
    assert [f.image_id for f in kept] == [1]
    assert reasons["no annotated person"] == 1
    assert reasons["no usable gimbal metadata"] == 1


def test_unknown_category_names_fail_loudly(tmp_path):
    """Guessing a category id silently would measure the wrong class."""
    coco = _coco([_img(1, -90.0)], [_ann(1, 10, 10, 30, 30, cat=7)],
                 cats=(("boat", 7),))
    p = tmp_path / "a.json"
    p.write_text(json.dumps(coco), encoding="utf-8")
    with pytest.raises(SystemExit):
        D.load_split(str(p))


def test_rescaling_puts_targets_at_our_size(tmp_path):
    """A 20 px source target becomes our ~39 px one, and the frame grows to match."""
    coco = _coco([_img(1, -90.0)], [_ann(1, 100, 100, 20, 20)])
    p = tmp_path / "a.json"
    p.write_text(json.dumps(coco), encoding="utf-8")
    f = D.select(D.load_split(str(p)))[0][0]
    plan = D.plan_tiles(f, wanted_px=38.7)
    assert plan["usable"]
    assert plan["scale"] == pytest.approx(38.7 / 20.0)
    assert plan["width"] == pytest.approx(3840 * plan["scale"], abs=1)
    assert plan["n_positive"] >= 1
    assert plan["orphaned_targets"] == 0


def test_most_tiles_are_negative_which_is_the_gate_headroom(tmp_path):
    """The rejection ceiling comes straight out of the annotations."""
    coco = _coco([_img(1, -90.0)], [_ann(1, 500, 500, 25, 25)])
    p = tmp_path / "a.json"
    p.write_text(json.dumps(coco), encoding="utf-8")
    f = D.select(D.load_split(str(p)))[0][0]
    plan = D.plan_tiles(f, wanted_px=38.7)
    ceiling = 1.0 - plan["n_positive"] / plan["n_tiles"]
    assert ceiling > E.break_even_rejection(E.DOWNSAMPLED, E.cascade_at(640))


# ----------------------------------------------------------------- fetch/verify
from perception.cascade import fetch_data as F  # noqa: E402


def _write_split(tmp_path, name, images, annotations, cats=(("swimmer", 1),)):
    d = tmp_path / "annotations"
    d.mkdir(exist_ok=True)
    p = d / f"instances_{name}.json"
    p.write_text(json.dumps(_coco(images, annotations, cats)), encoding="utf-8")
    return p


def test_verify_accepts_a_well_formed_split(tmp_path, capsys):
    imgs = [_img(i, -90.0 + i) for i in range(20)]
    anns = [_ann(i, 10, 10, 30, 30) for i in range(20)]
    _write_split(tmp_path, "train", imgs, anns)
    assert F.verify(str(tmp_path)) is True
    assert "READY" in capsys.readouterr().out


def test_verify_rejects_a_mirror_with_no_gimbal_metadata(tmp_path, capsys):
    """The failure this script exists to catch: a format conversion that kept
    the boxes and dropped the fields the oblique filter needs."""
    imgs = [{"id": i, "file_name": f"{i}.jpg", "width": 3840, "height": 2160}
            for i in range(20)]
    anns = [_ann(i, 10, 10, 30, 30) for i in range(20)]
    _write_split(tmp_path, "train", imgs, anns)
    assert F.verify(str(tmp_path)) is False
    out = capsys.readouterr().out
    assert "without gimbal pitch" in out and "NOT READY" in out


def test_verify_rejects_missing_person_category(tmp_path, capsys):
    imgs = [_img(i, -90.0) for i in range(5)]
    anns = [_ann(i, 10, 10, 30, 30, cat=7) for i in range(5)]
    _write_split(tmp_path, "train", imgs, anns, cats=(("boat", 7),))
    assert F.verify(str(tmp_path)) is False
    assert "no person-like category" in capsys.readouterr().out


def test_verify_reports_missing_directory(tmp_path):
    assert F.verify(str(tmp_path / "nope")) is False


def test_verify_warns_on_a_truncated_split(tmp_path, capsys):
    """8,930 is the published train size; anything else is a partial download."""
    imgs = [_img(i, -90.0) for i in range(20)]
    _write_split(tmp_path, "train", imgs, [_ann(i, 10, 10, 30, 30) for i in range(20)])
    F.verify(str(tmp_path))
    assert "expected 8,930" in capsys.readouterr().out


# ---------------------------------------------------------------- gate scoring
# The metric logic is testable without torch: it is arithmetic over score lists.
from perception.cascade import gate as GT  # noqa: E402


def test_threshold_is_chosen_by_recall_not_accuracy():
    """96 % of tiles are empty, so accuracy is a useless objective. The
    threshold must be the one that keeps the required fraction of positives."""
    scores = [0.9, 0.8, 0.7, 0.6] + [0.1] * 96
    labels = [1, 1, 1, 1] + [0] * 96
    assert GT.threshold_for_recall(scores, labels, 1.0) == pytest.approx(0.6)
    assert GT.threshold_for_recall(scores, labels, 0.75) == pytest.approx(0.7)


def test_threshold_raises_when_there_are_no_positives():
    with pytest.raises(ValueError):
        GT.threshold_for_recall([0.1, 0.2], [0, 0])


def test_per_target_recall_differs_from_per_tile_recall():
    """A target in two tiles is caught if EITHER fires. Reporting per-tile
    recall would understate the gate; reporting only per-tile would also hide
    a target lost in both."""
    #            t0        t1        t2        t3
    scores = [0.9,      0.2,      0.2,      0.2]
    labels = [1,        1,        1,        0]
    frames = [1, 1, 1, 1]
    # target A appears in tiles 0 and 1; target B only in tile 2
    tids = [[(1, "A")], [(1, "A")], [(1, "B")], []]
    res = GT.evaluate(scores, labels, frames, tids, threshold=0.5)
    assert res["tile_recall"] == pytest.approx(1 / 3)      # 1 of 3 positive tiles
    assert res["target_recall"] == pytest.approx(0.5)      # A found, B lost
    assert res["n_targets"] == 2 and res["targets_missed"] == 1


def test_rejection_counts_all_tiles_not_just_negatives():
    scores = [0.9] + [0.1] * 9
    labels = [1] + [0] * 9
    res = GT.evaluate(scores, labels, [1] * 10, [[(1, "A")]] + [[]] * 9, 0.5)
    assert res["rejection"] == pytest.approx(0.9)
    assert res["target_recall"] == pytest.approx(1.0)


def test_a_gate_that_rejects_everything_fails_on_recall():
    scores = [0.1] * 10
    labels = [1] + [0] * 9
    res = GT.evaluate(scores, labels, [1] * 10, [[(1, "A")]] + [[]] * 9, 0.5)
    assert res["rejection"] == pytest.approx(1.0)
    assert res["target_recall"] == pytest.approx(0.0)
    v = E.verdict(res["rejection"], res["target_recall"], E.DOWNSAMPLED,
                  E.cascade_at(640))
    assert v["cost_ok"] and not v["adopt"], "cheap but blind must not pass"
