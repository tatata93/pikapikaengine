"""Accept exact-feature public bytes, fresh CI and Native-only closed coverage scope."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit
import ast
import difflib
import json
import math
import re
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-sphere-box-coverage'
assert len(sys.argv)==3, 'Usage: public-summary.py FULL_FEATURE_COMMIT FRESH_SUMMARY_DIRECTORY'
FEATURE = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}',FEATURE)
assert subprocess.check_output(['git','rev-parse',FEATURE+'^{commit}'],cwd=ROOT,text=True).strip()==FEATURE
CHECKS = (ROOT/f'reports/{PREFIX}-checks').resolve()
CAPTURE = (ROOT/sys.argv[2]).resolve()
assert CAPTURE.is_dir() and CAPTURE.is_relative_to(CHECKS) and not (CAPTURE/'acceptance.json').exists()
RECIPE = f'reports/{PREFIX}-recipes'
PUBLIC_RECIPE = RECIPE+'/public.py'
SOURCES = ['core/include/pikapika/accelerated_sphere_box_coverage.hpp',
           'core/src/accelerated_sphere_box_coverage.cpp',
           'tests/accelerated_sphere_box_coverage_tests.cpp',
           'tests/accelerated_sphere_box_coverage_fixtures.cpp',
           'tests/accelerated_sphere_box_coverage_test_support.hpp',
           'scripts/verify-accelerated-sphere-box-coverage.py',
           'tests/accelerated_sphere_box_coverage_reference_tests.py']
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


SCOPE='Native-only conditional sphere-box helper: public diagram/lesson display and existing game compatibility; no browser numerical query or actual World certification.'

def literals(raw,names):
    found={}
    for node in ast.parse(raw.decode('utf-8')).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            if node.targets[0].id in names:found[node.targets[0].id]=ast.literal_eval(node.value)
    assert set(found)==set(names)
    return found


def workflow_commands(stage):
    return [line.strip() for line in stage.splitlines()
            if line.strip() and not line.lstrip().startswith(('- name:','run:'))]


def warnings_from_lines(lines):
    result=[]
    for line in lines:
        if 'warning:' not in line:continue
        match=re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$',line)
        assert match,line
        result.append({'file':match[1],'line':int(match[2]),'column':int(match[3]),'diagnostic':match[4]})
    return result


def warning_multiset(rows):
    assert type(rows) is list
    result=[]
    for row in rows:
        assert set(row)=={'file','line','column','diagnostic'}
        assert type(row['file']) is type(row['diagnostic']) is str
        assert type(row['line']) is type(row['column']) is int and row['line']>0 and row['column']>0
        result.append((row['file'],row['line'],row['column'],row['diagnostic']))
    return Counter(result)


local_path = f'reports/{PREFIX}-local-verification.json'
local = read(local_path);base = read(f'reports/{PREFIX}-baseline.json')
assert local['status']=='PASS' and local['baseCommit']==base['baseCommit']=='2901905b56c984f1b0a946684143d64394eda6c4'
for key,value in {'ctest':45,'nativeGroups':84,'finiteFixtures':75,'node':684,'skipped':0,
                  'selfTestGroups':16,'negativeControls':89,'exports':92,'sourceHeaders':67,
                  'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
                  'protectedFilesUnchanged':376,'generatedEntriesUnchanged':26,'modules':54}.items():
    assert type(local[key]) is int and local[key]==value,key
assert local['webBuild']=='cd45c7f1ac2ba5e5' and len(base['protected'])==376 and len(base['generatedEntries'])==26
assert set(local['newSources'])==set(SOURCES)
for path,value in local['evidence'].items():
    assert remember(path)==stamp(value),path
assert set(base['permittedOldSources'])=={'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'}
helper_paths = [RECIPE+'/summary.py',RECIPE+'/summary-run.py',PUBLIC_RECIPE,RECIPE+'/check.py',
                RECIPE+'/integrate.py',RECIPE+'/integrate-lesson.py',RECIPE+'/prepare.py',RECIPE+'/public-check.py']
feature_paths = set(base['protected'])|set(base['generatedEntries'])|set(base['permittedOldSources'])|set(SOURCES)|set(helper_paths)|{base['priorPublicReceipt'],'docs/learn/index.html'}
feature_blobs = git_blobs(FEATURE,feature_paths)
base_blobs = git_blobs(base['baseCommit'],[*base['protected'],*base['generatedEntries'],*base['permittedOldSources'],base['priorPublicReceipt'],'docs/learn/index.html'])
source_comparisons = {}
for path,value in base['protected'].items():
    assert remember(path)==stamp(value) and base_blobs[path]==feature_blobs[path],path
for path in SOURCES:
    assert remember(path)==stamp(local['newSources'][path]),path
    source_comparisons[path] = current_vs_blob(path,feature_blobs[path])
# One read-only collection driver fix is permitted after the exact feature.
# All other helper bytes and every production/oracle source remain feature-exact.
collection_dir=ROOT/f'reports/{PREFIX}-public-collection-development/run-001'
correction=read(collection_dir/'correction.json')
assert type(correction['schema']) is int and correction['schema']==1
assert correction['feature']==FEATURE and correction['source']==PUBLIC_RECIPE
original=(collection_dir/'original-public.py.txt').read_bytes()
assert remember(collection_dir/'original-public.py.txt')==stamp(correction['original'])==hash_bytes(feature_blobs[PUBLIC_RECIPE])
assert original==feature_blobs[PUBLIC_RECIPE]
replacements=[("'channels': {'pages': 99, 'githubSource': 1}","'channels': {'pages': 112, 'githubSource': 1}"),
              ("sum(row['distribution'] == 'pages' for row in files) == 99","sum(row['distribution'] == 'pages' for row in files) == 112")]
assert correction['literalReplacements']==[list(row) for row in replacements]
corrected=original
for old,new in replacements:
    assert corrected.count(old.encode())==1
    corrected=corrected.replace(old.encode(),new.encode(),1)
assert corrected==(ROOT/PUBLIC_RECIPE).read_bytes()
assert remember(PUBLIC_RECIPE)==stamp(correction['new'])
patch=''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),corrected.decode('utf-8').splitlines(True),
              fromfile='a/'+PUBLIC_RECIPE,tofile='b/'+PUBLIC_RECIPE)).encode()
assert patch==(collection_dir/'actual.patch.txt').read_bytes()
assert remember(collection_dir/'actual.patch.txt')==stamp(correction['patch'])==hash_bytes(patch)
assert correction['failure']==f'reports/{PREFIX}-checks/run-20261104-public-bytes-001/commands.json'
assert type(correction['scope']) is str and 'Fresh full113 collection must pass' in correction['scope']
for path in helper_paths:
    if path==PUBLIC_RECIPE:
        source_comparisons[path]={'raw':remember(path),'featureBlob':hash_bytes(feature_blobs[path]),'normalization':None,
          'collectionDriverCorrection':{'path':relative(collection_dir/'correction.json'),**remember(collection_dir/'correction.json')}}
    else:source_comparisons[path] = current_vs_blob(path,feature_blobs[path])
for path,value in base['generatedEntries'].items():
    assert remember(path)==stamp(value)==local['generatedEntries'][path]['raw'],path
    assert normalized_html(base_blobs[path])==normalized_html(feature_blobs[path])==normalized_html((ROOT/path).read_bytes()),path

# Exact authorized fragments from the feature's separate insertion-only helper.
fragments=literals(feature_blobs[RECIPE+'/integrate.py'],{'CMAKE_SOURCE','CMAKE_TEST','CI_STAGE','ATTR_LINES'})
assert [len(fragments[k].splitlines()) for k in ['CMAKE_SOURCE','CMAKE_TEST','CI_STAGE','ATTR_LINES']]==[6,8,13,2]
assert fragments['CMAKE_SOURCE'].splitlines()[0]=='target_sources(pikapika_core PRIVATE core/include/pikapika/accelerated_sphere_box_coverage.hpp core/src/accelerated_sphere_box_coverage.cpp)'
old_changes={}
for path,names in [('CMakeLists.txt',['CMAKE_SOURCE','CMAKE_TEST']),('.github/workflows/verify.yml',['CI_STAGE']),('.gitattributes',['ATTR_LINES'])]:
    archived=base['permittedOldSources'][path];old=archived['gitBlobUtf8'].encode()
    assert hash_bytes(old)==stamp(archived['gitBlob']) and old==base_blobs[path]
    value=feature_blobs[path]
    for name in names:
        chunk=fragments[name].encode();assert value.count(chunk)==1,path;value=value.replace(chunk,b'',1)
    assert value==old,path
    old_changes[path]={**current_vs_blob(path,feature_blobs[path]),'baseGitBlob':hash_bytes(old),'insertedLines':sum(len(fragments[k].splitlines()) for k in names),'reconstruction':'Exact declared insertions only; current raw equality first, CRLF-to-LF only if needed.'}
lesson_literals=literals(feature_blobs[RECIPE+'/integrate-lesson.py'],{'added'});assert set(lesson_literals)=={'added'}
added=lesson_literals['added'].encode();assert added.startswith(b'<figure id="sphere-box-coverage">')
assert feature_blobs['docs/learn/index.html'].count(added)==1
assert feature_blobs['docs/learn/index.html'].replace(added,b'',1)==base_blobs['docs/learn/index.html']
source_comparisons['docs/learn/index.html']=current_vs_blob('docs/learn/index.html',feature_blobs['docs/learn/index.html'])
stage=fragments['CI_STAGE']
manifest = read('assets/pikapika-simulation.build.json')
assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92 and all('accelerated_sphere_box_coverage' not in f for f in exports)
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:
    assert remember(path)['sha256']==value,path
for path,value in local['artifacts'].items():
    assert remember(path)==stamp(value),path
assert local['artifacts']['assets/pikapika-simulation.wasm']['bytes']==800982
assert local['artifacts']['assets/pikapika-simulation.mjs']['bytes']==61661
for row in local['commands']:
    assert type(row['exit']) is int and row['exit']==0 and row.get('timedOut',False) is False
    assert row['sourceStable'] is True and row['sourceBefore']==row['sourceAfter']
    for path,value in row['sourceAfter'].items():assert remember(path)==stamp(value),path
    for stream in ['stdout','stderr']:assert remember(row[stream])==stamp(row[stream+'Hash'])
independent=local['independentReference']
for key,value in {'status':'PASS','fixtures':75,'certified':20,'notCertified':21,'invalidInputs':34,'cellAudits':955,
 'returnedEvaluations':955,'returnedIntervals':14325,'coordinateRangeProofs':5730,'deltaSquareProofs':955,
 'rootSquareProofs':955,'sqrtRefinementsReturned':96929,'sqrtLimitedReturns':1,'limitedPositiveEvaluations':1,
 'maximumAudits':255,'maximumPartition':128,'maximumFrontier':127,'subdividedCertified':1,
 'inputFingerprint':'f4f2b48cb4834d95916b5b1a4e9711c27166b65bbc987454af111212416fefbb'}.items():assert independent[key]==value,key
for key,value in {'nativePublicValueFullEvaluationReplays':955,'nativeEndpointBitComparisons':28650,'nativeNegativeZeroEndpoints':6371,'nativeRootDiagnosticComparisons':1910}.items():assert local[key]==value,key
assert local['positiveControls']['mathematicallyValidWiderRootAccepted'] is True
assert local['positiveControls']['syntheticNonreturnedValueReservationAccepted'] is True
assert local['positiveControls']['limitedValidRootSelfTestAccepted'] is True
assert local['newSources']==base['newSources']
assert local['rootWork']=={'returnedResults':955,'returnedRefinements':96929,'limitedResults':1,'limitedPositiveEvaluations':1,'allNaturalWorkExact':True,'sumUpper':96929,'privateRootAttemptCount':None}
assert local['storageObservation']['sizeofCapacityBytes']==98456
assert local['storageObservation']['sizeofCapacityComponents']['inlineResult']==480

public=read(f'reports/{PREFIX}-public-bytes.json');runs=read(f'reports/{PREFIX}-public-runs.json')
assert public['schema']==1 and public['status']=='PASS' and public['commit']==FEATURE and public['build']==local['webBuild']
assert public['channels']=={'pages':112,'githubSource':1}
selected=[]
for node in ast.parse(feature_blobs[RECIPE+'/public.py'].decode('utf-8')).body:
    if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='PATHS' for n in node.targets):selected=list(ast.literal_eval(node.value))
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='PATHS':selected.extend(ast.literal_eval(node.value))
assert len(selected)==len(set(selected))==113 and len(public['files'])==113
assert {r['path'] for r in public['files']}==set(selected)
published={row['path']:row for row in public['files']};public_blobs=git_blobs(FEATURE,selected)
for path,row in published.items():
    assert stamp(row)==hash_bytes(public_blobs[path]),path
    url=urlsplit(row['url'])
    if path=='.github/workflows/verify.yml':
        assert row['distribution']=='github-source' and url.scheme=='https' and url.netloc=='raw.githubusercontent.com'
        assert unquote(url.path)=='/tatata93/pikapikaengine/'+FEATURE+'/'+path and not url.query and not url.fragment
    else:
        assert row['distribution']=='pages' and url.scheme=='https' and url.netloc=='tatata93.github.io'
        assert unquote(url.path)=='/pikapikaengine/'+path and not url.fragment
        query={'build':[public['build']]} if path.startswith('assets/') or path.endswith('.mjs') else {'v':[FEATURE[:7]]}
        assert parse_qs(url.query)==query
assert Counter(r['distribution'] for r in public['files'])=={'pages':112,'github-source':1}

ci=read(f'reports/{PREFIX}-public-ci-evidence.json')
assert type(ci['schema']) is int and ci['schema']==1 and ci['commit']==FEATURE
assert runs['schema']==1 and runs['commit']==FEATURE and len(runs['runs'])==2
assert len({r['id'] for r in runs['runs']})==2
assert {r['name'] for r in runs['runs']}=={'Engine verification','pages build and deployment'}
jobs=[]
for label,workflow_name,count in [('engine','Engine verification',1),('pages','pages build and deployment',3)]:
    section=ci[label]
    found=[r for r in runs['runs'] if r['name']==workflow_name];assert len(found)==1
    run=found[0]
    assert type(section['runId']) is int and section['runId']==run['id']
    assert run['head_sha']==FEATURE and run['status']=='completed' and run['conclusion']=='success'
    payload=section['jobs']['jobs'];assert type(payload) is list and len(payload)==count
    assert len({j['id'] for j in payload})==count
    for job in payload:
        # Connector jobs lack head_sha: the enclosing run and job.run_id link it.
        assert job['run_id']==run['id'] and job['status']=='completed' and job['conclusion']=='success'
        assert job['steps'] and all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'])
    jobs.extend(payload)
engine=ci['engine']['jobs']['jobs'][0]
assert engine['name']=='portable-core' and ci['engine']['jobId']==engine['id']
step_names=['Set up job']+re.findall(r'^      - name: (.+)$',feature_blobs['.github/workflows/verify.yml'].decode(),re.M)+['Complete job']
assert len(engine['steps'])==len(step_names)==25 and [s['name'] for s in engine['steps']]==step_names
assert 'Audit two-declared-error sphere box coverage independently' in step_names
log=ci['engine']['log'];assert remember(log['path'])==stamp(log)
raw_log=(ROOT/relative(log['path'])).read_bytes().decode('utf-8')
assert type(log['decodedCharacters']) is int and len(raw_log)==log['decodedCharacters']
assert type(log['totalLines']) is int and len(raw_log.splitlines())==log['totalLines']
clean=re.sub(r'\x1b\[[0-9;]*m','',raw_log)
for marker in ['100% tests passed, 0 tests failed out of 45','# tests 684','# pass 684','# fail 0','# skipped 0',
 'Accelerated sphere box coverage: 84 groups PASS; 75 finite fixtures; 955 full Evaluation exact-bit replays / 28650 endpoint comparisons / 6371 negative-zero endpoints / 1910 root diagnostic comparisons.',
 'Independent Fraction/fixed-AST range proof is separate; real allocator/value-throw fault injection not performed; no actual World/all-target acceptance.']:
    assert marker in clean,marker
for line in workflow_commands(stage):assert line in clean,line
assert '-Wall -Wextra -Wpedantic -Werror' in stage
assert 'core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_sphere_box_coverage.cpp tests/accelerated_sphere_box_coverage_tests.cpp tests/accelerated_sphere_box_coverage_fixtures.cpp' in stage
assert '-fsanitize=address,undefined' in stage and '-fno-sanitize-recover=undefined' in stage
assert 'cmp build/ci/accelerated-sphere-box-coverage-fixtures.json build/ci/accelerated-sphere-box-coverage-sanitized-fixtures.json' in stage
proofs=[]
for line in clean.splitlines():
    text=re.sub(r'^\d{4}-\d\d-\d\dT\S+Z\s+','',line).strip()
    if text.startswith('{') and text.endswith('}'):
        try:proofs.append(json.loads(text))
        except json.JSONDecodeError:pass
linux_reports=[p for p in proofs if type(p) is dict and p.get('inputFingerprint')==independent['inputFingerprint']]
assert len(linux_reports)>=2 and all(p==independent for p in linux_reports)
control_report={'status':'PASS','selfTestGroups':16,'fixtures':75,'labelAndOrderIndependent':True,
                'rejectedControls':89,'positiveControls':local['positiveControls']}
assert control_report in proofs
prior_path=base['priorPublicReceipt'];prior=read(prior_path)
assert (ROOT/prior_path).read_bytes()==base_blobs[prior_path]==feature_blobs[prior_path]
prior_excerpt='reports/accelerated-pair-coverage-job-126568510900-excerpt.json'
assert ci['warnings']['priorExcerptPath']==prior_excerpt
assert remember(prior_excerpt)==stamp(prior['evidence'][prior_excerpt])
old=read(prior_excerpt)
assert re.fullmatch('[0-9a-f]{40}',old['commit']) and old['jobId']==126568510900
old_lines=[re.sub(r'\x1b\[[0-9;]*m','',r['text']) for r in old['lines']]
actual_warnings=warnings_from_lines(clean.splitlines());prior_warnings=warnings_from_lines(old_lines)
assert len(actual_warnings)==len(prior_warnings)==48
current_set=warning_multiset(actual_warnings);prior_set=warning_multiset(prior_warnings)
assert current_set==prior_set and ci['warnings']['sameMultiset'] is True
assert warning_multiset(ci['warnings']['current'])==current_set
assert warning_multiset(ci['warnings']['prior'])==prior_set

# Fresh actual status/byte captures only; no old failure exceptions imported.
command_paths=sorted(p for p in CHECKS.rglob('*commands.json') if 'public' in p.relative_to(CHECKS).as_posix() and not any('public-summary' in q for q in p.relative_to(CHECKS).parts))
assert 1<=len(command_paths)<=128
public_commands=[];failed_collection_attempts=[]
for path in command_paths:
    rows=read(path);assert type(rows) is list
    for command in rows:
        assert command['name'] in {'status','bytes'}
        assert command['args'][-3:]==[RECIPE+'/public.py',command['name'],FEATURE]
        assert type(command['exit']) is int and command.get('timedOut',False) is False
        assert type(command['wallSeconds']) in (int,float) and math.isfinite(command['wallSeconds']) and command['wallSeconds']>=0
        datetime.fromisoformat(command['started'])
        for stream in ['stdout','stderr']:assert remember(command[stream])==stamp(command[stream+'Hash'])
        if command['exit']!=0:
            assert relative(path)==correction['failure'] and len(rows)==1 and command['name']=='bytes' and command['exit']==1
            assert (ROOT/command['stdout']).read_bytes()==b''
            error=(ROOT/command['stderr']).read_text(encoding='utf-8-sig')
            assert 'line 159, in main' in error and "assert sum(row['distribution'] == 'pages' for row in files) == 99" in error
            assert error.strip().endswith('AssertionError')
            failed_collection_attempts.append({**command,'commandFile':relative(path),'classification':'Collection driver footer count assertion; not completed receipt, CI failure or numerical failure','acceptedCollection':False})
        else:public_commands.append({**command,'commandFile':relative(path)})
assert {c['name'] for c in public_commands}=={'status','bytes'}
assert len(failed_collection_attempts)==1
latest={name:max((r for r in public_commands if r['name']==name),key=lambda r:datetime.fromisoformat(r['started'])) for name in ['status','bytes']}
status_rows=read(latest['status']['stdout'])
assert len(status_rows)==2 and {r['id'] for r in status_rows}=={r['id'] for r in runs['runs']}
for status in status_rows:
    actual=next(r for r in runs['runs'] if r['id']==status['id'])
    assert all(status[k]==actual[k] for k in ['id','name','status','conclusion','html_url'])
assert read(latest['bytes']['stdout'])=={'status':'PASS','files':113,'bytes':sum(r['bytes'] for r in public['files']),'build':public['build'],'channels':public['channels']}

browser_dir=ROOT/f'reports/{PREFIX}-public-browser'
observations=read(browser_dir/'observations.json')
assert type(observations['schema']) is int and observations['schema']==1 and observations['scope']==SCOPE
assert set(observations['observedURLs'])=={'diagram','lesson','game'}
required={'diagram.jpg','diagram-ax.txt','lesson.jpg','lesson-ax.txt','lesson-article.txt',
          'public-game.jpg','public-game-ax.txt','public-game-cover-report.json'}
names=observations['files']
assert type(names) is list and len(names)==len(set(names)) and required==set(names) and len(names)==8
assert all(type(n) is str and PurePosixPath(n).name==n and n!='observations.json' for n in names)
captures={};screens={}
for name in names:
    path=browser_dir/name;record=remember(path);assert record['bytes']>0
    captures[relative(path)]=record
    if name.endswith('.jpg'):
        width,height=jpeg_dimensions(path.read_bytes());assert 200<=width<=4096 and 100<=height<=4096
        screens[name]={'width':width,'height':height}
    elif name.endswith('.txt'):assert path.read_bytes().decode('utf-8-sig').strip()
    elif name.endswith('.json'):read(path)
    else:raise AssertionError('Unsupported original capture type: '+name)
captures[relative(browser_dir/'observations.json')]=remember(browser_dir/'observations.json')
source_paths={'docs/learn/index.html','docs/learn/diagrams/accelerated-sphere-box-coverage.svg','docs/ACCELERATED_SPHERE_BOX_COVERAGE.md'}
assert set(observations['sourceHashes'])==source_paths
for path,value in observations['sourceHashes'].items():assert stamp(value)==hash_bytes(public_blobs[path]),path
for name,path in [('diagram','docs/learn/diagrams/accelerated-sphere-box-coverage.svg'),('lesson','docs/learn/index.html')]:
    url=urlsplit(observations['observedURLs'][name])
    assert url.scheme=='https' and url.netloc=='tatata93.github.io' and unquote(url.path)=='/pikapikaengine/'+path
    assert parse_qs(url.query)=={'v':[FEATURE[:7]]}
    assert url.fragment==('sphere-box-coverage' if name=='lesson' else '')
image=observations['lessonImage']
assert image['complete'] is True and type(image['width']) is type(image['height']) is int
assert (image['width'],image['height'])==(1120,760)
assert image['src']=='diagrams/accelerated-sphere-box-coverage.svg'
assert observations['lessonGuideHref']=='../ACCELERATED_SPHERE_BOX_COVERAGE.md'
if 'rect' in image:
    assert type(image['rect']) is dict
    assert all(type(v) in (int,float) and math.isfinite(v) for v in image['rect'].values())
lesson=public_blobs['docs/learn/index.html'].decode('utf-8')
articles=[m for m in re.finditer(r'<article\b([^>]*)>(.*?)</article>',lesson,re.S) if 'accelerated-sphere-box-coverage.svg' in m[2]]
assert len(articles)==1 and re.search(r'\bid="accelerated"',articles[0][1])
assert re.findall(r'<img\b[^>]*\bsrc="([^"]*accelerated-sphere-box-coverage\.svg)"',articles[0][2])==[image['src']]
assert re.findall(r'<a\b[^>]*\bhref="([^"]*ACCELERATED_SPHERE_BOX_COVERAGE\.md)"',articles[0][2])==[observations['lessonGuideHref']]
parser=ArticleText();parser.feed(articles[0][0]);parser.close()
article=(browser_dir/'lesson-article.txt').read_bytes().decode('utf-8-sig')
assert re.sub(r'\s+','',article)==re.sub(r'\s+','',''.join(parser.parts))
game_url=urlsplit(observations['observedURLs']['game'])
assert game_url.scheme=='https' and game_url.netloc=='tatata93.github.io' and game_url.path in {'/pikapikaengine/','/pikapikaengine/index.html'}
assert parse_qs(game_url.query)=={'v':[FEATURE[:7]]} and not game_url.fragment
assert observations['game']['coverReportFile']=='public-game-cover-report.json'
assert observations['game']['scope']=='existing game compatibility only; new Native API not invoked'
assert observations['game']['boostObserved'] is True
game=read(browser_dir/observations['game']['coverReportFile'])
state=(browser_dir/'public-game-ax.txt').read_bytes().decode('utf-8-sig')
assert game['state']=='ready' and game['failure'] is None and game['pending'] is None and game['errors']==[]
assert '一時停止 / Pで再開' in state
kills=re.search(r'撃破\s+(\d+)',state);assert kills and int(kills[1])>=2
queries=game['counts']['queries']
assert all(type(game['counts'][k]) is int for k in ['queries','checked','validated'])
assert queries>0 and queries==game['counts']['checked']==game['counts']['validated']==len(game['records'])
assert all(r['state']=='completed' for r in game['records']) and any(r['clipSeconds']==1 for r in game['records'])
assert game['renderer']['residentMeshes']==3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId']==public['build'] and game['startup']['diagnostics']['wasmBytes']==800982
asset=urlsplit(game['startup']['assetURL'])
assert asset.scheme=='https' and asset.netloc=='tatata93.github.io' and asset.path=='/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset.query)=={'build':[public['build']]}

remember(__file__);remember(RECIPE+'/public-summary-run.py')
assert len(evidence)<=4096 and sum(v['bytes'] for v in evidence.values())<=256*1024*1024
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':FEATURE,
 'localVerification':{'path':local_path,**remember(local_path)},'ctest':45,'node':684,'skipped':0,
 'nativeGroups':84,'finiteFixtures':75,'nativePublicValueFullEvaluationReplays':955,'nativeEndpointBitComparisons':28650,
 'nativeNegativeZeroEndpoints':6371,'nativeRootDiagnosticComparisons':1910,'independentReference':independent,
 'independentReferenceScope':local['independentReferenceScope'],'rootWork':local['rootWork'],'selfTestGroups':16,'negativeControls':89,
 'localNativeScope':'MSVC finite75/45CTest and exact public-value all15I/root metadata replay, distinct from fresh GNU/instrumented execution.',
 'publicCiScope':{'engineSteps':25,'pagesJobs':3,'linuxIndependentReports':len(linux_reports),'newWerrorTranslationUnits':3,'fullyInstrumentedTranslationUnits':5,'regularInstrumentedFixtureByteComparison':True,'scope':'Fresh GNU regular and ASan/UBSan runs, same-Linux fixture bytecmp and independent full-range checks. No new WASM API or exact cross-compiler whole-DTO parity claim.'},
 'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
 'protectedFilesUnchanged':376,'generatedEntriesUnchanged':26,'modules':54,'entries':26,'webBuild':public['build'],
 'artifacts':local['artifacts'],'sourceComparisons':source_comparisons,'permittedOldChanges':old_changes,
 'publicFiles':113,'publicChannels':public['channels'],'publicBytes':sum(r['bytes'] for r in public['files']),
 'publicCommands':public_commands,'failedCollectionAttempts':failed_collection_attempts,'collectionDriverCorrection':{'record':correction,'path':relative(collection_dir/'correction.json'),'original':{'path':relative(collection_dir/'original-public.py.txt'),**remember(collection_dir/'original-public.py.txt')},'patch':{'path':relative(collection_dir/'actual.patch.txt'),**remember(collection_dir/'actual.patch.txt')},'scope':'Exact two collection-only footer constants changed after all113 original fetch comparisons. Original attempt remains failed; only fresh successful113/112/1 receipt is accepted. Production/math/CI/feature sources unchanged.'},'jobs':jobs,'warnings':{'current':48,'prior':48,'sameMultiset':True,'new':0},
 'browser':{'schema':1,'status':'PASS','phase':'public','commit':FEATURE,'buildId':public['build'],'wasmBytes':800982,'scope':SCOPE,'observations':observations,'evidence':captures,'screens':screens,'lessonArticleCharacters':len(article),'displayScope':'Image load/complete article text verified; original JPG/AX retained. Screenshot readability is reviewed separately by parent.'},
 'publicGame':{'paused':True,'kills':int(kills[1]),'queries':queries,'allCompleted':True,'boostObserved':True,'clip1Observed':True,'residentMeshes':3,'scope':'Existing sample compatibility only; new Native helper is not executed in browser.'},
 'historicalLocalAttempts':local['historicalAttempts'],'localCollectionNotes':local['collectionNotes'],'localLimitations':local['notMeasured'],
 'postFeatureVerifiers':{path:remember(path) for path in [relative(__file__),RECIPE+'/public-summary-run.py']},
 'scope':'Native-only two-declared-B/margin sphere-box. Independent six coordinate proofs use exact quadratic extrema plus B; integer-RN families begin at recorded boxes through delta/square/left-sum/threshold/gap with full root square/RN endpoint proof. Actual I-AST provenance is a separate Native bit replay. No actual World B derivation, external std::sqrt binding, all-compiler/pair/candidate certification, TOI/response, fault injection or used-heap/stack guarantee.',
 'ciEvidenceScope':'Full fetched job log bytes/hash/Unicode characters/line count, exact-feature jobs and all steps, literal audit commands and independent reports; warning multiset compared with retained prior excerpt.',
 'evidence':evidence}
assert not (CAPTURE/'acceptance.json').exists()
(CAPTURE/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','commit','ctest','node','publicFiles','publicChannels','publicBytes','webBuild']}))
