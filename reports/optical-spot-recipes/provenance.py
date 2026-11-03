from pathlib import Path
import datetime,hashlib,json,platform,subprocess
base=Path('build/optical-spot-proof')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
sources=['core/include/pikapika/optical_spot.hpp','core/src/optical_spot.cpp','tests/optical_spot_tests.cpp','docs/OPTICAL_SPOT.md','scripts/verify-optical-spot.py',
         'core/include/pikapika/optical_route.hpp','core/src/optical_route.cpp','core/include/pikapika/optical_bounds.hpp','core/src/optical_bounds.cpp',
         'core/include/pikapika/interval.hpp','core/src/interval.cpp','core/include/pikapika/optical_geometry.hpp','core/include/pikapika/core.hpp']
proofs=['native-tests.txt','native-fixtures.json','native-oracle.csv','wasm-tests.txt','wasm-fixtures.json','wasm-oracle.csv','fixture-comparison.json','oracle-comparison.json','checker-negative-controls.json','proof-commands.json']
recipes=['build.cmd','build-wasm.mjs','run-wasm.mjs','record-proof.py','negative-controls.py','provenance.py']
compiler=Path('C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Tools/MSVC/14.51.36231/bin/Hostx64/x64/cl.exe')
out=dict(recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseRevision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         platform=platform.platform(),python=platform.python_version(),
         sourceSHA256={str(p):sha(p) for p in sources},
         proofSHA256={p:sha(base/p) for p in proofs},recipeSHA256={p:sha(base/p) for p in recipes},
         artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [base/'spot-tests.exe',base/'spot-standalone.mjs',base/'spot-standalone.wasm']},
         nativeCompiler=dict(path=str(compiler),fileVersion='19.51.36247.0',sha256=sha(compiler),flags='/std:c++20 /O2 /EHsc /MD /fp:strict /W4'),
         wasmCompiler=dict(version=(base/'wasm-compiler.txt').read_text(),emsdkRevision=subprocess.check_output(['git','-C','build/toolchains/emsdk','rev-parse','HEAD'],text=True).strip(),
                           flags='-std=c++20 -O2 -fwasm-exceptions -fno-rtti -fno-fast-math -ffp-contract=off',link='MODULARIZE=1 EXPORT_ES6=1 ENVIRONMENT=node FILESYSTEM=0 EXIT_RUNTIME=0 ALLOW_MEMORY_GROWTH=1 MAXIMUM_MEMORY=268435456 STACK_SIZE=1048576'),
         validation=dict(nativeGroups=19,standaloneWasmGroups=18,fixtureComparison=json.loads((base/'fixture-comparison.json').read_text()),oracleComparison=json.loads((base/'oracle-comparison.json').read_text()),
                         positiveControls=4,negativeControls=72),
         limits=['Finite prescribed-route geometric weighted spot, not radiometric image or continuous-pupil quadrature bound.',
                 'Native-only rounding-mode rejection/restoration explains the one-group count difference.',
                 'Final API/source is original C++; existing route/bounds/interval sources are not modified by this task.',
                 'Exact binary64 .05/.005 parameters have their own Fraction paraxial target; ideal-decimal 639/11800 is a convenient nearby reference.',
                 'Partial work counters inside throwing original primitives are unavailable; numeric failure returns no statistics.',
                 'Standalone is independent proof artifact, shared ABI/distribution evidence is recorded separately by root.'])
(base/'provenance.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(artifacts=out['artifacts'],sourceSHA256={p:out['sourceSHA256'][p] for p in sources[:5]})))
