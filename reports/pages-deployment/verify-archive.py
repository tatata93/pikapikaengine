"""Verify the actual uncompressed Pages action tar against its selected manifest.

No extraction or network access. Manifest selection, the uploaded archive, and
actual HTTP delivery are distinct gates; this checks the second gate only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import tarfile

FILE_BYTES_LIMIT = 384 * 1024 * 1024
MANIFEST_BYTES_LIMIT = 8 * 1024 * 1024
MAX_FILES = 32768
MAX_ENTRIES = 65536
MAX_PATH_BYTES = 4096
MAX_ARCHIVE_BYTES = FILE_BYTES_LIMIT + MAX_ENTRIES * 1024 + 10240
CHUNK = 64 * 1024
MANIFEST_NAME = 'pages-manifest.json'


class BoundedTarInfo(tarfile.TarInfo):
    """Bound tarfile's internal format-metadata reads before it allocates them."""
    @classmethod
    def fromtarfile(cls, archive):
        archive.pages_header_count = getattr(archive, 'pages_header_count', 0) + 1
        need(archive.pages_header_count <= MAX_ENTRIES + 1, 'Physical tar header-count limit')
        return super().fromtarfile(archive)

    def _proc_member(self, archive):
        need(self.type != tarfile.GNUTYPE_SPARSE, 'Sparse members are not ordinary files')
        if self.type in (tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK,
                         tarfile.XHDTYPE, tarfile.XGLTYPE):
            need(0 <= self.size <= CHUNK, 'Bounded tar format-metadata body')
            if self.type in (tarfile.XHDTYPE, tarfile.XGLTYPE):
                position = archive.fileobj.tell()
                raw = archive.fileobj.read(self.size)
                archive.fileobj.seek(position)
                need(b'GNU.sparse.' not in raw, 'PAX sparse format is not supported')
        return super()._proc_member(archive)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, label + ' bounded integer')
    return value


def safe_path(name, *, member=False, directory=False):
    need(type(name) is str and '\\' not in name and ':' not in name, 'Safe POSIX archive path')
    need(not any(ord(c) < 32 or ord(c) == 127 for c in name), 'No control characters in path')
    need(len(name.encode('utf-8', errors='strict')) <= MAX_PATH_BYTES, 'Bounded UTF8 path')
    if member and directory and name in ('.', './'):
        return ''
    if member and name.startswith('./'):
        name = name[2:]
    if directory and name.endswith('/'):
        name = name[:-1]
    need(name and not name.startswith('/') and not name.endswith('/'), 'Relative nonempty path')
    need(all(part not in ('', '.', '..') for part in name.split('/')), 'No path traversal or aliases')
    return name


def manifest(raw):
    need(type(raw) is bytes and len(raw) <= MANIFEST_BYTES_LIMIT, 'Bounded manifest bytes')
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'Duplicate manifest JSON key')
            out[key] = value
        return out
    def constant(value):
        raise ValueError('Nonfinite manifest constant: ' + value)
    def floating(value):
        out = float(value)
        need(math.isfinite(out), 'Finite manifest number')
        return out
    data = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                      parse_constant=constant, parse_float=floating)
    need(type(data) is dict and type(data.get('schema')) is int and data['schema'] == 1 and
         data.get('kind') == 'pikapika-pages-bundle' and data.get('status') == 'PASS', 'Successful bundle manifest')
    budget = integer(data.get('budgetBytes'), FILE_BYTES_LIMIT, 'Manifest file-byte budget')
    need(budget > 0, 'Positive manifest budget')
    rows = data.get('files')
    need(type(rows) is list and 0 < len(rows) <= MAX_FILES, 'Bounded nonempty selected file inventory')
    expected = {}; total = 0
    for row in rows:
        need(type(row) is dict, 'Selected file object')
        name = safe_path(row.get('path'))
        need(name != MANIFEST_NAME and name not in expected, 'Unique selected file; manifest self is separate')
        size = integer(row.get('bytes'), FILE_BYTES_LIMIT, 'Selected file bytes')
        digest = row.get('sha256')
        need(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'Selected SHA256')
        total += size
        need(total + len(raw) <= budget, 'Selected payload plus manifest exceeds fixed budget')
        expected[name] = {'bytes':size, 'sha256':digest}
    need(integer(data.get('selectedFiles'), MAX_FILES, 'Selected count') == len(rows) and
         integer(data.get('selectedBytes'), FILE_BYTES_LIMIT, 'Selected bytes') == total, 'Selected inventory totals')
    expected[MANIFEST_NAME] = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
    parents = {''}
    for name in expected:
        parts = name.split('/')
        parents.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    need(not (parents & set(expected)), 'A file cannot also be a parent directory')
    return expected, parents, total, budget


def regular_path(path, label):
    need(not path.is_symlink() and path.is_file(), label + ' must be an actual regular file')


def read_manifest(path):
    regular_path(path, 'Manifest')
    with path.open('rb') as stream:
        raw = stream.read(MANIFEST_BYTES_LIMIT + 1)
    need(len(raw) <= MANIFEST_BYTES_LIMIT, 'Bounded manifest read')
    return raw


def zero_range(stream, start, length, label):
    stream.seek(start)
    while length:
        raw = stream.read(min(CHUNK, length))
        need(raw and not any(raw), label)
        length -= len(raw)


def verify(archive_path, manifest_path):
    archive_path, manifest_path = Path(archive_path), Path(manifest_path)
    raw = read_manifest(manifest_path)
    expected, parents, selected_bytes, budget = manifest(raw)
    regular_path(archive_path, 'Archive')
    initial = archive_path.stat()
    need(1024 <= initial.st_size <= MAX_ARCHIVE_BYTES and initial.st_size % 512 == 0,
         'Bounded uncompressed tar size and block alignment')
    seen = set(); actual_files = set(); entries = 0; payload = 0; directories = 0
    with archive_path.open('rb') as stream:
        # r: explicitly rejects gzip/bzip/xz instead of silently decompressing.
        with tarfile.open(fileobj=stream, mode='r:', errorlevel=2, tarinfo=BoundedTarInfo) as archive:
            for item in archive:
                entries += 1
                need(entries <= MAX_ENTRIES, 'Tar entry-count limit')
                need(item.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE) and
                     item.sparse is None and not item.linkname, 'Only ordinary regular files and parent directories')
                name = safe_path(item.name, member=True, directory=item.isdir())
                need(name not in seen, 'Duplicate normalized tar member: ' + name)
                seen.add(name)
                size = integer(item.size, FILE_BYTES_LIMIT, 'Tar member size')
                if item.isdir():
                    need(name in parents and size == 0, 'Only required parent directories are allowed')
                    directories += 1
                    continue
                need(name in expected, 'Unexpected tar file: ' + name)
                record = expected[name]
                need(size == record['bytes'], 'Tar file size mismatch: ' + name)
                payload += size
                need(payload <= budget and payload <= FILE_BYTES_LIMIT, 'Tar file-byte budget')
                body = archive.extractfile(item)
                need(body is not None, 'Regular file body unavailable')
                digest = hashlib.sha256(); remaining = size
                with body:
                    while remaining:
                        block = body.read(min(CHUNK, remaining))
                        need(block and len(block) <= remaining, 'Truncated tar file body')
                        digest.update(block); remaining -= len(block)
                    need(body.read(1) == b'', 'Read beyond declared regular member')
                need(digest.hexdigest() == record['sha256'], 'Tar file SHA256 mismatch: ' + name)
                padding = (-size) % 512
                if padding:
                    zero_range(stream, item.offset_data + size, padding, 'Nonzero tar payload padding')
                actual_files.add(name)
            end = archive.offset
        need(actual_files == set(expected), 'Missing selected files or manifest self: ' + ', '.join(sorted(set(expected)-actual_files)))
        # tarfile stops at its first zero header (and can otherwise silently
        # ignore malformed/trailing or concatenated archives). Require the full
        # remaining physical tail to be zero and contain the two end blocks.
        need(initial.st_size - end >= 1024, 'Two final tar end blocks required')
        zero_range(stream, end, initial.st_size - end, 'Nonzero/unparsed data after last member')
        stream.seek(0); digest = hashlib.sha256(); count = 0
        while True:
            block = stream.read(CHUNK)
            if not block: break
            count += len(block)
            need(count <= MAX_ARCHIVE_BYTES, 'Bounded physical archive read')
            digest.update(block)
    final = archive_path.stat()
    need((initial.st_size, initial.st_mtime_ns) == (final.st_size, final.st_mtime_ns) and count == initial.st_size,
         'Archive changed during verification')
    need(payload == selected_bytes + len(raw), 'Complete selected payload plus raw manifest')
    return {'schema':1, 'status':'PASS', 'archive':{'path':str(archive_path), 'bytes':count, 'sha256':digest.hexdigest()},
            'manifest':{'path':str(manifest_path), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()},
            'entries':entries, 'directories':directories, 'files':len(actual_files),
            'selectedFiles':len(expected)-1, 'selectedBytes':selected_bytes, 'fileBytes':payload,
            'hiddenSelectedFiles':sum(any(part.startswith('.') for part in name.split('/')) for name in expected if name != MANIFEST_NAME),
            'scope':'Actual uncompressed archive: exact selected file set plus raw manifest, all bytes/size/SHA256; parent directories only. No extraction, HTTP delivery, or numerical-engine claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.manifest)))
