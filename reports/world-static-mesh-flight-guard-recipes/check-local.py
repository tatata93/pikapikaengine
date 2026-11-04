"""Metadata-only final local receipt. Run only after the parent marks gates ready.

CLI: python check-local.py INPUTS.json FRESH_OUTPUT_DIR
INPUTS schema1 paths: baseline, nativeBuildCommands, nativeCommands, fixture,
originalFixture, storage, referenceReport, referenceControls, referenceFreeze,
artifactAudit, legacyReport, sdkReport, sdkRegressionReport, regressionReport, debugReport,
browserReport; sdkExchanges={flight,entry}; histories=[{path,classification}].
oldSourcePatches maps CMakeLists.txt/.github/workflows/verify.yml/.gitattributes
to literal [{before,after}] applied exactly once to baseline Git text.
lessonInsertion={after,text}. sourceMetadataExceptions (optional) lists exact
{commandFile,path,recorded,current,reason}; these never excuse compiled code.
No Native/SDK/build/World query is executed by this aggregation script.
"""
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CHECKS=ROOT/'reports/world-static-mesh-flight-guard-checks'
BASE='041570543724d984c244b91a45f564d140892e30'
CORE_SHA='635a2ffb8cd5a169351df10bd75d3ed929908930f730a7c9aa2b18b4f9742a73'
OLD8={'core/src/core.cpp','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'}
NEW7=['core/include/pikapika/world_static_mesh_flight_guard.hpp','core/src/world_static_mesh_flight_guard.cpp','tests/world_static_mesh_flight_guard_tests.cpp','tests/world_static_mesh_flight_guard_fixtures.cpp','tests/world_static_mesh_flight_guard_test_support.hpp','scripts/verify-world-static-mesh-flight-guard.py','tests/world_static_mesh_flight_guard_reference_tests.py']
COMPILED=set(NEW7[:5])|{'core/src/core.cpp','core/src/dynamics.cpp','core/include/pikapika/core.hpp','core/src/continuous_world.cpp','cmake/WorldFlightBinding.cmake','scripts/build-simulation.mjs'}
evidence={}
baseline_reconstructions={}

def need(ok,message):
 if not ok:raise AssertionError(message)

def path(value):
 need(type(value) is str or isinstance(value,Path),'explicit evidence path');value=str(value);need(value,'nonempty evidence path')
 p=(ROOT/value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
 need(p.is_relative_to(ROOT),'evidence path outside workspace')
 return p

def rel(p):return p.resolve().relative_to(ROOT).as_posix()

def info(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def remember(p):
 p=path(str(p));raw=p.read_bytes();need(len(raw)<=64*1024*1024,'bounded evidence bytes')
 evidence[rel(p)]=info(raw);return raw

def stamp(p):return info(remember(p))

def load(p):return json.loads(remember(p).decode('utf-8-sig'))

def expected_stamp(actual,expected,label):
 need(type(expected) is dict and type(expected.get('bytes')) is int and re.fullmatch('[0-9a-f]{64}',expected.get('sha256','')),'valid evidence stamp '+label)
 need(actual=={k:expected[k] for k in ['bytes','sha256']},'evidence hash '+label)

def require_pass(p):
 d=load(p);need(d.get('status')=='PASS','completed gate required '+str(p));return d

def blob(name):
 p=subprocess.run(['git','show',BASE+':'+name],cwd=ROOT,capture_output=True,timeout=30)
 need(p.returncode==0,'baseline Git blob '+name);return p.stdout

def lf(raw):return raw.replace(b'\r\n',b'\n')

def normalized_html(raw):
 raw=re.sub(rb'\?build=[0-9a-f]+',b'?build=GENERATED',raw)
 return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',lf(raw),flags=re.S)

def baseline_text_blob(name,expected):
 raw=blob(name)
 variants=[('git_blob_exact',raw),('LF',lf(raw)),('CRLF',lf(raw).replace(b'\n',b'\r\n'))]
 # build-web.mjs preserves a CRLF body but inserts one literal LF between the
 # generated inline import map and module script. Permit exactly that finite
 # construction, only when the complete recorded baseline byte hash matches.
 windows=lf(raw).replace(b'\n',b'\r\n')
 mixed,count=re.subn(rb'(<script type="importmap" id="engine-imports">.*?</script>)\r\n',rb'\1\n',windows,flags=re.S)
 if count==1:variants.append(('CRLF_body_generated_importmap_terminator_LF',mixed))
 matching=[(mode,candidate) for mode,candidate in variants if info(candidate)==expected]
 need(matching,'baseline Git/raw differ only declared text generation/line endings '+name)
 mode,candidate=matching[0]
 baseline_reconstructions[name]={'mode':mode,'gitBlob':info(raw),'reconstructedRaw':info(candidate),'recordedRaw':expected}
 return raw

def source_hashes():return {p:stamp(ROOT/p) for p in NEW7}

def command_rows(p,required=None,current=True):
 d=load(p);rows=d if type(d) is list else d.get('commands')
 need(type(rows) is list and rows,'nonempty completed command collection '+str(p))
 if required is not None:need({r['name'] for r in rows}==set(required),'exact command phases '+str(p))
 for row in rows:
  code=row.get('exit',row.get('exitCode'))
  need(type(code) is int and code==0 and not row.get('timedOut',False),'successful canonical command '+row.get('name',''))
  if 'sourceStable' in row:need(row['sourceStable'] is True,'source stability '+row['name'])
  before=row.get('sourceBefore',row.get('sources'))
  after=row.get('sourceAfter',before)
  if before is not None:
   need(before==after,'before/after command source hashes '+row['name'])
   if current:
    for name,expected in before.items():
     actual=stamp(ROOT/name)
     if actual!=expected:
      allowed=[e for e in CONFIG.get('sourceMetadataExceptions',[]) if e['commandFile']==rel(path(p)) and e['path']==name]
      need(name in {'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'} and name not in COMPILED and len(allowed)==1,'current code/source identity '+name+' in '+str(p))
      e=allowed[0];need(e['recorded']==expected and e['current']==actual and type(e['reason']) is str and e['reason'],'declared historical metadata exception')
  for stream in ['stdout','stderr']:
   value=row[stream]
   if type(value) is dict:
    q=path(value['path']);expected=value
   else:q=path(value);expected=row[stream+'Hash']
   expected_stamp(stamp(q),expected,row.get('name','')+'/'+stream)
  if 'binaryBefore' in row:
   need(row['binaryBefore']==row['binaryAfter'],'stable executed binary')
 return rows

def command_text(row,stream='stdout'):
 value=row[stream];return remember(path(value['path'] if type(value) is dict else value)).decode('utf-8',errors='strict')

def baseline_gate(b):
 need(b['schema']==1 and b['baseCommit']==BASE and len(b['protected'])==383 and len(b['generatedEntries'])==26,'accepted 383/26 baseline')
 need(set(b['permittedOldSources'])==OLD8,'exact eight permitted old paths')
 expected_stamp(stamp(path(b['priorPublicReceipt'])),b['priorPublicReceiptStamp'],'prior public receipt')
 old=load(path(b['priorPublicReceipt']));need(old['status']=='PASS','prior accepted receipt')
 for p,x in b['protected'].items():
  if p not in OLD8:expected_stamp(stamp(ROOT/p),x,'protected '+p)
 # core.cpp exact approved implementation, plus preservation of all other text.
 raw=remember(ROOT/'core/src/core.cpp');need(info(raw)['sha256']==CORE_SHA,'frozen audited core implementation')
 text=lf(raw).decode();oldtext=b['permittedOldSources']['core/src/core.cpp']['gitBlobUtf8']
 text=re.sub(r'#if !defined\(_M_ARM64EC\).*?#endif\n#endif\n\n','',text,count=1,flags=re.S)
 start=text.index('double Vec3::length() const {');end=text.index('Vec3 Vec3::normalized()',start)
 text=text[:start]+'double Vec3::length() const { return std::sqrt(dot(*this)); }\n'+text[end:]
 need(text==oldtext,'all other core source text unchanged')
 # No new source/export silently enters the existing shared Wasm build.
 p='scripts/build-simulation.mjs';addition='// Keep actual vector arithmetic explicit; Wasm retains the std::sqrt fallback.\n// No Native audited-profile macros or new World guard exports enter this SDK.\nsourceFlags[\'core/src/core.cpp\']=[\'-fno-fast-math\',\'-ffp-contract=off\'];\n'
 text=lf(remember(ROOT/p)).decode();need(text.count(addition)==1,'single SDK source flag addition')
 need(text.replace(addition,'')==b['permittedOldSources'][p]['gitBlobUtf8'],'all remaining SDK builder unchanged')
 patches=CONFIG['oldSourcePatches'];need(set(patches)=={'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'},'three explicit text integration declarations')
 editproof={}
 for name,replacements in patches.items():
  text=b['permittedOldSources'][name]['gitBlobUtf8'];need(type(replacements) is list,'literal patch list')
  for r in replacements:
   need(set(r)=={'before','after'} and all(type(r[k]) is str for k in r),'literal edit fields')
   need(r['before'] and text.count(r['before'])==1 and r['before']!=r['after'],'unique original literal')
   special=name=='.github/workflows/verify.yml' and r['before']=='cmake -S . -B build/ci -DCMAKE_BUILD_TYPE=Release' and r['after']=='cmake -S . -B build/ci -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON'
   need(r['after'].count(r['before'])==1 or special,'preserve every old literal except explicit compile-command export flags')
   text=text.replace(r['before'],r['after'],1)
  actual=remember(ROOT/name);expected=text.encode()
  need(actual==expected or lf(actual)==expected,'only declared text integration '+name)
  editproof[name]={'current':info(actual),'expectedLF':info(expected),'CRLFtoLF':actual!=expected,'replacements':replacements}
 entries={}
 for name,x in b['generatedEntries'].items():
  original=baseline_text_blob(name,x)
  actual=remember(ROOT/name);need(normalized_html(actual)==normalized_html(original),'generated-only HTML body '+name);entries[name]=info(actual)
 original=baseline_text_blob('docs/learn/index.html',b['lessonBefore'])
 insertion=CONFIG['lessonInsertion'];need(set(insertion)=={'after','text'} and insertion['text'] and 'world-flight-guard' in insertion['text'],'declared original lesson insertion')
 oldtext=lf(original).decode();need(oldtext.count(insertion['after'])==1,'unique lesson insertion point')
 need(lf(remember(ROOT/'docs/learn/index.html')).decode()==oldtext.replace(insertion['after'],insertion['after']+insertion['text'],1),'lesson unchanged except declared addition')
 return {'baseCommit':BASE,'protectedFiles':383,'permittedOldPaths':sorted(OLD8),'generatedEntries':entries,'textIntegrations':editproof,'baselineTextReconstruction':baseline_reconstructions}

def load_reference():
 s=importlib.util.spec_from_file_location('final_world_reference',ROOT/NEW7[5]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def mathematical_gate(ref):
 d=ref.load(path(CONFIG['fixture']));original=ref.load(path(CONFIG['originalFixture']))
 need(len(original['fixtures'])==49 and len(d['fixtures'])==51,'original49 plus two directed inputs')
 need([f['name'] for f in d['fixtures'][:49]]==[f['name'] for f in original['fixtures']],'original labels preserved')
 need(ref.input_fingerprint(d['fixtures'][:49])==ref.input_fingerprint(original['fixtures']),'all original input types/bits/order unchanged')
 for a,b in zip(d['fixtures'][:49],original['fixtures']):ref.equal(a['input'],b['input'],'complete original49 input')
 actual=ref.verify(d);saved=require_pass(path(CONFIG['referenceReport']));need(actual==saved,'saved independent report equals current reference')
 need(actual['mathematicalChildrenVerified']=={'flight':96,'metric':34,'planeBox':33,'sphereBox':21} and actual['childCalls']==184,'184 actual independent child verifications')
 need((actual['certifiedSeparated'],actual['notCertified'],actual['invalidInputs'])==(14,26,11),'complete51 classifications')
 controls=require_pass(path(CONFIG['referenceControls']));need(controls['selfTestGroups']==12 and controls['fixtures']==51 and controls['baseline']==actual and controls['labelAndOrderIndependent'] is True,'full reference/self/label-order proof')
 rejected=controls['rejectedControls'];need(len(rejected)==138 and len({r['name'] for r in rejected})==138 and all(r['rejected'] is True for r in rejected),'138 distinct actual rejected controls')
 optimized=load(path(CONFIG['referenceControls']).parent/'optimized-command.json');need(optimized['exitCode']!=0 and '-O' in optimized['command'],'actual optimized-mode rejection')
 need('without Python -O' in remember(path(CONFIG['referenceControls']).parent/'optimized.stderr.txt').decode(),'optimized refusal diagnostic')
 freeze=load(path(CONFIG['referenceFreeze']));need(freeze['status']=='FROZEN' and freeze['fixtures']==51,'frozen reference corpus')
 for x in freeze['sources']+freeze['protectedReferencesReadOnly']+freeze['attemptFiles']:expected_stamp(stamp(path(x['path'])),x,'reference freeze evidence')
 for name,row in [('mixed-static-explicit-primitive-e128-full-candidate',d['fixtures'][-2]),('dual-plane-predicate-meshes-separated-only',d['fixtures'][-1])]:need(row['name']==name,'explicit separately directed new input')
 return d,actual,controls

def native_gate(d):
 builds=command_rows(path(CONFIG['nativeBuildCommands']));rows=command_rows(path(CONFIG['nativeCommands']),{'fixtures','dedicated','storage'})
 values={r['name']:r for r in rows};expected_stamp(stamp(path(CONFIG['fixture'])),values['fixtures']['stdoutHash'],'actual Native fixture stream')
 need(remember(path(CONFIG['fixture']))==remember(path(values['fixtures']['stdout'])),'fixture full raw stdout equality')
 need('58 groups PASS; 51 finite fixtures; 184 actual child calls / 184 whole child DTO direct-repeat comparisons' in command_text(values['dedicated']),'Native58/51/184 direct-repeat executed')
 storage=load(path(CONFIG['storage']));need(storage['kind']=='world-static-mesh-flight-guard-storage' and storage['layoutSizes']==d['layoutSizes'],'same-run observed layout24')
 need(storage['scope']=='sizeof and observed capacities/logical requests only; not used heap/allocator/stack/RSS/peak guarantee','honest storage scope')
 need(storage['sizes']['result']==d['layoutSizes']['guardResult'] and storage['sizes']['bodyRecord']==d['layoutSizes']['bodyRecord'] and storage['sizes']['pairRecord']==d['layoutSizes']['pairRecord'],'actual public sizes')
 need(storage['logicalPayloadBytes']==d['fixtures'][0]['result']['reservation']['retained']['logicalPayloadBytes'],'observed base logical requested payload')
 return rows,storage

def artifact_gate(rows,d):
 audit=require_pass(path(CONFIG['artifactAudit']))
 for k in ['artifactsStable','sourcesStable','toolsStable','recipeStable','compilationFilesStable']:need(audit.get(k) is True,'complete artifact audit '+k)
 need(audit['binaryExecuted'] is False and audit['runtimeSelfIntrospection'] is False,'artifact instruction audit separated from execution')
 p=audit['profile'];need(p['profile']==1 and p['configuration']=='Release' and p['architecture']=='x64-sse2','actual audited configured profile')
 need(all(f['result']['binding']['buildId']==p['buildId'] for f in d['fixtures']),'all results bound to audited configuration identity')
 for x in audit['inputs'].values():expected_stamp(stamp(path(x['path'])),x,'current audited artifact')
 for x in audit['sources']:expected_stamp(stamp(path(x['path'])),x,'current audited compiled source')
 for x in audit['compilationProvenance']['files']:expected_stamp(stamp(path(x['path'])),x,'actual compiler/link evidence')
 for key,x in audit['toolsAfter'].items():
  expected_stamp(info(Path(x['path']).read_bytes()),x,'unchanged actual audit/compiler tool '+key)
 for row in audit['commands']:
  need(type(row['exitCode']) is int and row['exitCode']==0,'actual audit command success')
  for stream in ['stdout','stderr']:
   x=row[stream];expected_stamp(stamp(path(x['path'])),x,'artifact audit raw tool stream')
 need(audit['compilationProvenance']['noLinkTimeCodeGeneration'] is True,'no hidden link-time transformation')
 for row in rows:need(row['binaryBefore']=={k:audit['inputs']['binary'][k] for k in ['bytes','sha256']},'exact audited and executed linked binary')
 need(audit['proof']['dataflowControls']['rejectedControls']>0,'actual AST/dataflow controls')
 return audit

def sdk_gate(b):
 sdk=require_pass(path(CONFIG['sdkReport']));need(sdk['sourceStable'] is True and sdk['sourcesChanged']==['core/src/core.cpp'],'formal rebuild only existing core source changed')
 need((sdk['exports'],sdk['compiledTranslationUnits'],sdk['sourceHeaders'],sdk['runtimeMembers'],sdk['licenseNotices'])==(92,32,67,91,7),'unchanged SDK surface/runtime/notices')
 need(sdk['beforeManifest']==b['sdkManifest'],'original SDK manifest preserved')
 manifest=load(ROOT/'assets/pikapika-simulation.build.json');need(sdk['afterManifest']==manifest,'actual newly built current manifest')
 old=b['sdkManifest'];need(manifest['sources']==old['sources'] and len(manifest['sources'])==32 and set(manifest['sourceSha256'])==set(old['sourceSha256']),'same translation units/source-header membership')
 need([k for k in manifest['sourceSha256'] if manifest['sourceSha256'][k]!=old['sourceSha256'][k]]==['core/src/core.cpp'],'only allowed compiled core hash differs')
 for name,sha in manifest['sourceSha256'].items():need(stamp(ROOT/name)['sha256']==sha,'actual SDK source hash '+name)
 need(manifest['flags']==old['flags'] and manifest['licenses']==old['licenses'] and manifest['linkedLibraryMembers']==old['linkedLibraryMembers'] and sdk['runtimeMembersUnchanged'] is True,'all old exports/runtime/legal records unchanged')
 expected={**old['sourceFlags'],'core/src/core.cpp':['-fno-fast-math','-ffp-contract=off']};need(manifest['sourceFlags']==expected,'only SDK core strict graph flags added')
 for name,sha in manifest['licenses'].items():need(stamp(ROOT/name)['sha256']==sha,'unchanged license notice '+name)
 for name,x in manifest['artifacts'].items():expected_stamp(stamp(ROOT/name),x,'actual SDK binary/glue')
 need(sdk['artifacts']==manifest['artifacts'],'formal built artifact hashes')
 command_rows(path(CONFIG['sdkReport']).parent/'commands.json',{'formal-sdk-rebuild'})
 return {'exports':92,'compiledTranslationUnits':32,'sourceHeaders':67,'runtimeMembers':91,'licenseNotices':7,'artifacts':{p:stamp(ROOT/p) for p in ['assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']}}

def legacy_gate():
 r=require_pass(path(CONFIG['legacyReport']));need(r['sourceStable'] is True and set(r['native'])=={'legacy','simulation','supported'},'three old Native full reports')
 command_rows(path(CONFIG['legacyReport']).parent/'commands.json',{'legacy','simulation','supported','legacy-wasm'})
 for name,x in r['native'].items():need(x['byteEqual'] is True and x['before']==x['after'],'old full byte equality '+name)
 w=r['legacyWasm'];need(w['status']=='PASS' and w['fixtures']==20 and w['numericBits']==4520 and w['negativeZeroBits']==24 and w['comparedToBaseline'] is True,'actual old20 SDK baseline bit comparison')
 need(set(CONFIG['sdkExchanges'])=={'flight','entry'},'both actual old owned SDK regressions required')
 full=path(CONFIG['sdkRegressionReport']);require_pass(full)
 command_rows(full.parent/'commands.json',{'simulation','flight-native','flight-wire','flight-independent','flight-owned','flight-lab','entry-owned'})
 raw_reports={name:require_pass(full.parent/name/'report.json') for name in ['flight-native','flight-wire','flight-independent','flight-lab']}
 for name in ['flight-native','flight-independent']:
  x=raw_reports[name]
  need(tuple(x[k] for k in ['fixtureCount','accepted','hostRejected','numericBits','negativeZeroBits','decodedNumericBits','decodedNegativeZeroBits','records'])==(183,173,10,415506,5738,272814,5424,10397),'complete actual raw/independent flight report '+name)
  optimized=x['optimizedPythonRejected']
  need(type(optimized) is dict and set(optimized)=={'status','exitCode'} and optimized['status']=='PASS' and type(optimized['exitCode']) is int and optimized['exitCode']!=0,'old raw optimized Python actual nonzero rejection')
  controls=x['packetNegativeControls']
  need(controls['status']=='PASS' and type(controls['count']) is int and controls['count']==16 and len(controls['rejectedControls'])==16 and len({r['name'] for r in controls['rejectedControls']})==16 and all(r['rejected'] is True for r in controls['rejectedControls']),'actual16 copied packet controls rejected')
 need(raw_reports['flight-native']['acceptedInputFingerprint']==raw_reports['flight-independent']['acceptedInputFingerprint'],'same actual accepted complete input corpus')
 wire=raw_reports['flight-wire'];need(tuple(wire[k] for k in ['fixtures','accepted','hostRejected','numericBits','negativeZeroBits'])==(183,173,10,415689,5738),'raw Wasm whole wire including mode metadata')
 need(wire['wasm']==stamp(ROOT/'assets/pikapika-simulation.wasm'),'actual new Wasm raw wire provenance')
 exchanges={}
 for kind,name in CONFIG['sdkExchanges'].items():
  q=path(name);x=require_pass(q)
  if kind=='flight':
   need((x['fixtures'],x['actualModels'],x['hostRejected'])==(183,173,10) and x['sourceStable'] is True and x['originalExportsAndPrototypesUnchanged'] is True and x['oldEntryAndWorldUnchanged'] is True,'complete existing flight SDK183/173/10')
  else:need((x['fixtureCount'],x['actualModelFixtures'],x['hostRejected'])==(65,62,3),'complete existing entry SDK65/62/3')
  need(x['reference']['status']=='PASS','independent old owned DTO math '+kind)
  for file,expected in x['files'].items():expected_stamp(stamp(q.parent/file),expected,'old owned artifact '+kind+'/'+file)
  need(x['wasm']==stamp(ROOT/'assets/pikapika-simulation.wasm'),'fresh old SDK regression uses actual new artifact')
  exchanges[kind]=x
 return {'native':r['native'],'legacyWasm':w,'ownedSdk':exchanges,'actualRawAndLabReports':raw_reports}

def regression_gate():
 q=path(CONFIG['regressionReport']);r=require_pass(q);rows=command_rows(q.parent/'commands.json',{'build-all','ctest','node-tests','syntax','web-build'});text={v['name']:command_text(v) for v in rows}
 need('100% tests passed, 0 tests failed out of 46' in text['ctest'],'actual complete46 CTest')
 names=re.findall(r'Test\s+#\d+:\s+(\S+)\s+\.+\s+Passed',text['ctest']);need(len(names)==46 and len(set(names))==46 and 'world_static_mesh_flight_guard' in names,'all46 named tests including new guard')
 node=text['node-tests'];counts={}
 for key in ['tests','pass','fail','skipped']:
  m=re.search(r'(?:#|ℹ)\s*'+key+r'\s+(\d+)',node);need(m is not None,'actual Node summary '+key);counts[key]=int(m[1])
 need(counts=={'tests':684,'pass':684,'fail':0,'skipped':0},'684 Node/skip0')
 web=re.search(r'Web build ([0-9a-f]{16}): 54 versioned modules; generated import maps',text['web-build']);need(web is not None,'actual Web54 module output')
 for name in load(path(CONFIG['baseline']))['generatedEntries']:
  raw=remember(ROOT/name);markers=re.findall(rb'\?build=([0-9a-f]{16})',raw)
  need(markers and all(x.decode()==web[1] for x in markers),'all26 actual generated entries use current Web marker')
 return {'ctest':46,'ctestNames':names,'node':counts,'webBuildId':web[1],'modules':54,'entries':26,'commands':rows}

def debug_gate():
 q=path(CONFIG['debugReport']);d=require_pass(q);command_rows(q.parent/'commands.json',{'build','refusal'})
 need(d['profile']['profile']==0 and d['profile']['configuration']=='Debug','actual unconfigured Debug build')
 expected_stamp(stamp(ROOT/'build/native/Debug/pikapika_world_static_mesh_flight_guard_tests.exe'),d['binary'],'executed Debug binary')
 need('PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=0' in remember(q.parent/'actual-compile-commands.txt').decode('utf-16'),'actual Debug compile profile0')
 return d

def browser_gate(sdk,regressions):
 q=path(CONFIG['browserReport']);d=require_pass(q)
 need(d.get('phase')=='local' and d['wasmBytes']==sdk['artifacts']['assets/pikapika-simulation.wasm']['bytes'],'current actual local browser artifact')
 need(type(d['buildId']) is str and re.fullmatch('[0-9a-f]{16}',d['buildId']),'current browser Web build marker')
 need(d['buildId']==regressions['webBuildId'],'actual browser loaded final rebuilt Web cohort')
 need(type(d['scope']) is str and 'Native' in d['scope'] and any(x in d['scope'].lower() for x in ['no browser','not','未','なし']),'browser is display/game compatibility, no new browser numerical API')
 need(type(d['evidence']) is dict and len(d['evidence'])>=4,'actual browser evidence captures')
 for name,x in d['evidence'].items():expected_stamp(stamp(path(name)),x,'browser capture')
 game=d['game'];need(game['paused'] is True and game['kills']>=1 and game['boostClip1Observed'] is True and game['residentMeshes']==3,'actual paused game/boost/kill/residency')
 need(game['coverQueries']>0 and game['allCompleted'] is True,'all game cover queries actually completed')
 return d

def main():
 global CONFIG
 need(__debug__,'run final local receipt without Python -O');need(len(sys.argv)==3,'Usage: check-local.py INPUTS.json FRESH_OUTPUT_DIR')
 configuration=path(sys.argv[1]);CONFIG=load(configuration);need(CONFIG['schema']==1,'input path manifest schema')
 out=path(sys.argv[2]);need(out.is_relative_to(CHECKS),'fresh output under known checks root');out.mkdir(parents=True,exist_ok=False)
 before=source_hashes();recipe=stamp(Path(__file__))
 try:
  b=load(path(CONFIG['baseline']));baseline=baseline_gate(b);ref=load_reference();d,math,controls=mathematical_gate(ref);rows,storage=native_gate(d);audit=artifact_gate(rows,d);sdk=sdk_gate(b);legacy=legacy_gate();regressions=regression_gate();debug=debug_gate();browser=browser_gate(sdk,regressions)
  histories=[]
  need(type(CONFIG['histories']) is list and CONFIG['histories'],'explicit historical failed/provisional attempts')
  for item in CONFIG['histories']:
   need(set(item)=={'path','classification'} and type(item['classification']) is str and item['classification'],'exact bounded history descriptor')
   histories.append({**item,**stamp(path(item['path']))})
  need(source_hashes()==before and stamp(Path(__file__))==recipe,'all accepted new sources/recipe stable through aggregation')
  need(all(info(path(name).read_bytes())==x for name,x in evidence.items()),'all recorded evidence remains byte-stable through aggregation')
  report={'schema':1,'status':'PASS','baseCommit':BASE,'fixtures':51,'nativeGroups':58,'ctest':46,'node':684,'skipped':0,'independentReference':math,'selfTestGroups':12,'negativeControls':138,'baseline':baseline,'newSources':before,'binding':audit,'nativeCommands':rows,'storageObservation':storage,'sdk':sdk,'legacyRegressions':legacy,'regressions':regressions,'debugRefusal':debug,'browser':browser,'historicalAttempts':histories,'metadataExceptions':CONFIG.get('sourceMetadataExceptions',[]),'recipe':recipe,'inputManifest':stamp(configuration),'evidence':evidence,'scope':'Read-only finite World flight guard: independent mathematics and ownership/accounting, Native public-value repeatability, and actual object/link/compile binding are separate gates. No World advance/response/new browser query, general target guarantee, actual allocator/nonreturn injection, heap/stack bound or cross-compiler whole-output parity.'}
  (out/'acceptance.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({'status':'PASS','fixtures':51,'ctest':46,'node':684,'evidenceFiles':len(evidence)}));return 0
 except BaseException as error:
  (out/'failure.json').write_bytes((json.dumps({'schema':1,'status':'FAIL','error':type(error).__name__+': '+str(error),'inputManifest':str(configuration),'sourcesBefore':before,'sourcesAfter':source_hashes(),'evidence':evidence},indent=2)+'\n').encode());raise

if __name__=='__main__':raise SystemExit(main())
