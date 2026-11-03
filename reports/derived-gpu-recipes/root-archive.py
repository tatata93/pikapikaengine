import pathlib,json,hashlib
r=pathlib.Path(__file__).resolve().parents[2];files=[]
def copy(src,dst):
    b=src.read_bytes();target=r/'reports'/dst;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(b)
    assert target.read_bytes()==b
    files.append(dict(path='reports/'+dst,source=str(src.relative_to(r)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
checks=pathlib.Path(json.loads((r/'build/derived-gpu-root-check/latest.json').read_text())['runDirectory'])
for p in sorted(checks.iterdir()):
    if p.is_file():copy(p,'derived-gpu-checks/'+p.name)
reference=r/'build/derived-gpu-reference-root.txt'
copy(reference,'derived-gpu-reference-command.txt')
proof=json.loads(reference.read_text(encoding='utf-8-sig'));directory=pathlib.Path(proof['outputDirectory'])
for p in sorted(directory.iterdir()):
    if p.is_file():copy(p,'derived-gpu-correctness/'+p.name)
controls=pathlib.Path(proof['referenceControls']['runDirectory'])
for p in sorted(controls.rglob('*')):
    if p.is_file():copy(p,'derived-gpu-controls/'+p.relative_to(controls).as_posix())
browserCommand=r/'build/derived-gpu-browser-root-command.txt';copy(browserCommand,'derived-gpu-browser-command.txt')
browser=json.loads(browserCommand.read_text(encoding='utf-8-sig'))
copy(pathlib.Path(browser['runDirectory'])/'verification.json','derived-gpu-browser-verification.json')
controlCommand=r/'build/derived-gpu-browser-controls-final-command.txt';copy(controlCommand,'derived-gpu-browser-controls-command.txt')
controlInfo=json.loads(controlCommand.read_text(encoding='utf-8-sig'));controlDir=pathlib.Path(controlInfo['runDirectory'])
for p in sorted(controlDir.iterdir()):
    if p.is_file():copy(p,'derived-gpu-browser-controls/'+p.name)
names=['tools/derived-gpu-profile.mjs','tools/derived-gpu-cases.mjs','tools/derived-gpu-lab.mjs','tools/derived-gpu-lab.html','tests/derived-gpu-profile.test.mjs','tests/derived-gpu-cases.test.mjs','tests/derived-gpu-lab.test.mjs','scripts/build-web.mjs','scripts/verify-derived-gpu-lab.mjs','docs/learn/diagrams/derived-gpu-profile.svg']
for name in names:copy(r/name,'derived-gpu-recipes/'+name)
(r/'reports/derived-gpu-archive.json').write_bytes((json.dumps(dict(status='PASS',files=files),indent=2)+'\n').encode())
print(json.dumps(dict(files=len(files),bytes=sum(x['bytes'] for x in files))))
