#!/usr/bin/env python3
"""Copy a legacy run's output datasets + sysout into golden/<JOB>/ with a sha256 manifest."""
import hashlib, json, shutil, sys
from pathlib import Path

job = sys.argv[1]
src = Path("out/legacy")
dst = Path("golden") / job
if dst.exists():
    shutil.rmtree(dst)
manifest = {}
for sub in ("data", "sysout"):
    for f in sorted((src / sub).glob("*")):
        if f.is_file():
            t = dst / sub / f.name
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)
            manifest[f"{sub}/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
(dst / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"golden/{job}: {len(manifest)} files")
