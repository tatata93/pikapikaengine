import subprocess,pathlib,json,time,hashlib,sys
root=pathlib.Path.cwd();out=root/'build/sphere-triangle-mesh-core';asan=out/'asan';asan.mkdir(exist_ok=True)
vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
commands=json.loads((out/'commands.json').read_text())
def run(label,args):
 start=time.time();p=subprocess.run(args,cwd=root,capture_output=True);end=time.time()
 (out/(label+'.stdout.bin')).write_bytes(p.stdout);(out/(label+'.stderr.bin')).write_bytes(p.stderr)
 commands.append(dict(label=label,args=args,exitCode=p.returncode,elapsedSeconds=end-start,stdoutSha256=hashlib.sha256(p.stdout).hexdigest(),stderrSha256=hashlib.sha256(p.stderr).hexdigest()))
 (out/'commands.json').write_text(json.dumps(commands,indent=2),encoding='utf-8');print(label,p.returncode,round(end-start,3),flush=True)
 if p.returncode: print(p.stdout.decode(errors='replace')[-5000:]+p.stderr.decode(errors='replace')[-5000:]);sys.exit(p.returncode)
 return p
head='@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'
cmd=head+'cl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp tests/sphere_triangle_mesh_tests.cpp /Febuild\\sphere-triangle-mesh-core\\asan\\mesh-tests.exe /Fobuild\\sphere-triangle-mesh-core\\asan\\ /Fdbuild\\sphere-triangle-mesh-core\\asan\\mesh.pdb /link /INCREMENTAL:NO\n'
(out/'build-asan.cmd').write_text(cmd,encoding='utf-8')
run('compile-asan',['cmd','/d','/c',str(out/'build-asan.cmd')])
for label,suffix in [('asan',''),('asan-fixtures',' --fixtures')]:
 p=out/('run-'+label+'.cmd');p.write_text(head+'build\\sphere-triangle-mesh-core\\asan\\mesh-tests.exe'+suffix+'\n',encoding='utf-8')
 result=run(label,['cmd','/d','/c',str(p)])
 if label=='asan':print(result.stdout.decode(errors='replace')[-1000:])
assert (out/'fixtures.stdout.bin').read_bytes()==(out/'asan-fixtures.stdout.bin').read_bytes()
print('ASan fixture raw bytes exactly match Native',flush=True)
