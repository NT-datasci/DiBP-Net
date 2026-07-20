# Datasets

All corpora used in this study are **third-party and publicly available**. None are
redistributed here; obtain each from its original source under its own license.
Full citations are in the manuscript (Section 4, "Dataset and Cohort
Characteristics" and "External Cohorts and Subject Identity").

| Corpus | Role in the paper | Unit | Source |
|---|---|---|---|
| **UCI Cuff-Less BP** | in-domain benchmark (record split) | record (no patient IDs) | Kachuee et al., UCI Machine Learning Repository |
| **PulseDB** | subject-independent evaluation + split decomposition | patient | Wang et al. (2023); derived from MIMIC-III waveform matched subset + VitalDB |
| **Multi-Sensor PPG** | external cohort (calibratable) | patient | Hsieh et al. (2023) |
| **Hospital PPG** | external cohort (cross-sectional only) | patient | cited in manuscript Section 4 |
| **BCG** | considered, then excluded (median 4 beats/recording) | recording | cited in manuscript Section 4 |

> Exact reference entries, versions, and access terms are listed at their point of
> use in the manuscript. Please cite the original dataset papers, not this repository,
> when using the data.

## Expected local layout

The notebooks and scripts expect the raw and processed data under a top-level
`datasets/` directory and write derived artifacts to `outputs/` (both are git-ignored
because of their size — `datasets/` ~3.5 GB, `outputs/` ~32 GB). See the header cell
of each notebook for the exact sub-paths it reads and writes.

```
datasets/          # raw + processed corpora (obtain from sources above)
outputs/           # generated splits, checkpoints, metrics, figures
```

## Notes on identifiers

A central point of the paper is that **UCI ships no patient identifiers**, so its
splits group on the *record*, not the patient. PulseDB, Multi-Sensor PPG, and
Hospital PPG carry genuine patient IDs; BCG's identifier fields are redacted to a
constant. Handle each corpus's unit accordingly — see `scripts/make_pre_split_blocks.py`
(UCI) and `scripts/presplit_pulsedb.py` (PulseDB) for the split logic.
