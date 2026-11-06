"""Review record/variant descriptors separately, exact primitive/old getters, one learning article and required web build."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='cd6f9b8d035fe3dd952805efe54489335f264681'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-snapshot-inventory-final-001'
def need(v,m):
    if not v:raise ValueError(m)
def old(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def text(p):return (ROOT/p).read_text(encoding='utf8')
def main():
    need(__debug__ and not OUT.exists(),'Fresh final review');OUT.mkdir(parents=True)
    p='core/report-values-schema-v1.json';manifest=json.loads((ROOT/p).read_bytes());prior=json.loads(old(p))
    need(manifest['mappedVariants']==prior['mappedVariants'],'Separate existing variant unchanged')
    copy=dict(manifest);copy['mappedTypes']=copy['mappedTypes'][:-2];need(copy==prior,'All prior metadata and17 headers exact')
    need([row['cppType'] for row in manifest['mappedTypes'][-2:]]==['world_static_mesh_flight::Snapshot','world_static_mesh_flight::Inventory'],'Exactly2 added records')
    code=text('core/src/report_values_wire.cpp');descriptors=[];variant_bodies=[]
    for typ,body in re.findall(r'Status write\(Writer& w,const ([^&]+)& v\) noexcept \{(.*?)\n\}',code,re.S):
        if typ in {'accelerated_pair_coverage::Input','world_static_mesh_flight_guard::Child'}:variant_bodies.append(body);continue
        descriptors.append(dict(cppType=typ,fields=[dict(name=name,form=form) for form,name in re.findall(r'r\.(field|count|enumeration|array|optional_count|optional_array|optional_enumeration|optional_signed_enumeration|optional|fixed_bytes|bytes)\("([^"]+)"',body)]))
    expected=[dict(cppType=r['cppType'],fields=r['fields']) for r in manifest['mappedTypes']]
    need(descriptors==expected and len(descriptors)==95 and sum(len(r['fields']) for r in descriptors)==554 and len(variant_bodies)==2,'All ordered record descriptors and exactly2 separate variants')
    blocks=['\nStatus write(Writer& w,const world_static_mesh_flight::Snapshot& v) noexcept {\n    Record r(w);\n    r.field("gravity",v.gravity);\n    r.field("horizon",v.horizon);\n    r.field("settings",v.settings);\n    r.array("bodies",std::span(v.bodies));\n    r.array("planes",std::span(v.planes));\n    r.array("meshes",std::span(v.meshes));\n    return r.end();\n}\n', '\nStatus write(Writer& w,const world_static_mesh_flight::Inventory& v) noexcept {\n    Record r(w);\n    r.count("dynamic_bodies",v.dynamic_bodies);\n    r.count("static_bodies",v.static_bodies);\n    r.count("total_faces",v.total_faces);\n    r.count("colliders",v.colliders);\n    r.count("all_pairs",v.all_pairs);\n    r.field("excluded",v.excluded);\n    r.array("pairs",std::span(v.pairs));\n    return r.end();\n}\n']
    previous=code
    for block in blocks:
        need(previous.count(block)==1,'Each pure new data getter exactly once');previous=previous.replace(block,'')
    need(previous==old('core/src/report_values_wire.cpp').decode('utf8'),'All old getter source exact')
    declarations=['\nStatus write(Writer&,const world_static_mesh_flight::Snapshot&) noexcept;', '\nStatus write(Writer&,const world_static_mesh_flight::Inventory&) noexcept;'];header=text('core/include/pikapika/report_values_wire.hpp')
    for declaration in declarations:
        need(header.count(declaration)==1,'Each new declaration once');header=header.replace(declaration,'')
    need(header==old('core/include/pikapika/report_values_wire.hpp').decode('utf8'),'All old header source exact')
    for p in ['core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp']:need((ROOT/p).read_bytes()==old(p),'Primitive source exact')
    for row in manifest['headers']:need(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'Actual frozen header')
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-snapshot-inventory-native-001'
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native/name).read_bytes()):
            raw=(ROOT/row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Tested source unchanged')
    def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
    a,b=articles(old('docs/learn/index.html').decode('utf8')),articles(text('docs/learn/index.html'))
    need(a.keys()==b.keys() and len(a)==26 and [k for k in a if a[k]!=b[k]]==['controlled-tick'] and 'report-preparation-snapshot-inventory-wire.svg' in b['controlled-tick'],'Only corresponding article extended')
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True);(OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final web build')
    result=dict(status='PASS',mappedRecordTypes=95,mappedFields=554,mappedVariants=2,allOrderedDescriptorsExact=True,allOldGetterAndPrimitiveSourceExact=True,frozen17HeadersExact=True,testedSourcesUnchanged=True,other25ArticlesExact=True,webBuildExitCode=0,
        scope='Separate variant/record source review. No new numeric model; actual GNU owned preparation Snapshot/Inventory acceptance remains separate.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
