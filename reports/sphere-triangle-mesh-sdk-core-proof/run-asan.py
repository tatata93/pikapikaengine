import pathlib,subprocess,time,json,hashlib
r=pathlib.Path.cwd();o=r/'build/sphere-triangle-mesh-sdk-core';a=o/'asan';a.mkdir(exist_ok=True)
vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat';head='@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n';flags='cl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address /W4 /fp:strict /Icore/include '
build=head+flags+'/c core/src/simulation_api.cpp /Fobuild\\sphere-triangle-mesh-sdk-core\\asan\\simulation_api.obj /Fdbuild\\sphere-triangle-mesh-sdk-core\\asan\\api.pdb\nif errorlevel 1 exit /b %errorlevel%\n'+flags+'tests/sphere_triangle_mesh_sdk_tests.cpp build\\sphere-triangle-mesh-sdk-core\\asan\\simulation_api.obj build\\sphere-triangle-mesh-sdk-core\\frozen-core.lib /Febuild\\sphere-triangle-mesh-sdk-core\\asan\\mesh-sdk-tests.exe /Fobuild\\sphere-triangle-mesh-sdk-core\\asan\\tests.obj /Fdbuild\\sphere-triangle-mesh-sdk-core\\asan\\tests.pdb /link /INCREMENTAL:NO\n'
(o/'build-asan.cmd').write_text(build,encoding='utf-8');(o/'run-asan.cmd').write_text(head+'build\\sphere-triangle-mesh-sdk-core\\asan\\mesh-sdk-tests.exe\n',encoding='utf-8')
def run(label,args):
 start=time.perf_counter();p=subprocess.run(args,cwd=r,capture_output=True);elapsed=time.perf_counter()-start
 (o/(label+'.stdout.txt')).write_bytes(p.stdout);(o/(label+'.stderr.txt')).write_bytes(p.stderr)
 commands=json.loads((o/'commands.json').read_text());commands.append(dict(label=label,args=args,exitCode=p.returncode,elapsedObservedSeconds=elapsed,stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest()));(o/'commands.json').write_text(json.dumps(commands,indent=2),encoding='utf-8');print(label,p.returncode,round(elapsed,3),flush=True)
 if p.returncode:print(p.stdout.decode(errors='replace')[-8000:]+p.stderr.decode(errors='replace'));raise SystemExit(p.returncode)
 return p
run('transport-audit',['python',str(o/'audit.py')])
run('compile-asan',['cmd','/d','/c',str(o/'build-asan.cmd')])
p=run('asan',['cmd','/d','/c',str(o/'run-asan.cmd')]);print(p.stdout.decode(errors='replace')[-2000:])
