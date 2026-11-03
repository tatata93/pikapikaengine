"""Run actual web build/regressions without changing any authored assets."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
output = root / "reports"


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def assets():
    return {p.relative_to(root).as_posix(): digest(p)
            for p in sorted((root / "assets").rglob("*")) if p.is_file()}


def run(name, arguments):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    result = subprocess.run(arguments, cwd=root, capture_output=True, timeout=600)
    log = output / f"web-cache-{name}.txt"
    log.write_bytes(result.stdout + result.stderr)
    return {"arguments": arguments, "started": started,
            "wallSeconds": time.perf_counter() - clock, "exit": result.returncode,
            "log": log.relative_to(root).as_posix(), **digest(log)}


before = assets()
node = shutil.which("node")
build = run("build", [node, "scripts/build-web.mjs"])
if build["exit"]:
    raise SystemExit("build failed")
with ThreadPoolExecutor(max_workers=2) as executor:
    tests = executor.submit(run, "tests", [node, "--test", "tests/*.test.mjs", "docs/learn/learn.test.mjs"])
    syntax = executor.submit(run, "syntax", [node, "scripts/check.mjs"])
    results = [build, tests.result(), syntax.result()]
after = assets()
assert before == after, "authored assets changed during checks"
sources = ["scripts/build-web.mjs", "tests/web-build.test.mjs"]
report = {"schema": 1, "generated": datetime.now(timezone.utc).isoformat(),
          "status": "PASS" if all(r["exit"] == 0 for r in results) else "FAIL",
          "node": subprocess.check_output([node, "--version"], text=True).strip(),
          "commands": results, "assetsUnchanged": True, "assets": before,
          "sources": {p: digest(root / p) for p in sources}}
(output / "web-cache-local-verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "commands": len(results),
                  "assetsUnchanged": True}))
if report["status"] != "PASS":
    sys.exit(1)
