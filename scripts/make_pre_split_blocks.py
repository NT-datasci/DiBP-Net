# ══════════════════════════════════════════════════════════════════════════════
#  make_pre_split_blocks.py — a patient-block-aware split for UCI
# ------------------------------------------------------------------------------
#  WHY THIS EXISTS
#  ---------------
#  The UCI Cuff-Less BP dataset (Kachuee) ships 4 .mat files and NO patient IDs.
#  In phase1.ipynb::extract_uci we therefore set
#        out_subj.append(np.int32(i))          # i = the RECORD index
#  so a "subject" in this project is one of the 12,000 UCI *records*, not a
#  patient. UCI is derived from MIMIC-II, where one patient contributes many
#  records, and those records sit CONTIGUOUSLY in the cell array.
#
#  Measured on outputs/phase_0/data/uci_manifest.csv (2026-07-13):
#      SBP variogram in record-index space, normalised by the total variance
#      (1.0 == statistically independent; random pairs measure 1.002):
#          lag   1 -> 0.318      lag  50 -> 0.858
#          lag   2 -> 0.410      lag 100 -> 0.905
#          lag   3 -> 0.465      lag 200 -> 0.937
#          lag  10 -> 0.646      lag 500 -> 0.949
#      i.e. SBP of adjacent records correlates at r ~ 0.68, decaying to ~0 only
#      after several hundred positions. Adjacent records are the SAME PATIENT.
#
#  Consequence for the ORIGINAL split (GroupShuffleSplit over record id):
#      100.0% of the 1,798 test records have a train record within +/-3 positions
#       90.9% have one IMMEDIATELY adjacent (+/-1)
#      SBP corr(test record, its adjacent train record) = +0.709
#          (vs +0.011 for randomly paired test/train records)
#  The old split prevents RECORD leakage. It does not prevent PATIENT leakage.
#  Every "subject-level" claim we make about UCI is really record-level.
#
#  WHAT THIS SCRIPT DOES
#  ---------------------
#  We cannot recover patient IDs — they do not exist. But we do not need them:
#  patients occupy CONTIGUOUS RUNS of record indices, so we split on contiguous
#  BLOCKS of records and drop a GUARD BAND at every boundary where the two sides
#  land in different splits. Everything else (Q proxy, per-subject baseline, HTN
#  label, 11-beat windowing, metadata) is byte-for-byte the original
#  make_pre_split, so the resulting MAE is directly comparable to the 4.18 mmHg
#  the paper currently reports.
#
#  HONEST LIMITS OF THIS FIX — state these in the paper, do not oversell:
#   1. A guard band REDUCES leakage, it does not prove leakage is zero. With
#      guard=100 the residual adjacent-record correlation is r ~ 0.10 (V=0.905).
#   2. A patient whose records span MORE than one block will still straddle a
#      split boundary if the guard is shorter than their run. Blocks are a
#      heuristic for an unavailable ground truth.
#   3. So the honest claim is "leakage substantially reduced and quantified",
#      never "leakage eliminated".
#
#  HOW TO USE
#  ----------
#      python make_pre_split_blocks.py --dry-run     # audit the split, fast
#      python make_pre_split_blocks.py               # build it (slow)
#  Then in phase2, point DATA_DIR at outputs/phase_1/data/pre_split_blocks and
#  retrain ONE seed. Report BOTH numbers. The difference IS the leakage.
# ══════════════════════════════════════════════════════════════════════════════
import os
import argparse
import numpy as np


def _audit_split(train_rec, val_rec, test_rec, sbp_by_rec, label=""):
    """The same leakage test that condemned the original split, re-run on ours."""
    tr = np.sort(np.asarray(train_rec))
    print(f"\n  ── LEAKAGE AUDIT {label} ──")
    print(f"     train {len(train_rec):,} | val {len(val_rec):,} | test {len(test_rec):,} records")

    # nearest train record to each test record — unbounded, via binary search.
    # (An earlier version capped the search at 400 and then correlated only the
    #  test records that found a neighbour. Once the guard pushes every neighbour
    #  past the cap, that subset collapses to a handful of block-edge records and
    #  the correlation it reports is pure noise. Do not reintroduce the cap.)
    pos   = np.searchsorted(tr, test_rec)
    lo    = tr[np.clip(pos - 1, 0, len(tr) - 1)]
    hi    = tr[np.clip(pos,     0, len(tr) - 1)]
    d_lo, d_hi = np.abs(test_rec - lo), np.abs(test_rec - hi)
    nearest = np.where(d_lo <= d_hi, lo, hi)
    dists   = np.minimum(d_lo, d_hi)
    n = len(dists)

    for k in (1, 3, 10, 50, 100, 200):
        c = int((dists <= k).sum())
        print(f"     test records with a TRAIN record within +/-{k:<3d}: "
              f"{c:>5,} / {n:,}  ({100 * c / n:5.1f}%)")
    print(f"     index distance to nearest train record — "
          f"min {dists.min()}  median {np.median(dists):.0f}  max {dists.max()}")

    a = np.array([sbp_by_rec[r] for r in test_rec])
    b = np.array([sbp_by_rec[r] for r in nearest])
    rng = np.random.default_rng(0)
    print(f"     SBP corr(test rec, its NEAREST train rec) = {np.corrcoef(a, b)[0, 1]:+.3f}"
          f"   [n={n:,}]")
    print(f"       random pairing, for scale                = "
          f"{np.corrcoef(a, rng.permutation(b))[0, 1]:+.3f}")
    print(f"     mean |SBP diff| to nearest train record   = {np.mean(np.abs(a - b)):.2f} mmHg"
          f"   [{len(np.unique(nearest)):,} distinct neighbours]")
    print( "       ^ under a guard band this figure is degenerate: every test record deep")
    print( "         inside a test block shares the same block-edge neighbour, so `b` has")
    print( "         few distinct values and its variance collapses. Judge the split on the")
    print( "         CORRELATION and the DISTANCE, not on this number.")
    print(f"     ── ORIGINAL record-level split, for comparison: 90.9% adjacent, "
          f"r = +0.709 ──")


def make_pre_split_blocks(
    src_path      = "outputs/phase_1/data/universal_tensors_clean.npz",
    manifest_path = "outputs/phase_0/data/uci_manifest.csv",
    out_dir       = "outputs/phase_1/data/pre_split_blocks",
    n_beats       = 10,
    window_stride = 3,
    block_size    = 600,      # records per contiguous block
    guard         = 100,      # records dropped either side of a CROSS-SPLIT boundary
    test_frac     = 0.15,
    val_frac      = 0.15,
    random_state  = 42,
    dry_run       = False,
):
    print("[make_pre_split_blocks] patient-BLOCK-aware split for UCI")
    print(f"  block_size={block_size}  guard={guard}  seed={random_state}")

    raw      = np.load(src_path)
    X_ppg    = raw["X_ppg"]
    Y_abp    = raw["Y_abp"]
    Y_bp     = raw["Y_bp"]
    dur_all  = raw["beat_durations"]
    subj_raw = raw["subject_ids"]        # == UCI RECORD index
    pop_mu   = float(raw["pop_mu"])
    pop_sig  = float(raw["pop_sig"])
    N        = len(X_ppg)
    print(f"  beats={N:,}   pop_mu={pop_mu}   pop_sig={pop_sig}")

    # ── 2. Subject re-indexing — IDENTICAL to make_pre_split, over ALL records,
    #        so subj ids and n_subjects stay compatible with existing checkpoints.
    unique_subjs = np.unique(subj_raw)
    n_subjects   = len(unique_subjs)
    subj_remap   = {s: i for i, s in enumerate(unique_subjs)}
    subj_idx     = np.array([subj_remap[s] for s in subj_raw], dtype=np.int64)
    print(f"  n_subjects(records)={n_subjects:,}   id range 0..{n_subjects-1}")

    # ══ 6'. THE ONLY THING THAT DIFFERS: contiguous BLOCK split + guard band ══
    rng = np.random.default_rng(random_state)

    # Natural hard boundaries: the 4 Part_*.mat files are separate cell arrays,
    # so a patient can never straddle them. Use them as forced block edges.
    part_edges = None
    if os.path.exists(manifest_path):
        import pandas as pd
        man = pd.read_csv(manifest_path)
        parts = man["part"].values
        part_edges = sorted({int(np.where(parts == p)[0].min()) for p in np.unique(parts)})
        print(f"  Part_*.mat boundaries at record idx: {part_edges}")

    # cut [0, max_id] into contiguous blocks, forced to break at part edges
    edges = set(range(0, int(unique_subjs.max()) + block_size, block_size))
    if part_edges:
        edges |= set(part_edges)
    edges = np.array(sorted(edges))

    blocks = []                                   # list of (lo, hi) record-id ranges
    for lo, hi in zip(edges[:-1], edges[1:]):
        recs = unique_subjs[(unique_subjs >= lo) & (unique_subjs < hi)]
        if len(recs):
            blocks.append((lo, hi, recs))
    nb = len(blocks)
    print(f"  {nb} contiguous blocks "
          f"(median {int(np.median([len(b[2]) for b in blocks]))} records each)")

    # assign whole blocks to splits
    order = rng.permutation(nb)
    n_te  = max(1, int(round(test_frac * nb)))
    n_va  = max(1, int(round(val_frac * nb)))
    assign = np.array(["train"] * nb, dtype=object)
    assign[order[:n_te]] = "test"
    assign[order[n_te:n_te + n_va]] = "val"
    print(f"  blocks — train:{(assign=='train').sum()}  "
          f"val:{(assign=='val').sum()}  test:{(assign=='test').sum()}")

    # guard band: drop records within `guard` of a boundary whose neighbour block
    # belongs to a DIFFERENT split. Same-split neighbours need no guard.
    keep = {"train": [], "val": [], "test": []}
    dropped = 0
    for bi, (lo, hi, recs) in enumerate(blocks):
        me = assign[bi]
        left_diff  = bi > 0      and assign[bi - 1] != me
        right_diff = bi < nb - 1 and assign[bi + 1] != me
        # NOTE: we deliberately do NOT exempt Part_*.mat boundaries from the guard.
        # It is tempting to assume no patient spans two .mat files, but nothing in
        # the dataset documents that, and an unverifiable assumption is exactly the
        # kind of thing that put us here. The guard costs ~3 x `guard` records.
        m = np.ones(len(recs), dtype=bool)
        if left_diff:
            m &= (recs >= lo + guard)
        if right_diff:
            m &= (recs < hi - guard)
        dropped += int((~m).sum())
        keep[me].append(recs[m])

    train_rec = np.concatenate(keep["train"]) if keep["train"] else np.array([], int)
    val_rec   = np.concatenate(keep["val"])   if keep["val"]   else np.array([], int)
    test_rec  = np.concatenate(keep["test"])  if keep["test"]  else np.array([], int)
    print(f"  guard band dropped {dropped:,} records "
          f"({100*dropped/n_subjects:.1f}% of the dataset — this is the price of honesty)")

    # ── self-audit: run the exact test that condemned the original split ──────
    if os.path.exists(manifest_path):
        import pandas as pd
        man = pd.read_csv(manifest_path)
        sbp_by_rec = dict(zip(np.arange(len(man)), man["sbp"].values.astype(float)))
        _audit_split(train_rec, val_rec, test_rec, sbp_by_rec, "(BLOCK split)")

    if dry_run:
        print("\n[dry-run] split audited, no windows written. "
              "Re-run without --dry-run to build.")
        return

    # ══ everything below is make_pre_split VERBATIM ═════════════════════════
    print("\n  Computing Q proxy ...")
    ppg = X_ppg[:, 0, :]
    d   = np.gradient(ppg, axis=-1)
    q   = np.maximum(d, 0.0)
    a   = np.trapezoid(q, axis=-1)[..., np.newaxis]
    a   = np.where(a < 1e-6, 1e-6, a)
    Q_all = (q / a * 8.0).astype(np.float32)

    sort_order   = np.argsort(subj_raw, kind="stable")
    sorted_subjs = subj_raw[sort_order]
    first_pos    = np.searchsorted(sorted_subjs, unique_subjs)
    first_idx    = sort_order[first_pos]
    map_vals     = (Y_abp[first_idx].max(axis=-1) + Y_abp[first_idx].min(axis=-1)) / 2.0
    subj_to_base = dict(zip(unique_subjs, map_vals.astype(np.float32)))
    base_all     = np.array([subj_to_base[s] for s in subj_raw], dtype=np.float32)

    sbp_all = Y_bp[:, 0]
    dbp_all = Y_bp[:, 1]
    htn_all = ((sbp_all >= 130) | (dbp_all >= 80)).astype(np.float32)
    dom_all = np.zeros(N, dtype=np.int64)

    tr_idx = np.where(np.isin(subj_raw, train_rec))[0]
    va_idx = np.where(np.isin(subj_raw, val_rec))[0]
    te_idx = np.where(np.isin(subj_raw, test_rec))[0]
    print(f"  beats — train:{len(tr_idx):,}  val:{len(va_idx):,}  test:{len(te_idx):,}")

    half = n_beats // 2

    def _build_windows(beat_idx):
        idx_s  = np.sort(beat_idx)
        X_s, Q_s   = X_ppg[idx_s, 0, :], Q_all[idx_s]
        Yabp_s, Ybp_s = Y_abp[idx_s], Y_bp[idx_s]
        dur_s, htn_s  = dur_all[idx_s], htn_all[idx_s]
        subj_s, dom_s, base_s = subj_idx[idx_s], dom_all[idx_s], base_all[idx_s]

        Xw, Qw, Yaw, Ybpw = [], [], [], []
        durw, htnw, subjw, domw, basew = [], [], [], [], []
        M = len(X_s)
        for i in range(half, M - half, window_stride):
            if subj_s[i - half] != subj_s[i + half]:
                continue
            sl = slice(i - half, i + half + 1)
            Xw.append(X_s[sl]);   Qw.append(Q_s[sl]);   Yaw.append(Yabp_s[sl])
            Ybpw.append(Ybp_s[i]); durw.append(dur_s[i]); htnw.append(htn_s[i])
            subjw.append(subj_s[i]); domw.append(dom_s[i]); basew.append(base_s[i])
        return (np.array(Xw, np.float32), np.array(Qw, np.float32),
                np.array(Yaw, np.float32), np.array(Ybpw, np.float32),
                np.array(durw, np.float32), np.array(htnw, np.float32),
                np.array(subjw, np.int64), np.array(domw, np.int64),
                np.array(basew, np.float32))

    os.makedirs(out_dir, exist_ok=True)
    outs = {}
    for name, idx in (("train", tr_idx), ("val", va_idx), ("test", te_idx)):
        print(f"  Building {name} windows ...")
        outs[name] = _build_windows(idx)
        print(f"    {name} windows: {len(outs[name][0]):,}")

    keys = ["X", "Q", "Yabp", "Ybp", "dur", "htn", "subj", "dom", "base"]
    for name, arrays in outs.items():
        path = os.path.join(out_dir, f"{name}_split.npz")
        np.savez_compressed(path, **dict(zip(keys, arrays)))
        print(f"  Saved {path}  X={arrays[0].shape}")

    sbp_tr, dbp_tr = sbp_all[tr_idx], dbp_all[tr_idx]
    np.savez_compressed(
        os.path.join(out_dir, "split_metadata.npz"),
        pop_mu=np.float32(pop_mu), pop_sig=np.float32(pop_sig),
        sbp_mu=np.float32(sbp_tr.mean()), sbp_sig=np.float32(sbp_tr.std()),
        dbp_mu=np.float32(dbp_tr.mean()), dbp_sig=np.float32(dbp_tr.std()),
        n_subjects=np.int64(n_subjects), n_beats=np.int64(n_beats),
        window_stride=np.int64(window_stride), test_frac=np.float32(test_frac),
        random_state=np.int64(random_state),
        block_size=np.int64(block_size), guard=np.int64(guard),
    )
    print("  Saved split_metadata.npz")
    print("\n[make_pre_split_blocks] Done.")
    print(f"  sbp_mu={sbp_tr.mean():.1f}  sbp_sig={sbp_tr.std():.1f}   "
          f"(original split: 127.9 / 23.2 — a large shift here means the block")
    print( "   assignment drew an unrepresentative train set; re-check before training)")
    print("\n  NEXT: point phase2's DATA_DIR at this directory, retrain ONE seed,")
    print("        and report BOTH numbers. The difference IS the leakage.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="audit the split only, write nothing")
    ap.add_argument("--block-size", type=int, default=600)
    ap.add_argument("--guard", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    make_pre_split_blocks(block_size=a.block_size, guard=a.guard,
                          random_state=a.seed, dry_run=a.dry_run)
