import pathlib,subprocess,time,json,hashlib,shutil
r=pathlib.Path.cwd();o=r/'build/sphere-triangle-mesh-sdk-core';o.mkdir(exist_ok=True)
lib=r/'build/native/Release/pikapika_core.lib';shutil.copyfile(lib,o/'frozen-core.lib')
vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
cmd='@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
flags='cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include '
cmd+=flags+'/c core/src/simulation_api.cpp /Fobuild\\sphere-triangle-mesh-sdk-core\\simulation_api.obj\nif errorlevel 1 exit /b %errorlevel%\n'
for source,name in [('tests/sphere_triangle_mesh_sdk_tests.cpp','mesh-sdk-tests'),('tools/sphere_triangle_mesh_sdk_probe.cpp','mesh-sdk-probe'),('tests/simulation_api_tests.cpp','existing-api-tests')]:
 cmd+=flags+source+' build\\sphere-triangle-mesh-sdk-core\\simulation_api.obj build\\sphere-triangle-mesh-sdk-core\\frozen-core.lib /Febuild\\sphere-triangle-mesh-sdk-core\\'+name+'.exe /Fobuild\\sphere-triangle-mesh-sdk-core\\'+name+'.obj /link /INCREMENTAL:NO\nif errorlevel 1 exit /b %errorlevel%\n'
(o/'build-native.cmd').write_text(cmd,encoding='utf-8')
commands=[]
def run(label,args):
 start=time.perf_counter();p=subprocess.run(args,cwd=r,capture_output=True);elapsed=time.perf_counter()-start
 (o/(label+'.stdout.txt')).write_bytes(p.stdout);(o/(label+'.stderr.txt')).write_bytes(p.stderr)
 commands.append(dict(label=label,args=args,exitCode=p.returncode,elapsedObservedSeconds=elapsed,stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest()));(o/'commands.json').write_text(json.dumps(commands,indent=2),encoding='utf-8');print(label,p.returncode,round(elapsed,3),flush=True)
 if p.returncode:print(p.stdout.decode(errors='replace')[-8000:]+p.stderr.decode(errors='replace'));raise SystemExit(p.returncode)
 return p
run('compile',['cmd','/d','/c',str(o/'build-native.cmd')])
p=run('native',[str(o/'mesh-sdk-tests.exe')]);print(p.stdout.decode(errors='replace'))
p=run('existing-native',[str(o/'existing-api-tests.exe')]);print(p.stdout.decode(errors='replace')[-400:])
