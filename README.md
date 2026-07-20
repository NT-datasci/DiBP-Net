# DiBP-Net: Diagnosing Benchmark Validity in Cuffless Blood Pressure Estimation

Code, trained-model pointers, pre-registration, deviation log, and the complete
before/after audit trail for the paper:

> N. Na Prasit, *DiBP-Net: Diagnosing Benchmark Validity in Cuffless Blood Pressure
> Estimation.* (under review). <!-- TODO: add DOI once published -->

This repository is the reproducibility package. It is deliberately small: the raw
datasets are third-party and public (see [`DATA.md`](DATA.md)) and the trained
checkpoints are archived separately (see [`CHECKPOINTS.md`](CHECKPOINTS.md)).

## What the paper shows

1. **Benchmark validity.** The UCI cuffless-BP corpus ships no patient identifiers;
   its records sit contiguously by patient (adjacent-record SBP r = +0.709) and BP
   is nearly constant within a record (ICC = 0.955), so a corrected block-aware
   split is needed and every UCI accuracy number is an upper bound on across-patient
   performance.
2. **Identifiability.** With only the ODE residual as physical supervision, just
   tau = RC is identifiable; raw compliance C reverses sign across domains while tau
   does not.
3. **Calibration transfer.** The representation transfers across external cohorts;
   the calibration does not. A pre-registered falsification test localises the
   residual external gap to within-session drift of the *label*, not the model.

## Repository layout

```
release/
├── README.md              # this file
├── LICENSE                # MIT (code); dataset licences are separate — see DATA.md
├── requirements.txt       # Python dependencies
├── DATA.md                # how to obtain the public datasets
├── CHECKPOINTS.md         # where the trained weights are archived
├── notebooks/
│   ├── phase0_extract_data.ipynb   # raw signal extraction / windowing
│   ├── phase1_uci.ipynb            # UCI processing, splits, Phase-1 tables
│   ├── phase2_dibpnet.ipynb        # DiBP-Net: definition, training, evaluation
│   └── phase2_pulsedb.ipynb        # PulseDB retrain + split-decomposition control
├── scripts/
│   ├── make_pre_split_blocks.py    # UCI block-aware (guard-band) split + audit
│   ├── presplit_pulsedb.py         # PulseDB subject-level split preparation
│   └── audit_numbers.py            # re-verifies every reported number from source files
└── docs/
    ├── PREREGISTRATION.md          # locked confirmatory endpoint (drift falsification)
    ├── DEVIATION_LOG.md            # every deviation from the pre-registration
    └── AUDIT_MASTER.md             # before/after audit trail of reported numbers
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Tested with Python 3.10+. Training uses PyTorch; a CUDA GPU is recommended for the
Phase-2 notebooks but inference and evaluation run on CPU.

## Reproducing the results

The pipeline runs in order. Each notebook documents its own inputs/outputs at the
top; paths point at the `datasets/` and `outputs/` directories described in
[`DATA.md`](DATA.md) and [`CHECKPOINTS.md`](CHECKPOINTS.md).

1. **`notebooks/phase0_extract_data.ipynb`** — extract and window the raw waveforms.
2. **`notebooks/phase1_uci.ipynb`** — build the UCI splits and Phase-1 tables.
3. **`notebooks/phase2_dibpnet.ipynb`** — train DiBP-Net and produce the main-text
   metrics (beat-level Raw / GCal / SCal MAE, HTN AUC, ablations, latent diagnostics).
4. **`notebooks/phase2_pulsedb.ipynb`** — retrain on PulseDB's genuine patient IDs
   and run the record-vs-subject split decomposition.

Auxiliary:
- `scripts/make_pre_split_blocks.py --dry-run` reproduces the UCI adjacency-leakage
  and guard-band audit (Section 5.1).
- `scripts/audit_numbers.py` re-checks the reported figures against the source CSVs.

## Pre-registration and audit trail

The one confirmatory test — the within-session drift falsification (Section 5.6) —
was pre-registered with a single locked endpoint before any numbers were observed.
`docs/PREREGISTRATION.md` is that document; `docs/DEVIATION_LOG.md` records every
departure from it; `docs/AUDIT_MASTER.md` is the before/after trail for every number
in the manuscript.

## Citation

<!-- TODO(author): replace with the final citation + DOI on acceptance. -->
```bibtex
@article{NaPrasit_DiBPNet,
  title  = {DiBP-Net: Diagnosing Benchmark Validity in Cuffless Blood Pressure Estimation},
  author = {Na Prasit, Natthanan},
  year   = {2026},
  note   = {under review}
}
```

## License

Code is released under the MIT License (see [`LICENSE`](LICENSE)). The datasets are
third-party and retain their own licenses and access terms — see [`DATA.md`](DATA.md).
