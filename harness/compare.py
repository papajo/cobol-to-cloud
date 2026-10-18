#!/usr/bin/env python3
"""Parity check: compare modern output dir against golden manifest. Exit 1 on any mismatch.

TODO(phase 4): field-level diff using copybook layout when hashes differ.
"""
import hashlib, json, sys
from pathlib import Path

golden, actual = Path(sys.argv[1]), Path(sys.argv[2])
manifest = json.loads((golden / "manifest.json").read_text())
bad = 0
for rel, h in manifest.items():
    f = actual / rel
    if not f.exists():
        print(f"MISSING {rel}"); bad += 1
    elif hashlib.sha256(f.read_bytes()).hexdigest() != h:
        print(f"DIFF    {rel}"); bad += 1
print(f"{len(manifest) - bad}/{len(manifest)} identical")
sys.exit(1 if bad else 0)
