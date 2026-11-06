"""Final exact source/descriptor/unchanged-article review and required web build."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-identity-body-final-001'
def need(v,m):
    if not v:raise ValueError(m)
def main():
    need(__debug__ and not OUT.exists(),'Fresh final review');OUT.mkdir(parents=True)
    manifest=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes());code=(ROOT/'core/src/report_values_wire.cpp').read_text()
    descriptors=[]
    for typ,body in re.findall(r'Status write\(Writer& w,const ([^&]+)& v\) noexcept \{(.*?)\n\}',code,re.S):
        descriptors.append(dict(cppType=typ,fields=[dict(name=name,form=form) for form,name in re.findall(r'r\.(field|count|enumeration|array|optional_count|optional_array|optional_enumeration|optional_signed_enumeration|optional|fixed_bytes|bytes)\("([^"]+)"',body)]))
    expected=[dict(cppType=row['cppType'],fields=row['fields']) for row in manifest['mappedTypes']]
    need(descriptors==expected and len(descriptors)==56 and sum(len(r['fields']) for r in descriptors)==353,'All56 types/353 exact ordered descriptors')
    held=[row for row in expected if row['cppType'].startswith('sphere_triangle_mesh_held_load::')]
    need(len(held)==13 and sum(len(row['fields']) for row in held)==98,'All held13 types/98 reviewed members mapped')
    flight=[row for row in expected if row['cppType'].startswith('sphere_triangle_mesh_free_flight_guard::')]
    need(len(flight)==5 and sum(len(row['fields']) for row in flight)==34,'Free flight5 types/34 reviewed members mapped')
    need(manifest['signedEnumFields']==[dict(cppType='sphere_triangle_mesh_free_flight_guard::Result',field='flight_failure',underlyingType='int32_t',wireTag='enumeration',payload='little-endian U32: value modulo 2^32; signed value is payload if below 2^31, otherwise payload - 2^32')],'Exact signed enum representation contract')
    need(manifest['fixedBytesFields']==[dict(cppType='world_static_mesh_flight_guard::BindingInfo',field='build_id',sourceType='std::array<char,65>',bytes=65,wireTag='bytes',payload='All65 object-representation bytes in source order, including embedded and final NUL; no text normalization')],'Exact fixed65 opaque bytes contract')
    need(len(manifest['headers'])==16,'Frozen16 source headers')
    for row in manifest['headers']:
        need(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'Actual reviewed header '+row['path'])
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-identity-body-native-001'
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native/name).read_bytes()):
            raw=(ROOT/row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Tested source remains exact '+row['path'])
    before=subprocess.check_output(['git','show','7a8b54e1:docs/learn/index.html'],cwd=ROOT).decode('utf8')
    after=(ROOT/'docs/learn/index.html').read_text()
    def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
    a,b=articles(before),articles(after);need(a.keys()==b.keys() and len(a)==26,'Same26 articles')
    changed=[k for k in a if a[k]!=b[k]];need(len(changed)==1 and 'report-guard-identity-body-wire.svg' in b[changed[0]],'Only corresponding article extended')
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True)
    (OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final web build')
    result=dict(status='PASS',other25ArticlesExact=True,mappedTypes=56,mappedFields=353,heldTypes=13,heldFields=98,allCurrentDescriptorsMatchGetter=True,frozen16HeadersExact=True,testedSourcesUnchanged=True,webBuildExitCode=p.returncode,changedArticle=changed[0],scope='Exact declaration/schema/source review; no runtime reflection, new numeric query or GNU acceptance.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
