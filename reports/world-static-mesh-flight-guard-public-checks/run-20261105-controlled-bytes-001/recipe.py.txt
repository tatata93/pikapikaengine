"""Compare public distribution bytes with one exact Git commit; no CI/UI claim.

Usage: python public-bytes.py FULL_COMMIT NEW_OUTPUT_DIRECTORY
Only the build-hash reproduction normalizes CRLF. HTTP and blob equality is raw.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import argparse
import json
import re
import runpy
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
EXPECTED_BUILD = '25509ed4cc1d87e4'
REFERENCE = 'reports/accelerated-sphere-box-coverage-recipes/public.py'
ADDITIONS = (
    'core/include/pikapika/world_static_mesh_flight_guard.hpp',
    'core/src/world_static_mesh_flight_guard.cpp',
    'tests/world_static_mesh_flight_guard_tests.cpp',
    'tests/world_static_mesh_flight_guard_fixtures.cpp',
    'tests/world_static_mesh_flight_guard_test_support.hpp',
    'scripts/verify-world-static-mesh-flight-guard.py',
    'tests/world_static_mesh_flight_guard_reference_tests.py',
    'cmake/WorldFlightBinding.cmake',
    'core/src/core.cpp',
    'docs/WORLD_STATIC_MESH_FLIGHT_GUARD.md',
    'docs/WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md',
    'docs/learn/diagrams/world-static-mesh-flight-guard.svg',
    'reports/world-static-mesh-flight-guard-local-verification.json',
    'reports/2026-11-05-world-static-mesh-flight-guard.md',
    'reports/world-static-mesh-flight-guard-primary-sources.json',
    'reports/world-static-mesh-flight-guard-recipes/audit-binding.py',
    'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def valid_path(path):
    require(isinstance(path, str) and path and '\\' not in path and '\x00' not in path,
            'Invalid repository path')
    parsed = PurePosixPath(path)
    require(not parsed.is_absolute() and str(parsed) == path and
            all(part not in ('.', '..') for part in parsed.parts) and
            re.fullmatch(r'[A-Za-z0-9_.\-/]+', path), 'Unsafe repository path: ' + path)
    return path


class Git:
    def __init__(self, commit, out):
        self.commit, self.out, self.commands, self.tree, self.cache = commit, out, [], {}, {}

    def run(self, args):
        command = ['git', *args]
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row = {'argv': command, 'cwd': str(ROOT), 'exitCode': completed.returncode,
               'stdout': identity(completed.stdout), 'stderr': identity(completed.stderr),
               'stderrText': completed.stderr.decode('utf-8', errors='replace')}
        self.commands.append(row)
        require(completed.returncode == 0, 'Git command failed: ' + repr(command))
        return completed.stdout

    def initialize(self):
        require(self.run(['rev-parse', self.commit + '^{commit}']).decode().strip() == self.commit,
                'Exact commit not found')
        raw = self.run(['ls-tree', '-r', '-l', '-z', self.commit])
        (self.out / 'git-tree.raw').write_bytes(raw)
        for record in raw.split(b'\0'):
            if not record:
                continue
            meta, name = record.split(b'\t', 1)
            mode, kind, oid, size = meta.decode('ascii').split()
            path = name.decode('utf-8')
            self.tree[path] = {'mode': mode, 'type': kind, 'oid': oid,
                               'bytes': int(size) if size != '-' else None}

    def blob(self, path):
        valid_path(path)
        require(path in self.tree, 'Missing commit path: ' + path)
        entry = self.tree[path]
        require(entry['type'] == 'blob' and entry['mode'] in ('100644', '100755') and
                entry['bytes'] <= MAX_FILE, 'Non-file/oversized blob: ' + path)
        if path not in self.cache:
            data = self.run(['cat-file', 'blob', entry['oid']])
            require(len(data) == entry['bytes'], 'Git blob size mismatch')
            self.cache[path] = data
        return self.cache[path]


def build_cohort(git):
    builder = git.blob('scripts/build-web.mjs').decode('utf-8')
    # Reproduce this pinned builder family, rather than guessing a future format.
    for literal in ("['engine','samples','tools','docs/learn','assets']",
                    "...modules,'style.css','assets/pikapika-core.wasm','assets/pikapika-simulation.wasm'",
                    ".replaceAll('\\r\\n','\\n')"):
        require(literal in builder, 'Unrecognized build-web hash contract: ' + literal)
    modules = []
    for directory in ('engine', 'samples', 'tools', 'docs/learn', 'assets'):
        modules.extend(sorted(path for path in git.tree if str(PurePosixPath(path).parent) == directory
                              and path.endswith('.mjs') and not path.endswith('.test.mjs')))
    assets = sorted(path for path in git.tree if str(PurePosixPath(path).parent) == 'assets'
                    and re.search(r'\.(json|scene)$', path))
    require(len(modules) == 54, 'Expected 54 builder modules')
    match = re.search(r"for\(const \[file,prefix,entry\]of \[(.*?)\]\)\{", builder, re.S)
    require(match is not None, 'Builder HTML entry list missing')
    triples = re.findall(r"\['([^']+)','([^']+)','([^']+)'\]", match[1])
    reconstructed = ','.join("['%s','%s','%s']" % triple for triple in triples)
    require(reconstructed == match[1] and len(triples) == 26 and
            len({triple[0] for triple in triples}) == 26, 'Builder HTML entries not exactly parsed')
    inputs = [*modules, 'style.css', 'assets/pikapika-core.wasm', 'assets/pikapika-simulation.wasm', *assets]
    digest, rows = sha256(), []
    for path in inputs:
        raw = git.blob(path)
        hashed = raw if path.endswith('.wasm') else raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8')
        digest.update(path.encode('utf-8'))
        digest.update(hashed)
        rows.append({'path': path, 'raw': identity(raw), 'hashInput': identity(hashed)})
    full = digest.hexdigest()
    require(full[:16] == EXPECTED_BUILD, 'Commit build hash differs: ' + full[:16])
    for file, prefix, entry in triples:
        html = git.blob(file).decode('utf-8')
        maps = re.findall(r'<script type="importmap" id="engine-imports">(.*?)</script>', html, re.S)
        require(len(maps) == 1, 'Expected unique engine-imports: ' + file)
        expected = {'imports': {prefix + path: prefix + path + '?build=' + EXPECTED_BUILD for path in modules}}
        require(json.loads(maps[0]) == expected, 'Commit import-map cohort differs: ' + file)
        require('<script type="module" src="' + entry + '?build=' + EXPECTED_BUILD + '"></script>' in html,
                'Commit module entry differs: ' + file)
    return {'build': full[:16], 'sha256': full, 'moduleCount': len(modules),
            'entryCount': len(triples), 'modules': modules, 'entries': [x[0] for x in triples],
            'assetData': assets, 'hashInputs': rows}


class Transfers:
    def __init__(self, out, commit, expected):
        self.out, self.commit, self.expected = out, commit, expected
        self.lock, self.total = threading.Lock(), 0

    def read(self, response, requested):
        # Reserve before I/O, so concurrent responses cannot exceed the shared
        # download-body budget even when an unexpected response is enormous.
        with self.lock:
            allowed = min(requested, MAX_TOTAL - self.total)
            require(allowed > 0, 'HTTP total reaches 64 MiB')
            self.total += allowed
        try:
            chunk = response.read(allowed)
        except Exception:
            # Keep the full grant charged on an unknown partial-read failure.
            raise
        with self.lock:
            self.total -= allowed - len(chunk)
        return chunk

    def fetch(self, path):
        channel = 'github-source' if path == '.github/workflows/verify.yml' else 'pages'
        quoted = urllib.parse.quote(path, safe='/')
        url = ('https://raw.githubusercontent.com/tatata93/pikapikaengine/' + self.commit + '/' + quoted
               if channel == 'github-source' else 'https://tatata93.github.io/pikapikaengine/' + quoted +
               '?build=' + EXPECTED_BUILD + '&v=' + self.commit)
        row = {'path': path, 'url': url, 'distribution': channel, 'expected': identity(self.expected[path])}
        raw = bytearray()
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'pikapikaengine-exact-commit-byte-verification',
                                                          'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
            try:
                response = urllib.request.urlopen(request, timeout=40)
            except urllib.error.HTTPError as error:
                response = error  # Preserve error status, headers and bounded body too.
            with response:
                row.update(httpStatus=response.status, finalURL=response.geturl(),
                           headers=list(response.headers.items()))
                length = response.headers.get('Content-Length')
                if length is not None:
                    require(0 <= int(length) <= MAX_FILE, 'HTTP Content-Length exceeds per-file limit')
                while True:
                    if len(raw) == MAX_FILE:
                        require(not self.read(response, 1), 'HTTP body exceeds 16 MiB')
                        break
                    chunk = self.read(response, min(65536, MAX_FILE - len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
                require(response.status == 200, 'HTTP status is not 200')
                require(bytes(raw) == self.expected[path], 'Public bytes differ from exact Git blob')
            row['status'] = 'PASS'
        except Exception as error:
            row.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
        destination = self.out / 'http' / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        row.update(actual=identity(raw), rawPath=destination.relative_to(self.out).as_posix())
        metadata = self.out / 'http-metadata' / (path + '.json')
        metadata.parent.mkdir(parents=True, exist_ok=True)
        write_json(metadata, row)
        return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('commit')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{40}', args.commit), 'A full lowercase commit SHA is required')
    out = args.output.resolve()
    require(out.is_relative_to(ROOT) and out != ROOT, 'Fresh output must be within this repository')
    out.mkdir(parents=True, exist_ok=False)
    recipe = Path(__file__).read_bytes()
    (out / 'recipe.py.txt').write_bytes(recipe)
    write_json(out / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()),
                                       'started': datetime.now(timezone.utc).isoformat(), 'recipe': identity(recipe)})
    git, result = Git(args.commit, out), {'schema': 1, 'status': 'FAIL', 'commit': args.commit,
        'scope': 'Exact-commit public distribution bytes only. No GNU CI, UI operation, numerical query, or World advance acceptance.'}
    try:
        git.initialize()
        reference = git.blob(REFERENCE)
        reference_copy = out / 'reference-public.py.txt'
        reference_copy.write_bytes(reference)
        namespace = runpy.run_path(str(reference_copy), run_name='public_bytes_reference_only')
        prior = namespace['PATHS']
        require(type(prior) is tuple and len(prior) == len(set(prior)) == 113, 'Expected reference PATHS113')
        cohort = build_cohort(git)
        paths = sorted(set((*prior, *ADDITIONS, *cohort['modules'], *cohort['entries'],
                            *cohort['assetData'], 'style.css', 'assets/pikapika-core.wasm', 'assets/pikapika-simulation.wasm')))
        expected = {valid_path(path): git.blob(path) for path in paths}
        require(sum(map(len, expected.values())) <= MAX_TOTAL, 'Expected cohort exceeds total limit')
        write_json(out / 'reference.json', {'path': REFERENCE, 'commit': args.commit, **identity(reference),
                                           'blob': git.tree[REFERENCE], 'loadedWithoutMain': True})
        write_json(out / 'cohort.json', cohort)
        write_json(out / 'git-blobs.json', [{'path': path, **git.tree[path], **identity(expected[path])} for path in paths])
        transfers = Transfers(out, args.commit, expected)
        with ThreadPoolExecutor(max_workers=4) as executor:
            files = list(executor.map(transfers.fetch, paths))
        failed = [row['path'] for row in files if row['status'] != 'PASS']
        result.update(status='FAIL' if failed else 'PASS', build=cohort['build'], files=files,
                      failedPaths=failed, fileCount=len(files), bytes=sum(row['actual']['bytes'] for row in files),
                      channels={'pages': sum(row['distribution'] == 'pages' for row in files),
                                'githubSource': sum(row['distribution'] == 'github-source' for row in files)},
                      limits={'perFileBytes': MAX_FILE, 'totalHTTPBytes': MAX_TOTAL, 'parallelRequests': 4})
        require(Path(__file__).read_bytes() == recipe, 'Recipe changed during observation')
    except Exception as error:
        result.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
    finally:
        write_json(out / 'git-commands.json', git.commands)
        result['finished'] = datetime.now(timezone.utc).isoformat()
        write_json(out / 'receipt.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'commit', 'build', 'fileCount', 'bytes', 'channels', 'failedPaths', 'error') if key in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
