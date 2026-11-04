import subprocess,pathlib,json,time,hashlib,sys
root=pathlib.Path.cwd();out=root/'reports/sphere-triangle-mesh-marker-proof';out.mkdir(exist_ok=False)
(root/'build/sphere-triangle-mesh-marker').mkdir(exist_ok=True)
vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
commands=[]
def run(label,args):
 start=time.time(); p=subprocess.run(args,cwd=root,capture_output=True); end=time.time()
 (out/(label+'.stdout.txt')).write_bytes(p.stdout);(out/(label+'.stderr.txt')).write_bytes(p.stderr)
 commands.append(dict(label=label,args=args,exitCode=p.returncode,elapsedSeconds=end-start,stdoutSha256=hashlib.sha256(p.stdout).hexdigest(),stderrSha256=hashlib.sha256(p.stderr).hexdigest()))
 (out/'commands.json').write_text(json.dumps(commands,indent=2),encoding='utf-8');print(label,p.returncode,round(end-start,3),flush=True)
 if p.returncode: print(p.stdout.decode(errors='replace')[-5000:]+p.stderr.decode(errors='replace')[-5000:]);sys.exit(p.returncode)
 return p
cmd='@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp tests/sphere_triangle_mesh_tests.cpp /Febuild\\sphere-triangle-mesh-marker\\mesh-tests.exe /Fobuild\\sphere-triangle-mesh-marker\\ /link /INCREMENTAL:NO\n'
(out/'build-native.cmd').write_text(cmd,encoding='utf-8')
run('compile-native',['cmd','/d','/c',str(out/'build-native.cmd')])
p=run('native',[str(root/'build/sphere-triangle-mesh-marker/mesh-tests.exe')]);print(p.stdout.decode(errors='replace')[-3000:])
run('fixtures',[str(root/'build/sphere-triangle-mesh-marker/mesh-tests.exe'),'--fixtures'])
run('reference',[sys.executable,'scripts/verify-sphere-triangle-mesh.py',str(out/'fixtures.stdout.txt')])

assert (out/'fixtures.stdout.txt').read_bytes()==(root/'reports/sphere-triangle-mesh-core-proof/fixtures.stdout.txt').read_bytes()
print('Fixture bytes unchanged from accepted native/ASan corpus')
