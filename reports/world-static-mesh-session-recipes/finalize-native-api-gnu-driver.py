"""Freeze local driver preflight without promoting it to actual GNU success."""
from pathlib import Path
import ast,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-integration/run-20261105-native-api-gnu-driver-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh integration output');OUT.mkdir();local=HERE/'run-20261105-native-api-gnu-driver-004/local-verification.json';r=json.loads(local.read_bytes());need(r['status']=='PASS' and r['actualGNUExecuted'] is False,'Actual local refusal/policy only')
    write(HERE/'run-20261105-native-api-gnu-driver-001/local-preflight-failure.json',dict(status='FAIL',reason='Job-count text preflight counted on.push as a job; fixed by limiting search to jobs mapping.',actualGNUExecuted=False,scope='Failure annotation; original synthetic controls/actual Windows refusal retained in this directory. This is not a downloaded full stderr trace.'))
    note='2026-11-05 新Native C API用GNU driverを準備。通常buildは再構成せず、別の新鮮DebugとC/C++両方を明示O1 ASan-UBSanにしたbuildで46production+2harness（うちC1TU）を検査する計画。CMAKE_CXX_FLAGSだけではCを計装できないためCMAKE_C_FLAGS/Releaseも別指定し、実C compiler path/version/target/flagsと実link7libraryを検査する。各9入力1254bit/142負零/全U32を独立照合し、通常/Debug/san全文raw一致・実-O・normal/parent/compiler/source不変を要求。新stepは既存owner job内、6job/既存public guard/20分5+25分1を維持。actual Windows拒否004（build0/新build作成なし）とsynthetic C-option12拒否/ASTが成功しただけで実GNUは未受入。初回事前検査のjob数regex失敗も保存。'
    for rel in ['docs/RESEARCH.md','docs/legal/REFERENCES.md','reports/world-static-mesh-session-recipes/GNU_PLAN.md']:
        p=ROOT/rel;p.write_text(p.read_text(encoding='utf8')+'\n\n'+note+' 外部資料・実装・依存・素材・課金・有料runner・権限拡張・license選定なし。\n',encoding='utf8',newline='\n')
    p=ROOT/'docs/PLAN.md';s=p.read_text(encoding='utf8');i=s.index('再開用の最新状態:');e=s.index('\n\n',i);s=s[:i]+'再開用の最新状態: '+note+' Native C API本体94fd7d9はpush済み、公開Pages/旧5専用job成功・portableは観測時進行中。前段77a363b source/token GNU45TUと全6job/manifest2007/READYは受入済みだが新C API全依存GNUを意味しない。次はdriverをpushし実15regular command+別-OのGNU46/2TU/9ケースを確定、失敗なら実logを保存して修正。その後新C API allocator故障/再入、pump/保持全Report getterへ。過去buildを再構成しない。新APIはC ABIのplain lifecycleのみ、WASM/ゲーム/mesh/任意全guard/専門物理は未完。'+s[e:];p.write_text(s,encoding='utf8',newline='\n')
    files=[ROOT/'.github/workflows/verify.yml',HERE/'verify-native-api-gnu.py',HERE/'check-native-api-gnu-driver.py',Path(__file__).resolve(),ROOT/'core/include/pikapika/world_static_mesh_session_api.h',ROOT/'core/src/world_static_mesh_session_api.cpp',ROOT/'tests/world_static_mesh_session_api_tests.cpp',ROOT/'tests/world_static_mesh_session_api_c_tests.c',ROOT/'scripts/verify-world-static-mesh-session-api.py']
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    before=[stamp(p) for p in files];p=subprocess.run(['node','scripts/build-web.mjs'],cwd=ROOT,capture_output=True,timeout=90);(OUT/'build.stdout.txt').write_bytes(p.stdout);(OUT/'build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0 and before==[stamp(p) for p in files],'Actual Web build/source stable');write(OUT/'build.json',dict(argv=['node','scripts/build-web.mjs'],exitCode=p.returncode,sourceStable=True))
    receipt=dict(schema=1,status='LOCAL_NATIVE_C_API_GNU_DRIVER_PREFLIGHT_PASS',actualGNUExecuted=False,actualLocalVerification=stamp(local),actualWindowsRefusal=stamp(HERE/'run-20261105-native-api-gnu-driver-004/verification.json'),syntheticCOptionRejections=12,expectedRegularGNUCommands=15,plannedProductionTUs=46,plannedHarnessTUs=2,plannedActualCHarnessTUs=1,plannedSourceRowsPerBuild=9,plannedMappedFloatBitValues=1254,existingSixJobsAndBudgetsUnchanged=True,normalBuildMutationPlanned=False,sourceStamps=before,actualWebBuild=stamp(OUT/'build.json'),scope='Local policy copies and actual unsupported-platform refusal only. Genuine GNU C/C++/ASan execution pending. No new production changes or numerical/WASM/game capability promotion.')
    canonical=ROOT/'reports/world-static-mesh-session-c-api-gnu-driver-verification.json';write(canonical,receipt);write(HERE/'native-api-gnu-driver-freeze.json',dict(schema=1,status=receipt['status'],sources=before,canonical=stamp(canonical)))
    print(json.dumps(dict(status=receipt['status'],actualGNUExecuted=False)))
if __name__=='__main__':main()
