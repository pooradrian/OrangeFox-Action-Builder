#!/usr/bin/env python3
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

WS = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
PROBE = WS / "probe"
PROBE.mkdir(exist_ok=True)
TARGETS = ("external/libarchive", "external/libfuse3", "prebuilts/fox-go")


def run(cmd, timeout=300):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    try:
        p = subprocess.run([str(c) for c in cmd], timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("!! TIMEOUT", flush=True)
        return -1
    if p.stdout:
        print(p.stdout[-6000:], flush=True)
    if p.stderr:
        print("STDERR:\n" + p.stderr[-8000:], flush=True)
    print(f"!! exit={p.returncode}", flush=True)
    return p.returncode


print("=== environment ===")
run(["git", "--version"])
run(["df", "-h", str(WS)])

print("\n=== 1. sync script ===")
SYNC = PROBE / "sync"
if not SYNC.exists():
    run(["git", "clone", "--depth", "1", "https://gitlab.com/OrangeFox/sync.git", str(SYNC)])
text = (SYNC / "orangefox_sync.sh").read_text(errors="replace")
lines = text.splitlines()
for i, line in enumerate(lines, 1):
    if re.search(r"SCRIPT_VERSION=|repo (sync|init)|^repo_sync\(\)", line):
        print(f"{i}: {line.rstrip()}")
print("-- 16.0 flow function --")
idx = next((i for i, l in enumerate(lines) if re.match(r"^do_fox_16", l)), None)
if idx is not None:
    print("\n".join(f"{i + 1}: {l}" for i, l in enumerate(lines[idx:idx + 60], idx)))

print("\n=== 2. manifest ===")
MAN = PROBE / "manifest"
if not MAN.exists():
    rc = run(["git", "clone", "--depth", "1", "-b", "fox_16.0",
              "https://gitlab.com/OrangeFox/Manifest.git", str(MAN)])
    if rc != 0:
        run(["git", "clone", "--depth", "1", "https://gitlab.com/OrangeFox/Manifest.git", str(MAN)])

remotes, default = {}, {}
projects = []
for p in sorted(MAN.rglob("*.xml")):
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as e:
        print("skip", p, e)
        continue
    for el in root.iter():
        if el.tag == "remote" and el.get("name"):
            remotes.setdefault(el.get("name"), el.get("fetch"))
        elif el.tag == "default":
            default.setdefault("remote", el.get("remote"))
            default.setdefault("revision", el.get("revision"))
        elif el.tag == "project" and el.get("name"):
            projects.append((p.name, el))

print("-- remotes --")
for k, v in sorted(remotes.items()):
    print(f"{k} -> {v}")
print(f"default: remote={default.get('remote')} revision={default.get('revision')}")

found = []
print("\n-- target entries --")
for src, el in projects:
    if el.get("name") in TARGETS or el.get("path") in TARGETS:
        print(f"[{src}] {ET.tostring(el, encoding='unicode').strip()}")
        found.append(el)
if not found:
    print("NO TARGET ENTRIES FOUND IN MANIFEST")


def url_of(el):
    fetch = el.get("fetch") or remotes.get(el.get("remote") or default.get("remote")) or remotes.get("origin")
    return f"{fetch.rstrip('/')}/{el.get('name')}"


print("\n=== 3. fetch tests ===")
for el in found:
    name = el.get("name")
    rev = el.get("revision") or default.get("revision")
    url = url_of(el)
    print(f"\n### {name} | url={url} | revision={rev}")
    run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}\n", f"{url}/info/refs?service=git-upload-pack"], timeout=60)
    d = PROBE / "t" / name.replace("/", "__")
    if not (d / ".git").exists():
        run(["git", "init", "-q", str(d)])
    run(["git", "-C", str(d), "ls-remote", "--symref", url, "HEAD"], timeout=120)
    if rev and re.fullmatch(r"[0-9a-f]{40}", rev):
        run(["git", "-C", str(d), "fetch", "--no-tags", url, rev], timeout=600)
    else:
        ref = rev if (rev or "").startswith("refs/") else f"refs/heads/{rev or 'HEAD'}"
        if ref == "refs/heads/HEAD":
            ref = "HEAD"
        run(["git", "-C", str(d), "fetch", "--no-tags", "--depth=1", url, f"+{ref}:refs/remotes/probe/deep"], timeout=600)
        run(["git", "-C", str(d), "fetch", "--no-tags", url, f"+{ref}:refs/remotes/probe/full"], timeout=600)

print("\n=== done ===")
