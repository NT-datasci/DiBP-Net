# Trained checkpoints

The trained DiBP-Net checkpoints (UCI and PulseDB), together with the generated
splits and the metric CSVs behind every table, are **too large for version control**
and are archived on Zenodo:

> **Zenodo archive:** https://doi.org/10.5281/zenodo.21450521

Download the archive and unpack it so that the checkpoint and split files sit under
the `outputs/` directory the notebooks expect (see [`DATA.md`](DATA.md) and each
notebook's header cell for the exact sub-paths).

## What the archive contains

- Trained DiBP-Net weights (UCI `v192`; PulseDB subject-split and record-split controls)
- The seven baseline-encoder checkpoints used in the control experiment (Table 7)
- Pre-computed splits (UCI block-aware guard-band split; PulseDB subject/record splits)
- The per-table metric CSVs re-verified by `scripts/audit_numbers.py`

## Reproducing from scratch instead

If you prefer not to download the checkpoints, run the pipeline end-to-end
(`notebooks/phase0` → `phase1` → `phase2_dibpnet` → `phase2_pulsedb`); training is
seeded, and the reported figures include a 5-seed robustness band
(SBP 4.18 ± 0.05 mmHg).
