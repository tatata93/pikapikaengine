"""Accept actual Native faults and earlier real GNU C API as separate gates."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-integration/run-20261105-native-api-allocation-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def append(rel,text):
    p=ROOT/rel;p.write_text(p.read_text(encoding='utf8')+'\n\n'+text+'\n',encoding='utf8',newline='\n')
def main():
    need(not OUT.exists(),'Fresh integration');OUT.mkdir();main=HERE/'run-20261105-native-api-allocation-main-001/verification.json';r=json.loads(main.read_bytes());need(r['status']=='FINITE_NATIVE_MAIN_C_API_ALLOCATION_PASS' and r['sourceStable'],'Actual main normal fault acceptance')
    gnu=ROOT/'reports/world-static-mesh-session-c-api-gnu-verification.json';g=json.loads(gnu.read_bytes());need(g['status']=='ACTUAL_FINITE_GNU_NATIVE_C_API_PASS','Actual earlier C/C++ GNU accepted')
    local=HERE/'run-20261105-native-api-allocation-gnu-driver-001/local-verification.json';d=json.loads(local.read_bytes());need(d['status']=='PASS' and len(d['copiedRecordRejections'])==14 and d['actualGNUFaultExecuted'] is False,'Local GNU fault driver preflight only')
    note='2026-11-05 C APIの実GNU13.3 C/C++をsource57d8bd8/job127285493025で有限受入。15command、全46production+2harness（C1）の通常/真Debug/明示C+C++ O1 ASan-UBSanで各9/1254bit/142負零と全U32/rawが正規化なし一致、実-O/source/normal/parent/compiler不変も成功。decoded137908B/実JSON保存、child raw/objectはrunner-local。全6Engine/Pages成功・manifest2018件61150288BのGit照合も確認。別のNative Release故障試験はcontext1+stage14/create3/reset3/read2の実bad_alloc23地点と4outer×5再入20、初期捕捉/全過去cache/active owner/世代/復帰/非確保getterを確認。fresh wfocam1 mainでも2CTest・旧20profile・旧9/1254bit/全故障raw一致が成功。登録Release56/Debug54、Debugは一覧だけ・旧54全再実行ではない。最初のMSVC NDEBUG表記parser失敗を保持し、fresh wfoca2で補正。新故障testのGNUは別1command driverと14コピー拒否/実Windows拒否0commandまでで未実行。全allocator/OS OOM/aligned/CRT/thread/post-pump faultやpump/mesh/full guard/JS/WASM/ゲームの完成ではない。'
    for rel in ['docs/RESEARCH.md','docs/legal/REFERENCES.md','reports/world-static-mesh-session-recipes/GNU_PLAN.md']:append(rel,note+' 外部資料・実装・依存・素材・課金・有料runner・権限拡張・license選定の追加なし。')
    append('docs/WORLD_STATIC_MESH_SESSION_SDK_PLAN.md','## C/C++実GNUと限定故障経路の受入\n\n'+note+'\n[実GNU](../reports/world-static-mesh-session-c-api-gnu-verification.json)／[Native故障](../reports/world-static-mesh-session-c-api-allocation-verification.json)。')
    append('docs/WORLD_STATIC_MESH_SESSION_C_API.md','## 実GNUと限定Native故障の続報\n\n'+note+'\n[実GNU受入](../reports/world-static-mesh-session-c-api-gnu-verification.json)と[Native故障受入](../reports/world-static-mesh-session-c-api-allocation-verification.json)は別の実行。通常故障実行ファイルへASanを混ぜたとは扱わない。')
    p=ROOT/'docs/PLAN.md';s=p.read_text(encoding='utf8');i=s.index('再開用の最新状態:');e=s.index('\n\n',i);s=s[:i]+'再開用の最新状態: '+note+' 次は今回の新allocation target/driverをpushし実GNU normalの故障全観測位置・20再入・復帰を確定。STLにより割当回数が異なり得るためNative23と架空一致させない。その後pumpに必要な有界・所有load packet wireと、実pump結果をallocationなしmoveでcacheして全Reportを有界getterで回収するC ABIへ。過去build(wfoca1/2,wfocam1含む)は再構成しない。先行57d8bd8の全6CI成功を今回新fault targetの成功へ流用しない。物理専門モデル/一般接触/流体損傷/IK/高精度撮像とゲーム接続は未完。'+s[e:];p.write_text(s,encoding='utf8',newline='\n')
    image=ROOT/'docs/learn/diagrams/world-static-mesh-session-api.svg';s=image.read_text(encoding='utf8').replace('Native C API v1の原著概念図。物理進行や性能の測定結果ではありません。','MSVC / GNU 13で形式と所有を有限検査。物理進行や性能の測定図ではありません。');image.write_text(s,encoding='utf8',newline='\n');im=stamp(image);append('docs/legal/ASSETS.md','2026-11-05 C API原著図の状態説明を実MSVC/GNU有限受入へ更新。'+str(im['bytes'])+'B、SHA256 `'+im['sha256']+'`。概念図で物理進行・性能測定ではない。外部素材なし。')
    p=ROOT/'docs/learn/index.html';s=p.read_text(encoding='utf8');old=re.findall(r'<article\b.*?</article>',s,re.S);need(len(old)==26,'26 articles');s=s.replace('実C/C++ caller、MSVCのRelease・Debug各9入力の全1254 bit値と12改変拒否を検査しました。新APIのGNU・sanitizer、pump・mesh・任意全guard・WASM・ゲーム接続は次段です。','実C/C++ caller、MSVCのRelease・Debug各9入力の全1254 bit値と12改変拒否を検査しました。実GNU 13の通常・Debug・C/C++両方のASan/UBSanでも全値が一致しました。別のNative通常版では実new失敗23地点と再入20を検査し、Worldと過去cache、復帰を確認しました。全allocatorやGNUの故障注入、pump・mesh・任意全guard・WASM・ゲーム接続は次段です。');need(old[:25]==re.findall(r'<article\b.*?</article>',s,re.S)[:25],'Old25 articles unchanged');p.write_text(s,encoding='utf8',newline='\n')
    sources=[ROOT/'CMakeLists.txt',ROOT/'.github/workflows/verify.yml',ROOT/'tests/world_static_mesh_session_api_allocation_tests.cpp',HERE/'check-native-api-allocation.py',HERE/'check-native-api-allocation-main.py',HERE/'verify-native-api-allocation-gnu.py',HERE/'check-native-api-allocation-gnu-driver.py',Path(__file__).resolve()]
    for p in sources:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    before=[stamp(p) for p in sources]
    receipt=dict(schema=1,status='FINITE_NATIVE_MAIN_C_API_ACTUAL_ALLOCATION_PASS',actualMain=stamp(main),actualIsolated=stamp(HERE/'run-20261105-native-api-allocation-002/verification.json'),initialParserFailureRetained=stamp(HERE/'run-20261105-native-api-allocation-001/verification.json'),contextFailurePositions=1,operationFailurePositions={'stage':14,'create':3,'reset':3,'read':2},actualOperationFailures=22,actualTotalFailurePositions=23,actualAllocatorBusyReentryChecks=20,cachedGetterAllocations=0,normalReleaseOnly=True,actualSanitizedFaultExecutable=False,actualGNUFaultExecuted=False,actualNewReleaseCTests=2,registeredTests=r['inventories'],old54TestsRerun=False,old20ProfilesRawExact=True,newGNUFaultDriverLocal=stamp(local),sources=before,scope='Finite actual Native scalar/array global-new failures and allocator reentry, complete plain cache/live owner/recovery assertions. Earlier real GNU C/C++ data/sanitizer result is separate. All allocator/aligned/CRT/OS OOM/thread/post-pump faults, pump/mesh/full guard/JS/WASM/game unaccepted.')
    canonical=ROOT/'reports/world-static-mesh-session-c-api-allocation-verification.json';write(canonical,receipt)
    commands=[]
    for name,argv in [('learn',['node','--test','docs/learn/learn.test.mjs']),('syntax',['node','scripts/check.mjs']),('build',['node','scripts/build-web.mjs'])]:
        start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=90);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);row=dict(name=name,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.json'),row);need(p.returncode==0,'Actual final '+name)
    need(before==[stamp(p) for p in sources],'Source stable after integration');write(OUT/'verification.json',dict(status='PASS',old25ArticlesExact=True,sourceStable=True,commands=commands));write(HERE/'native-api-allocation-freeze.json',dict(schema=1,status=receipt['status'],sources=before,canonical=stamp(canonical),integration=stamp(OUT/'verification.json')))
    print(json.dumps(dict(status=receipt['status'],actualTotalFailures=23,actualGNUFaultExecuted=False)))
if __name__=='__main__':main()
