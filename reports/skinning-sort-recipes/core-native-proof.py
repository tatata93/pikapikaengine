import hashlib,json,subprocess
from pathlib import Path
p=Path('build/skinning-sort');records=[]
vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
def run(cmd,label,output=None):
 r=subprocess.run(cmd,capture_output=True);(p/(label+'.stdout.bin')).write_bytes(r.stdout);(p/(label+'.stderr.bin')).write_bytes(r.stderr)
 records.append({'label':label,'command':cmd,'exitCode':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace'),'stdoutSha256':hashlib.sha256(r.stdout).hexdigest(),'stderrSha256':hashlib.sha256(r.stderr).hexdigest()});(p/'native-commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
 if output:(p/output).write_bytes(r.stdout)
 print(label,'exit',r.returncode)
 if output:print('Raw output bytes',len(r.stdout),'sha256',hashlib.sha256(r.stdout).hexdigest())
 else:print(r.stdout.decode('utf-8',errors='replace'))
 print(r.stderr.decode('utf-8',errors='replace'))
 if r.returncode:raise SystemExit(r.returncode)
for name,source,asan in [('native','core/src/skinning.cpp',False),('asan-before','build/skinning-sort/before-skinning.cpp',True),('asan-after','core/src/skinning.cpp',True)]:
 directory=p/name;directory.mkdir(exist_ok=True);extra='/Zi /fsanitize=address' if asan else ''
 content=f'@echo off\ncall "{vc}" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict {extra} /Icore/include {source} core/src/motion.cpp tests/skinning_tests.cpp /Fe{directory}/skinning.exe /Fo{directory}/ /Fd{directory}/skinning.pdb /link /INCREMENTAL:NO\nif errorlevel 1 exit /b %errorlevel%\n{directory}\\skinning.exe\nexit /b %errorlevel%\n'
 script=p/(name+'.cmd');script.write_text(content,encoding='utf-8');run(['cmd.exe','/d','/c',str(script)],name)
for args,output,label in [(['--fixtures'],'native.json','native-fixtures'),(['--oracle'],'native-oracle.csv','native-oracle')]:run([str(p/'native/skinning.exe'),*args],label,output)
for current,previous in [('native.json','reports/skinning-native.json'),('native-oracle.csv','reports/skinning-native-oracle.csv')]:
 old=Path(previous)
 if not old.exists():old=Path('build/skinning-proof')/current
 if (p/current).read_bytes()!=old.read_bytes():raise RuntimeError('Baseline bytes differ: '+current+' vs '+str(old))
print('Native fixture and oracle raw bytes equal prior reference')
