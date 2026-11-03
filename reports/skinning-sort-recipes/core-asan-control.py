import json,subprocess
from pathlib import Path
p=Path('build/skinning-sort');vc=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
script=p/'asan-control.cmd';script.write_text(f'@echo off\ncall "{vc}" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address build/skinning-sort/asan-control.cpp /Febuild/skinning-sort/asan-control.exe /Fobuild/skinning-sort/ /Fdbuild/skinning-sort/asan-control.pdb /link /INCREMENTAL:NO\nif errorlevel 1 exit /b %errorlevel%\nbuild\\skinning-sort\\asan-control.exe\nexit /b %errorlevel%\n',encoding='utf-8')
command=['cmd.exe','/d','/c',str(script)];r=subprocess.run(command,capture_output=True);(p/'asan-control.stdout.bin').write_bytes(r.stdout);(p/'asan-control.stderr.bin').write_bytes(r.stderr)
passed=r.returncode!=0 and b'AddressSanitizer' in r.stderr+r.stdout and b'heap-buffer-overflow' in r.stderr+r.stdout
obj={'command':command,'exitCode':r.returncode,'expectedNonzero':True,'observedHeapBufferOverflow':passed,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace')};(p/'asan-control.json').write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8');print('ASan negative control',passed,'exit',r.returncode)
if not passed:raise SystemExit(1)
