"""Publish finite Native lifecycle evidence only after the actual main gate."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
MAIN=HERE/'run-20261105-native-api-main-001/verification.json'
OUT=ROOT/'reports/world-static-mesh-session-integration/run-20261105-native-api-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def append(rel,text):
    p=ROOT/rel;p.write_text(p.read_text(encoding='utf8')+'\n\n'+text+'\n',encoding='utf8',newline='\n')
def main():
    r=json.loads(MAIN.read_bytes());need(r['status']=='FINITE_NATIVE_MAIN_PLAIN_SESSION_C_API_PASS' and r['sourceStable'] and len(r['copiedRejections'])==12,'Actual latest main acceptance required');need(not OUT.exists(),'Fresh finalization');OUT.mkdir()
    note='2026-11-05 Native plain-source C API v1を実装・正式mainへ追加。独立libraryで原本stage/revision、実owner create/read/reset/destroyと固定所有readを公開し、旧pp_sim_handle/SDK/core40/数値profile/sampleを変更しない。fresh wfocm1の実MSVC Release/DebugでCとC++ callerをcompile、両新CTest/各9入力1254 F64 bit値・142負零/全U32の独立参照、12コピー改変拒否と実-O、旧20profile全文一致が成功。stage失敗の旧原本失効/active保持、旧世代/reset/destroy/read寿命、full64 ID/tick、4slot/退役を試験。登録Release55/Debug54だが実行は新CTestだけで旧54全再実行ではない。新C APIのGNU/sanitizer/全allocator故障、pump/mesh/任意全guard/JS/WASM/ゲーム接続は未受入。'
    append('docs/RESEARCH.md',note+' 新外部資料・code・依存・素材・有料操作なし。本体license未選定。')
    append('docs/legal/REFERENCES.md',note+' 既存リポジトリAPIから独自設計し、外部実装の転載・新資料実読・課金やlicense選定はない。')
    append('docs/WORLD_STATIC_MESH_SESSION_SDK_PLAN.md','## Native lifecycle C APIの有限受入\n\n'+note+'\n[利用契約](WORLD_STATIC_MESH_SESSION_C_API.md)／[受入記録](../reports/world-static-mesh-session-c-api-verification.json)。')
    append('reports/world-static-mesh-session-recipes/GNU_PLAN.md','実77a363bは全6Engine job/Pages成功が確定（wire addon job271秒、portable911秒）。配信manifest2007件61090972BをGit treeと照合し、公開game READYを確認。これとは別にNative C ABIをmainへ追加した。新APIのGNU独立全9入力・計装/故障は次段で、先行45TU addon成功へ混ぜない。')
    append('README.md','Native向け追加: [plain-source session C API](docs/WORLD_STATIC_MESH_SESSION_C_API.md)で原本stage/create/read/reset/destroyを扱えます。最大8body/16plane、失敗stageの旧原本失効と所有readを検査済み。pump・WASM・ゲーム統合は後続です。')
    p=ROOT/'docs/PLAN.md';s=p.read_text(encoding='utf8');i=s.index('再開用の最新状態:');e=s.index('\n\n',i);s=s[:i]+'再開用の最新状態: '+note+' 正式receipt reports/world-static-mesh-session-c-api-verification.json。先行77a363bのsource/token GNU45production+2wire harnessは通常/真Debug/O1 ASan-UBSanで各27/77全文一致・source独立604bit/13拒否、全6公開job/Pages/manifest2007/READYまで実受入済み。次は新C APIのGNU実C/C++と独立9入力/全46依存計装、実allocator故障/再入の別試験、その後pump/保持Reportの有界getter。過去build(wfoc1,wfocm1含む)を再構成しない。新Nativeライブラリを既存WASM/ゲームへ接続済みとしない。専門物理/一般接触/流体損傷/IK/撮像は未完。'+s[e:];p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'docs/learn/index.html';s=p.read_text(encoding='utf8');old=re.findall(r'<article\b.*?</article>',s,re.S);need(len(old)==26,'26 articles');i=s.rindex('</article>');s=s[:i]+'<h3>原本の版と、読出し結果の寿命を分ける</h3><figure><img src="diagrams/world-static-mesh-session-api.svg" width="1040" height="550" alt="原本revisionを明示してownerを作り、成功readだけが所有cacheを交換する。不正stageは旧stageを失効し、active ownerと過去readを保持。"><figcaption>原著のNative C APIの概念図。物理stepや実測性能の図ではありません。</figcaption></figure><p>Native C言語から原本をstageし、Worldの作成・読出し・リセット・破棄を呼べる独立APIを追加しました。stage成功で原本の版を受け取り、その版を明示して作成します。失敗stageの後に古い原本を暗黙に再利用しません。成功readは独立cacheになり、owner破棄後も保持します。contextを削除する前にはcallerへcopyしてください。</p><p>実C/C++ caller、MSVCのRelease・Debug各9入力の全1254 bit値と12改変拒否を検査しました。新APIのGNU・sanitizer、pump・mesh・任意全guard・WASM・ゲーム接続は次段です。<a href="../WORLD_STATIC_MESH_SESSION_C_API.md">使い方と所有の契約</a> · <a href="../../reports/world-static-mesh-session-c-api-verification.json">Nativeの実受入</a></p>'+s[i:];need(old[:25]==re.findall(r'<article\b.*?</article>',s,re.S)[:25],'Old25 articles unchanged');p.write_text(s,encoding='utf8',newline='\n')
    image=ROOT/'docs/learn/diagrams/world-static-mesh-session-api.svg';st=stamp(image);append('docs/legal/ASSETS.md','2026-11-05 原著図world-static-mesh-session-api.svg: '+str(st['bytes'])+'B、SHA256 `'+st['sha256']+'`。原本revision/owner token/所有readの概念図。実測traceや物理進行の結果ではない。外部画像・font・素材追加なし。')
    api_sources=['core/include/pikapika/world_static_mesh_session_api.h','core/src/world_static_mesh_session_api.cpp','tests/world_static_mesh_session_api_tests.cpp','tests/world_static_mesh_session_api_c_tests.c','scripts/verify-world-static-mesh-session-api.py','CMakeLists.txt']
    for rel in ['scripts/verify-world-static-mesh-session-api.py','reports/world-static-mesh-session-recipes/check-native-api.py','reports/world-static-mesh-session-recipes/check-native-api-main.py']:ast.parse((ROOT/rel).read_text(encoding='utf8'),filename=rel)
    source_stamps=[stamp(ROOT/p) for p in api_sources];commands=[]
    # Write the canonical receipt before local-link checking.
    receipt=dict(schema=1,status='FINITE_NATIVE_MAIN_PLAIN_SESSION_C_API_PASS',actualMainVerification=stamp(MAIN),actualIsolatedVerification=stamp(HERE/'run-20261105-native-api-001/verification.json'),sources=source_stamps,actualCAndCxxCallers=True,actualReleaseDebug=True,sourceRowsPerBuild=9,mappedFloatBitValues=1254,negativeZeroOccurrences=142,copiedIndependentRejections=12,actualOptimizedPythonRefused=True,old20ProfileDocumentsRawExact=True,registeredTests=r['inventories'],old54TestsRerun=False,actualNewDirectedCTestPerConfiguration=1,actualGNUForNewCAPI=False,pumpImplemented=False,oldSDKOrWASMChanged=False,scope='Finite main Native C/C++ lifecycle/staging and all plain read values. Real earlier GNU45 source/token phase is separate. No new allocator-fault, reentry, pointer authentication/thread safety, arbitrary full guard/mesh, pump, JS/WASM/game or whole engine completion.')
    canonical=ROOT/'reports/world-static-mesh-session-c-api-verification.json';write(canonical,receipt)
    for name,argv in [('learn',['node','--test','docs/learn/learn.test.mjs']),('syntax',['node','scripts/check.mjs']),('build',['node','scripts/build-web.mjs'])]:
        start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=90);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);row=dict(name=name,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.json'),row);need(p.returncode==0,'Actual final '+name)
    need(source_stamps==[stamp(ROOT/p) for p in api_sources],'Native source stable after docs/checks')
    write(OUT/'verification.json',dict(status='PASS',commands=commands,old25ArticlesExact=True,nativeSourceStable=True))
    write(HERE/'native-api-freeze.json',dict(schema=1,status=receipt['status'],sources=source_stamps,main=stamp(MAIN),canonical=stamp(canonical),integration=stamp(OUT/'verification.json')))
    print(json.dumps(dict(status='PASS',nativeSourceStable=True,commands=len(commands))))
if __name__=='__main__':main()
