# Deviation Log

Append-only. Records every departure from
`PRESPECIFICATION.md` (the locked analysis plan, dated 2026-07-13, fixed before
the corrected external-cohort analysis). The pre-specification itself is **never
edited**; each deviation is recorded here, with its reason, as that document requires.

---

## D1 — BCG is excluded entirely, not retained for cross-sectional analysis

**Pre-specified rule.** §2 stated that an inadmissible cohort is *"not deleted"*
and is *"retained for cross-sectional analyses only"*. §3 permitted a full drop
only if the cohort *"cannot support a cross-sectional analysis either,
operationalised as: fewer than 30 admissible units after de-duplication, or no
definable unit at all."*

**What actually happened.** After re-keying, BCG has 2,469 definable recording
units, which is far above the 30-unit threshold. The pre-specified
operationalisation therefore does **not** trigger a full drop. It nevertheless
turns out that BCG can produce **no cross-sectional result at all**:

- Every cross-sectional quantity we report (the correlation of $R$, $C$, $\tau$
  and $c_{\text{slow}}$ with SBP, and the HTN-2-versus-Normal effect sizes)
  requires the model's Windkessel read-outs, which require a forward pass.
- A forward pass requires an 11-beat input window.
- BCG recordings hold a median of **4** beats and a maximum of **9**. **No
  recording reaches 11 beats.** The pipeline's own window builder reports
  `too few beats/subj — skip`, yielding **0 usable windows** out of 2,469 units.

BCG therefore has zero valid data for *any* analysis in this manuscript, not
merely reduced power.

**Deviation.** BCG is dropped from the manuscript entirely.

**Why the pre-specified threshold was not amended.** The natural temptation is
to shorten the input window for BCG so that it clears the bar, or to rewrite §3's
threshold so that it now excludes BCG cleanly. Both were rejected. Shortening the
window after seeing the result is a design change made to rescue a cohort, and
editing a locked threshold so that it matches an outcome already observed is
rule-bending. Either move is the exact retroactive protocol-fitting this
manuscript exists to criticise, and either would be visible in this repository's
history. The rule stays as written and the gap in it is recorded here instead.

**The condition that should have been pre-specified**, stated now for any future
work, and explicitly **not** applied retroactively as if it had been:

> A cohort with zero model-eligible input windows is excluded regardless of its
> unit count.

This was not anticipated because we did not expect metadata corruption of this
severity: a corpus whose patient and trial fields are both redacted to the
literal string `'X'`, and whose subject grouping in our own pipeline was an
index that restarts every fold.

**What the old BCG numbers actually measured.** Under the previous keying, one
pseudo-subject merged a mean of **3.7 real recordings** (max 5), each carrying a
different BP label, with SBP differing by up to 53 mmHg within a single
pseudo-subject. Every 11-beat window the model consumed for BCG therefore spanned
several unrelated recordings. The contamination was in the model *input*, not
only in the calibration step.

**Consequences.**

- Every BCG number is withdrawn: MAE, AAMI/BHS, Windkessel $r$ and $d$, ICC,
  $V(1)$, drift, re-referencing.
- The **"BCG temporal inversion"** reported as an *unresolved anomaly* is
  withdrawn as a finding. Its cause is identified: the "first three beats" and
  the "last three beats" of a pseudo-subject came from different recordings.
- Cohort counts throughout the manuscript change. Analyses requiring subject
  calibration now run on **PulseDB and Multi-Sensor PPG** (Hospital PPG yields
  `n_eval=0`, as it already did before this audit). Cross-sectional analyses run
  on **PulseDB, Multi-Sensor PPG and Hospital PPG** (73 windows, 53 subjects).
- Every aggregate previously computed over cohorts is recomputed, including the
  external mean SBP MAE and the drift-recovery percentages quoted in the Abstract
  and Conclusion.

---

## D2 — Multi-Sensor PPG re-keying, as pre-specified

Not a deviation; recorded for completeness. §4 committed to adopting the
corrected keying unconditionally and direction-blind. Applied: 2,383 row-index
pseudo-subjects replaced by the **1,195 real patient identifiers** the corpus
ships. As declared in §0, this moves the numbers in a direction that **weakens**
our thesis, and it is reported anyway.
