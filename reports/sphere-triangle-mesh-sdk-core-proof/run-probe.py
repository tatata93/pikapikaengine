import pathlib,subprocess,json,time,hashlib
r=pathlib.Path.cwd();o=r/'build/sphere-triangle-mesh-sdk-core';args=[str(o/'mesh-sdk-probe.exe'),'--rows',str(o/'input.rows')];start=time.perf_counter();p=subprocess.run(args,cwd=r,capture_output=True)
(o/'probe.json').write_bytes(p.stdout);(o/'probe.stderr.txt').write_bytes(p.stderr)
a=json.loads((o/'commands.json').read_text());a.append(dict(label='probe',args=args,exitCode=p.returncode,elapsedObservedSeconds=time.perf_counter()-start,stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest()));(o/'commands.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
print('probe',p.returncode,len(p.stdout),p.stderr.decode(errors='replace'));p.check_returncode();v=json.loads(p.stdout);print({k:v[k] for k in ['fixtureCount','accepted','hostRejected']});print([(f['name'],f['failedPhase'],f['exchangeStatus']) for f in v['fixtures'] if f['failedPhase']])
