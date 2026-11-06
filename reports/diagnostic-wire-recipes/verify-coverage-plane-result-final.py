"""Review record/variant descriptors separately, exact primitive/old getters, one learning article and required web build."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='62b85fdc31fb50d9916f60fb1863e1799681af2b'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-plane-result-final-001'
def need(v,m):
    if not v:raise ValueError(m)
def old(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def text(p):return (ROOT/p).read_text(encoding='utf8')
def main():
    need(__debug__ and not OUT.exists(),'Fresh final review');OUT.mkdir(parents=True)
    p='core/report-values-schema-v1.json';manifest=json.loads((ROOT/p).read_bytes());prior=json.loads(old(p))
    need(manifest['mappedVariants']==prior['mappedVariants'],'Separate existing variant unchanged')
    copy=dict(manifest);copy['mappedTypes']=copy['mappedTypes'][:-1];need(copy==prior,'All prior metadata and17 headers exact')
    need([row['cppType'] for row in manifest['mappedTypes'][-1:]]==['accelerated_plane_box_coverage::Result'],'Exactly1 added record')
    code=text('core/src/report_values_wire.cpp');descriptors=[];variant_bodies=[]
    for typ,body in re.findall(r'Status write\(Writer& w,const ([^&]+)& v\) noexcept \{(.*?)\n\}',code,re.S):
        if typ=='accelerated_pair_coverage::Input':variant_bodies.append(body);continue
        descriptors.append(dict(cppType=typ,fields=[dict(name=name,form=form) for form,name in re.findall(r'r\.(field|count|enumeration|array|optional_count|optional_array|optional_enumeration|optional_signed_enumeration|optional|fixed_bytes|bytes)\("([^"]+)"',body)]))
    expected=[dict(cppType=r['cppType'],fields=r['fields']) for r in manifest['mappedTypes']]
    need(descriptors==expected and len(descriptors)==76 and sum(len(r['fields']) for r in descriptors)==439 and len(variant_bodies)==1,'All ordered record descriptors and exactly1 separate variant')
    block='\nStatus write(Writer& w,const accelerated_plane_box_coverage::Result& v) noexcept {\n    Record r(w);\n    r.enumeration("status",static_cast<std::uint32_t>(v.status));\n    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));\n    r.optional("snapshot",v.snapshot);\n    r.field("snapshot_validated",v.snapshot_validated);\n    r.optional_count("failed_input",v.failed_input);\n    r.field("partition_complete",v.partition_complete);\n    r.array("audits",std::span<const accelerated_plane_box_coverage::Audit>(v.audits));\n    r.array("partition",std::span<const accelerated_plane_box_coverage::PartitionLeaf>(v.partition));\n    r.array("frontier",std::span<const accelerated_plane_box_coverage::Cell>(v.frontier));\n    r.optional("current",v.current);\n    r.field("work",v.work);\n    r.bytes("message",v.message);\n    return r.end();\n}\n'
    need(code.count(block)==1 and code.replace(block,'')==old('core/src/report_values_wire.cpp').decode('utf8'),'Only1 pure data getter added')
    declaration='\nStatus write(Writer&,const accelerated_plane_box_coverage::Result&) noexcept;'
    header=text('core/include/pikapika/report_values_wire.hpp');need(header.count(declaration)==1 and header.replace(declaration,'')==old('core/include/pikapika/report_values_wire.hpp').decode('utf8'),'Only1 declaration')
    for p in ['core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp']:need((ROOT/p).read_bytes()==old(p),'Primitive source exact')
    for row in manifest['headers']:need(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'Actual frozen header')
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-plane-result-native-001'
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native/name).read_bytes()):
            raw=(ROOT/row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Tested source unchanged')
    def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
    a,b=articles(old('docs/learn/index.html').decode('utf8')),articles(text('docs/learn/index.html'))
    need(a.keys()==b.keys() and len(a)==26 and [k for k in a if a[k]!=b[k]]==['controlled-tick'] and 'report-coverage-plane-result-wire.svg' in b['controlled-tick'],'Only corresponding article extended')
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True);(OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final web build')
    result=dict(status='PASS',mappedRecordTypes=76,mappedFields=439,mappedVariants=1,allOrderedDescriptorsExact=True,allOldGetterAndPrimitiveSourceExact=True,frozen17HeadersExact=True,testedSourcesUnchanged=True,other25ArticlesExact=True,webBuildExitCode=0,
        scope='Separate variant/record source review. No new numeric model; actual GNU plane Result acceptance remains separate.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
