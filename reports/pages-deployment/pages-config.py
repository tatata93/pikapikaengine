"""Inspect, or switch the existing public Pages site to a committed workflow.

Uses the existing Git credential in memory only. No tokens are printed or saved.
No site creation, billing changes, custom domain changes or credential writes.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "tatata93/pikapikaengine"
API = "https://api.github.com/repos/" + REPOSITORY + "/pages"


def git(*arguments, input=None, env=None):
    result = subprocess.run(["git", *arguments], cwd=ROOT, input=input,
                            capture_output=True, timeout=40, env=env)
    if result.returncode:
        raise RuntimeError("Git operation failed: " + arguments[0])
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--enable-workflow", action="store_true")
    arguments = parser.parse_args()
    output = (ROOT / arguments.output).resolve()
    allowed = ROOT / "reports" / "pages-deployment"
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        raise RuntimeError("Output must be a fresh reports/pages-deployment subdirectory")
    output.mkdir(parents=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    credential = git("credential", "fill", input=(
        "protocol=https\nhost=github.com\npath=" + REPOSITORY + ".git\n\n"
    ).encode(), env=env)
    fields = dict(line.split(b"=", 1) for line in credential.splitlines() if b"=" in line)
    token = fields.get(b"password")
    if not token:
        raise RuntimeError("Existing Git credential unavailable")

    def request(method, body=None):
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "pikapikaengine-pages-configuration",
                   "X-GitHub-Api-Version": "2026-03-10",
                   "Authorization": "Bearer " + token.decode()}
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        with urllib.request.urlopen(urllib.request.Request(
                API, data=data, headers=headers, method=method), timeout=40) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None

    status, before = request("GET")
    (output / "before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
    change_status = None
    if arguments.enable_workflow:
        head = git("rev-parse", "HEAD").strip()
        if head != git("rev-parse", "origin/main").strip():
            raise RuntimeError("Workflow must first be pushed to origin/main")
        workflow = git("show", "HEAD:.github/workflows/pages.yml")
        if b"build/pages-site" not in workflow or b"scripts/build-pages.mjs" not in workflow:
            raise RuntimeError("Committed workflow does not name the reviewed bundle")
        if before.get("build_type") not in ("legacy", "workflow"):
            raise RuntimeError("Unexpected Pages build type")
        if before["build_type"] == "legacy":
            change_status, _ = request("PUT", {"build_type": "workflow"})
            if change_status != 204:
                raise RuntimeError("Unexpected Pages update response")
        _, after = request("GET")
        for key in ("html_url", "cname", "https_enforced", "public"):
            if before.get(key) != after.get(key):
                raise RuntimeError("Unexpected existing site setting change: " + key)
        if after.get("build_type") != "workflow":
            raise RuntimeError("Workflow build type not confirmed")
        (output / "after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
    receipt = {"schema": 1, "timeUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "repository": REPOSITORY, "getStatus": status,
               "beforeBuildType": before.get("build_type"),
               "requestedBody": {"build_type": "workflow"} if arguments.enable_workflow else None,
               "putStatus": change_status,
               "credentialPolicy": "Existing Git credential in memory; no credential output or write"}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        raise SystemExit("Pages API refused request: HTTP " + str(error.code)) from None
    except Exception as error:
        raise SystemExit(type(error).__name__ + ": " + str(error)) from None
