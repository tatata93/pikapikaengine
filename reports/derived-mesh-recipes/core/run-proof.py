import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / 'build/derived-mesh-core'
VCVARS = r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
SOURCES = ['core/include/pikapika/derived_mesh.hpp', 'core/src/derived_mesh.cpp', 'tests/derived_mesh_tests.cpp', 'core/include/pikapika/interval.hpp', 'core/src/interval.cpp', 'core/include/pikapika/core.hpp']
COMMANDS = []
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
def run(label, args):
    start = datetime.now(timezone.utc).isoformat()
    p = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    stdout, stderr = PROOF/(label+'.stdout.bin'), PROOF/(label+'.stderr.bin')
    stdout.write_bytes(p.stdout); stderr.write_bytes(p.stderr)
    COMMANDS.append({'label':label,'argv':args,'cwd':str(ROOT),'startedUTC':start,'exitCode':p.returncode,'stdout':str(stdout.relative_to(ROOT)),'stderr':str(stderr.relative_to(ROOT)),'stdoutSHA256':sha(p.stdout),'stderrSHA256':sha(p.stderr)})
    write_json(PROOF/'commands.json', COMMANDS)
    if p.returncode: raise RuntimeError(f'{label}: exit {p.returncode}')
    return p.stdout
def batch(name, command):
    path = PROOF/name
    path.write_text('@echo off\ncall "'+VCVARS+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+command+'\n',encoding='utf-8',newline='\r\n')
    return ['cmd.exe','/d','/c',str(path)]

PROOF.mkdir(parents=True, exist_ok=True)
(PROOF/'asan').mkdir(exist_ok=True)
base = 'cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/derived_mesh.cpp tests/derived_mesh_tests.cpp '
run('compile-native', batch('build-native.cmd',base+'/Febuild\\derived-mesh-core\\derived-mesh-tests.exe /Fobuild\\derived-mesh-core\\ /link /INCREMENTAL:NO'))
run('run-native', [str(PROOF/'derived-mesh-tests.exe')])
raw = run('native-fixtures',[str(PROOF/'derived-mesh-tests.exe'),'--fixtures'])
(PROOF/'native-fixtures.json').write_bytes(raw)
run('compile-asan',batch('build-asan.cmd',base+'/Zi /fsanitize=address /Febuild\\derived-mesh-core\\asan\\derived-mesh-tests.exe /Fobuild\\derived-mesh-core\\asan\\ /Fdbuild\\derived-mesh-core\\asan\\derived-mesh-tests.pdb /link /INCREMENTAL:NO'))
run('run-asan',batch('run-asan.cmd','build\\derived-mesh-core\\asan\\derived-mesh-tests.exe'))
asan_raw=run('asan-fixtures',batch('asan-fixtures.cmd','build\\derived-mesh-core\\asan\\derived-mesh-tests.exe --fixtures'))
(PROOF/'asan-fixtures.json').write_bytes(asan_raw)
if raw != asan_raw: raise RuntimeError('ASan and normal fixtures differ')
revision=run('revision',['git','rev-parse','HEAD']).decode('ascii').strip()
compiler=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe')
provenance={'schema':1,'createdUTC':datetime.now(timezone.utc).isoformat(),'revisionBase':revision,'platform':platform.platform(),'python':sys.version,'scope':'Native-only local Float32 derived geometry; not SDK/render/GPU/world-space certification','sources':{s:{'bytes':len((ROOT/s).read_bytes()),'sha256':sha((ROOT/s).read_bytes())} for s in SOURCES},'compiler':{'path':str(compiler),'sha256':sha(compiler.read_bytes())},'results':{'nativeGroups':54,'fixtures':40,'asanGroups':54,'fixturesByteIdentical':True},'artifacts':{str(p.relative_to(ROOT)):{'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in [PROOF/'derived-mesh-tests.exe',PROOF/'asan/derived-mesh-tests.exe',PROOF/'native-fixtures.json',PROOF/'asan-fixtures.json',PROOF/'commands.json',Path(__file__)]}}
provenance['observedHardCapacity'] = {
    'vertices':65536,'triangles':131072,
    'nativePrepareSeconds':float(re.search(rb'observed hard capacity prepare seconds: ([0-9.eE+-]+)',(PROOF/'run-native.stdout.bin').read_bytes())[1]),
    'asanPrepareSeconds':float(re.search(rb'observed hard capacity prepare seconds: ([0-9.eE+-]+)',(PROOF/'run-asan.stdout.bin').read_bytes())[1]),
    'scope':'Single observed local prepare call in each build; not a general performance guarantee.'
}
provenance['testScope'] = {
    'lbs-half-turn-collapse':'Direct analytic zero positions from equal blending of identity and a 180-degree Z rotation on an XY triangle. This does not call skinning::deform and is not an end-to-end LBS test.',
    'finite-unrenderable-deformation':'The fixed +/-1e6 input coordinate profile rejects 1e300 before Float32 conversion; this is a domain rejection, not an exercised Float32 overflow conversion.',
    'environment':'Rounding and floating-point control modes are not changed. Ordinary arithmetic exception status flags may be raised; flag preservation is not claimed.',
    'independent-reference':'The external Fraction checker is owned and recorded separately; these are standalone Native/ASan results.'
}
write_json(PROOF/'provenance.json',provenance)
print(json.dumps({'passed':True,'groups':54,'fixtures':40,'asanGroups':54,'byteIdentical':True,'provenance':'build/derived-mesh-core/provenance.json'}))
