import collections
import hashlib
import json
import pathlib
import re
import subprocess

root=pathlib.Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical_html(data):
    text=data.decode('utf-8').replace('\r\n','\n')
    assert len(re.findall(r'<script type="importmap" id="engine-imports">',text))==1
    text=re.sub(r'<script type="importmap" id="engine-imports">[\s\S]*?</script>','GENERATED_IMPORT_MAP',text)
    return re.sub(r'\?build=[0-9a-f]{16}','?build=GENERATED_BUILD',text)

allowedCode={'.gitattributes','engine/renderer.mjs','samples/app.mjs','samples/robot.mjs','samples/back-cover.mjs',
             'scripts/create-robot-back-cover.mjs','tests/derived-renderer.test.mjs','tests/robot-back-cover-source.test.mjs',
             'tests/robot-back-cover.test.mjs','assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json','index.html'}
allowedDocs={'docs/PLAN.md','docs/ROBOT_BACK_COVER.md','docs/learn/index.html','docs/learn/diagrams/robot-back-cover.svg',
             'docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md'}
excluded='reports/robot-cover-scope-audit.json'
paths=git('diff','--cached','--name-only','-z','--','.',':(exclude)'+excluded).decode().split('\0')[:-1]
rows=[]
for p in paths:
    data=git('show',':'+p)
    if (p.startswith('tools/') and p.endswith('.html')) or p=='docs/learn/buoyancy.html':
        old=git('show','HEAD:'+p)
        assert canonical_html(old)==canonical_html(data),'NON-GENERATED CHANGE '+p
        category='generated build URLs/import map only; exact remaining HTML unchanged'
    elif p in allowedCode:category='original cover source/game/renderer retirement implementation and regression tests'
    elif p in allowedDocs:category='required plan/lesson/original diagram/legal record for this feature'
    elif p.startswith('reports/robot-cover-') or p=='reports/2026-11-04-robot-cover.md':
        category='this feature verification recipes and retained raw measurements/logs/screenshots'
    else:raise RuntimeError('UNREVIEWED PATH '+p)
    assert data==(root/p).read_bytes(),p+' index/working bytes differ'
    rows.append(dict(path=p,category=category,bytes=len(data),newlines=data.count(b'\n'),sha256=sha(data)))
counts=collections.Counter(row['category'] for row in rows)
lineCounts=collections.Counter()
for row in rows:lineCounts[row['category']]+=row['newlines']
diff=git('diff','--cached','--binary','--','.',':(exclude)'+excluded)
record=dict(status='PASS',baseRevision=git('rev-parse','HEAD').decode().strip(),
            stagedDiffSHA256=sha(diff),stagedFiles=len(rows),categories=dict(counts),newlinesByCategory=dict(lineCounts),files=rows,
            authorization='AGENTS.md explicitly requires npm run build before milestone push and authorizes original engine/game development plus milestone commits/pushes. Existing user instruction also requires validation records, original diagrams and preservation of source assets.',
            noUnrelatedToolImplementationChanges=True,excludedSelfReferentialMetadata=excluded,
            scope='All tools HTML changes proven generated-only byte-for-byte after removing import maps/build tokens. No tools MJS or C++/SDK/kernel/package/workflow changes are staged. Approximately 100k added lines are predominantly retained JSON/log observations, not 100k implementation lines.')
(root/'reports/robot-cover-scope-audit.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({k:record[k] for k in ['status','baseRevision','stagedDiffSHA256','stagedFiles','categories','newlinesByCategory','noUnrelatedToolImplementationChanges']},indent=2))
