#!/usr/bin/env python3
import subprocess
from pathlib import Path
import os

WS = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
REL = WS / "rel"


def run(cmd, timeout=600):
    print(f"$ {' '.join(map(str, cmd))}", flush=True)
    p = subprocess.run([str(c) for c in cmd], timeout=timeout, capture_output=True, text=True)
    print(p.stdout[-4000:], flush=True)
    if p.stderr:
        print("STDERR:", p.stderr[-2000:], flush=True)


if not (REL / ".git").exists():
    run(["git", "clone", "--depth", "1", "-b", "android-16.0.0_r1",
         "https://android.googlesource.com/platform/build/release", str(REL)])

for rel_name in ["bp1a", "bp2a"]:
    print(f"\n=== {rel_name} ===")
    run(["bash", "-c",
         f"ls {REL}/flag_values/{rel_name} | grep -i board; echo '---'; "
         f"cat {REL}/flag_values/{rel_name}/RELEASE_BOARD_API_LEVEL.textproto 2>/dev/null || echo 'NO FILE'"])
