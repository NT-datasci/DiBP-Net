# Audit Master Reference: Subject-Keying Defect

Single source of truth for every number that moved. Written **before** any
manuscript prose was edited, so that the rewrite reads off this table rather than
re-deriving numbers five times.

Companion documents:
- `PRESPECIFICATION.md` (locked analysis plan, dated 2026-07-13)
- `DEVIATION_LOG.md` (append-only)
- `outputs/audit_subject_keying/` (before/ snapshot, bug_evidence.json, diff)

---

## 1. The defect

`phase1.ipynb` assigned `subject_ids` from the **row index** in three extractors:

| extractor | key | genuine? |
|---|---|---|
| `extract_uci` | `np.int32(i)` | no, record index (already disclosed in the manuscript) |
| `extract_sensors` | `np.int32(i)` | **no** — the corpus ships 1,195 real `patient` IDs that were ignored |
| `extract_bcg` | `np.int32(i)` | **no** — `patient` and `trial` are redacted to the literal `'X'` |
| `extract_hospital` | `int(df_meta["subject_ID"])` | yes |
| `extract_pulsedb` | `subj_hash` | yes |

**Mechanism.** In `extract_sensors` and `extract_bcg` the index `i` **restarts at
0 on every fold**. Rows sharing an index across folds were therefore merged into
one pseudo-subject. For BCG a pseudo-subject spanned a mean of **3.7 unrelated
recordings** (max 5), with SBP differing by up to **53 mmHg** inside a single
"subject". Because the model consumes 11-beat windows keyed on `subject_ids`, the
contamination reached the model **input**, not merely the calibration step.

**Second, independent property.** BCG and Hospital PPG carry exactly **one BP
label per unit** (within-unit SBP range = 0.0 mmHg, median and max). They are
cross-sectional corpora by construction and cannot support any within-session
analysis, whatever the keying.

## 2. Cohort status after the fix

| cohort | unit | units | model windows | MAE / calibration | cross-sectional |
|---|---|---|---|---|---|
| UCI | record | 11,967 | yes | yes (upper bound) | yes |
| PulseDB | patient | 2,845 | yes | **yes** | yes |
| Multi-Sensor PPG | patient (**re-keyed**) | 2,383 → **1,195** | 14,828 (1,027 subj) | **yes** | yes |
| Hospital PPG | patient | 219 | 73 (53 subj) | no (`n_eval=0`) | yes |
| **BCG** | recording | 671 → 2,469 | **0** (median 4 beats, max 9; needs 11) | **dropped** | **dropped** |

**Cohort counts are context-dependent and must not be stated as one number:**
MAE/AAMI/calibration runs on **2** external cohorts; cross-sectional analyses run
on **3**.

---

## 3. Every number that moved

### 3.1 Headline (Abstract, Intro, Contributions, Conclusion)

| quantity | old | **new** | note |
|---|---|---|---|
| mean external SBP MAE | 20.1 | **18.7** | mean of {PulseDB 20.91, Multi-Sensor 16.42} |
| external ratio vs UCI | 3.8–5.6× | **3.9–5.0×** | |
| continuous re-referencing recovery | 31–39% | **31–32%** | PulseDB 31.4, Multi-Sensor 32.4 |
| deployable 15 s recovery | 3–11% | **7–11%** | Multi-Sensor 7.4, PulseDB 11.0 |
| "four external cohorts" | 4 | **2 (MAE) / 3 (cross-sectional)** | |

### 3.2 §V-A and Table III

| quantity | old | **new** |
|---|---|---|
| ICC(SBP) UCI | 0.955 | 0.955 (unchanged) |
| ICC(SBP) PulseDB | 0.425 | 0.425 (unchanged) |
| **ICC(SBP) Multi-Sensor** | **0.279** | **0.625** |
| ICC(SBP) BCG | 0.150 | **row removed** |
| V(1) UCI | 0.03 | 0.03 |
| V(1) PulseDB | 0.53 | 0.53 |
| **V(1) Multi-Sensor** | **0.54** | **0.15** |
| V(1) BCG | 1.08 | **row removed** |
| **V(1) separation** | **18–36×** | **5–18×** |

**These two rows weaken our own argument** and are reported as such, per
pre-specification §4. The UCI-versus-external gap narrows but does not close:
0.955 against 0.425–0.625, still a factor of 1.5 to 2.2.

### 3.3 §V-C and Table VI (AAMI/BHS, beat-level SCal)

BCG rows removed entirely. Multi-Sensor recomputed.

| row | MAE | ME | SD | ≤5 | ≤10 | ≤15 | AAMI | BHS |
|---|---|---|---|---|---|---|---|---|
| UCI SBP | 4.20 | +0.17 | 6.89 | 73.8 | 90.9 | 96.2 | PASS | A |
| UCI DBP | 2.56 | +0.03 | 4.06 | 86.3 | 96.9 | 99.2 | PASS | A |
| PulseDB SBP | 20.91 | +0.80 | 27.91 | 18.3 | 34.3 | 47.7 | FAIL | D |
| PulseDB DBP | 11.84 | +1.07 | 15.96 | 31.1 | 54.7 | 71.1 | FAIL | D |
| **Multi-Sensor SBP** | **16.42** | **−1.90** | **21.76** | **23.5** | **41.8** | **56.0** | FAIL | D |
| **Multi-Sensor DBP** | **8.39** | **−0.49** | **11.37** | **42.9** | **68.1** | **82.5** | FAIL | D |

(old Multi-Sensor: SBP 23.46 / DBP 11.67; old BCG: SBP 16.02 ME +8.66, DBP 16.25 ME +14.72)

Other §V-C items:
- UMAP overlap ratio: 1.07–1.65 → **1.45–1.99**
- Subject-bias gain: PulseDB 1.98 (unchanged), Multi-Sensor 3.36 → **3.21**;
  the BCG case where SCal *increased* error by 0.91 mmHg is **withdrawn**, and with
  it the "ballistocardiographic modality" explanation, which was factually wrong:
  the BCG corpus feeds **PPG** to the model (its feature file is entirely
  `ppg_*`, `vpg_*`, `apg_*` columns).

### 3.4 §V-D and Table VII (cross-domain Windkessel)

| cohort | `c_slow` r | `c_slow` d | raw `C` r |
|---|---|---|---|
| UCI (test) | 0.885 | 3.024 | **−0.381** |
| PulseDB | 0.589 | 1.822 | **+0.188** |
| **Multi-Sensor** | **+0.562** (was −0.005) | **1.542** (was 0.019) | **+0.227** (was −0.050) |
| Hospital PPG | 0.871 | 2.525 | −0.099 |
| BCG | — | — | **row removed** |

**The "Multi-Sensor anomaly" does not exist.** The paragraph stating that
*"the Multi-Sensor PPG dataset presents an anomaly, with all four quantities
collapsing near zero (|r|<0.01)"* described the subject-keying defect, not the
data. Multi-Sensor now behaves like PulseDB.

**The core identifiability finding survives and is stronger.** Raw `C` reverses
sign between UCI (−0.381) and **both** externals (+0.188, +0.227), while
`c_slow`, `R` and `τ` do not. The old caveat "preserved across three of four
external datasets (Multi-Sensor excepted)" is deleted: there is now **no
exception**.

### 3.5 §V-E and Table VIII (static recalibration)

| candidate | baseline | after | Δ |
|---|---|---|---|
| moment-matched features | 18.66 | 18.52 | −0.14 |
| output quantile mapping | 18.66 | 18.80 | +0.15 |
| **supervised in-domain refit (70% labels)** | 18.66 | **17.82** | **−0.84** (was −0.53) |

The conclusion is unchanged and slightly stronger in absolute terms: no static
remedy closes a gap of roughly 14 mmHg, even one handed 70% of the target labels.

### 3.6 §V-F (pre-specified drift test) — **role changes**

| Multi-Sensor `c_slow` vs SBP | old | **new** |
|---|---|---|
| full-session | **−0.018** (the "collapse") | **+0.537** |
| first-3 beats | +0.182 | **+0.686** |

The collapse the test was designed to explain **never happened**. What survives,
and is now consistent across both admissible cohorts rather than rescued by one:

| cohort | full-session | first-3 | Δ |
|---|---|---|---|
| PulseDB | 0.591 | 0.835 | **+0.244** |
| Multi-Sensor | 0.537 | 0.686 | **+0.149** |

The 3×3 window grid still shows the same signature in both: the correlation moves
when the **SBP** window moves and barely moves when the **parameter** window
moves. The label wanders; the read-out does not.

**The BCG temporal inversion is withdrawn.** Its "first three beats" and "last
three beats" came from different recordings.

### 3.7 §VI-C and drift-recovery statistics

| quantity | old | **new** |
|---|---|---|
| N subjects | 5,090 | **3,538** |
| drift slope | 0.595 mmHg/beat | **0.365** |
| MAE reduction (static → rolling) | 7.55 mmHg | **6.35** |
| paired t | 49.1 | **35.2** |
| Cohen's d_z | 0.69 | **0.59** |
| power | >0.999 | >0.999 (unchanged) |

### 3.8 Supplementary

- **S1** (PulseDB subgroup): unchanged (PulseDB was never affected). Now backed by
  `exp8_pulsedb_subgroup.csv`.
- **S2** (periodic recalibration): BCG row removed; PulseDB 31.4% / 11.0%,
  Multi-Sensor 32.4% / 7.4%. Now backed by `exp_periodic_recalibration.csv`.
- **S3** (selection bias): **Multi-Sensor inclusion falls from 95.4% to 70.2%**
  (721 of 1,027). The ≥11-beat cohort now covers only seven real patients in ten,
  a genuine generalisability caveat that the pseudo-subject keying had hidden.
  Max |g| across cohorts: 0.36. BCG row removed.
- **S4** (stage recovery): Multi-Sensor 28.3–35.1%, PulseDB 29.6–40.2%.
  Overall 28.3–40.2% (was 29.6–42.2%). BCG row removed.

---

## 4. What weakens, stated plainly

Two results move against us and are reported without dilution:

1. **The ICC gap narrows.** UCI 0.955 against externals 0.42–0.63, not 0.15–0.43.
   Multi-Sensor's label is more stable within a real patient than the
   pseudo-subject keying made it look. The claim that UCI's BP is "nearly a
   per-record constant" still holds; the claim that external corpora "collapse"
   to a low ICC does not, and the wording must come down.
2. **The V(1) separation shrinks from 18–36× to 5–18×.**

Neither reverses the argument. Both must be visible in the manuscript rather than
absorbed silently.

## 5. What strengthens

- Two fabricated anomalies (BCG inversion, Multi-Sensor collapse) are removed,
  and with them two passages of hand-waving.
- The `C` sign reversal now holds in **every** admissible external cohort, with no
  exception to explain away.
- The drift signature is **consistent across both cohorts** instead of being
  confirmed in one and contradicted in another.
- The manuscript can demonstrate, on its own data, the exact failure mode it
  exists to expose, and can show the audit trail that caught it.
