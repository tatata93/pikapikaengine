"""Accept exact-feature public bytes, fresh CI and Native-only closed coverage scope."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit
import ast
import json
import math
import re
import runpy
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-pair-coverage'
assert len(sys.argv)==3, 'Usage: public-summary.py FULL_FEATURE_COMMIT FRESH_SUMMARY_DIRECTORY'
FEATURE = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}',FEATURE)
assert subprocess.check_output(['git','rev-parse',FEATURE+'^{commit}'],cwd=ROOT,text=True).strip()==FEATURE
CHECKS = (ROOT/f'reports/{PREFIX}-checks').resolve()
CAPTURE = (ROOT/sys.argv[2]).resolve()
assert CAPTURE.is_dir() and CAPTURE.is_relative_to(CHECKS)
RECIPE = f'reports/{PREFIX}-recipes'
PUBLIC_RECIPE = RECIPE+'/public.py'
SOURCES = ['core/include/pikapika/accelerated_pair_coverage.hpp',
           'core/src/accelerated_pair_coverage.cpp',
           'tests/accelerated_pair_coverage_tests.cpp',
           'tests/accelerated_pair_coverage_fixtures.cpp',
           'tests/accelerated_pair_coverage_test_support.hpp',
           'scripts/verify-accelerated-pair-coverage.py',
           'tests/accelerated_pair_coverage_reference_tests.py']
evidence = {}


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT),p
    return p.relative_to(ROOT).as_posix()


def stamp(value):
    assert type(value['bytes']) is int and 0<=value['bytes']<=64*1024*1024
    assert type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256'])
    return {'bytes':value['bytes'],'sha256':value['sha256']}


def hash_bytes(raw):
    assert len(raw)<=64*1024*1024
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def remember(path):
    key = relative(path)
    evidence[key] = hash_bytes((ROOT/key).read_bytes())
    return evidence[key]


def read(path):
    remember(path)
    def floating(token):
        value = float(token)
        assert math.isfinite(value) and not (value==0 and any(c in '123456789' for c in token.lower().split('e')[0]))
        return value
    def pairs(items):
        result = {}
        for key,value in items:
            assert key not in result,key
            result[key] = value
        return result
    return json.loads((ROOT/relative(path)).read_text(encoding='utf-8-sig'),parse_float=floating,
                      parse_int=lambda t:-0.0 if t=='-0' else int(t),object_pairs_hook=pairs,
                      parse_constant=lambda t:(_ for _ in ()).throw(AssertionError(t)))


def git_blobs(commit,paths):
    assert re.fullmatch('[0-9a-f]{40}',commit)
    paths = sorted(set(paths));assert len(paths)<=2048
    for path in paths:
        p = PurePosixPath(path)
        assert not p.is_absolute() and '..' not in p.parts and p.as_posix()==path
    raw = subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
                                  input=''.join(commit+':'+p+'\n' for p in paths).encode())
    assert len(raw)<=128*1024*1024
    result = {};offset = 0
    for path in paths:
        end = raw.index(b'\n',offset);header = raw[offset:end].split()
        assert len(header)==3 and header[1]==b'blob',path
        size = int(header[2]);assert 0<=size<=64*1024*1024
        offset = end+1;result[path] = raw[offset:offset+size]
        assert len(result[path])==size and raw[offset+size:offset+size+1]==b'\n'
        offset += size+1
    assert offset==len(raw)
    return result


def current_vs_blob(path,blob):
    raw = (ROOT/path).read_bytes()
    if raw==blob:
        conversion = None
    else:
        assert Path(path).suffix in {'.cpp','.hpp','.h','.py','.mjs','.yml','.md','.json','.html','.css','.txt'} or path in {'CMakeLists.txt','.gitattributes'}
        assert b'\r\n' in raw and raw.replace(b'\r\n',b'\n')==blob,path
        conversion = 'Declared Git-text CRLF-to-LF only after exact raw comparison.'
    return {'raw':remember(path),'featureBlob':hash_bytes(blob),'normalization':conversion}


def normalized_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',
                  re.sub(rb'\?build=[a-f0-9]{16}',b'',raw),flags=re.S).replace(b'\r\n',b'\n')


def jpeg_dimensions(raw):
    assert raw[:2]==b'\xff\xd8'
    at = 2
    while at+4<=len(raw):
        assert raw[at]==255
        marker = raw[at+1];at += 2
        length = int.from_bytes(raw[at:at+2],'big')
        assert length>=2 and at+length<=len(raw)
        if marker in (192,193,194):
            assert length>=7
            return int.from_bytes(raw[at+5:at+7],'big'),int.from_bytes(raw[at+3:at+5],'big')
        at += length
    raise AssertionError('No JPEG frame')


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self,data):
        self.parts.append(data)


local_path = f'reports/{PREFIX}-local-verification.json'
local = read(local_path);base = read(f'reports/{PREFIX}-baseline.json')
assert local['status']=='PASS' and local['baseCommit']==base['baseCommit']=='41c9cc2d28817e3491b8ab8e47922cc5cc153ae5'
for key,value in {'ctest':43,'nativeGroups':69,'finiteFixtures':65,'node':684,'skipped':0,
                  'selfTestGroups':14,'negativeControls':53,'exports':92,'sourceHeaders':67,
                  'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
                  'protectedFilesUnchanged':362,'generatedEntriesUnchanged':26,'modules':54}.items():
    assert type(local[key]) is int and local[key]==value,key
assert local['webBuild']=='cd45c7f1ac2ba5e5' and len(base['protected'])==362 and len(base['generatedEntries'])==26
assert set(local['newSources'])==set(SOURCES)
for path,value in local['evidence'].items():
    assert remember(path)==stamp(value),path
assert set(base['permittedOldSources'])=={'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'}
helper_paths = [RECIPE+'/summary.py',RECIPE+'/summary-run.py',PUBLIC_RECIPE,RECIPE+'/check.py',
                RECIPE+'/browser-record.py']
feature_paths = set(base['protected'])|set(base['generatedEntries'])|set(base['permittedOldSources'])|set(SOURCES)|set(helper_paths)
feature_blobs = git_blobs(FEATURE,feature_paths)
base_blobs = git_blobs(base['baseCommit'],[*base['protected'],*base['generatedEntries'],*base['permittedOldSources']])
source_comparisons = {}
for path,value in base['protected'].items():
    assert remember(path)==stamp(value) and base_blobs[path]==feature_blobs[path],path
for path in SOURCES:
    assert remember(path)==stamp(local['newSources'][path]),path
    source_comparisons[path] = current_vs_blob(path,feature_blobs[path])
for path in helper_paths:
    source_comparisons[path] = current_vs_blob(path,feature_blobs[path])
for path,value in base['generatedEntries'].items():
    assert remember(path)==stamp(value)==local['generatedEntries'][path]['raw'],path
    assert normalized_html(base_blobs[path])==normalized_html(feature_blobs[path])==normalized_html((ROOT/path).read_bytes()),path

# Reuse the *literal* authorized fragments of the frozen local verifier, not its
# executable aggregation. Its current bytes above also match the feature blob.
tree = ast.parse((ROOT/RECIPE/'summary.py').read_text())
fragments = {}
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'CMAKE_LIBRARY','CMAKE_TEST','CI_MAIN','CI_AUDIT','ATTRS'}:
        fragments[node.targets[0].id] = ast.literal_eval(node.value)
assert set(fragments)=={'CMAKE_LIBRARY','CMAKE_TEST','CI_MAIN','CI_AUDIT','ATTRS'}
old_changes = {}
for path,names in [('CMakeLists.txt',['CMAKE_LIBRARY','CMAKE_TEST']),
                   ('.github/workflows/verify.yml',['CI_MAIN','CI_AUDIT']),('.gitattributes',['ATTRS'])]:
    archived = base['permittedOldSources'][path]
    old = archived['gitBlobUtf8'].encode()
    assert hash_bytes(old)==stamp(archived['gitBlob']) and old==base_blobs[path]
    raw = (ROOT/path).read_bytes();reconstructed = raw
    for name in names:
        chunk = fragments[name].encode()
        if reconstructed.count(chunk)!=1:chunk = chunk.replace(b'\n',b'\r\n')
        assert reconstructed.count(chunk)==1,path
        reconstructed = reconstructed.replace(chunk,b'',1)
    if reconstructed!=old:
        assert b'\r\n' in reconstructed and reconstructed.replace(b'\r\n',b'\n')==old,path
    old_changes[path] = {**current_vs_blob(path,feature_blobs[path]),'baseGitBlob':hash_bytes(old),
                         'authorizedFragments':names,'reconstruction':'Exact insertions and declared text CRLF-to-LF only.'}

manifest = read('assets/pikapika-simulation.build.json')
assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92 and all('accelerated_pair_coverage' not in f for f in exports)
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:
    assert remember(path)['sha256']==value,path
for path,value in local['artifacts'].items():
    assert remember(path)==stamp(value),path
assert local['artifacts']['assets/pikapika-simulation.wasm']['bytes']==800982
assert local['artifacts']['assets/pikapika-simulation.mjs']['bytes']==61661
for row in local['commands']:
    assert type(row['exit']) is int and row['exit']==0 and row.get('timedOut',False) is False
    assert row['sourceStable'] is True and row['sourceBefore']==row['sourceAfter']
    for path,value in row['sourceAfter'].items():
        if path==RECIPE+'/check.py' and stamp(value)==stamp(local['recorderEvidenceExtensionChange']['source']['before']):
            archived = local['recorderEvidenceExtensionChange']['source']['beforeArchive']
            assert remember(archived)==stamp(value)
            assert (ROOT/archived).read_bytes().replace(b"(out/'LastTest.log').write_bytes",b"(out/'LastTest.txt').write_bytes")== (ROOT/path).read_bytes()
        else:
            assert remember(path)==stamp(value),path
    for stream in ['stdout','stderr']:assert remember(row[stream])==stamp(row[stream+'Hash'])
independent = local['independentReference']
assert independent['status']=='PASS' and independent['inputFingerprint']=='867fef69e55cf8461310b07f0144c8d2288987ab68311d6d86a04b01e8cca85e'
assert {k:independent[k] for k in ['fixtures','certified','notCertified','invalidInputs','cellAudits','returnedIntervals','planeRangeProofs','sphereRangeProofs','maximumAudits','maximumPartition','maximumFrontier','subdividedCertified']}=={
    'fixtures':65,'certified':18,'notCertified':19,'invalidInputs':28,'cellAudits':1913,'returnedIntervals':1913,
    'planeRangeProofs':690,'sphereRangeProofs':1223,'maximumAudits':255,'maximumPartition':128,'maximumFrontier':127,'subdividedCertified':2}
assert local['nativePublicValueExactBitReplays']==1913 and local['nativeNegativeZeroIntervalBounds']==0
assert local['positiveControls']['mathematicallyValidWiderIntervalAccepted'] is True
assert local['positiveControls']['syntheticNonreturnedAttemptAccepted'] is True

public = read(f'reports/{PREFIX}-public-bytes.json')
runs = read(f'reports/{PREFIX}-public-runs.json')
assert public['schema']==1 and public['status']=='PASS' and public['commit']==FEATURE and public['build']==local['webBuild']
assert public['channels']=={'pages':83,'githubSource':1}
assert runs['schema']==1 and runs['commit']==FEATURE
paths = runpy.run_path(str(ROOT/PUBLIC_RECIPE))['PATHS']
assert len(paths)==len(set(paths))==84 and len(public['files'])==84
assert {r['path'] for r in public['files']}==set(paths)
public_blobs = git_blobs(FEATURE,paths)
for item in public['files']:
    assert stamp(item)==hash_bytes(public_blobs[item['path']]),item['path']
    url = urlsplit(item['url'])
    if item['path']=='.github/workflows/verify.yml':
        assert item['distribution']=='github-source' and url.scheme=='https' and url.netloc=='raw.githubusercontent.com'
        assert unquote(url.path)=='/tatata93/pikapikaengine/'+FEATURE+'/.github/workflows/verify.yml'
        assert not url.query and not url.fragment
        continue
    assert item['distribution']=='pages'
    assert url.scheme=='https' and url.netloc=='tatata93.github.io' and unquote(url.path)=='/pikapikaengine/'+item['path']
    if item['path'].startswith('assets/') or item['path'].endswith('.mjs'):
        assert parse_qs(url.query)=={'build':[public['build']]}
    else:
        assert parse_qs(url.query)=={'v':[FEATURE[:7]]}
assert Counter(r['distribution'] for r in public['files'])=={'pages':83,'github-source':1}

# Exact successful run/job/step provenance. The connector does not supply
# job.head_sha; the containing run head and each job.run_id establish linkage.
assert len(runs['runs'])==2 and len({r['id'] for r in runs['runs']})==2
assert {r['name'] for r in runs['runs']}=={'Engine verification','pages build and deployment'}
jobs = []
for run in runs['runs']:
    assert run['head_sha']==FEATURE and run['status']=='completed' and run['conclusion']=='success'
    found = read(f'reports/{PREFIX}-run-{run["id"]}.json')['jobs']
    assert found
    for job in found:
        assert job['run_id']==run['id'] and job['status']=='completed' and job['conclusion']=='success'
        assert job['steps'] and all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'])
    jobs.extend(found)
assert len(jobs)==4
engine = [j for j in jobs if j['name']=='portable-core'];assert len(engine)==1
engine = engine[0]
workflow = feature_blobs['.github/workflows/verify.yml'].decode()
step_names = ['Set up job']+re.findall(r'^      - name: (.+)$',workflow,re.M)+['Complete job']
assert len(step_names)==len(engine['steps'])==23 and [s['name'] for s in engine['steps']]==step_names
assert 'Audit owned accelerated pair coverage independently' in step_names
log = read(f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json')
assert log['jobId']==engine['id'] and log['runId']==engine['run_id'] and log['commit']==FEATURE
assert type(log['fullLineCount']) is int and 0<len(log['lines'])<=16384
ordinals = [r['line'] for r in log['lines']]
assert all(type(n) is int for n in ordinals) and ordinals==sorted(set(ordinals)) and 1<=ordinals[0]<=ordinals[-1]<=log['fullLineCount']
text = '\n'.join(r['text'] for r in log['lines'])
clean = re.sub(r'\x1b\[[0-9;]*m','',text)
for marker in ['100% tests passed, 0 tests failed out of 43','# tests 684','# pass 684','# fail 0','# skipped 0',
               'Accelerated pair coverage: 69 groups PASS; 65 finite fixtures; 1913 actual public-value exact-bit replays, 0 negative-zero interval bounds.',
               'Range mathematics is a separate independent reference; natural allocation/value-throw fault injection not performed.']:
    assert marker in clean,marker
for name in ['CI_MAIN','CI_AUDIT']:
    for line in fragments[name].splitlines():
        # Keep the loop terminator as well as every literal command. ANSI-coded
        # original lines are retained in the excerpt and stripped only above.
        if line.strip() and not line.lstrip().startswith(('run:','- name:')):
            assert line.strip() in clean,line
proofs = []
for line in log['lines']:
    value = re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ','',line['text']).strip()
    if value.startswith('{') and value.endswith('}'):
        try:proofs.append(json.loads(value))
        except json.JSONDecodeError:pass
linux_reports = [p for p in proofs if type(p) is dict and p.get('inputFingerprint')==independent['inputFingerprint']]
assert len(linux_reports)>=2 and all(p==independent for p in linux_reports)
assert any(p=={'status':'PASS','selfTestGroups':14,'fixtures':65,'labelAndOrderIndependent':True,
               'rejectedControls':53,'positiveControls':local['positiveControls']} for p in proofs)
prior = read(base['priorPublicReceipt'])
old_engine = [j for j in prior['jobs'] if j['name']=='portable-core'];assert len(old_engine)==1
old_log = read(f'reports/world-static-mesh-preparation-job-{old_engine[0]["id"]}-excerpt.json')


def warning_records(data):
    result = []
    for row in data['lines']:
        if 'warning:' not in row['text']:continue
        match = re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$',row['text'])
        assert match,row['text']
        result.append((match[1],int(match[2]),int(match[3]),match[4]))
    return result


warnings,old_warnings = warning_records(log),warning_records(old_log)
assert len(warnings)==len(old_warnings)==48 and Counter(warnings)==Counter(old_warnings)

# Fresh public captures belong only to this milestone. No old network/helper
# failure exception is carried forward, and this verifier's own folders are out.
command_paths = sorted(p for p in CHECKS.rglob('*commands.json')
                       if 'public' in str(p.relative_to(CHECKS)) and 'public-summary' not in str(p))
assert 1<=len(command_paths)<=128
public_commands = []
failed_attempts = []
for path in command_paths:
    for command in read(path):
        if command['name'] not in {'status','bytes','browser-record'}:continue
        if command['name']=='browser-record':
            assert command['args'][-2:]==[RECIPE+'/browser-record.py',FEATURE]
            assert command['sourceStable'] is True and command['sourceBefore']==command['sourceAfter']
            assert set(command['sourceAfter'])=={RECIPE+'/browser-record.py'}
            for source,value in command['sourceAfter'].items():assert remember(source)==stamp(value),source
        else:
            assert command['args'][-3:]==[PUBLIC_RECIPE,command['name'],FEATURE]
        assert type(command['exit']) is int
        assert type(command['wallSeconds']) in (int,float) and math.isfinite(command['wallSeconds']) and command['wallSeconds']>=0
        datetime.fromisoformat(command['started'])
        for stream in ['stdout','stderr']:assert remember(command[stream])==stamp(command[stream+'Hash'])
        # Public failures are preserved and require explicit review, never a silent success exception.
        assert command['exit']==0
        public_commands.append({**command,'commandFile':relative(path)})
assert failed_attempts==[]
assert {r['name'] for r in public_commands}=={'status','bytes','browser-record'}
latest = {name:max((r for r in public_commands if r['name']==name),key=lambda r:datetime.fromisoformat(r['started'])) for name in ['status','bytes']}
statuses = read(latest['status']['stdout'])
assert len(statuses)==2 and {r['id'] for r in statuses}=={r['id'] for r in runs['runs']}
for status in statuses:
    actual = next(r for r in runs['runs'] if r['id']==status['id'])
    assert all(status[k]==actual[k] for k in ['id','name','status','conclusion','html_url'])
assert read(latest['bytes']['stdout'])=={'status':'PASS','files':84,'bytes':sum(r['bytes'] for r in public['files']),'build':public['build'],'channels':public['channels']}
# The browser contract is deliberately required, not synthesized while pending.
# Only a concept SVG/lesson and the unchanged game run here: no Native coverage
# execution, numerical browser query, Native/WASM parity or geometry proof.
browser_dir = ROOT/f'reports/{PREFIX}-public-browser'
browser = read(browser_dir/'browser-verification.json')
assert type(browser['schema']) is int and browser['schema']==1 and browser['status']=='PASS' and browser['phase']=='public'
assert browser['commit']==FEATURE
assert browser['buildId']==public['build'] and browser['wasmBytes']==800982
assert browser['recipe']=={'path':RECIPE+'/browser-record.py',**remember(RECIPE+'/browser-record.py')}
assert browser['publicByteReceipt']=={'path':f'reports/{PREFIX}-public-bytes.json',**remember(f'reports/{PREFIX}-public-bytes.json')}
assert browser['scope']=='Native-only pair coverage: public diagram/lesson display and existing game compatibility; no browser coverage query.'
assert browser['diagram']['path']=='docs/learn/diagrams/accelerated-pair-coverage.svg'
assert browser['diagramBottom']['path']==browser['diagram']['path']
assert browser['lesson']['path']=='docs/learn/index.html'
for key in ['diagram','diagramBottom','lesson']:
    observed = browser[key];url = urlsplit(observed['url'])
    assert url.scheme=='https' and url.netloc=='tatata93.github.io' and unquote(url.path)=='/pikapikaengine/'+observed['path']
    assert parse_qs(url.query)=={'v':[FEATURE[:7]]}
    assert observed['source']==hash_bytes(public_blobs[observed['path']])
    assert relative(observed['screenshot'])==relative(browser_dir/(('diagram-bottom' if key=='diagramBottom' else key)+'.jpg'))
    assert relative(observed['accessibility'])==relative(browser_dir/(('diagram-bottom' if key=='diagramBottom' else key)+'-ax.txt'))
    assert remember(observed['screenshot'])['bytes']>0 and remember(observed['accessibility'])['bytes']>0
for path,value in browser['evidence'].items():
    assert (ROOT/relative(path)).is_relative_to(browser_dir)
    assert remember(path)==stamp(value),path
required_capture = {relative(browser_dir/name) for name in ['diagram.jpg','diagram-ax.txt','diagram-bottom.jpg','diagram-bottom-ax.txt','lesson.jpg','lesson-ax.txt',
                    'public-game.jpg','public-game-ax.txt','public-game-cover-report.json','lesson-article.txt','observations.json']}
assert required_capture==set(browser['evidence']) and len(browser['evidence'])==11
observations = read(browser_dir/'observations.json')
assert set(observations['observedURL'])=={'diagram','diagramBottom','lesson','game'}
for key in ['diagram','diagramBottom','lesson']:
    assert observations['observedURL'][key]==browser[key]['url']
game_url = urlsplit(observations['observedURL']['game'])
assert game_url.scheme=='https' and game_url.netloc=='tatata93.github.io'
assert game_url.path in {'/pikapikaengine/','/pikapikaengine/index.html'} and parse_qs(game_url.query)=={'v':[FEATURE[:7]]}
lesson_source = public_blobs[browser['lesson']['path']].decode('utf-8')
articles = [m for m in re.finditer(r'<article\b([^>]*)>(.*?)</article>',lesson_source,re.S)
            if 'accelerated-pair-coverage.svg' in m[2]]
assert len(articles)==1
article = articles[0]
article_id = re.search(r'\bid="([a-z0-9_-]+)"',article[1])[1]
image_sources = re.findall(r'<img\b[^>]*\bsrc="([^"]*accelerated-pair-coverage\.svg)"',article[2])
guide_hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]*ACCELERATED_PAIR_COVERAGE\.md)"',article[2])
assert article_id=='accelerated' and urlsplit(browser['lesson']['url']).fragment=='accelerated'
assert image_sources==['diagrams/accelerated-pair-coverage.svg'] and guide_hrefs==['../ACCELERATED_PAIR_COVERAGE.md']
image = observations['lessonImage']
assert image['src']==image_sources[0] and image['complete'] is True
assert type(image['naturalWidth']) is int and type(image['naturalHeight']) is int
assert (image['naturalWidth'],image['naturalHeight'])==(1120,780)
assert observations['guideHref']==guide_hrefs[0]
assert observations['lessonArticleFile']==relative(browser_dir/'lesson-article.txt')
article_text = (ROOT/observations['lessonArticleFile']).read_text(encoding='utf-8-sig')
parser = ArticleText();parser.feed(article[0]);parser.close()
assert re.sub(r'\s+','',article_text)==re.sub(r'\s+','',''.join(parser.parts))
assert type(observations['files']) is list and len(observations['files'])==len(set(observations['files']))
visual_files = {relative(browser_dir/name) for name in ['diagram.jpg','diagram-ax.txt','diagram-bottom.jpg','diagram-bottom-ax.txt','lesson.jpg','lesson-ax.txt','public-game.jpg','public-game-ax.txt']}
assert visual_files|{relative(browser_dir/'lesson-article.txt')}<=set(observations['files'])<=visual_files|{
    relative(browser_dir/'public-game-cover-report.json'),relative(browser_dir/'lesson-article.txt')}
assert set(observations['files'])<=set(browser['evidence'])
screens = {}
for path in sorted(visual_files):
    if path.endswith('.jpg'):
        width,height = jpeg_dimensions((ROOT/path).read_bytes())
        assert 200<=width<=4096 and 100<=height<=4096
        screens[path] = {'width':width,'height':height,**remember(path)}
game = read(browser_dir/'public-game-cover-report.json')
state = (browser_dir/'public-game-ax.txt').read_text(encoding='utf-8-sig')
for name in ['public-game.jpg','public-game-ax.txt']:assert remember(browser_dir/name)['bytes']>0
assert game['state']=='ready' and game['failure'] is None and game['pending'] is None and game['errors']==[]
assert '一時停止 / Pで再開' in state
kills = re.search(r'撃破\s+(\d+)',state);assert kills and int(kills[1])>0
queries = game['counts']['queries']
assert all(type(game['counts'][key]) is int for key in ['queries','checked','validated'])
assert type(queries) is int and queries>0 and queries==game['counts']['checked']==game['counts']['validated']==len(game['records'])
assert all(r['state']=='completed' for r in game['records']) and any(r['clipSeconds']==1 for r in game['records'])
assert game['renderer']['residentMeshes']==3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId']==public['build'] and game['startup']['diagnostics']['wasmBytes']==800982
asset = urlsplit(game['startup']['assetURL'])
assert asset.scheme=='https' and asset.netloc=='tatata93.github.io' and asset.path=='/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset.query).get('build')==[public['build']]
browser_commands = [r for r in public_commands if r['name']=='browser-record']
assert browser_commands
for command in browser_commands:
    assert read(command['stdout'])=={'status':'PASS','commit':FEATURE,'capturedEvidence':len(browser['evidence']),
                                     'buildId':browser['buildId'],'gameQueries':queries,'scope':browser['scope']}
# UI operation history is not a command failure or passed compatibility run.
ui_history_dir = ROOT/f'reports/{PREFIX}-public-browser-development/run-001'
ui_note_path = ui_history_dir/'note.json'
ui_ax_path = ui_history_dir/'first-defeat-ax.txt'
ui_note = read(ui_note_path)
assert type(ui_note['schema']) is int and ui_note['schema']==1 and ui_note['feature']==FEATURE
assert type(ui_note['scope']) is str and ui_note['scope'].startswith('Observed UI-operation history only;')
ui_ax = ui_ax_path.read_text(encoding='utf-8-sig')
assert 'DEFEAT' in ui_ax and re.search(r'撃破\s+1\s+機.*経過\s+21\s+秒',ui_ax)
assert '/pikapikaengine/?v='+FEATURE[:7] in ui_ax
ui_operation_history = {
    'note':{'path':relative(ui_note_path),**remember(ui_note_path),'record':ui_note},
    'firstDefeatAccessibility':{'path':relative(ui_ax_path),**remember(ui_ax_path)},
    'acceptedCompatibilityEvidence':False,
    'scope':'Separate observed input/preparation timing history: no F key was sent by the timed-out container8 attempt; subsequent focused input worked and the live game reached normal defeat. The fresh restart compatibility capture above is required independently. No model/product bug or successful pause/boost result is inferred from this history.'}

development = {}
for path in sorted((ROOT/f'reports/{PREFIX}-public-summary-development').rglob('*')):
    if path.is_file() and path.suffix.lower() not in {'.exe','.obj','.lib','.pdb','.ilk','.log'}:
        development[relative(path)]=remember(path)
remember(__file__)
assert len(evidence)<=4096 and sum(v['bytes'] for v in evidence.values())<=256*1024*1024
report = {'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':FEATURE,
          'localVerification':{'path':local_path,**remember(local_path)},'ctest':43,'node':684,'skipped':0,
          'nativeGroups':69,'finiteFixtures':65,'nativePublicValueExactBitReplays':1913,'nativeNegativeZeroIntervalBounds':0,'independentReference':independent,'selfTestGroups':14,'negativeControls':53,
          'localNativeScope':'Recorded MSVC Native65 input/result coverage audit and exact public-value replay, separate from the fresh Linux and instrumented executions.',
          'publicCiScope':{'engineSteps':23,'linuxIndependentReports':len(linux_reports),
                           'regularAndFullyInstrumentedFixturesCompared':True,'newWarningAuditedTranslationUnits':3,'fullyInstrumentedTranslationUnits':5,
                           'scope':'GNU Native and all five dependent TUs instrumented under ASan/UBSan, exact regular/instrumented fixture cmp and full-cell mathematical audits; no Native/WASM coverage parity.'},
          'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
          'protectedFilesUnchanged':362,'generatedEntriesUnchanged':26,'modules':54,'entries':26,'webBuild':public['build'],
          'artifacts':local['artifacts'],'sourceComparisons':source_comparisons,'permittedOldChanges':old_changes,
          'publicFiles':84,'publicChannels':public['channels'],'publicBytes':sum(r['bytes'] for r in public['files']),'publicCommands':public_commands,
          'failedAttempts':failed_attempts,'uiOperationHistory':ui_operation_history,
          'jobs':jobs,'warnings':{'current':48,'prior':48,'sameFileLineColumnDiagnosticMultiset':True,'new':0},
          'browser':browser,'browserObservations':observations,'browserScreens':screens,
          'lessonArticleVerification':{'characters':len(article_text),'sourceArticle':article_id,
              'scope':'Complete visible text equals feature article data after whitespace removal; screenshot/AX and actual image-load observations remain separate display evidence.'},
          'publicGame':{'paused':True,'kills':int(kills[1]),'queries':queries,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3},
          'historicalAttempts':local['historicalAttempts'],'collectionNotes':local['collectionNotes'],
          'postFeatureVerifiers':{p:remember(p) for p in [RECIPE+'/public-summary.py',RECIPE+'/public-summary-run.py']},
          'publicVerifierDevelopment':development,
          'recorderEvidenceExtensionChange':local['recorderEvidenceExtensionChange'],
          'localVerificationLimitations':{'recordedLocalNotes':local['notMeasured'],
              'scope':'Local-stage notes remain historical; the separate publicCiScope above is the fresh Linux/sanitizer execution evidence.'},
          'scope':'Native point-coefficient sphere-pair/raw-plane whole-cell noncontact coverage only. Mathematical containment and exact public-value output provenance remain separate. Existing browser game does not execute this helper. No World propagation, inflation, candidate, entry/TOI/response/advance, natural fault injection or used-heap/stack/process memory guarantee is inferred.',
          'ciEvidenceScope':'Exact feature run/job/all-step states, original finite command/test excerpts and all warning records; full remote logs are not claimed archived.',
          'evidence':evidence}
(ROOT/f'reports/{PREFIX}-public-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','commit','ctest','node','publicFiles','publicChannels','publicBytes','webBuild']}))
