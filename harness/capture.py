#!/usr/bin/env python3
"""Capture one legacy job run into golden/<JOB>/ with a sha256 manifest.

Captured: the job's SYSOUT/STDOUT files (STDERR copied for diagnosis but NOT hashed — runtime noise),
flat datasets written during the run (mtime newer than out/legacy/.runstart), and for every KSDS the run
modified, its key-ordered unload from out/legacy/unload/ (BDB files themselves are not byte-stable).
Refuses a run whose MAXCC exceeds --max-rc (default 0), so a broken run never becomes golden.
Usage: capture.py JOB [--max-rc N]
"""
import hashlib, json, shutil, sys
from pathlib import Path

job = sys.argv[1].upper()
max_rc = int(sys.argv[sys.argv.index("--max-rc") + 1]) if "--max-rc" in sys.argv else 0
leg = Path("out/legacy")
rc_file = leg / "sysout" / f"{job}.MAXCC"
if not rc_file.exists():
    sys.exit(f"{job}: no MAXCC recorded — did the run happen?")
rc = int(rc_file.read_text())
if rc > max_rc:
    sys.exit(f"{job}: MAXCC={rc} > {max_rc}; not capturing (see out/legacy/sysout/{job}.*)")
marker = leg / ".runstart"
if not marker.exists():
    sys.exit("no out/legacy/.runstart — run via `make golden JOB=...`")
t0 = marker.stat().st_mtime
catalog = json.loads((leg / "vsam/catalog.json").read_text())
ksds = {Path(k).name for k in catalog}

dst = Path("golden") / job
shutil.rmtree(dst, ignore_errors=True)
manifest, touched_ksds = {}, []
for f in sorted((leg / "sysout").glob(f"{job}.*.txt")):
    manifest[f"sysout/{f.name}"] = f
for f in sorted((leg / "data").iterdir()):
    if f.is_file() and not f.name.startswith(".") and f.stat().st_mtime >= t0:
        base = f.name.rsplit(".", 1)[0] if f.name.rsplit(".", 1)[-1].isdigit() else f.name
        if f.name in ksds or base in ksds:
            touched_ksds.append(base if base in ksds else f.name)
        else:
            manifest[f"data/{f.name}"] = f
missing = []
for k in sorted(set(touched_ksds)):
    u = leg / "unload" / k
    if u.exists() and u.stat().st_mtime >= t0:
        manifest[f"vsam/{k}"] = u
    else:
        missing.append(k)
out = {}
for rel, f in manifest.items():
    t = dst / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, t)
    if not rel.endswith(".STDERR.txt"):
        out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
(dst / "manifest.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"golden/{job}: {len(out)} files")
if missing:
    sys.exit(f"{job}: modified KSDS without fresh unload: {', '.join(missing)} (run make legacy-unload)")
