#!/usr/bin/env python3
"""One-time PulseDB pre-split — run ONCE in a terminal (NOT in Jupyter).

Why: pulsedb_tensors.npz is DEFLATE-compressed, so numpy's mmap_mode="r"
silently falls back to a FULL in-RAM decompression of X_ppg (~8 GB), which
OOM-kills the kernel on any machine without a lot of free RAM.

What this does: streams each array out of the .npz in 16 MB chunks (constant
RAM, never materialising the 8 GB array) and rewrites them as *uncompressed*
.npy files. Uncompressed .npy CAN be memory-mapped, so afterwards
load_pulsedb() opens X_ppg with a real mmap and only the sampled windows
(~320 MB) ever touch RAM.

Usage:
    python3 presplit_pulsedb.py
Then just re-run the notebook normally — load_pulsedb() auto-detects the
uncompressed folder and uses it.
"""
import os
import sys
import zipfile
import numpy as np
from numpy.lib import format as npf

NPZ_PATH = "outputs/phase_1/data/pulsedb_tensors.npz"
OUT_DIR  = "outputs/phase_1/data/pulsedb_uncompressed"
CHUNK    = 16 * 1024 * 1024  # 16 MB


def _read_header(fp):
    """Read a .npy header from a (streaming) file object, return
    (shape, fortran_order, dtype) and leave fp positioned at the data.
    Uses the stable read_array_header_{1,2}_0 API (not private helpers)."""
    major, minor = npf.read_magic(fp)
    if (major, minor) == (1, 0):
        return npf.read_array_header_1_0(fp)
    if (major, minor) == (2, 0):
        return npf.read_array_header_2_0(fp)
    raise ValueError(f"unsupported .npy version {major}.{minor}")


def stream_member(zf, member, out_path):
    """Stream one compressed .npy member -> uncompressed .npy on disk."""
    with zf.open(member) as f:
        shape, fortran, dtype = _read_header(f)
        with open(out_path, "wb") as out:
            npf.write_array_header_2_0(
                out, {"descr": npf.dtype_to_descr(dtype),
                      "fortran_order": fortran, "shape": shape})
            copied = 0
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                copied += len(chunk)
        gb = copied / 1024 ** 3
        print(f"    {member:<20} shape={shape} dtype={dtype}  ({gb:.2f} GB)")


def main():
    if not os.path.exists(NPZ_PATH):
        sys.exit(f"[ERROR] not found: {NPZ_PATH}")
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Streaming {NPZ_PATH}  ->  {OUT_DIR}/")
    with zipfile.ZipFile(NPZ_PATH) as zf:
        members = [m for m in zf.namelist() if m.endswith(".npy")]
        for m in members:
            arr_name = m[:-4]
            out_path = os.path.join(OUT_DIR, arr_name + ".npy")
            stream_member(zf, m, out_path)

    # sanity: mmap X_ppg back to confirm it is now memory-mappable
    xp = os.path.join(OUT_DIR, "X_ppg.npy")
    if os.path.exists(xp):
        mm = np.load(xp, mmap_mode="r")
        print(f"\n  verify: X_ppg mmap OK  shape={mm.shape} dtype={mm.dtype}")
        del mm
    print("\nDONE — re-run the notebook; load_pulsedb() will use the "
          "uncompressed folder automatically (no OOM).")


if __name__ == "__main__":
    main()
