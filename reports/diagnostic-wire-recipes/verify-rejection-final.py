"""Review exact refusal-only product diff, unchanged v1/descriptors, learning article and web build."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='9af0210804e59c97fff83191a1137cc862e9a138'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-rejection-final-002'
def need(v,m):
    if not v:raise ValueError(m)
def old(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def text(p):return (ROOT/p).read_text(encoding='utf8')
def main():
    need(__debug__ and not OUT.exists(),'Fresh final review');OUT.mkdir(parents=True)
    h='core/include/pikapika/diagnostic_wire.hpp';c='core/src/diagnostic_wire.cpp'
    declaration='    // Emit nothing. Reentry is transient; an existing failure is preserved.\n    // Otherwise latch invalid_state, even before begin() or after finish().\n    // This does not revoke bytes already sent or clear complete().\n    Status reject_invalid_value() noexcept;\n'
    definition='Status Writer::reject_invalid_value() noexcept {\n    if(const auto s=gate();s!=Status::ok) return s;\n    return fail(Status::invalid_state);\n}\n'
    need(text(h).count(declaration)==1 and text(h).replace(declaration,'')==old(h).decode('utf8'),'Only public method/comment; all old members/layout/tag/Status exact')
    need(text(c).count(definition)==1 and text(c).replace(definition,'')==old(c).decode('utf8'),'Only gate/fail method; old serialization exact')
    p='core/report-values-schema-v1.json';m=json.loads((ROOT/p).read_bytes());prior=json.loads(old(p))
    need(m['mappedTypes']==prior['mappedTypes'] and len(m['mappedTypes'])==62 and sum(len(x['fields']) for x in m['mappedTypes'])==369,'All62/369 descriptors unchanged')
    copy=json.loads(json.dumps(m));changed=[]
    for row,previous in zip(copy['headers'],prior['headers'],strict=True):
        raw=(ROOT/row['path']).read_bytes();need(('bytes' not in row or len(raw)==row['bytes']) and hashlib.sha256(raw).hexdigest()==row['sha256'],'Actual reviewed header')
        if row!=previous:changed.append(row['path']);row.clear();row.update(previous)
    need(changed==[h] and copy==prior,'Only diagnostic header review changed; other16 headers and all metadata exact')
    for p in ['core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp']:
        need((ROOT/p).read_bytes()==old(p),'Old getter source exact')
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-rejection-native-001'
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native/name).read_bytes()):
            raw=(ROOT/row['path']).read_bytes();need(('bytes' not in row or len(raw)==row['bytes']) and hashlib.sha256(raw).hexdigest()==row['sha256'],'Tested source unchanged')
    def articles(s):return dict(re.findall(r'<article id="([^"]+)"(.*?)</article>',s,re.S))
    a,b=articles(old('docs/learn/index.html').decode('utf8')),articles(text('docs/learn/index.html'))
    need(a.keys()==b.keys() and len(a)==26 and [k for k in a if a[k]!=b[k]]==['controlled-tick'] and 'diagnostic-wire-rejection.svg' in b['controlled-tick'],'Only corresponding lesson extended')
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True)
    (OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required final web build')
    result=dict(status='PASS',onlyRejectionMethodAdded=True,oldMembersLayoutTagsStatusAndSerializationExact=True,mappedTypes=62,mappedFields=369,
        descriptorsAndOther16ReviewedHeadersUnchanged=True,reviewedHeaders=17,testedSourcesUnchanged=True,other25ArticlesExact=True,webBuildExitCode=0,
        inputVariantMapped=False,scope='Refusal primitive only; no new numerical query or GNU acceptance.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
