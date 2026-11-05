"""Retain failed GNU logs and actual byte-identical Native warning correction."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-publication/run-20261106-packet-gnu-failed-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh failed-log originals');OUT.mkdir();local=HERE/'run-20261106-packet-warning-fix-001/verification.json';r=json.loads(local.read_bytes());need(r['status']=='FINITE_NATIVE_PACKET_WARNING_CORRECTION_PASS' and r['sourceStable'] and all(c['exitCode']==0 for c in r['commands']),'Actual correction Native gate')
    logs=[]
    for job in [127333324427,127333324482]:
        p=OUT/(str(job)+'-decoded.log.txt');p.write_bytes(base64.b64decode((ROOT/'build'/('packet-failed-'+str(job)+'.base64')).read_bytes()));text=p.read_text(encoding='utf8');need('range-loop-construct' in text and 'world_static_mesh_session_packet_wire_tests.cpp' in text,'Actual new-harness compile diagnostic');logs.append(stamp(p))
    write(OUT/'receipt.json',dict(schema=1,status='ACTUAL_GNU_COMPILE_FAILURE_PRESERVED',source='455ea31dde7fbf71abc71a47a7afbad7c7cf375c',runId=42052868521,failedJobs=[127333324427,127333324482],decodedLogs=logs,scope='Complete returned decoded UTF8 logs, not raw HTTP bytes. Both builds stopped under Werror=range-loop-construct in new test32. No new packet GNU reference/ASan success. Four older dedicated jobs and Pages succeeded separately.'))
    for rel in ['core/include/pikapika/world_static_mesh_session_packet_wire.hpp','core/src/world_static_mesh_session_packet_wire.cpp']:
        need(subprocess.run(['git','show','455ea31dde7fbf71abc71a47a7afbad7c7cf375c:'+rel],cwd=ROOT,capture_output=True,check=True).stdout==(ROOT/rel).read_bytes(),'Production decoder unchanged '+rel)
    note='2026-11-06 packet source455ea31のGNU Engine42052868521はportable127333324427/owner127333324482のbuildで新test32行range-loop-construct/Werrorにより失敗。4旧専用job/Pages成功と分離し両decoded全文を保存。loop variableをconst auto&へ修正し、decoder/header/入力/数値条件は不変。fresh wfopkw1の実Release/Debug、9command/lifetime/全24 raw前後一致と各独立492bit参照が成功。実GNU packet/ASanはまだ未受入で次CIを要する。'
    for rel in ['docs/RESEARCH.md','docs/legal/REFERENCES.md','reports/world-static-mesh-session-recipes/GNU_PLAN.md']:
        p=ROOT/rel;p.write_text(p.read_text(encoding='utf8')+'\n\n'+note+' 外部資料・依存・素材・有料操作・権限拡張なし。\n',encoding='utf8',newline='\n')
    p=ROOT/'docs/PLAN.md';s=p.read_text(encoding='utf8');i=s.index('再開用の最新状態:');e=s.index('\n\n',i);s=s[:i]+'再開用の最新状態: '+note+' 次はWeb/stage/push後の実owner packet addon11command（normal/真Debug/O1 ASan-UBSan各24/492bit/164負零/4round mode/whole raw）とparent全artifact不変を確認。GCC警告を抑制しない。Native本文/全原本は履歴として保持、過去buildを再構成しない。先行C API actual GNU46+C/C++/fault18はaa0e367で全6CI成功済みだが今回新packet GNU成功へ混ぜない。その後実pump/保持全Reportの有界取得。モデル/owner3源/旧SDK/WASM/sample不変。専門物理/一般接触/流体損傷/IK/撮像未完。'+s[e:];p.write_text(s,encoding='utf8',newline='\n')
    web=ROOT/'reports/world-static-mesh-session-integration/run-20261106-packet-warning-fix-001';web.mkdir();p=subprocess.run(['node','scripts/build-web.mjs'],cwd=ROOT,capture_output=True,timeout=90);(web/'build.stdout.txt').write_bytes(p.stdout);(web/'build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Actual Web build');write(web/'build.json',dict(argv=['node','scripts/build-web.mjs'],exitCode=p.returncode))
    canonical=ROOT/'reports/world-static-mesh-session-packet-warning-verification.json';write(canonical,dict(schema=1,status='FINITE_NATIVE_PACKET_WARNING_CORRECTION_PASS',actualNativeCorrection=stamp(local),actualFailedGNU=stamp(OUT/'receipt.json'),productionDecoderChanged=False,actualGNUForNewPackets=False,all24RawExactBeforeAndAfter=True,pinned492ValueReference=True,actualWebBuild=stamp(web/'build.json'),scope='Real Native correction plus preserved actual GNU failure; no new GNU/ASan success promotion.'));print(json.dumps(dict(status='FINITE_NATIVE_PACKET_WARNING_CORRECTION_PASS',actualGNUForNewPackets=False)))
if __name__=='__main__':main()
