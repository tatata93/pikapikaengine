"""Individually enumerate and audit the lab publication paths before staging."""
from pathlib import Path
from hashlib import sha256
import json,re,subprocess
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-lab'
base=json.loads((root/f'reports/{prefix}-baseline.json').read_text());local=json.loads((root/f'reports/{prefix}-local-verification.json').read_text())
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def info(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
assert git('rev-parse','HEAD').decode().strip()==base['baseCommit']
assert not git('diff','--cached','--name-only').strip(),'Index must be empty before this publication audit'
assert local['status']=='PASS' and local['node']==684 and local['focused']==23
def blob(path):return git('show',base['baseCommit']+':'+path)
for path,expected in base['protected'].items():assert info((root/path).read_bytes())==expected,path
def norm(data):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'',data),flags=re.S).replace(b'\r\n',b'\n')
generated=list(base['generatedEntries']);assert len(generated)==25
for path in generated:assert norm((root/path).read_bytes())==norm(blob(path)),path
old_build=blob('scripts/build-web.mjs');new_build=(root/'scripts/build-web.mjs').read_bytes();addition=b"['tools/sphere-triangle-mesh-flight-lab.html','../','sphere-triangle-mesh-flight-lab.mjs'],"
assert new_build.count(addition)==1 and new_build.replace(addition,b'',1)==old_build
old_test=blob('tests/web-build.test.mjs');new_test=(root/'tests/web-build.test.mjs').read_bytes();assert new_test.replace(b"count,26,'all current game/lab/lesson entry points'",b"count,25,'all current game/lab/lesson entry points'",1)==old_test
workflow=(root/'.github/workflows/verify.yml').read_bytes().replace(b'\r\n',b'\n');line=b'          node scripts/verify-sphere-triangle-mesh-flight-lab.mjs build/ci/sphere-triangle-mesh-flight-lab\n'
assert workflow.count(line)==1 and workflow.replace(line,b'',1)==blob('.github/workflows/verify.yml')
appended=['docs/RESEARCH.md','docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md']
for path in appended:assert (root/path).read_bytes().replace(b'\r\n',b'\n').startswith(blob(path)),path
old_plan=blob('docs/PLAN.md').decode();plan=(root/'docs/PLAN.md').read_text(encoding='utf8');paragraph=lambda t:re.sub(r'再開位置:.*?(?=\n\n)','再開位置:GENERATED-MILESTONE',t,count=1,flags=re.S);assert paragraph(old_plan)==paragraph(plan)
lesson_old=blob('docs/learn/index.html').decode();lesson=(root/'docs/learn/index.html').read_text(encoding='utf8');start=lesson.index('<figure><img src="diagrams/sphere-triangle-mesh-flight-lab.svg"');end=lesson.index('</article>',start);assert lesson[:start]+lesson[end:]==lesson_old
paths=set(generated+appended+['.github/workflows/verify.yml','docs/PLAN.md','docs/learn/index.html','docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB.md','docs/learn/diagrams/sphere-triangle-mesh-flight-lab.svg','scripts/build-web.mjs','scripts/verify-sphere-triangle-mesh-flight-lab.mjs','tests/web-build.test.mjs','tests/sphere-triangle-mesh-flight-lab.test.mjs','tools/sphere-triangle-mesh-flight-lab.html','tools/sphere-triangle-mesh-flight-lab.mjs','tools/sphere-triangle-mesh-flight-presets.mjs',f'reports/2026-11-04-{prefix}.md'])
# Only this milestone's newly created report roots are eligible; every actual
# file is enumerated below. No wildcard reaches Git or another authoring area.
for entry in (root/'reports').iterdir():
 if not entry.name.startswith(prefix+'-'):continue
 for path in ([entry] if entry.is_file() else sorted(entry.rglob('*'))):
  if path.is_file() and path.relative_to(root).as_posix()!=f'reports/{prefix}-recipes/public-summary.py':paths.add(path.relative_to(root).as_posix())
paths.update([f'reports/{prefix}-publication-audit.json',f'reports/{prefix}-publication-paths.json',f'reports/{prefix}-publication-paths.nul'])
assert not any(any(c in p for c in '*?[]\n\r\x00') for p in paths)
assert all(not p.startswith(('core/','engine/','assets/','samples/','platform/')) for p in paths)
audit={'schema':1,'status':'PASS','baseCommit':base['baseCommit'],'protectedFilesUnchanged':len(base['protected']),'existingGeneratedHtmlBodiesUnchanged':25,'buildEntryOnly':True,'testEntryCountOnly':True,'ciOneProofCommandOnly':True,'researchAndLegalAppendOnly':appended,'planOnlyResumeParagraph':True,'lessonOnlyOneOriginalFigureAndLabExplanation':True,'scope':'Exact individual paths; future World design and public-summary draft excluded. Existing349 sources/artifacts unchanged; only25 generated HTML maps/URLs and three declared integration fragments change.'}
manifest=root/f'reports/{prefix}-publication-paths.json';manifest.write_text(json.dumps(sorted(paths),indent=2)+'\n',encoding='utf8')
(root/f'reports/{prefix}-publication-paths.nul').write_bytes(b'\x00'.join(p.encode() for p in sorted(paths))+b'\x00')
audit['paths']=sorted(paths);audit['files']=len(paths);audit['pathListHash']=info(manifest.read_bytes());(root/f'reports/{prefix}-publication-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in audit.items() if k!='paths'}))
