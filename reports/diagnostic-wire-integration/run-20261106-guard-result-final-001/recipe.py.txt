"""Exact97/575 descriptor and old-source review, isolated17th CI job, one lesson, required web build."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='8ebf611a3c37281f5248b2d0422d2cd8c988f65f'
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-native-004'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-result-final-001'
def need(v,m):
 if not v:raise ValueError(m)
def old(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def text(p):return (ROOT/p).read_text(encoding='utf8')
def main():
 need(__debug__ and not OUT.exists(),'Fresh final review')
 n=json.loads((NATIVE/'verification.json').read_bytes());need(n['status']=='FINITE_NATIVE_REPORT_GUARD_RESULT_PASS' and n['sourceStable'] and n['protectedRawExact'],'Complete Native first')
 manifest=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes());prior=json.loads(old('core/report-values-schema-v1.json'));copy=dict(manifest);copy['mappedTypes']=copy['mappedTypes'][:-1]
 need(copy==prior and manifest['mappedTypes'][-1]['cppType']=='world_static_mesh_flight_guard::GuardResult','Exactly one new record; old metadata and variants exact')
 code=text('core/src/report_values_wire.cpp');descriptors=[];variants=[]
 for typ,body in re.findall(r'Status write\(Writer& w,const ([^&]+)& v\) noexcept \{(.*?)\n\}',code,re.S):
  if typ in {'accelerated_pair_coverage::Input','world_static_mesh_flight_guard::Child'}:variants.append(body);continue
  descriptors.append(dict(cppType=typ,fields=[dict(name=name,form=form) for form,name in re.findall(r'r\.(field|count|enumeration|array|optional_count|optional_array|optional_enumeration|optional_signed_enumeration|optional|fixed_bytes|bytes)\("([^"]+)"',body)]))
 need(descriptors==[dict(cppType=r['cppType'],fields=r['fields']) for r in manifest['mappedTypes']] and len(descriptors)==97 and sum(len(r['fields']) for r in descriptors)==575 and len(variants)==2,'Every ordered descriptor, separate variants')
 block=re.search(r'\nStatus write\(Writer& w,const world_static_mesh_flight_guard::GuardResult& v\) noexcept \{.*?\n\}\n',code,re.S);helper=re.search(r'    template<class T> void optional_array\(std::string_view name,const std::optional<std::vector<T>>& value\) noexcept \{.*?\n    \}\n',code,re.S)
 need(block is not None and helper is not None,'New record and optional vector overload exactly identifiable')
 need(code.replace(block.group(),'').replace(helper.group(),'')==old('core/src/report_values_wire.cpp').decode('utf8'),'All old getter and helper code byte-exact after removing only new blocks')
 header=text('core/include/pikapika/report_values_wire.hpp');declaration='\nStatus write(Writer&,const world_static_mesh_flight_guard::GuardResult&) noexcept;';need(header.count(declaration)==1 and header.replace(declaration,'')==old('core/include/pikapika/report_values_wire.hpp').decode('utf8'),'Old declaration header exact')
 for p in ['core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp']:need((ROOT/p).read_bytes()==old(p),'Primitive implementation exact')
 for row in manifest['headers']:
  raw=(ROOT/row['path']).read_bytes();need(hashlib.sha256(raw).hexdigest()==row['sha256'] and raw==old(row['path']),'Frozen numerical header exact')
 for name in ['source-before.json','protected-before.json']:
  for row in json.loads((NATIVE/name).read_bytes()):
   raw=(ROOT/row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Every actually tested/protected source exact')
 def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
 a,b=articles(old('docs/learn/index.html').decode('utf8')),articles(text('docs/learn/index.html'))
 need(a.keys()==b.keys() and len(a)==26 and [k for k in a if a[k]!=b[k]]==['controlled-tick'] and 'report-guard-result-wire.svg' in b['controlled-tick'],'Only corresponding learning article extended')
 workflow=text('.github/workflows/verify.yml');previous=old('.github/workflows/verify.yml').decode('utf8');need(workflow.startswith(previous),'All16 old CI jobs exact');added=workflow[len(previous):]
 need(added.count('  native-')==1 and '  native-guard-result-diagnostics:' in added and 'timeout-minutes: 20' in added and 'github.event.repository.private == false' in added,'One isolated public20min job')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True);(OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final web build')
 result=dict(status='PASS',mappedRecordTypes=97,mappedFields=575,mappedVariants=2,allOrderedDescriptorsExact=True,allOldGetterAndPrimitiveSourceExact=True,optionalVectorHelperAdditionOnly=True,frozen17HeadersExact=True,testedSourcesUnchanged=True,other25ArticlesExact=True,existing16CIJobsExact=True,onePublic20MinuteDiagnosticJobAdded=True,webBuildExitCode=0,scope='Source review and required build only. Actual new GNU and publication remain separate. No new numerical model or game connection.')
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
