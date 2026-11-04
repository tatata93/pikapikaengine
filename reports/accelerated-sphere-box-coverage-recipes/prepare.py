"""Capture a FINAL accepted plane receipt baseline. Not run during preparation.
Usage: python .../prepare.py FULL_NEW_PLANE_RECEIPT_HEAD
This does not integrate/build, regenerate the SDK or replace check.py.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-sphere-box-coverage'
PREAUTHOR='reports/accelerated-sphere-box-coverage-development/before-implementation.json'
RECEIPT='reports/accelerated-plane-box-coverage-public-verification.json'
BASELINE=f'reports/{PREFIX}-baseline.json'
SOURCES={
 'core/include/pikapika/accelerated_sphere_box_coverage.hpp':(7361,'b1095fca311ac2eb4a1b6d464e85945d11ae82d2ae86ab59c5547cef5fbd7ada'),
 'core/src/accelerated_sphere_box_coverage.cpp':(20894,'3c531d94a1d1fa362fa2fc0bcf093e79eefc942df11793681b8bb0fd7d76dc5e'),
 'tests/accelerated_sphere_box_coverage_tests.cpp':(27615,'55fa3407dcf97adfea09f2cbc82a7d07a0678975bcea1fa1e9ec3c48e2151c83'),
 'tests/accelerated_sphere_box_coverage_fixtures.cpp':(15285,'13140ea9b0e499eb3edfdb0845ad3f945f8e64e20d316752ac590d9203c30644'),
 'tests/accelerated_sphere_box_coverage_test_support.hpp':(939,'5b040bf536c9d7b8c1fa0b7f64e9158e1c84a0a7f71554fe70796655bba9b923'),
 'scripts/verify-accelerated-sphere-box-coverage.py':(27140,'207e506b477be44edbb2b741a65ab5ded0b2305c903d37da4010e1f3b22dd6ff'),
 'tests/accelerated_sphere_box_coverage_reference_tests.py':(22162,'7dc93c173c210830ad319c261ab676e77cbd75a693cfa0cc10b0e576bcf6fcc7'),
}
INTEGRATIONS=['CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']
def need(condition,message):
 if not condition:raise RuntimeError(message)
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def file_info(path):return info((ROOT/path).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def frozen_sources():
 result={}
 for path,(size,digest) in SOURCES.items():
  actual=file_info(path);need(actual=={'bytes':size,'sha256':digest},'Frozen source changed: '+path);result[path]=actual
 code=(ROOT/'tests/accelerated_sphere_box_coverage_tests.cpp').read_text(encoding='utf-8')
 need('named(const std::vector<f::Case>& corpus,std::string_view name)' in code,'Lookup must pass string_view by value')
 return result

def validate_base(base):
 need(re.fullmatch(r'[0-9a-f]{40}',base) is not None,'Supply a full lowercase NEW receipt commit')
 need(git('rev-parse','HEAD').decode().strip()==base,'Baseline must be current receipt HEAD')
 pre=json.loads((ROOT/PREAUTHOR).read_text(encoding='utf-8'))
 need(base!=pre['baseCommit'],'Pre-authoring public-pending HEAD is not the final accepted baseline')
 need(len(pre['protected'])==376 and len(pre['generatedEntries'])==26 and len(pre['integrations'])==3,'Pre-authoring dimensions changed')
 for group in ['protected','generatedEntries','integrations']:
  for path,expected in pre[group].items():need(file_info(path)==expected,'Original '+group+' changed: '+path)
 receipt_raw=(ROOT/RECEIPT).read_bytes();receipt=json.loads(receipt_raw)
 need(git('show',base+':'+RECEIPT)==receipt_raw,'PASS public receipt must already be committed at the NEW HEAD')
 need(receipt['status']=='PASS' and receipt['commit']!=base,'Require separate postfeature PASS receipt commit')
 subprocess.run(['git','merge-base','--is-ancestor',receipt['commit'],base],cwd=ROOT,check=True)
 expected={'ctest':44,'node':684,'skipped':0,'nativeGroups':74,'finiteFixtures':67,'publicFiles':100,
           'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7}
 for key,value in expected.items():need(receipt[key]==value,'Unexpected plane receipt '+key)
 need(receipt['postfixTestVerification']['record']['new']=={'bytes':21208,'sha256':'901dbab86cadceb69ef9e293fc9bf7951a37411128e9013a046562fe01ef2cba'},'Corrected three-line plane helper provenance missing')
 need(file_info('tests/accelerated_plane_box_coverage_tests.cpp')==receipt['postfixTestVerification']['record']['new'],'Corrected plane test changed')
 manifest=json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf-8'))
 need(manifest==pre['sdkManifest'],'SDK manifest changed')
 new_sources=frozen_sources()
 changed=set(git('diff','--name-only',base,'--').decode().splitlines())
 need(not changed.intersection(set(pre['protected'])|set(pre['generatedEntries'])|set(INTEGRATIONS)|{RECEIPT}),'Protected tracked differences from final HEAD')
 return pre,receipt,new_sources

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('base');args=parser.parse_args()
 out=ROOT/BASELINE;need(not out.exists(),'Do not overwrite a final baseline')
 pre,receipt,sources=validate_base(args.base)
 permitted={}
 for path in INTEGRATIONS:
  raw=(ROOT/path).read_bytes();blob=git('show',args.base+':'+path)
  need(raw.replace(b'\r\n',b'\n')==blob,'Integration file is not its receipt Git blob: '+path)
  permitted[path]={'raw':info(raw),'gitBlob':info(blob),'gitBlobUtf8':blob.decode('utf-8')}
 record={'schema':1,'baseCommit':args.base,'created':datetime.now(timezone.utc).isoformat(),
  'scope':'Final accepted plane receipt baseline; new Native sphere-box standalone/math remain separate and no actual World, SDK or public sphere acceptance is inferred.',
  'preAuthoring':{'path':PREAUTHOR,**file_info(PREAUTHOR),'baseCommit':pre['baseCommit'],'scope':pre['scope']},
  'protected':pre['protected'],'generatedEntries':pre['generatedEntries'],'permittedOldSources':permitted,
  'lessonBefore':file_info('docs/learn/index.html'),'sdkManifest':pre['sdkManifest'],
  'priorPublicReceipt':RECEIPT,'priorPublicReceiptStamp':file_info(RECEIPT),'priorPublicFeatureCommit':receipt['commit'],
  'newSources':sources,'standaloneFreeze':file_info('reports/accelerated-sphere-box-coverage-native-development/run-001/freeze.json'),
  'storageClarification':{'vectorPayloadSizeofTimesCapacityBytes':97976,'inlineResultBytes':480,'combinedLogicalBytes':98456,'snapshotAlreadyInsideResult':True,'scope':'Observed vector capacity payload plus inline result only; no allocator, transient, stack, RSS or heap bound.'}}
 with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps({'status':'PASS','base':args.base,'protected':376,'entries':26,'newSources':7,'baseline':BASELINE}))
if __name__=='__main__':main()
