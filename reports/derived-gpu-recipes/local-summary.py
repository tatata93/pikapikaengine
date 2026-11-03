import pathlib,json,hashlib
r=pathlib.Path(__file__).resolve().parents[2];names=['4','64','512','retry-4'];records=[];files=[]
for name in names:
    p=r/'reports'/('derived-gpu-local-'+name+'.json');b=p.read_bytes();d=json.loads(b)
    assert d['status']=='completed' and d['execution']['drawCompleted']==20
    files.append(dict(path=p.relative_to(r).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    records.append(dict(caseName=d['caseName'],build=d['environment']['buildMarker'],verified=d['verified'],execution=d['execution'],environment=d['environment'],gpuEnvironment=d['gpu']['environment'],disposal=d['disposal'],measureSummary=[x for x in d['summary'] if x['phase']=='measure']))
for name in ['derived-gpu-local.png','derived-gpu-browser-verification.json','derived-gpu-browser-controls/controls.json']:
    p=r/'reports'/name;b=p.read_bytes();files.append(dict(path=p.relative_to(r).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
proof=json.loads((r/'reports/derived-gpu-browser-verification.json').read_text());controls=json.loads((r/'reports/derived-gpu-browser-controls/controls.json').read_text());assert proof['numericComparisons']==136460 and controls['rejected']==7
out=dict(status='PASS',browserReports=4,actualPrepareCalls=40,actualDraws=80,newUploads=40,cacheDraws=40,comparedNumericValues=proof['numericComparisons'],browserVerifierRejectedControls=controls['rejected'],records=records,files=files,scope='One local IAB/Chrome155 Windows observation. Other browser/OS load uncontrolled; no GPU timestamps, pixel readback, cold-system or general fps claim.')
(r/'reports/derived-gpu-local-verification.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(dict(status='PASS',reports=4,draws=80,numericComparisons=proof['numericComparisons'])))
