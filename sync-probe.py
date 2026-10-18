#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

WS = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
PROBE = WS / "probe3"
PROBE.mkdir(exist_ok=True)


def run(cmd, timeout=600, maxout=14000):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    try:
        p = subprocess.run([str(c) for c in cmd], timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("!! TIMEOUT", flush=True)
        return ""
    out = p.stdout or ""
    if out:
        print(out[-maxout:], flush=True)
    if p.stderr:
        print("STDERR:\n" + p.stderr[-maxout:], flush=True)
    print(f"!! exit={p.returncode}", flush=True)
    return out


def sh(cmd, timeout=300):
    return run(["bash", "-c", cmd], timeout=timeout)


print("=== A. upstream OrangeFox Manifest history ===")
MAN = PROBE / "man"
if not (MAN / ".git").exists():
    run(["git", "clone", "https://gitlab.com/OrangeFox/Manifest.git", str(MAN)])
run(["git", "-C", str(MAN), "log", "--oneline", "-20", "origin/fox_16.0"])
print("-- sepolicy pin changes in history --")
sh(f"git -C {MAN} log --oneline -S 'system/sepolicy' origin/fox_16.0 | head -15")
print("-- eb1e5d7 stat --")
run(["git", "-C", str(MAN), "show", "--stat", "eb1e5d7"], maxout=6000)
print("-- eb1e5d7 full diff (small files only) --")
sh(f"git -C {MAN} show eb1e5d7 -- fox.xml twrp-default.xml | head -120")
print("-- commits between 4c65ca2 and eb1e5d7 --")
sh(f"git -C {MAN} log --oneline 4c65ca2..eb1e5d7 2>/dev/null | head -20")

print("\n=== B. system/sepolicy entry in the pinned snapshot (4c65ca2) ===")
sh(f"git -C {MAN} show 4c65ca2:twrp-default.xml | grep -n -B2 -A2 sepolicy")
sh(f"git -C {MAN} show 4c65ca2:default.xml | grep -n 'system/sepolicy'")
sh(f"git -C {MAN} show 4c65ca2:remove-minimal.xml | grep -n 'system/sepolicy'")
print("-- same grep at eb1e5d7 (upstream head) --")
sh(f"git -C {MAN} show eb1e5d7:twrp-default.xml 2>/dev/null | grep -n -B2 -A2 sepolicy")
sh(f"git -C {MAN} show eb1e5d7:default.xml 2>/dev/null | grep -n 'system/sepolicy'")

print("\n=== C. OrangeFox system/sepolicy fork ===")
SEP = PROBE / "sep"
if not (SEP / ".git").exists():
    run(["git", "clone", "https://gitlab.com/OrangeFox/system/sepolicy.git", str(SEP)], timeout=900)
run(["git", "-C", str(SEP), "log", "--format=%h %cI %s", "-25", "origin/fox_16.0"], maxout=8000)
print("-- history of the hwcrypto vendor file --")
sh(f"git -C {SEP} log --format='%h %cI %s' -- vendor/hal_hwcrypto_default.te | head -15")
print("-- history of public/attributes around gates --")
sh(f"git -C {SEP} log --format='%h %cI %s' -5 -- public/attributes")
print("-- current branch head: does the vendor file exist + gated? --")
sh(f"git -C {SEP} show origin/fox_16.0:vendor/hal_hwcrypto_default.te 2>&1 | head -20")
print("-- current head: hwcrypto gates in public/attributes --")
sh(f"git -C {SEP} show origin/fox_16.0:public/attributes | grep -n -B4 -A8 hwcrypto | head -40")

print("\n=== D. build/release flags for bp1a (AOSP android-16.0.0_r1) ===")
REL = PROBE / "rel"
if not (REL / ".git").exists():
    run(["git", "clone", "--depth", "1", "-b", "android-16.0.0_r1",
         "https://android.googlesource.com/platform/build/release", str(REL)], timeout=600)
sh(f"ls {REL}/flag_values/ 2>/dev/null; echo ---; ls {REL}/flag_values/bp1a 2>/dev/null | grep -i board; echo '-- value file if present --'; cat {REL}/flag_values/bp1a/RELEASE_BOARD_API_LEVEL.textproto 2>/dev/null; echo '-- declaration --'; cat {REL}/flag_declarations/RELEASE_BOARD_API_LEVEL.textproto 2>/dev/null")

print("\n=== done ===")
