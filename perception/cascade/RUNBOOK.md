# Stage 1 runbook — download, verify, train, decide

Order matters. Steps 3 and 4 are cheap and can kill the experiment before you
spend GPU hours; do not skip ahead to training because it feels like progress.

---

## 1. Download

**Use the official source, not the Kaggle mirror.**

> https://seadronessee.cs.uni-tuebingen.de/dataset

Take **Object Detection v2**. Registration is required; the test-set ground
truth is withheld, so our held-out evaluation uses the **val** split.

| | |
|---|---|
| Size | ~12.7 GB compressed |
| Contents | 14,227 images — train 8,930 / val 1,547 / test 3,750 |
| Format | COCO JSON |

**Why not Kaggle.** The mirror at `ubiratanfilho/sds-dataset` may be a format
conversion. Our frame selection depends on **per-image gimbal pitch** to
exclude oblique views, and a YOLO-format conversion keeps the boxes and drops
that field. If it is missing, every oblique frame silently enters the training
set and the recall you measure belongs to an easier problem than the one we fly.
Step 3 checks for exactly this — the mirror is fine *if it passes*.

**Download directly onto the GPU machine** if you can. Moving 12.7 GB twice is
an hour you do not need to spend.

---

## 2. Get onto the university GPU

Typical HPC pattern — substitute your cluster's specifics:

```bash
ssh <you>@<gpu-host>
# if the cluster uses SLURM, get an interactive GPU session rather than
# running on the login node (which will get you throttled or killed):
srun --partition=gpu --gres=gpu:1 --cpus-per-task=8 --mem=32G --time=08:00:00 --pty bash
nvidia-smi          # confirm you actually have a device
df -h .             # need ~25 GB: the archive plus its unpacked copy
```

Then get the repo and an environment:

```bash
git clone <this repo> && cd Drikr-NIDAR
python -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install pillow pytest
python -m pytest perception/tests/test_cascade.py -q     # 32 tests, ~1 s
```

If those tests do not pass, stop — the environment is wrong, not the science.

---

## 3. Unzip, then VERIFY before anything else

```bash
mkdir -p data/seadronessee && cd data/seadronessee
unzip ~/seadronessee-odv2.zip          # or tar -xzf, per what you downloaded
cd -

python -m perception.cascade.fetch_data --verify-only --dest data/seadronessee
```

This is the cheapest step and the one most worth reading. It exits non-zero
unless:

- COCO JSON is present (not YOLO `.txt`)
- a person-like category exists — if the class is named something we did not
  anticipate, it prints the real names and you edit `PERSON_CATEGORY_HINTS`
  in `dataset.py`
- **gimbal pitch is present on ≥50% of images** — the check the whole thing
  turns on
- split sizes match 8,930 / 1,547 / 3,750, else it warns of a truncated unpack

**If it fails, do not train.** A number produced from data that cannot support
the oblique filter is not a result.

---

## 4. Stage 0b — the ceiling in the real data (minutes, no GPU)

```bash
python perception/cascade/run_experiment.py \
    --ann data/seadronessee/annotations/instances_train.json
```

Reads annotations only — no images, no model. It reports how many frames
survive selection, and what fraction of tiles are negative.

**Read the last line.** Max rejection is the ceiling a *perfect* gate could
reach. If it is below the **80.5%** break-even, no model can make the cascade
pay and you stop here having spent an afternoon instead of a fortnight.

Our own mission geometry says the ceiling should be ~87–96%. If SeaDronesSee
comes out much lower, that tells you its frames are more crowded than ours —
worth understanding before treating its recall as transferable.

---

## 5. Smoke run (30 minutes)

```bash
python -m perception.cascade.gate \
    --ann   data/seadronessee/annotations/instances_train.json \
    --val-ann data/seadronessee/annotations/instances_val.json \
    --images data/seadronessee/images \
    --input 640 --epochs 1 --limit 2000
```

You are not looking at the verdict here, only that the pipeline moves: tiles
extract, positives are non-zero, loss decreases, a threshold is chosen and a
report prints. `--limit` caps total tiles.

Common failures: `--images` pointing at the wrong level (file names in the JSON
are relative to it), and zero positive tiles (category mapping — go back to
step 3).

---

## 6. Full run (hours)

```bash
python -m perception.cascade.gate \
    --ann   data/seadronessee/annotations/instances_train.json \
    --val-ann data/seadronessee/annotations/instances_val.json \
    --images data/seadronessee/images \
    --input 640 --epochs 8 --seed 0 \
    2>&1 | tee docs/sizing/cascade-stage1-output.txt
```

Use `--input 640`. Gate cost barely moves the break-even (75.3% → 80.5% across
a 16× range), so there is no reason to starve the gate of resolution — and at
160 px input our 39 px target becomes 9.7 px.

`tee` the output: it is evidence, and it belongs in the repo next to the other
committed model outputs.

---

## 7. Read the verdict

`report()` prints both criteria and an explicit ADOPT / DO NOT ADOPT.

**Adopt only if both pass:**

1. rejection ≥ **80.5%**
2. per-**target** recall ≥ **90%**

Ignore per-tile recall — it is printed for diagnosis, not decision. And note
the caveat the report prints: ODv2 has no track IDs, so it cannot show whether
gate failures **correlate** across the twelve looks of a pass. A passing number
here is necessary, not sufficient.

**If it passes**, the prize is the target at **39 px instead of 19 px for the
same compute**, which moves us out of TinyPerson's `tiny3` band where published
AP50 is 29–61%. That is a big enough change to reopen the survey-altitude
decision.

**If it fails on recall**, the cascade is dead in this form — a gate that drops
survivors cannot be fixed by tuning downstream.

**If it fails on rejection only**, it is not dead: try `--input 320`, which
lowers the break-even to 76.4%, and check whether a Stage 0 classical
rejector (contrast/saliency over open water) removes the easy tiles before the
gate ever runs.

---

## 8. Then the measurement this cannot make

Download the **MOT split**, which has track IDs, and measure whether the same
identity is missed across consecutive frames. That is the correlation number
our decision rule assumes the worst about. Until it exists, the worst case is
what we plan against.

---

## Commit the result either way

```bash
git add docs/sizing/cascade-stage1-output.txt
git commit -m "Cascade Stage 1: measured rejection X%, per-target recall Y%"
```

A negative result is worth as much as a positive one here and costs the same to
obtain. It closes a question that is currently open in the proposal.
