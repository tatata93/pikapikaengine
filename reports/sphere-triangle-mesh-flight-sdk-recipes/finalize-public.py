"""Record only a successfully captured exact-commit public acceptance."""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-sdk'
feature=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',feature);short=feature[:7]
proof=json.loads((root/f'reports/{prefix}-public-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and proof['commit']==feature
assert (proof['nativeGroups'],proof['fixtures'],proof['actualModelFixtures'],proof['hostRejected'],proof['ctest'],proof['node'])==(200,183,173,10,41,631)
engine=next(j for j in proof['jobs'] if j['name']=='portable-core');pages=next(j for j in proof['jobs'] if j['name']=='deploy')
assert all(j['status']=='completed' and j['conclusion']=='success' for j in proof['jobs'])
game=proof['publicGame'];build=proof['webBuild']
resume=f'保持荷重/丸め自由伝播guardのraw共有SDK {short}を公開受入。独立mode/全21kindの6入口を追加し92exports/67source-header/32TUへ正式再build。WASM800982B/glue61661B/runtime91/7通知、Web{build}/51modules25entries。Native200ABI群/41CTest/631Node skip0、183完全入力の173実モデル/10host拒否、全packet415506bits5738負零・復号272814bits5424負零・Node415689bits5738負零と独立Fraction/16改ざん拒否がWindows/Linuxで成功。API/test/probeのASan-UBSanとRelease/sanitized183packet byte比較、既存純核の別ASanも成功。333原本/25HTML保持、旧W1全20Native byte/SDK4520bits24負零と旧entry全所有照合を保全。公開45ファイル{proof["publicBytes"]}Bがfeature blobと一致。実公開ゲーム{game["kills"]}撃破/boostclip1/停止・{game["queries"]}照会全完了3常駐/error0。既存40警告に旧APIの別target再コンパイルによる同一診断8件が加わった48警告、新診断なし。HEAP容量64MiB観測はused heap/stack高水位/実growth/fault注入を証明しない。[ガイド](SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md)・[受入記録](../reports/2026-11-04-sphere-triangle-mesh-flight-sdk.md)。次は[所有JS API](SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)：全6能力の書込前検出・原本capture一度・全診断所有copyとdecoder監査を実装する。JS所有API/手動UI、World advance/全pair順序/接触応答・流体損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$','再開位置: '+resume,text,count=1,flags=re.M);assert n==1;p.write_text(text.rstrip()+'\n\nraw flight SDK公開受入追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md';text=p.read_text(encoding='utf-8');old='ローカル受入済み、公開検証待ち。';assert old in text;p.write_text(text.replace(old,f'コード{short}で公開受入済み。',1),encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md';text=p.read_text(encoding='utf-8');old='raw C ABI/WASM交換はローカル受入済み、公開検証待ち';assert old in text;p.write_text(text.replace(old,f'raw C ABI/WASM交換は{short}で公開受入済み',1),encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md';text=p.read_text(encoding='utf-8');old='raw C ABIのローカル全wire/独立参照は成功し、公開受入は確認待ち。';assert old in text;p.write_text(text.replace(old,f'raw C ABIの全wire/独立参照とコード{short}の公開受入は成功した。',1),encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8').rstrip()+f'\n\nraw flight SDK公開受入: Engine run{engine["run_id"]}/job{engine["id"]}、Pages run{pages["run_id"]}の全job/step成功。183交換の173実モデルだけを独立Fractionへ送り、API/probe計装・Release/sanitized packet byte比較と既存純核別計装を区別して確認。公開45ファイル{proof["publicBytes"]}Bが正確なfeature blobと一致。実公開ゲーム{game["kills"]}撃破/{game["queries"]}完了照会/boost/停止、原著SVG全表示を保存した。48警告は既存40件と旧APIを追加2targetで再コンパイルした同一診断8件で、新しいunused helperは公開前に削除して再検証した。raw交換の受入をJS所有/World応答やheap使用量/stack高水位の測定へ拡張しない。次段は未実装の所有JS計画。\n',encoding='utf-8',newline='\n')
p=root/f'reports/2026-11-04-{prefix}.md';text=p.read_text(encoding='utf-8');text=text.replace(' — ローカル受入',' — 公開受入',1);text=text.replace('公開CI/Pagesは確認待ち。',f'コード`{short}`の公開CI/Pagesと配信を確認済み。',1)
text+=f'''
## 公開受入

Engine [run{engine['run_id']}](https://github.com/tatata93/pikapikaengine/actions/runs/{engine['run_id']})（job{engine['id']}）、Pages [run{pages['run_id']}](https://github.com/tatata93/pikapikaengine/actions/runs/{pages['run_id']})の全job/step成功。Linuxの200ABI群・41CTest・631Node skip0、183完全入力/173実モデル/10host拒否、全packet/decoded bits・独立Fraction・16改ざん拒否と旧W1互換性が成功。現在のAPI/test/probeとfixture writerをASan/UBSanへ計装し、Release/sanitizedの183全packet JSONがbyte一致した。リンクした既存archive全体をこのAPI手順だけで計装したとはせず、純held/guard等の依存を含む独立sanitizer手順も別に成功を確認した。新test/probeのstrict/Werrorも成功した。Windows sanitizer・実allocation fault注入は意味しない。

警告48件。前版40件に、旧APIの同じ4診断を追加2targetで再コンパイルした8件が加わった。元API本文は保存され、新しい診断はない。[公開機械監査](sphere-triangle-mesh-flight-sdk-public-verification.json)に全run/job/stepと行番号付きの有界抜粋を保存した。抜粋を全原ログarchiveとは呼ばない。

公開45ファイル計{proof['publicBytes']}Bがfeatureの正確なGit blobと一致。公開Web build{build}/800982B WASMの実ゲームで{game['kills']}撃破・boostclip1・停止、{game['queries']}照会すべて完了/checked/validated、3resident mesh/error0を確認した。原著図と実画面・表示JSONを[ブラウザ記録](sphere-triangle-mesh-flight-sdk-browser)へ保存した。新raw照会をゲーム接触へ適用した証拠ではない。

次は[所有JS API計画](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)。現段階の新能力はraw C ABI/WASMにあり、JS所有API・手動UI・World接触応答は未実装。HEAP容量と使用量/stack高水位/実growth/allocator faultの区別も引き続き保持する。

[ゲーム起動](https://tatata93.github.io/pikapikaengine/?v={short})・[共有SDKの解説](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v={short}#accelerated)
'''
p.write_text(text,encoding='utf-8',newline='\n')
print('Public raw SDK receipt recorded; owned JS is the next unimplemented milestone.')
