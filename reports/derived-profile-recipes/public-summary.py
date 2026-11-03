import pathlib,json,hashlib,re
r=pathlib.Path(__file__).resolve().parents[2]
code='5602496c2d5d2e935e6104295be71d83b6733170'
ci=json.loads((r/'reports/derived-profile-run-41669801929.json').read_text());pages=json.loads((r/'reports/derived-profile-run-41669800722.json').read_text())
for run in [ci,pages]:
    assert run['jobs'] and all(j['status']=='completed' and j['conclusion']=='success' for j in run['jobs'])
log=(r/'reports/derived-profile-job-126034816237.txt').read_text(encoding='utf-8')
for text in ['v22.23.4','GNU 13.3.0','100% tests passed, 0 tests failed out of 30','# pass 407','# skipped 0','"numericComparisons": 2841','"nativeNumericBitComparisons": 2318','"profiledQueries": 48','"queryCount": 32','"totalComparedNumericValues": 54410','PASS 69 skinning test groups','27 skin binding IO groups passed','derived mesh: 54 groups passed (40 fixtures)']:
    assert text in log,text
assert log.count('warning:')==36
assert log.count('"rejectedControls": 36')==3
http=json.loads((r/'reports/derived-profile-http.json').read_text());assert http['status']=='PASS' and http['revision']==code and len(http['files'])==16
game=json.loads((r/'reports/derived-profile-game-dom.json').read_text());assert 'C++ WASM / WEBGPU READY' in game['text'] and game['launch']['enabled']
lesson=json.loads((r/'reports/derived-profile-lesson-dom.json').read_text());assert lesson['articles']==25 and 'Nodeの値を実GPUやゲームのfpsへ換算しません。' in lesson['text']
files=[]
for p in sorted((r/'reports').glob('derived-profile-*')):
    if p.is_file() and (p.suffix in ['.png'] or p.name.startswith(('derived-profile-job-','derived-profile-run-')) or p.name in ['derived-profile-http.json','derived-profile-game-dom.json','derived-profile-lesson-dom.json']):
        b=p.read_bytes();files.append(dict(path=p.relative_to(r).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
out=dict(status='PASS',codeCommit=code,ciRun=41669801929,ciJob=126034816237,pagesRun=41669800722,ciNode='22.23.4',ciCompiler='GNU 13.3.0',nodePassed=407,nodeSkipped=0,ctestPassed=30,profiledNativeDerivedBits=2318,legacyFullBits=2841,profiledQueries=48,ciQuickCalls=32,ciQuickComparedNumericValues=54410,referenceControlBatches=3,rejectedPerBatch=36,sanitizerGroups=[69,27,54],warningLines=36,publicHTTPFiles=16,browser='actual IAB; robot startup READY only, no combat controls, no performance or hardware adapter classification',files=files)
(r/'reports/derived-profile-public-verification.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(files),ci='407 Node / 30 CTest',publicHTTP=16)))
