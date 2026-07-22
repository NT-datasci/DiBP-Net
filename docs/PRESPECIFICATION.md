# Pre-Specification: Cohort Admissibility After the Subject-Keying Audit

**Locked:** 2026-07-13, before re-running any downstream experiment.
**Author:** N. Na Prasit
**Scope:** DiBP-Net manuscript, all external-cohort results.

This document fixes the decision rules *before* the corrected numbers exist, so
that the choice of which cohorts to keep, and in which analyses, cannot be
accused of being tuned to whichever result looks better. It follows the same
discipline as the EXP-R4 pre-specified falsification test already reported in
the manuscript.

---

## 0. What we already know (declared, not hidden)

Honesty requires stating what was observed *during bug diagnosis*, before this
document was written. These facts are already known and are NOT re-decidable:

- `extract_sensors` and `extract_bcg` keyed `subject_ids` on the **row index**,
  not on any patient identifier. `extract_uci` does the same (already disclosed
  in the manuscript). `extract_pulsedb` and `extract_hospital` use genuine IDs.
- Multi-Sensor PPG **does** ship real patient IDs (1,195 patients). The row-index
  keying invented 2,383 pseudo-subjects and split each patient across folds.
- Re-keying Multi-Sensor to real patients moves our one-way ICC(SBP) estimate
  from ~0.19 to **~0.58**. **This weakens our argument**, because it makes an
  external corpus look more label-stable, not less. We commit to reporting it.
- BCG ships `patient` and `trial` **redacted to the literal string `'X'`**. No
  patient identifier exists or can be recovered.
- BCG and Hospital PPG carry **exactly one BP label per unit**: the median and
  maximum within-unit SBP range are both **0.0 mmHg**. They are cross-sectional
  corpora by construction.

What is **not** yet known, and is what these rules govern: every downstream
quantity (MAE, AUC, AAMI/BHS, Windkessel r and d, domain-gap means, drift
correlations, recovery percentages, and all table entries derived from them).

---

## 1. Admissibility rule for *within-session* analyses

An analysis is **within-session** if it requires more than one blood-pressure
observation per unit. This covers: ICC, the semivariogram `V(l)`, within-session
drift (EXP-R4, R4b, R4c), per-subject re-referencing, periodic recalibration, and
subject-level bias correction (SCal).

A cohort is **admissible** for these analyses if and only if it satisfies **both**:

- **(A1) Genuine unit.** The unit is a patient identifier shipped by the source
  distribution. A row index, a fold-local counter, or a redacted field does not
  qualify.
- **(A2) Non-degenerate label.** The **median within-unit SBP range exceeds
  0.5 mmHg**, the resolution of the reference BP device already used as a
  threshold elsewhere in the manuscript.

A cohort failing either test is **inadmissible** for every within-session
analysis. No exceptions, no per-analysis appeals.

## 2. Treatment of an inadmissible cohort

An inadmissible cohort is **not deleted**. It is:

- **Retained** for *cross-sectional* analyses only: correlation of a read-out
  with SBP across units, and between-stage effect sizes. These need one label per
  unit and are therefore valid.
- **Removed** from every within-session table, figure and aggregate, including
  any mean, range or "3 of 4 datasets" style count computed across cohorts. An
  aggregate must not silently include a cohort that is excluded from the analysis
  it aggregates.
- **Labelled** in every table in which it still appears, with its unit
  (`patient` / `recording`) and the fact that it carries one BP label per unit.

## 3. Full-cohort exclusion

A cohort is dropped **entirely** only if it fails (A1) **and** cannot support a
cross-sectional analysis either, operationalised as: fewer than **30 admissible
units** after de-duplication, or no definable unit at all.

## 4. Re-keying is unconditional and direction-blind

Where genuine identifiers exist but were unused (Multi-Sensor PPG), the corrected
keying is adopted **unconditionally**. We commit in advance to reporting the
corrected numbers **whichever direction they move**, including the case, already
observed in §0, where the correction weakens our own thesis. The superseded
row-index numbers are reported only in the audit trail (§6), never as a result.

## 5. Consequences that follow mechanically from these rules

Applying §1 to the facts in §0, *without seeing any new downstream number*:

| Cohort | (A1) genuine unit | (A2) label varies | Within-session | Cross-sectional |
|---|---|---|---|---|
| UCI | ✗ (record index) | ✓ | record-level only, as already disclosed | ✓ |
| PulseDB | ✓ patient | ✓ | **admissible** | ✓ |
| Multi-Sensor PPG | ✓ patient (after re-key) | ✓ | **admissible** | ✓ |
| **BCG** | ✗ redacted | ✗ (range = 0.0) | **INADMISSIBLE** | ✓ (unit = recording) |
| **Hospital PPG** | ✓ patient | ✗ (range = 0.0) | **INADMISSIBLE** | ✓ |

Therefore, **fixed now, before the numbers**:

- Within-session analyses run on **PulseDB and Multi-Sensor PPG only**.
- BCG and Hospital PPG appear **only** in cross-sectional results, each labelled
  with its unit and its one-label-per-unit property.
- The "BCG temporal inversion" reported as *unresolved* in the current manuscript
  is **withdrawn as a finding**. Its cause is identified: the fold-local row
  index collapsed five unrelated recordings into one pseudo-subject, so its
  "first three beats" and "last three beats" came from different recordings. It
  will be reported as a **data-keying artifact**, not a physiological anomaly.
- Any aggregate previously computed over {PulseDB, Multi-Sensor, BCG} is
  recomputed over {PulseDB, Multi-Sensor} and its stated range updated. This
  includes the external-mean SBP MAE, the re-referencing recovery percentage and
  the periodic-update recovery percentage.

## 6. Audit trail

Every number that changes is recorded old-versus-new in
`outputs/audit_subject_keying/` and reported as supplementary evidence, so that
the detection and correction of the defect is inspectable rather than asserted.
Superseded artifacts are preserved as `*.bak-oldsubj`.

---

*Locked before the corrected pipeline was executed. Any deviation from these
rules must be reported as a deviation, with its reason, in the manuscript.*
