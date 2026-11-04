import pathlib,subprocess,hashlib,json,datetime,sys
r=pathlib.Path.cwd();o=r/'build/sphere-triangle-mesh-core'
owned=['core/include/pikapika/sphere_triangle_mesh.hpp','core/src/sphere_triangle_mesh.cpp','tests/sphere_triangle_mesh_tests.cpp']
deps=['core/include/pikapika/sphere_triangle.hpp','core/src/sphere_triangle.cpp','core/include/pikapika/interval.hpp','core/src/interval.cpp','scripts/verify-sphere-triangle-mesh.py','scripts/verify-sphere-triangle.py']
def entry(p):
 b=(r/p).read_bytes();return {'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'CRbytes':b.count(b'\r')}
commands=json.loads((o/'commands.json').read_text());assert len(commands)==7 and all(x['exitCode']==0 for x in commands)
normal=(o/'fixtures.stdout.bin').read_bytes();san=(o/'asan-fixtures.stdout.bin').read_bytes();assert normal==san
fx=json.loads(normal);assert len(fx['fixtures'])==48
for name in ['native','asan']:assert b'PASS 59 groups;' in (o/(name+'.stdout.bin')).read_bytes();assert (o/(name+'.stderr.bin')).stat().st_size==0
for name in ['compile-native','compile-asan']:
 assert (o/(name+'.stderr.bin')).stat().st_size==0
 assert b'warning' not in (o/(name+'.stdout.bin')).read_bytes().lower()
reference=json.loads((o/'reference.stdout.bin').read_bytes());assert reference['status']=='PASS'
accept={'status':'PASS','nativeGroups':59,'asanGroups':59,'finiteFixtures':48,'nativeAsanFixtureBytesEqual':True,'fixtureBytes':len(normal),'fixtureSHA256':hashlib.sha256(normal).hexdigest(),'reference':reference,'commands':len(commands),'limits':{'surfaces':64,'candidates':448,'sqrtRefinements':32768},'unsupportedEnvironmentTests':['FE_UPWARD priority over invalid empty source','FTZ DAZ rejection and caller restore'],'scope':'Pure Native read-only enumeration, no ABI/World/CCD/manifold/response integration; source 3 files only.'}
(o/'acceptance.json').write_text(json.dumps(accept,indent=2)+'\n',encoding='utf-8')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=r,capture_output=True,check=True).stdout.decode().strip()
prov={'schema':1,'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseCommit':head,'ownedSources':[entry(p) for p in owned],'dependencies':[entry(p) for p in deps],'artifacts':[entry(str(p.relative_to(r)).replace('\\','/')) for p in sorted(o.glob('*')) if p.is_file() and p.suffix not in ['.obj','.pdb','.exe','.lib'] and p.name!='provenance.json'],'reproduce':['python build/sphere-triangle-mesh-core/run-proof.py','python build/sphere-triangle-mesh-core/run-asan.py','python build/sphere-triangle-mesh-core/finalize.py'],'compiler':'MSVC, vcvars64 from Visual Studio 18 BuildTools; /O2 /W4 /fp:strict, ASan separate /Zi /fsanitize=address; no third-party dependencies','limitations':['Finite corpus independent Fraction comparison is separate from interval construction proof.','ASan successful execution with actual stdout and zero exit, not inferred from silence.','Fault-injected allocation tests not added; fatal owned prefix contract separate from ordinary row failures.','No timing values are performance guarantees.']}
(o/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n',encoding='utf-8');print(json.dumps({'sources':prov['ownedSources'],'acceptance':accept},indent=2))
