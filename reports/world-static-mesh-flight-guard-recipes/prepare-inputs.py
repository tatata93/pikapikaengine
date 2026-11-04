"""Prepare explicit final receipt inputs; never invoke check-local or any build.

Use only after the parent declares all final gates ready. Example:
 python prepare-inputs.py --ready --native-build CHECKS/run-build-final \
  --candidate CHECKS/run-candidate-final --audit BINDING/run-final/audit.json \
  --regressions CHECKS/run-regression-final --debug CHECKS/run-debug-final \
  --browser reports/.../browser-verification.json --output CHECKS/inputs-001.json
All paths are workspace relative (or absolute inside the workspace). No prior
receipt/raw log/source is rewritten. The output file must not already exist.
"""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PREFIX='reports/world-static-mesh-flight-guard-'
CHECKS=ROOT/(PREFIX+'checks')
BASE='041570543724d984c244b91a45f564d140892e30'
SPECIAL_BEFORE='cmake -S . -B build/ci -DCMAKE_BUILD_TYPE=Release'
SPECIAL_AFTER='cmake -S . -B build/ci -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON'

def need(ok,message):
 if not ok:raise AssertionError(message)

def path(value):
 p=(ROOT/str(value)).resolve() if not Path(value).is_absolute() else Path(value).resolve()
 need(p.is_relative_to(ROOT),'workspace evidence only');return p

def rel(value):return path(value).relative_to(ROOT).as_posix()

def read(value):return path(value).read_bytes()

def stamp(value):
 b=read(value);return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def load(value):return json.loads(read(value).decode('utf-8-sig'))

def lf(raw):return raw.replace(b'\r\n',b'\n').decode('utf-8')

def blob(name):
 run=subprocess.run(['git','show',BASE+':'+name],cwd=ROOT,capture_output=True,timeout=30)
 need(run.returncode==0,'baseline Git source '+name);return lf(run.stdout)

def unique_insertion(text,index,addition):
 """Select a literal anchor without changing or dropping any original byte."""
 if index:
  width=1
  while width<index and text.count(text[index-width:index])!=1:width+=1
  before=text[index-width:index]
  if text.count(before)==1:return {'before':before,'after':before+addition}
 width=1
 while index+width<len(text) and text.count(text[index:index+width])!=1:width+=1
 before=text[index:index+width]
 need(before and text.count(before)==1,'unique literal insertion anchor')
 return {'before':before,'after':addition+before}

def insertion_patches(original,target,name):
 work=original;patches=[]
 if name=='.github/workflows/verify.yml':
  need(work.count(SPECIAL_BEFORE)==target.count(SPECIAL_AFTER)==1,'exact workflow generator/compile-command export change')
  r={'before':SPECIAL_BEFORE,'after':SPECIAL_AFTER};patches.append(r);work=work.replace(r['before'],r['after'],1)
 oldlines=work.splitlines(keepends=True);newlines=target.splitlines(keepends=True)
 offsets=[0]
 for line in oldlines:offsets.append(offsets[-1]+len(line))
 matcher=difflib.SequenceMatcher(None,oldlines,newlines,autojunk=False);inserts=[]
 for tag,a,b,c,d in matcher.get_opcodes():
  if tag=='equal':continue
  if tag=='insert':inserts.append((offsets[a],''.join(newlines[c:d])));continue
  need(tag=='replace','old text deleted outside explicit insertion: '+name)
  # A paths-list addition can occur inside one otherwise preserved line.
  # Keep character matching bounded to the changed block, not the whole YAML.
  oldpart=''.join(oldlines[a:b]);newpart=''.join(newlines[c:d]);need(len(oldpart)+len(newpart)<=16384,'bounded inline insertion block')
  inline=difflib.SequenceMatcher(None,oldpart,newpart,autojunk=False)
  for inner,x,y,z,w in inline.get_opcodes():
   need(inner in {'equal','insert'},'old text changed outside explicit insertion: '+name+' / '+inner)
   if inner=='insert':inserts.append((offsets[a]+x,newpart[z:w]))
 for index,addition in reversed(inserts):
  r=unique_insertion(work,index,addition)
  need(r['after'].count(r['before'])==1,'old anchor survives exactly once')
  patches.append(r);work=work.replace(r['before'],r['after'],1)
 need(work==target,'exact complete declared insertion reconstruction '+name)
 return patches

def lesson_insertion(original,target):
 start=0
 while start<min(len(original),len(target)) and original[start]==target[start]:start+=1
 end=0
 while end<len(original)-start and end<len(target)-start and original[-end-1]==target[-end-1]:end+=1
 oldend=len(original)-end;newend=len(target)-end
 need(oldend==start,'lesson must preserve all original text as one insertion')
 added=target[start:newend]
 need(added and 'world-flight-guard' in added,'new original World lesson figure/text')
 r=unique_insertion(original,start,added)
 need(r['after'].endswith(added) and r['after']==r['before']+added,'lesson insertion must follow a unique original prefix')
 result={'after':r['before'],'text':added}
 need(original.replace(result['after'],result['after']+result['text'],1)==target,'whole lesson single insertion')
 return result

def require_pass(value):
 d=load(value);need(d.get('status')=='PASS','missing or nonpassing final gate '+str(value));return d

def require_commands(directory,names):
 p=path(directory)/'commands.json';d=load(p)
 need(type(d) is list and {x['name'] for x in d}==set(names),'all final command phases '+str(directory))
 for row in d:need(row['exit']==0 and row.get('timedOut',False) is False and row['sourceStable'] is True,'completed stable command '+row['name'])
 return rel(p)

def history_paths(final_audit,final_debug,final_candidate):
 rows={}
 def add(p,classification):
  p=path(p)
  if p.is_file():rows[rel(p)]={'path':rel(p),'classification':classification}
 # Explicitly bounded old failed collections; no current canonical success is
 # excluded merely by a filename or an arbitrary nonzero exit.
 for command in sorted(CHECKS.glob('*/commands.json')):
  if command.parent in {path(final_debug),path(final_candidate)}:continue
  d=load(command)
  if not any(x.get('exit') not in (0,) for x in d):continue
  classification='Retained prior nonzero command attempt; original stdout/stderr records actual failure and is not a successful final gate.'
  if 'candidate-001' in command.parent.name:classification='Initial Native dedicated test expected-status mismatch; actual original49 mathematical/source/accounting proof retained separately. Only authored expectations were corrected, plus two separately directed inputs.'
  elif 'regression-' in command.parent.name:classification='Prior full CTest invocation failed because the new test CLI received an empty generator-expression argument. Normal dedicated58 route was separately successful; later --run alias/CTest integration fixes are test/harness only.'
  add(command,classification)
  for r in d:
   for key in ['stdout','stderr']:
    if key in r:add(r[key],classification)
 for p in sorted((ROOT/(PREFIX+'binding-development')).glob('*/audit.json')):
  if p.resolve()==path(final_audit):continue
  d=load(p);classification='Retained earlier artifact-auditor attempt ('+d.get('status','unknown')+'); not the final exact linked binary/compile receipt.'
  add(p,classification)
  for row in d.get('commands',[]):
   for key in ['stdout','stderr']:
    item=row.get(key)
    if type(item) is dict and 'path' in item:add(item['path'],classification)
 add(ROOT/(PREFIX+'reference-development/freeze.json'),'Complete independent self/prepin/final history: includes checker-only import indentation failure, original49 and final51 actual proofs, twelve self groups and138 rejections. Not a production/allocator fault injection.')
 add(ROOT/(PREFIX+'local-browser/collection-history.json'),'Actual browser collection/rebind/timeout history; display/game collection issues are distinct from a new Native numerical query or physics fault injection.')
 need(rows,'retained history is required');return list(rows.values())

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--ready',action='store_true',help='Use only after the parent explicitly declares all final gates ready.')
 for name in ['native-build','candidate','audit','regressions','debug','browser','output']:parser.add_argument('--'+name,required=True)
 parser.add_argument('--sdk',default=PREFIX+'checks/run-20261104-sdk-002')
 parser.add_argument('--sdk-regression',default=PREFIX+'checks/run-20261105-sdk-regression-001')
 parser.add_argument('--legacy',default=PREFIX+'checks/run-20261104-legacy-after-001')
 parser.add_argument('--reference',default=PREFIX+'reference-development/run-008/controls')
 args=parser.parse_args();need(args.ready,'parent final gate-ready notice required; no input manifest written')
 out=path(args.output);need(out.is_relative_to(CHECKS) and not out.exists(),'exclusive new input manifest under checks root')
 fixture=path(args.candidate)/'fixtures.json';storage=path(args.candidate)/'storage.json'
 native_commands=require_commands(args.candidate,['fixtures','dedicated','storage'])
 build_commands=path(args.native_build)/'commands.json';need(build_commands.is_file(),'explicit actual final Native build receipt')
 require_commands(args.regressions,['build-all','ctest','node-tests','syntax','web-build'])
 require_commands(args.debug,['build','refusal'])
 audit=require_pass(args.audit);need(audit.get('compilationFilesStable') is True,'final complete compilation/binary audit')
 browser=require_pass(args.browser);need(browser['phase']=='local','actual final local browser receipt')
 require_pass(path(args.regressions)/'regression.json');require_pass(path(args.debug)/'refusal.json')
 require_pass(path(args.sdk)/'build-observation.json');require_pass(path(args.sdk_regression)/'sdk-regression.json');require_pass(path(args.legacy)/'regression.json')
 for p in [fixture,storage,path(args.reference)/'reference.json',path(args.reference)/'negative-controls.json']:need(p.is_file(),'required complete actual evidence '+str(p))
 need(read(fixture)==read(ROOT/(PREFIX+'checks/run-20261105-candidate-002/fixtures.json')),'--run alias must preserve the accepted complete51 Native fixture bytes')
 base=load(ROOT/(PREFIX+'baseline.json'));need(base['baseCommit']==BASE and len(base['protected'])==383,'accepted383 baseline')
 patches={}
 normalization={}
 for name in ['CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']:
  old=blob(name);current=read(ROOT/name);normalized=lf(current)
  patches[name]=insertion_patches(old,normalized,name)
  normalization[name]={'raw':stamp(ROOT/name),'LF':{'bytes':len(normalized.encode()),'sha256':hashlib.sha256(normalized.encode()).hexdigest()},'declaredCRLFtoLF':current!=normalized.encode()}
 insertion=lesson_insertion(blob('docs/learn/index.html'),lf(read(ROOT/'docs/learn/index.html')))
 config={'schema':1,'baseline':PREFIX+'baseline.json','nativeBuildCommands':rel(build_commands),'nativeCommands':native_commands,
  'fixture':rel(fixture),'originalFixture':PREFIX+'checks/run-20261104-candidate-001/fixtures.json','storage':rel(storage),
  'referenceReport':rel(path(args.reference)/'reference.json'),'referenceControls':rel(path(args.reference)/'negative-controls.json'),'referenceFreeze':PREFIX+'reference-development/freeze.json',
  'artifactAudit':rel(args.audit),'legacyReport':rel(path(args.legacy)/'regression.json'),'sdkReport':rel(path(args.sdk)/'build-observation.json'),
  'sdkRegressionReport':rel(path(args.sdk_regression)/'sdk-regression.json'),'sdkExchanges':{'flight':rel(path(args.sdk_regression)/'flight-owned/report.json'),'entry':rel(path(args.sdk_regression)/'entry-owned/report.json')},
  'regressionReport':rel(path(args.regressions)/'regression.json'),'debugReport':rel(path(args.debug)/'refusal.json'),'browserReport':rel(args.browser),
  'oldSourcePatches':patches,'lessonInsertion':insertion,'sourceMetadataExceptions':[],
  'histories':history_paths(args.audit,args.debug,args.candidate),
  'inputPreparation':{'scope':'Read-only metadata/paths and exact old-text reconstruction only. Does not execute or accept check-local, any Native model, SDK, browser or build.',
   'baseCommit':BASE,'recipe':stamp(Path(__file__)),'normalization':normalization,'selectedNativeBinary':audit['inputs']['binary'],'candidateFixture':stamp(fixture)}}
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as stream:stream.write((json.dumps(config,indent=2)+'\n').encode())
 print(json.dumps({'status':'INPUTS_PREPARED_NOT_ACCEPTED','path':rel(out),**stamp(out),'patchCounts':{k:len(v) for k,v in patches.items()},'historicalFiles':len(config['histories'])}))

if __name__=='__main__':main()
