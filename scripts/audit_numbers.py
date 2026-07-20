#!/usr/bin/env python3
"""Trace every number printed in the manuscript back to a CSV that produced it.

Audits from the side of what is *printed*, not from a list of what we know changed.
That list is memory; this is the fact on the page.

Run from the project root (the directory that holds outputs/), passing the
manuscript source(s) to audit:

    python scripts/audit_numbers.py --tex paper/bspc/_body.tex paper/bspc/_appendix.tex

Verdicts, most severe first:

  STALE     the value is absent from the live outputs but present in the
            pre-fix snapshot (outputs/audit_subject_keying/before/). A number
            that survived the correction. Highest severity: it is not merely
            unverifiable, it is verifiably obsolete.
  ORPHAN    absent from live outputs and from the pre-fix snapshot. Either a
            derived quantity whose formula this script does not know, a figure
            cited from another paper, or an invention. Needs an eyeball.
  COHORT    matches a live value, but the cohort named beside it in the prose is
            not the cohort that value belongs to. This is the p=0.006-in-BCG
            shape of defect: right number, wrong owner.
  OK        matches a live value, cohort consistent (or no cohort named).
  DERIVED   not a literal in any CSV, but reproduced by a mean/difference/percent
            over live values. Treated as OK, listed separately so the formula can
            be spot-checked.
"""
import argparse, csv, glob, itertools, os, re, sys
from collections import defaultdict

ROOT = os.getcwd()   # run from the project root that contains outputs/
LIVE_GLOBS = ["outputs/phase_2_v192/**/*.csv"]
STALE_DIFF = "outputs/audit_subject_keying/diff_before_after.csv"
# per-beat dumps and epoch curves hold ~100k values; at that size any number matches by
# coincidence and the signal dies. Everything else under exports/ is a real results table
# (stage_analysis_test.csv is Table XI's source) and must stay in.
EXCLUDE = ("/hist/", "beats_", "training_history", "manifest", "matched")

COHORTS = {
    "uci": ["uci"],
    "pulsedb": ["pulsedb"],
    "sensors": ["multi-sensor", "multisensor", "sensors"],
    "hospital": ["hospital"],
    "bcg": ["bcg"],
}


def load_csvs(patterns):
    """-> list of (value, file, column, row_label)"""
    out, files = [], []
    for pat in patterns:
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)
    for f in sorted(set(files)):
        if any(e in f for e in EXCLUDE):
            continue
        try:
            rows = list(csv.DictReader(open(f)))
        except Exception:
            continue
        if not rows:
            continue
        keycol = list(rows[0].keys())[0]
        for r in rows:
            label = str(r.get(keycol, ""))
            for col, cell in r.items():
                if cell is None:
                    continue
                # a cell may hold "117.1±15.9" or "[0.83, 0.94]"
                for m in re.finditer(r"-?\d+\.?\d*", str(cell)):
                    try:
                        out.append((float(m.group()), os.path.basename(f), col, label))
                    except ValueError:
                        pass
    return out


def derived_values(vals):
    """Means, differences and percent-drops within one file+column. Covers the
    common 'mean over the two external cohorts' and 'delta' patterns."""
    by = defaultdict(list)
    for v, f, c, l in vals:
        by[(f, c)].append(v)
    out = set()
    for (f, c), vs in by.items():
        vs = [v for v in set(vs) if abs(v) < 1e6]
        if len(vs) > 12:          # avoid combinatorial blowup on long columns
            continue
        for a, b in itertools.combinations(vs, 2):
            out.add(round((a + b) / 2, 4))
            out.add(round(a - b, 4))
            out.add(round(b - a, 4))
            if a:
                out.add(round((a - b) / a * 100, 4))
            if b:
                out.add(round((b - a) / b * 100, 4))
    return out


def strip_tex(s):
    s = s[s.index(r"\begin{document}"):] if r"\begin{document}" in s else s
    s = re.sub(r"(?<!\\)%.*", "", s)                       # comments
    s = s.replace("{,}", ",")                              # LaTeX thin comma: 6{,}305
    s = s.replace("--", " \u2013 ").replace("---", " \u2014 ")   # ranges are not minus signs
    # commands whose arguments are never results
    for cmd in ("cite", "ref", "label", "eqref", "includegraphics", "setlength",
                "setcounter", "renewcommand", "newcommand", "vspace", "hspace",
                "addtolength", "definecolor", "input", "usepackage", "IEEEauthorrefmark",
                "markboth", "hypersetup", "arraystretch", "tabcolsep", "url", "href"):
        s = re.sub(r"\\" + cmd + r"\s*(\[[^\]]*\])?\s*(\{[^{}]*\})+", " ", s)
    s = re.sub(r"\\(begin|end)\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)                     # remaining macros
    return s


# numbers that are configuration or structure, not findings
CONFIG_CTX = re.compile(
    r"batch size|learning rate|lr |weight decay|seed|epoch|dropout|dimension|"
    r"AdamW|Section|Fig\.|Figure|Table|Eq\.|Appendix|\bS\d|\btimes10|10\^",
    re.I)


def audit(texpath, live, stale, derived):
    src = open(texpath).read()
    body = strip_tex(src)
    live_by_val = defaultdict(list)
    for v, f, c, l in live:
        live_by_val[v].append((f, c, l))
    stale_vals = {v for v, *_ in stale}

    findings = []
    for m in re.finditer(r"(?<![\w.])(-?\d+(?:,\d{3})*(?:\.\d+)?)(?![\w])", body):
        raw = m.group(1)
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        lo = max((body.rfind(sep, 0, m.start()) for sep in ("\\\\", ".", ";")), default=-1)
        hi = min((h for h in (body.find(sep, m.end()) for sep in ("\\\\", ".", ";")) if h > 0), default=len(body))
        row = re.sub(r"\s+", " ", body[max(lo + 1, m.start() - 160): min(hi, m.end() + 90)]).strip()
        ctx = re.sub(r"\s+", " ", body[max(0, m.start() - 110):m.end() + 60]).strip()
        # skip structural / config integers
        if val == int(val) and abs(val) <= 30 and not re.search(r"\d\s*(mmHg|%|beats|patients|records|subjects)", ctx):
            continue
        if CONFIG_CTX.search(ctx) and val == int(val):
            continue

        dec = len(raw.split(".")[1]) if "." in raw else 0

        def hits(pool):
            return [x for x in pool if round(x, dec) == val or abs(x - val) <= 0.5 * 10 ** (-dec)]

        lm = hits(live_by_val.keys())
        if lm:
            srcs = [s for h in lm for s in live_by_val[h]]
            # cohort consistency: which cohort does the prose name next to it?
            named = {k for k, kws in COHORTS.items()
                     if any(w in row.lower() for w in kws)}
            if named:
                owned = set()
                for f, c, l in srcs:
                    blob = (f + " " + c + " " + l).lower()
                    for k, kws in COHORTS.items():
                        if any(w in blob for w in kws):
                            owned.add(k)
                    if not any(any(w in blob for w in kws) for kws in COHORTS.values()):
                        owned |= named          # cohort-agnostic source, no claim
                if owned and not (named & owned):
                    findings.append(("COHORT", val, ctx, f"names {sorted(named)}, value lives in {sorted(owned)}"))
                    continue
            findings.append(("OK", val, ctx, srcs[0][0]))
            continue

        if any(round(d, dec) == val or abs(d - val) <= 0.5 * 10 ** (-dec) for d in derived):
            findings.append(("DERIVED", val, ctx, "mean/diff/percent over live values"))
            continue
        if hits(stale_vals):
            findings.append(("STALE", val, ctx, "present only in the PRE-FIX snapshot"))
            continue
        findings.append(("ORPHAN", val, ctx, "not in any live or pre-fix CSV"))
    return findings


ap = argparse.ArgumentParser()
ap.add_argument("--tex", nargs="+", required=True,
                help="manuscript source file(s) to audit against the live CSVs")
a = ap.parse_args()

live = load_csvs(LIVE_GLOBS)
# a value counts as STALE only if the diff says that exact cell moved
stale = []
for r in csv.DictReader(open(os.path.join(ROOT, STALE_DIFF))):
    try:
        stale.append((float(r["before"]), r["file"], r["cell"], r["cell"]))
    except (ValueError, KeyError):
        pass
derived = derived_values(live)
print(f"ground truth : {len({f for _,f,_,_ in live})} live CSVs, {len(live)} values "
      f"(+{len(derived)} derived)\npre-fix      : {len({f for _,f,_,_ in stale})} CSVs, {len(stale)} values\n")

ORDER = ["STALE", "COHORT", "ORPHAN", "DERIVED", "OK"]
grand = defaultdict(int)
for t in a.tex:
    f = audit(os.path.join(ROOT, t), live, stale, derived)
    counts = defaultdict(int)
    for v, *_ in f:
        counts[v] += 1
        grand[v] += 1
    print("=" * 78)
    print(f"{t}   " + "  ".join(f"{k}={counts[k]}" for k in ORDER if counts[k]))
    print("=" * 78)
    for kind in ["STALE", "COHORT", "ORPHAN"]:
        rows = [x for x in f if x[0] == kind]
        if not rows:
            continue
        print(f"\n--- {kind} ({len(rows)}) ---")
        for _, val, ctx, why in rows:
            print(f"  {val:>12}   {why}")
            print(f"               ...{ctx[-105:]}")
    print()
print("TOTAL  " + "  ".join(f"{k}={grand[k]}" for k in ORDER if grand[k]))
