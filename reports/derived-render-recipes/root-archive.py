import pathlib,json,hashlib
r=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(json.loads((r/'build/derived-render-root/latest.json').read_text())['runDirectory']);rows=[]
def copy(src,dest):
    b=(r/src).read_bytes();p=r/dest;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(b)
    rows.append(dict(original=str(src),path=dest,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
for p in out.iterdir():
    if p.is_file():copy(p.relative_to(r),'reports/derived-render-root-'+p.name)
for p in ['engine/derived-render.mjs','engine/renderer.mjs','tools/skin-binding-lab.mjs','tests/derived-renderer.test.mjs','tests/skin-binding-lab.test.mjs','build/derived-render-root/verify.py','build/derived-render-root/archive.py']:
    dest='reports/derived-render-recipes/root-'+pathlib.Path(p).name if p.startswith('build/') else 'reports/derived-render-recipes/'+p
    copy(pathlib.Path(p),dest)
v=json.loads((out/'verification.json').read_text());v['archive']=rows;v['browser']={'observations':15,'backend':'Actual browser WebGPU API; adapter hardware/software identity unmeasured','fixedScene':'6 vertices / 4 triangles / 288 upload bytes','file':'reports/derived-render-local-browser.json'}
v['reviewFix']={'problem':'Array.every skipped absent elements in plain audit arrays','regression':'One new group rejects six hole mutations across cross, Q, normalized and normalError; valid dense actual SDK result accepted','preFixRun':'build/derived-render-root/proof-w4u28h07','preFixNodePassed':390,'finalNodePassed':391,'scope':'C++ output was dense; no C++/WASM numerical result changed'}
(r/'reports/derived-render-verification.json').write_bytes((json.dumps(v,indent=2)+'\n').encode())
print('ARCHIVE',len(rows),'finalNode',v['nodePassed'],'SDK audits',len(v['sdkAudit']))
