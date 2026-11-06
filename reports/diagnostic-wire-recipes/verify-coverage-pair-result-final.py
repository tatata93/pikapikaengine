"""Finite source review and aggregation after actual Native, all mutation shards, and Web acceptance."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='28bb30a003dfd2e85e0e554c86b1b9ec237cfa74'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-pair-result-final-001'
def need(v,m):
    if not v:raise ValueError(m)
def old(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh final review');OUT.mkdir(parents=True)
    manifest=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes());prior=json.loads(old('core/report-values-schema-v1.json'))
    copy=dict(manifest);copy['mappedTypes']=copy['mappedTypes'][:-1];need(copy==prior,'All prior metadata, variant and17 headers exact')
    need(manifest['mappedTypes'][-1]['cppType']=='accelerated_pair_coverage::Result','Only new Result')
    code=(ROOT/'core/src/report_values_wire.cpp').read_text(encoding='utf8');descriptors=[];variants=[]
    for typ,body in re.findall(r'Status write\(Writer& w,const ([^&]+)& v\) noexcept \{(.*?)\n\}',code,re.S):
        if typ=='accelerated_pair_coverage::Input':variants.append(body);continue
        descriptors.append(dict(cppType=typ,fields=[dict(name=name,form=form) for form,name in re.findall(r'r\.(field|count|enumeration|array|optional_count|optional_array|optional_enumeration|optional_signed_enumeration|optional|fixed_bytes|bytes)\("([^"]+)"',body)]))
    need(descriptors==[dict(cppType=r['cppType'],fields=r['fields']) for r in manifest['mappedTypes']] and len(descriptors)==68 and sum(len(r['fields']) for r in descriptors)==401 and len(variants)==1,'All ordered descriptors')
    block='''
Status write(Writer& w,const accelerated_pair_coverage::Result& v) noexcept {
    Record r(w);
    r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional("snapshot",v.snapshot);
    r.field("snapshot_validated",v.snapshot_validated);
    r.optional_count("failed_input",v.failed_input);
    r.field("partition_complete",v.partition_complete);
    r.array("audits",std::span<const accelerated_pair_coverage::Audit>(v.audits));
    r.array("partition",std::span<const accelerated_pair_coverage::PartitionLeaf>(v.partition));
    r.array("frontier",std::span<const accelerated_pair_coverage::Cell>(v.frontier));
    r.optional("current",v.current);
    r.field("work",v.work);
    r.bytes("message",v.message);
    return r.end();
}
'''
    need(code.count(block)==1 and code.replace(block,'')==old('core/src/report_values_wire.cpp').decode('utf8'),'Only pure const data getter')
    header=(ROOT/'core/include/pikapika/report_values_wire.hpp').read_text(encoding='utf8');decl='\nStatus write(Writer&,const accelerated_pair_coverage::Result&) noexcept;'
    need(header.count(decl)==1 and header.replace(decl,'')==old('core/include/pikapika/report_values_wire.hpp').decode('utf8'),'Only declaration')
    for p in ['core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp']:need((ROOT/p).read_bytes()==old(p),'Primitive exact')
    for row in manifest['headers']:need(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'Frozen header exact')
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-pair-result-native-002/verification.json';n=json.loads(native.read_bytes());need(n['status']=='FINITE_NATIVE_REPORT_COVERAGE_PAIR_RESULT_PASS','Complete Native acceptance')
    integration=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-pair-result-native-002/verification.json';i=json.loads(integration.read_bytes());need(i['status']=='FINITE_COVERAGE_PAIR_RESULT_INTEGRATION_PASS','Complete integration')
    web=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-pair-result-web-002/verification.json';w=json.loads(web.read_bytes());need(w['status']=='FINITE_COVERAGE_PAIR_RESULT_WEB_PASS','Actual Web acceptance')
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native.parent/name).read_bytes()):need(stamp(ROOT/row['path'])==row,'Tested bytes still exact')
    def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
    before=articles(old('docs/learn/index.html').decode('utf8'));after=articles((ROOT/'docs/learn/index.html').read_text(encoding='utf8'))
    need(before.keys()==after.keys() and len(before)==26 and [k for k in before if before[k]!=after[k]]==['controlled-tick'] and 'report-coverage-pair-result-wire.svg' in after['controlled-tick'],'Only corresponding lesson')
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True,timeout=240);(OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final Web build')
    review=dict(status='PASS',mappedRecordTypes=68,mappedFields=401,mappedVariants=1,allOrderedDescriptorsExact=True,oldMetadataHeadersGettersAndPrimitiveSourceExact=True,testedSourcesUnchanged=True,other25ArticlesExact=True,webBuildExitCode=0)
    (OUT/'verification.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf8')
    r=dict(schema=1,status=n['status'],nativeReceipt=stamp(native),integrationReceipt=stamp(integration),finalReview=stamp(OUT/'verification.json'),webReceipt=stamp(web),native=n['native'],reference=n['reference'],referenceControls=i['referenceControls'],totalMappedRecordTypes=68,totalMappedFields=401,totalMappedVariants=1,reviewedHeaders=17,registeredTests=n['registeredTests'],selectedCTestPerConfiguration=28,oldPrimitive1148Control827All24RecordAndInput1899FixturesAndRunOutputsRawExact=True,old20ProfilesRawExact=i['old20ProfilesRawExact'],protectedFiles=n['protectedFiles'],protectedFilesStable=n['protectedRawExact'],newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,oldCoreBuiltOrLinked=False,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Complete pair Result12 fields only. No numerical model query in getter; actual GNU and target-specific valueless reachability separate; whole World Report/pump/JS/WASM/game connection pending.')
    (ROOT/'reports/diagnostic-wire-coverage-pair-result-verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(review))
if __name__=='__main__':main()
