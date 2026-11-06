"""Read deployed Pages manifest and compare every declared blob to a fixed Git tree.

This checks manifest metadata for the entire bundle, not HTTP bytes of every file.
Use the separate bounded public-bytes checker for selected actual HTTP transfers.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 384 * 1024 * 1024
MANIFEST_LIMIT = 16 * 1024 * 1024


def need(value, message):
    if not value:
        raise ValueError(message)


def read_manifest_bytes(response):
    raw = response.read(MANIFEST_LIMIT + 1)
    need(len(raw) <= MANIFEST_LIMIT, "Manifest exceeds bounded read")
    return raw


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    need(re.fullmatch("[0-9a-f]{40}", args.source), "Complete fixed source SHA required")
    out = (ROOT / args.output).resolve()
    allowed = ROOT / "reports/pages-deployment"
    need(out.is_relative_to(allowed) and out != allowed and not out.exists(), "Fresh Pages report directory required")
    out.mkdir(parents=True)
    url = "https://tatata93.github.io/pikapikaengine/pages-manifest.json?source=" + args.source
    request = urllib.request.Request(url, headers={"User-Agent": "pikapikaengine-pages-manifest-audit", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = read_manifest_bytes(response)
        headers = dict(response.headers)
        status = response.status
    (out / "pages-manifest.json").write_bytes(raw)
    value = json.loads(raw)
    need(value["schema"] == 1 and value["kind"] == "pikapika-pages-bundle" and value["status"] == "PASS", "Successful bundle schema required")
    need(value["head"] == args.source, "Deployed manifest is not the requested source")
    need(type(value["budgetBytes"]) is int and 0 < value["budgetBytes"] <= LIMIT, "Bounded bundle budget")
    files, excluded = value["files"], value["excluded"]
    need(type(files) is list and type(excluded) is list, "Complete selected/excluded inventory")
    tree = {}
    for row in git("ls-tree", "-rlz", args.source).split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, oid, size = meta.decode().split()
        need(kind == "blob" and mode in ("100644", "100755"), "Only regular tracked blobs supported")
        tree[name.decode("utf-8")] = {"oid": oid, "bytes": int(size)}
    names = set()
    for row in files + excluded:
        name = row["path"]
        need(type(name) is str and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and "\\" not in name and ":" not in name, "Safe manifest path")
        need(name not in names and name in tree, "Unique declared tracked path")
        names.add(name)
        need(row["gitBlob"] == tree[name]["oid"] and type(row["bytes"]) is int and row["bytes"] == tree[name]["bytes"], "Manifest metadata differs from Git: " + name)
    need(names == set(tree), "Manifest inventory must cover the fixed complete tree")
    selected_bytes = sum(row["bytes"] for row in files)
    need(selected_bytes == value["selectedBytes"] and len(files) == value["selectedFiles"], "Selected inventory totals")
    need(len(excluded) == value["excludedFiles"] and sum(row["bytes"] for row in excluded) == value["excludedBytes"], "Excluded inventory totals")
    need(len(tree) == value["trackedFiles"] and sum(row["bytes"] for row in tree.values()) == value["trackedBytes"], "Complete source totals")
    need(selected_bytes + len(raw) <= value["budgetBytes"], "Deployed bundle remains within fixed budget")
    selected_names = {row["path"] for row in files}
    cohort = json.loads(git("show", args.source + ":" + value["cohort"]["path"]))
    preserved = {row["path"] for row in cohort["files"] if row["distribution"] == "pages"}
    need(len(preserved) == 216 and preserved <= selected_names, "All prior accepted Pages paths retained")
    for row in files:
        need(not row["path"].startswith((".git/", ".github/")), "Git metadata must not be published")
    query = ("\n".join(row["gitBlob"] for row in files) + "\n").encode()
    process = subprocess.run(["git", "cat-file", "--batch"], input=query, cwd=ROOT, capture_output=True, check=True)
    data, offset = process.stdout, 0
    for row in files:
        end = data.index(b"\n", offset)
        oid, kind, size = data[offset:end].decode().split()
        size = int(size)
        need(oid == row["gitBlob"] and kind == "blob" and size == row["bytes"], "Git batch blob framing")
        start = end + 1
        blob = data[start:start+size]
        need(hashlib.sha256(blob).hexdigest() == row["sha256"] and data[start+size:start+size+1] == b"\n", "Deployed declared hash differs from Git: " + row["path"])
        offset = start + size + 1
    need(offset == len(data), "Complete Git blob consumption")
    receipt = {"schema": 1, "status": "PASS", "source": args.source, "url": url,
               "httpStatus": status, "headers": headers, "manifestBytes": len(raw),
               "manifestSha256": hashlib.sha256(raw).hexdigest(), "selectedFiles": len(files),
               "selectedBytes": selected_bytes, "bundleBytes": selected_bytes+len(raw),
               "excludedFiles": len(excluded), "excludedBytes": value["excludedBytes"],
               "cohortPagesPreserved": len(preserved), "affectedEvidenceLinks": len(value["linkImpact"]),
               "scope": "Actual HTTP manifest; every declared selected SHA256 and inventory blob compared to fixed Git tree. Not HTTP transfer verification of every selected file; selected real transfers are checked separately."}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k != "headers"}))


if __name__ == "__main__":
    main()
