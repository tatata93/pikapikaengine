import pathlib,json,hashlib,shutil
r=pathlib.Path(__file__).resolve().parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
files=[]
def copy(src,dst):
    b=src.read_bytes();target=r/'reports'/dst;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(b)
    assert target.read_bytes()==b
    files.append(dict(path='reports/'+dst,source=str(src.relative_to(r)),bytes=len(b),sha256=sha(b)))
std=r/'build/derived-profile-root/run-20261103155558576-199ad571c1'
for p in sorted(std.iterdir()):
    if p.is_file():copy(p,'derived-profile-standard/'+p.name)
proof=r/'build/derived-profile-verification/run-OGdceM'
for p in sorted(proof.iterdir()):
    if p.is_file():copy(p,'derived-profile-correctness/'+p.name)
control=r/'build/derived-mesh-reference-profile/run-dqk0v_ro'
for p in sorted(control.rglob('*')):
    if p.is_file():copy(p,'derived-profile-controls/'+p.relative_to(control).as_posix())
checks=r/'build/derived-profile-root-check/proof-whvqdu0s'
for p in sorted(checks.iterdir()):
    if p.is_file():copy(p,'derived-profile-checks/'+p.name)
for p in ['tools/derived-profile.mjs','scripts/profile-derived-mesh.mjs','scripts/derived-profile-cases.mjs','scripts/verify-derived-profile.mjs','tests/derived-profile.test.mjs','tests/derived-profile-cli.test.mjs']:
    copy(r/p,'derived-profile-recipes/'+p)
copy(r/'build/derived-profile-root-command.txt','derived-profile-standard-command.txt')
copy(r/'build/derived-profile-reference-root.txt','derived-profile-correctness-command.txt')
index=dict(status='PASS',scope='Raw bytes retained; Node-only timing and correctness proof are separate.',files=files)
(r/'reports/derived-profile-archive.json').write_bytes((json.dumps(index,indent=2)+'\n').encode())
print(json.dumps(dict(files=len(files),bytes=sum(x['bytes'] for x in files)),indent=2))
