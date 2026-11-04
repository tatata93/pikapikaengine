"""Accept fresh public evidence for the Native-only declared-B plane-box helper.

This post-feature verifier never executes a coverage query or manufactures CI,
browser, sanitizer or parity evidence. Missing/failed evidence rejects.
"""
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from urllib.parse import parse_qs,unquote,urlsplit
import ast,json,math,re,subprocess,sys

if not __debug__:raise SystemExit('Run without Python -O')
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-plane-box-coverage'
assert len(sys.argv)==3,'Usage: public-summary.py FULL_FEATURE_COMMIT FRESH_SUMMARY_DIRECTORY'
FEATURE=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',FEATURE)
assert subprocess.check_output(['git','rev-parse',FEATURE+'^{commit}'],cwd=ROOT,text=True).strip()==FEATURE
CHECKS=(ROOT/f'reports/{PREFIX}-checks').resolve()
CAPTURE=(ROOT/sys.argv[2]).resolve()
assert CAPTURE.is_dir() and CAPTURE.is_relative_to(CHECKS) and not (CAPTURE/'acceptance.json').exists()
RECIPE=f'reports/{PREFIX}-recipes'
SOURCES=['core/include/pikapika/accelerated_plane_box_coverage.hpp',
 'core/src/accelerated_plane_box_coverage.cpp','tests/accelerated_plane_box_coverage_tests.cpp',
 'tests/accelerated_plane_box_coverage_fixtures.cpp','tests/accelerated_plane_box_coverage_test_support.hpp',
 'scripts/verify-accelerated-plane-box-coverage.py','tests/accelerated_plane_box_coverage_reference_tests.py']
SCOPE='Native-only conditional plane-box helper: public diagram/lesson display and existing game compatibility; no browser numerical query or actual World certification.'
evidence={}


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


local_path=f'reports/{PREFIX}-local-verification.json'
local=read(local_path);base=read(f'reports/{PREFIX}-baseline.json')
fix_dir=ROOT/f'reports/{PREFIX}-ci-fix-development/run-001'
fix=read(fix_dir/'acceptance.json')
test_source='tests/accelerated_plane_box_coverage_tests.cpp'
original_feature='a9093238a7cb0c9c82b70c00613610124ca4213b'
assert FEATURE!=original_feature and fix['schema']==1 and fix['status']=='PASS'
assert fix['phase']=='targeted-postfix-local' and fix['baseCommit']==original_feature and fix['source']==test_source
assert subprocess.run(['git','merge-base','--is-ancestor',original_feature,FEATURE],cwd=ROOT).returncode==0
assert stamp(fix['original'])=={'bytes':21174,'sha256':'e3ff93de57b149d2a5f541aa7ba9da0d2a40443cecc56f79cff0a554acb1f759'}
assert stamp(fix['new'])=={'bytes':21208,'sha256':'901dbab86cadceb69ef9e293fc9bf7951a37411128e9013a046562fe01ef2cba'}
original_tests_path=fix_dir/'original-tests.cpp.txt'
assert remember(original_tests_path)==stamp(fix['original']) and remember(test_source)==stamp(fix['new'])
old_tests=original_tests_path.read_bytes()
expected_tests=old_tests
for before,after in [
 (b'#include <string>\n',b'#include <string>\n#include <string_view>\n'),
 (b'named(const std::vector<f::Case>& corpus,const std::string& name)',b'named(const std::vector<f::Case>& corpus,std::string_view name)'),
 (b'"Missing fixed case: "+name',b'"Missing fixed case: "+std::string(name)')]:
    assert expected_tests.count(before)==1
    expected_tests=expected_tests.replace(before,after,1)
assert expected_tests==(ROOT/test_source).read_bytes()
assert remember(fix_dir/'actual.patch.txt')==stamp(fix['patch'])
actual_patch=subprocess.check_output(['git','diff','--no-ext-diff','--no-color',original_feature,'--',test_source],cwd=ROOT)
assert actual_patch==(fix_dir/'actual.patch.txt').read_bytes()
assert (fix['groups'],fix['finiteFixtures'],fix['fullEvaluationProvenance'],fix['endpointBits'],fix['negativeZeroEndpoints'],fix['msvcWarnings'])==(74,67,1306,15672,2496,0)
assert fix['sourceStable'] is True and fix['otherCompiledSourcesUnchanged'] is True and fix['sdkArtifactsUnchanged'] is True
assert fix['sourceBefore']==fix['sourceAfter'] and len(fix['sourceAfter'])==13
for path,value in fix['sourceAfter'].items():assert remember(path)==stamp(value),path
assert [r['name'] for r in fix['commands']]==['compile','native-tests','native-fixtures','storage']
for row in fix['commands']:
    assert type(row['exit']) is int and row['exit']==0 and row['timedOut'] is False and row['sourceStable'] is True
    assert row['sourceBefore']==row['sourceAfter']==fix['sourceAfter']
    for stream in ['stdout','stderr']:assert remember(fix_dir/row[stream])==stamp(row[stream+'Hash'])
assert fix['fixtureByteIdenticalToOriginalStandalone'] is True and fix['fixtureByteIdenticalToCanonicalNative'] is True
assert fix['storageByteIdenticalToOriginalStandalone'] is True
for path in [fix_dir/'native-fixtures.json',ROOT/f'reports/{PREFIX}-native-development/run-001/native-fixtures.json',
             ROOT/f'reports/{PREFIX}-checks/run-20261104-native-001/native-fixtures.json']:
    assert remember(path)==stamp(fix['fixtures'])=={'bytes':676814,'sha256':'0dafa4e430ad34958a25795b07a8785972cdf9dd6071cf2f24a8b1a676493cc1'}
assert (fix_dir/'storage.json').read_bytes()==(ROOT/f'reports/{PREFIX}-native-development/run-001/native-storage.json').read_bytes()
remember(fix_dir/'storage.json')


def verify_historical_local_source(path,value):
    # Keep the original local receipt untouched. Only this exact old test is
    # resolved to its archived original; its new bytes have a separate receipt.
    if path==test_source:
        assert stamp(value)==stamp(fix['original'])==stamp(local['newSources'][test_source])
        assert remember(original_tests_path)==stamp(value)
    else:assert remember(path)==stamp(value),path


assert local['status']=='PASS' and local['baseCommit']==base['baseCommit']=='26b96cfb0673b7555845e848552dc9294e0b71d7'
for key,value in {'ctest':44,'nativeGroups':74,'finiteFixtures':67,'node':684,'skipped':0,
 'nativePublicValueFullEvaluationReplays':1306,'nativeEndpointBitComparisons':15672,'nativeNegativeZeroEndpoints':2496,
 'selfTestGroups':16,'negativeControls':65,'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,
 'runtimeMembers':91,'licenseNoticesUnchanged':7,'protectedFilesUnchanged':369,'generatedEntriesUnchanged':26,'modules':54}.items():
    assert type(local[key]) is int and local[key]==value,key
assert local['webBuild']=='cd45c7f1ac2ba5e5'
assert len(base['protected'])==369 and len(base['generatedEntries'])==26
assert set(local['newSources'])==set(SOURCES)
for path,value in local['evidence'].items():verify_historical_local_source(path,value)
helper_paths=[RECIPE+'/'+name+'.py' for name in ['check','summary','summary-run','integrate','public','public-check']]
paths=set(base['protected'])|set(base['generatedEntries'])|set(base['permittedOldSources'])|set(SOURCES)|set(helper_paths)|{'docs/learn/index.html',base['priorPublicReceipt']}
paths|={relative(fix_dir/'acceptance.json'),relative(original_tests_path),relative(fix_dir/'actual.patch.txt')}
feature_blobs=git_blobs(FEATURE,paths)
original_blobs=git_blobs(original_feature,[*SOURCES,local_path])
assert old_tests==original_blobs[test_source]
assert (ROOT/local_path).read_bytes()==original_blobs[local_path]==git_blobs(FEATURE,[local_path])[local_path]
for path in [relative(fix_dir/'acceptance.json'),relative(original_tests_path),relative(fix_dir/'actual.patch.txt')]:
    assert (ROOT/path).read_bytes()==feature_blobs[path],path
base_blobs=git_blobs(base['baseCommit'],[*base['protected'],*base['generatedEntries'],*base['permittedOldSources'],'docs/learn/index.html',base['priorPublicReceipt']])
source_comparisons={}
for path,value in base['protected'].items():
    assert remember(path)==stamp(value) and feature_blobs[path]==base_blobs[path],path
for path in SOURCES:
    if path==test_source:
        assert hash_bytes(original_blobs[path])==stamp(local['newSources'][path])
        assert hash_bytes(feature_blobs[path])==stamp(fix['new'])==remember(path)
    else:
        assert feature_blobs[path]==original_blobs[path] and remember(path)==stamp(local['newSources'][path]),path
    source_comparisons[path]=current_vs_blob(path,feature_blobs[path])
for path in helper_paths:source_comparisons[path]=current_vs_blob(path,feature_blobs[path])
for path,value in base['generatedEntries'].items():
    assert remember(path)==stamp(value)==local['generatedEntries'][path]['raw'],path
    assert normalized_html(base_blobs[path])==normalized_html(feature_blobs[path])==normalized_html((ROOT/path).read_bytes()),path

# Reconstruct only the three authorized old-file insertions from feature bytes.
cmake=feature_blobs['CMakeLists.txt'].decode('utf-8')
start=cmake.index('target_sources(pikapika_core PRIVATE core/src/accelerated_plane_box_coverage.cpp)\n')
library=cmake[start:cmake.index('endif()\n',start)+len('endif()\n')]
start=cmake.index('  add_executable(pikapika_accelerated_plane_box_coverage_tests ')
end='  add_test(NAME accelerated_plane_box_coverage COMMAND pikapika_accelerated_plane_box_coverage_tests)\n'
test=cmake[start:cmake.index(end,start)+len(end)]
assert (len(library.splitlines()),len(test.splitlines()))==(6,8)
integration=literals(feature_blobs[RECIPE+'/integrate.py'],{'stage','added'})
stage=integration['stage'];assert len(stage.splitlines())==13
assert stage.startswith('      - name: Audit declared-error plane box coverage independently\n')
attrs='reports/accelerated-plane-box-coverage-* -text -whitespace\nreports/accelerated-plane-box-coverage-*/** -text -whitespace\n'
old_changes={}
for path,chunks in [('CMakeLists.txt',[library,test]),('.github/workflows/verify.yml',[stage]),('.gitattributes',[attrs])]:
    archived=base['permittedOldSources'][path];old=archived['gitBlobUtf8'].encode()
    assert old==base_blobs[path] and hash_bytes(old)==stamp(archived['gitBlob'])
    reconstructed=feature_blobs[path]
    for chunk in chunks:
        value=chunk.encode();assert reconstructed.count(value)==1,path
        reconstructed=reconstructed.replace(value,b'',1)
    assert reconstructed==old,path
    old_changes[path]={**current_vs_blob(path,feature_blobs[path]),'baseGitBlob':hash_bytes(old),
                       'insertedLines':sum(len(c.splitlines()) for c in chunks)}
addition=integration['added'].encode();assert addition.startswith(b'<figure id="plane-box-coverage">')
assert feature_blobs['docs/learn/index.html'].count(addition)==1
assert feature_blobs['docs/learn/index.html'].replace(addition,b'',1)==base_blobs['docs/learn/index.html']

manifest=read('assets/pikapika-simulation.build.json');assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports=json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92 and all('plane_box_coverage' not in f for f in exports)
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:assert remember(path)['sha256']==value,path
for path,value in local['artifacts'].items():assert remember(path)==stamp(value),path
assert local['artifacts']['assets/pikapika-simulation.wasm']['bytes']==800982
assert local['artifacts']['assets/pikapika-simulation.mjs']['bytes']==61661
for row in local['commands']:
    assert type(row['exit']) is int and row['exit']==0 and row.get('timedOut',False) is False
    assert row['sourceStable'] is True and row['sourceBefore']==row['sourceAfter']
    for path,value in row['sourceAfter'].items():verify_historical_local_source(path,value)
    for stream in ['stdout','stderr']:assert remember(row[stream])==stamp(row[stream+'Hash'])
independent=local['independentReference']
assert independent['status']=='PASS' and independent['inputFingerprint']=='2d660f51cb84c0bdbc8f8f9e3d26bf59caf92d53878bc12c0bf2ebce72408ec9'
for key,value in {'fixtures':67,'certified':20,'notCertified':20,'invalidInputs':27,'cellAudits':1306,
 'returnedEvaluations':1306,'returnedIntervals':7836,'coordinateRangeProofs':3918,'astCornerProofs':2612,
 'maximumAudits':255,'maximumPartition':128,'maximumFrontier':127,'subdividedCertified':1}.items():assert independent[key]==value,key
assert local['positiveControls']['mathematicallyValidWiderDistanceAccepted'] is True
assert local['positiveControls']['syntheticNonreturnedAttemptAccepted'] is True

# All selected resource bytes are compared with exact feature blobs, across the
# distinct Pages/source channels. No native helper export is inferred from them.
public=read(f'reports/{PREFIX}-public-bytes.json');runs=read(f'reports/{PREFIX}-public-runs.json')
assert public['schema']==1 and public['status']=='PASS' and public['commit']==FEATURE and public['build']==local['webBuild']
assert public['channels']=={'pages':99,'githubSource':1}
selected=[]
for node in ast.parse(feature_blobs[RECIPE+'/public.py'].decode('utf-8')).body:
    if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='PATHS' for n in node.targets):selected=list(ast.literal_eval(node.value))
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='PATHS':selected.extend(ast.literal_eval(node.value))
assert len(selected)==len(set(selected))==100 and len(public['files'])==100
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
assert Counter(r['distribution'] for r in public['files'])=={'pages':99,'github-source':1}

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
assert len(engine['steps'])==len(step_names)==24 and [s['name'] for s in engine['steps']]==step_names
assert 'Audit declared-error plane box coverage independently' in step_names
log=ci['engine']['log'];assert remember(log['path'])==stamp(log)
raw_log=(ROOT/relative(log['path'])).read_bytes().decode('utf-8')
assert type(log['decodedCharacters']) is int and len(raw_log)==log['decodedCharacters']
assert type(log['totalLines']) is int and len(raw_log.splitlines())==log['totalLines']
clean=re.sub(r'\x1b\[[0-9;]*m','',raw_log)
for marker in ['100% tests passed, 0 tests failed out of 44','# tests 684','# pass 684','# fail 0','# skipped 0',
 'Accelerated plane box coverage: 74 groups PASS; 67 finite fixtures; 1306 full Evaluation exact-bit replays / 15672 endpoint comparisons / 2496 negative-zero endpoints.',
 'Independent Fraction/fixed-AST range proof is separate; real allocator/value-throw fault injection not performed; no actual World/all-target acceptance.']:
    assert marker in clean,marker
for line in workflow_commands(stage):assert line in clean,line
assert '-Wall -Wextra -Wpedantic -Werror' in stage
assert 'core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_plane_box_coverage.cpp tests/accelerated_plane_box_coverage_tests.cpp tests/accelerated_plane_box_coverage_fixtures.cpp' in stage
assert '-fsanitize=address,undefined' in stage and '-fno-sanitize-recover=undefined' in stage
assert 'cmp build/ci/accelerated-plane-box-coverage-fixtures.json build/ci/accelerated-plane-box-coverage-sanitized-fixtures.json' in stage
proofs=[]
for line in clean.splitlines():
    text=re.sub(r'^\d{4}-\d\d-\d\dT\S+Z\s+','',line).strip()
    if text.startswith('{') and text.endswith('}'):
        try:proofs.append(json.loads(text))
        except json.JSONDecodeError:pass
linux_reports=[p for p in proofs if type(p) is dict and p.get('inputFingerprint')==independent['inputFingerprint']]
assert len(linux_reports)>=2 and all(p==independent for p in linux_reports)
control_report={'status':'PASS','selfTestGroups':16,'fixtures':67,'labelAndOrderIndependent':True,
                'rejectedControls':65,'positiveControls':local['positiveControls']}
assert control_report in proofs
prior_path=base['priorPublicReceipt'];prior=read(prior_path)
assert (ROOT/prior_path).read_bytes()==base_blobs[prior_path]==feature_blobs[prior_path]
prior_excerpt='reports/accelerated-pair-coverage-job-126568510900-excerpt.json'
assert ci['warnings']['priorExcerptPath']==prior_excerpt
assert remember(prior_excerpt)==stamp(prior['evidence'][prior_excerpt])
old=read(prior_excerpt)
assert old['commit']==prior['commit'] and old['jobId']==126568510900
old_lines=[re.sub(r'\x1b\[[0-9;]*m','',r['text']) for r in old['lines']]
actual_warnings=warnings_from_lines(clean.splitlines());prior_warnings=warnings_from_lines(old_lines)
assert len(actual_warnings)==len(prior_warnings)==48
current_set=warning_multiset(actual_warnings);prior_set=warning_multiset(prior_warnings)
assert current_set==prior_set and ci['warnings']['sameMultiset'] is True
assert warning_multiset(ci['warnings']['current'])==current_set
assert warning_multiset(ci['warnings']['prior'])==prior_set

# The first feature failed GCC's new-test Werror audit. Preserve that complete
# failed execution and its separately successful byte/UI collection as history;
# neither substitutes for the final feature's all-success CI or fresh captures.
failed_dir=ROOT/f'reports/{PREFIX}-public-ci-development/run-001'
failed_note=read(failed_dir/'note.json')
assert failed_note['schema']==1 and failed_note['commit']==original_feature and failed_note['conclusion']=='failure'
assert failed_note['runId']==41835425148 and failed_note['jobId']==126592955091
assert failed_note['failedStep']=='Audit declared-error plane box coverage independently'
assert 'before execution' in failed_note['collectionNote'] and '64000-byte' in failed_note['collectionNote']
old_runs=read(failed_dir/'original-public-runs.json')
assert old_runs['schema']==1 and old_runs['commit']==original_feature and len(old_runs['runs'])==2
assert all(r['head_sha']==original_feature and r['status']=='completed' for r in old_runs['runs'])
assert {r['name']:r['conclusion'] for r in old_runs['runs']}=={'Engine verification':'failure','pages build and deployment':'success'}
old_jobs=read(failed_dir/'engine-jobs.json')['jobs'];old_pages=read(failed_dir/'pages-jobs.json')['jobs']
assert len(old_jobs)==1 and len(old_pages)==3
old_job=old_jobs[0]
assert old_job['id']==failed_note['jobId'] and old_job['run_id']==failed_note['runId'] and old_job['conclusion']=='failure'
assert [s['name'] for s in old_job['steps']]==step_names and len(old_job['steps'])==24
assert [(s['number'],s['conclusion']) for s in old_job['steps'] if s['conclusion']!='success']==[(22,'failure'),(23,'skipped')]
assert all(j['conclusion']=='success' and j['status']=='completed' and all(s['conclusion']=='success' and s['status']=='completed' for s in j['steps']) for j in old_pages)
assert {old_job['run_id'],*[j['run_id'] for j in old_pages]}=={r['id'] for r in old_runs['runs']}
failed_log_path=failed_dir/'failed-job-full.txt'
assert remember(failed_log_path)=={'bytes':900623,'sha256':'c81b0c297b24cc2125321445a2b8eeae0d52ee0cd9df21dab20b05ec893fe453'}
failed_log=failed_log_path.read_bytes().decode('utf-8')
assert len(failed_log)==900113 and len(failed_log.splitlines())==11902 and original_feature in failed_log
failed_clean=re.sub(r'\x1b\[[0-9;]*m','',failed_log)
errors=re.findall(r'tests/accelerated_plane_box_coverage_tests\.cpp:(\d+):(\d+): error: possibly dangling reference[^\r\n]*\[-Werror=dangling-reference\]',failed_clean)
assert [(int(line),int(column)) for line,column in errors]==[(69,17),(70,17),(71,17),(72,17)]
assert '100% tests passed, 0 tests failed out of 44' in failed_clean and '# pass 684' in failed_clean
failed_proofs=[]
for line in failed_clean.splitlines():
    text=re.sub(r'^\d{4}-\d\d-\d\dT\S+Z\s+','',line).strip()
    if text.startswith('{') and text.endswith('}'):
        try:failed_proofs.append(json.loads(text))
        except json.JSONDecodeError:pass
assert independent in failed_proofs and control_report in failed_proofs
old_public=read(failed_dir/'original-public-bytes.json')
assert old_public['schema']==1 and old_public['status']=='PASS' and old_public['commit']==original_feature
assert old_public['channels']=={'pages':99,'githubSource':1} and len(old_public['files'])==100
assert {row['path'] for row in old_public['files']}==set(selected)
original_public_blobs=git_blobs(original_feature,selected)
for row in old_public['files']:assert stamp(row)==hash_bytes(original_public_blobs[row['path']]),row['path']
archived_browser=ROOT/f'reports/{PREFIX}-public-browser-development/run-002/original-captures'
archived_names={'diagram-ax.txt','diagram.jpg','lesson-article.txt','lesson-ax.txt','lesson.jpg',
                'observations.json','public-game-ax.txt','public-game-cover-report.json','public-game.jpg'}
assert {p.name for p in archived_browser.iterdir()}==archived_names
archived_browser_evidence={relative(archived_browser/name):remember(archived_browser/name) for name in sorted(archived_names)}
archived_blobs=git_blobs(FEATURE,archived_browser_evidence)
for path in archived_browser_evidence:assert (ROOT/path).read_bytes()==archived_blobs[path],path
old_observations=read(archived_browser/'observations.json')
assert set(old_observations['observedURLs'])=={'diagram','lesson','game'}
assert all(parse_qs(urlsplit(url).query)=={'v':[original_feature[:7]]} for url in old_observations['observedURLs'].values())
for path,value in old_observations['sourceHashes'].items():assert stamp(value)==hash_bytes(original_public_blobs[path]),path
failed_public_attempt={'commit':original_feature,'conclusion':'failure','runId':old_job['run_id'],'jobId':old_job['id'],
 'failedStep':failed_note['failedStep'],'note':failed_note,'fullLog':{'path':relative(failed_log_path),**remember(failed_log_path),'decodedCharacters':len(failed_log),'totalLines':len(failed_log.splitlines())},
 'jobs':old_jobs+old_pages,'completedBeforeFailure':{'ctest':44,'node':684,'independentReference':independent,'selfAndControls':control_report},
 'notCompleted':['New plane-box sanitizer execution / fixture bytecmp','Final existing WebAssembly step'],
 'priorSuccessfulByteCollection':{'path':relative(failed_dir/'original-public-bytes.json'),**remember(failed_dir/'original-public-bytes.json'),'files':100,'bytes':sum(r['bytes'] for r in old_public['files'])},
 'priorBrowserArchive':archived_browser_evidence,'acceptedFeature':False,
 'scope':'The test-helper diagnostic stopped Werror. Product/math runs completed before failure remain historical; the new sanitizer and final WASM step were not completed. The fixed feature requires independent fresh all-24-step CI, all100 bytes and actual browser captures. Initial oversized log-data write was rejected by the tool interface before execution, as recorded in the note.'}
failed_paths=[relative(p) for p in failed_dir.iterdir() if p.is_file()]
assert set(failed_paths)=={relative(failed_dir/name) for name in ['note.json','failed-job-full.txt','engine-jobs.json','pages-jobs.json','original-public-bytes.json','original-public-runs.json']}
failed_blobs=git_blobs(FEATURE,failed_paths)
for path in failed_paths:assert (ROOT/path).read_bytes()==failed_blobs[path],path

# Only fresh public status/byte captures from this milestone participate. All
# attempts stay visible; no prior milestone's network/helper exception is reused.
command_paths=sorted(p for p in CHECKS.rglob('*commands.json')
                     if 'public' in p.relative_to(CHECKS).as_posix()
                     and not any('public-summary' in part for part in p.relative_to(CHECKS).parts))
assert 1<=len(command_paths)<=128
public_commands=[];prior_public_commands=[]
for path in command_paths:
    rows=read(path);assert type(rows) is list
    for command in rows:
        assert command['name'] in {'status','bytes'},command['name']
        assert command['args'][-3:-1]==[RECIPE+'/public.py',command['name']]
        assert command['args'][-1] in {FEATURE,original_feature}
        assert type(command['exit']) is int and command['exit']==0 and command.get('timedOut',False) is False
        assert type(command['wallSeconds']) in (int,float) and math.isfinite(command['wallSeconds']) and command['wallSeconds']>=0
        datetime.fromisoformat(command['started'])
        for stream in ['stdout','stderr']:assert remember(command[stream])==stamp(command[stream+'Hash'])
        record={**command,'commandFile':relative(path)}
        (public_commands if command['args'][-1]==FEATURE else prior_public_commands).append(record)
assert {c['name'] for c in public_commands}=={'status','bytes'}
assert {c['name'] for c in prior_public_commands}=={'status','bytes'}
latest={name:max((r for r in public_commands if r['name']==name),key=lambda r:datetime.fromisoformat(r['started'])) for name in ['status','bytes']}
status_rows=read(latest['status']['stdout'])
assert len(status_rows)==2 and {r['id'] for r in status_rows}=={r['id'] for r in runs['runs']}
assert all(r['status']=='completed' and r['conclusion']=='success' for r in status_rows)
byte_output=read(latest['bytes']['stdout'])
assert byte_output=={'status':'PASS','files':100,'bytes':sum(r['bytes'] for r in public['files']),
                    'build':public['build'],'channels':public['channels']}

browser_dir=ROOT/f'reports/{PREFIX}-public-browser'
observations=read(browser_dir/'observations.json')
assert type(observations['schema']) is int and observations['schema']==1 and observations['scope']==SCOPE
assert set(observations['observedURLs'])=={'diagram','lesson','game'}
required={'diagram.jpg','diagram-ax.txt','lesson.jpg','lesson-ax.txt','lesson-article.txt',
          'public-game.jpg','public-game-ax.txt','public-game-cover-report.json'}
names=observations['files']
assert type(names) is list and len(names)==len(set(names)) and required<=set(names) and len(names)<=24
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
source_paths={'docs/learn/index.html','docs/learn/diagrams/accelerated-plane-box-coverage.svg','docs/ACCELERATED_PLANE_BOX_COVERAGE.md'}
assert set(observations['sourceHashes'])==source_paths
for path,value in observations['sourceHashes'].items():assert stamp(value)==hash_bytes(public_blobs[path]),path
for name,path in [('diagram','docs/learn/diagrams/accelerated-plane-box-coverage.svg'),('lesson','docs/learn/index.html')]:
    url=urlsplit(observations['observedURLs'][name])
    assert url.scheme=='https' and url.netloc=='tatata93.github.io' and unquote(url.path)=='/pikapikaengine/'+path
    assert parse_qs(url.query)=={'v':[FEATURE[:7]]}
    assert url.fragment==('plane-box-coverage' if name=='lesson' else '')
image=observations['lessonImage']
assert image['complete'] is True and type(image['width']) is type(image['height']) is int
assert (image['width'],image['height'])==(1120,750)
assert image['src']=='diagrams/accelerated-plane-box-coverage.svg'
assert observations['lessonGuideHref']=='../ACCELERATED_PLANE_BOX_COVERAGE.md'
if 'rect' in image:
    assert type(image['rect']) is dict
    assert all(type(v) in (int,float) and math.isfinite(v) for v in image['rect'].values())
lesson=public_blobs['docs/learn/index.html'].decode('utf-8')
articles=[m for m in re.finditer(r'<article\b([^>]*)>(.*?)</article>',lesson,re.S) if 'accelerated-plane-box-coverage.svg' in m[2]]
assert len(articles)==1 and re.search(r'\bid="accelerated"',articles[0][1])
assert re.findall(r'<img\b[^>]*\bsrc="([^"]*accelerated-plane-box-coverage\.svg)"',articles[0][2])==[image['src']]
assert re.findall(r'<a\b[^>]*\bhref="([^"]*ACCELERATED_PLANE_BOX_COVERAGE\.md)"',articles[0][2])==[observations['lessonGuideHref']]
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

# Optional, bounded history of this milestone's actual UI read failure. It is
# not substituted for the successful current captures above or called an
# executed model/fault-injection test. No prior milestone's history is imported.
collection_history=[]
history_dir=ROOT/f'reports/{PREFIX}-public-browser-development/run-001'
if history_dir.exists():
    assert history_dir.is_dir() and {p.name for p in history_dir.iterdir()}=={'note.json','expanded-ax.txt'}
    note=read(history_dir/'note.json')
    assert type(note['schema']) is int and note['schema']==1
    assert note['stage']=='read visible expanded cover JSON'
    assert note['result']=='CDP read timed out before any file write or subsequent collapse action'
    assert note['scope']=='UI data collection failure; not a model/test/play success or product failure. Actual expanded AX was already captured.'
    diagnostic=note['diagnostic']
    assert type(diagnostic) is str and len(diagnostic)<=2048
    tab=re.fullmatch(r'Timed out after 3000ms waiting for selector pre: Timed out running CDP command Runtime\.evaluate for tab (\d+)',diagnostic)
    assert tab
    history_ax=(history_dir/'expanded-ax.txt').read_bytes().decode('utf-8-sig')
    assert len(history_ax)<=128*1024 and 'Browser tab: '+tab[1]+',' in history_ax
    assert '/pikapikaengine/?v='+original_feature[:7] in history_ax
    assert 'button (expanded) 背面カバーの計測記録' in history_ax
    collection_history.append({'classification':'Original-feature UI read failure; final-feature capture accepted separately','commit':original_feature,
      'note':{'path':relative(history_dir/'note.json'),**remember(history_dir/'note.json'),'record':note},
      'expandedAccessibility':{'path':relative(history_dir/'expanded-ax.txt'),**remember(history_dir/'expanded-ax.txt')},
      'acceptedCompatibilityEvidence':False,
      'currentSuccessfulCapture':{'path':relative(browser_dir/'public-game-cover-report.json'),**remember(browser_dir/'public-game-cover-report.json')},
      'scope':'The original feature saved a 3000ms CDP read timeout before writing/collapsing. The parent reports an original-feature AX resync and 10000ms read of the same visible pre succeeded. Final-feature compatibility requires the separately validated fresh current capture; neither that retry nor the archived original nine captures establishes final-feature acceptance. No model change, requery, fabricated JSON, product failure or successful fault injection is inferred.'})

remember(__file__);remember(RECIPE+'/public-summary-run.py')
assert len(evidence)<=4096 and sum(v['bytes'] for v in evidence.values())<=256*1024*1024
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':FEATURE,
 'localVerification':{'path':local_path,**remember(local_path)},
 'ctest':44,'node':684,'skipped':0,'nativeGroups':74,'finiteFixtures':67,
 'nativePublicValueFullEvaluationReplays':1306,'nativeEndpointBitComparisons':15672,'nativeNegativeZeroEndpoints':2496,
 'independentReference':independent,'selfTestGroups':16,'negativeControls':65,
 'localNativeScope':'Original MSVC finite67/44CTest receipt remains byte unchanged with the original test source; the other six new sources are unchanged. The single test-only helper patch has a separate targeted74 receipt below. Neither is substituted for fresh final-feature GNU/instrumented executions.',
 'postfixTestVerification':{'path':relative(fix_dir/'acceptance.json'),**remember(fix_dir/'acceptance.json'),
   'record':fix,'originalTestArchive':{'path':relative(original_tests_path),**remember(original_tests_path)},
   'exactPatch':{'path':relative(fix_dir/'actual.patch.txt'),**remember(fix_dir/'actual.patch.txt')},
   'originalLocalReportPreserved':True,'unchangedOtherNewSources':6,
   'scope':'Only explicit string_view include, named() parameter by value and diagnostic string materialization changed. Original and targeted fixtures are byte identical; no kernel/input/oracle/threshold/SDK change.'},
 'publicCiScope':{'engineSteps':24,'pagesJobs':3,'linuxIndependentReports':len(linux_reports),
   'newWerrorTranslationUnits':3,'fullyInstrumentedTranslationUnits':5,'regularInstrumentedFixtureByteComparison':True,
   'scope':'Fresh GNU regular and ASan/UBSan runs, same-Linux fixture bytecmp and independent full-range checks. No new WASM API or exact cross-compiler whole-DTO parity claim.'},
 'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
 'protectedFilesUnchanged':369,'generatedEntriesUnchanged':26,'modules':54,'entries':26,'webBuild':public['build'],
 'artifacts':local['artifacts'],'sourceComparisons':source_comparisons,'permittedOldChanges':old_changes,
 'publicFiles':100,'publicChannels':public['channels'],'publicBytes':sum(r['bytes'] for r in public['files']),
 'publicCommands':public_commands,'priorFeaturePublicCommands':prior_public_commands,
 'failedPublicAttempt':failed_public_attempt,'jobs':jobs,'warnings':{'current':48,'prior':48,'sameMultiset':True,'new':0},
 'browser':{'schema':1,'status':'PASS','phase':'public','commit':FEATURE,'buildId':public['build'],'wasmBytes':800982,
   'scope':SCOPE,'observations':observations,'evidence':captures,'screens':screens,
   'lessonArticleCharacters':len(article),'displayScope':'Image-load and complete article text verified; original JPG/AX retained. Screenshot readability is a separate parent visual review, not inferred by this script.'},
 'publicGame':{'paused':True,'kills':int(kills[1]),'queries':queries,'allCompleted':True,'boostObserved':True,'clip1Observed':True,'residentMeshes':3,
   'scope':'Existing sample compatibility only; new Native helper is not executed in the browser.'},
 'historicalLocalAttempts':local['historicalAttempts'],'localLimitations':local['notMeasured'],
 'collectionHistory':collection_history,
 'postFeatureVerifiers':{path:remember(path) for path in [relative(__file__),RECIPE+'/public-summary-run.py']},
 'scope':'Native-only plane-box coverage conditional on caller-declared B/margin and fixed exact-or-RN association. No actual World B derivation, all-compiler/pair/candidate certification, metric proof, TOI/response, actual allocation/value fault injection or used-heap/stack guarantee.',
 'ciEvidenceScope':'Full fetched job log bytes/hash/Unicode characters/line count, exact-feature jobs and every step, literal audit commands and independent reports; warning multiset checked against the retained previous excerpt.',
 'evidence':evidence}
(CAPTURE/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','commit','ctest','node','publicFiles','publicChannels','publicBytes','webBuild']}))


