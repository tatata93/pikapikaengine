from pathlib import Path
import json
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-entry-lab'
v=json.loads((root/f'reports/{prefix}-public-verification.json').read_text(encoding='utf-8'))
assert v['status']=='PASS' and v['commit']=='263d53127989b3779bcb214ead3c12415449e094'
assert (v['ctest'],v['node'],v['publicFiles'],v['publicBytes'],v['existingWarnings'])==(38,631,93,2506249,36)
assert v['publicBrowser']['numericBits']==180165 and v['publicBrowser']['negativeZeroBits']==5061
resume='再開位置: 手動entryラボ263d531を公開受入。専用21群/631Node skip0/38CTest、25例24実model+host拒否1・追加13packet・2実Blob保存=180165数値bits5061負零が実公開でも一致。全256audit/128partition/127frontier/64ID/別所属/初期点prefix/失敗祖先を保持。Engine41785159270/Pages41785158716全job/step成功・既存36warning multiset不変、93公開file2506249Bがfeatureblob一致。公開ゲーム1撃破/boostclip1/停止・22全照会完了3常駐/error0。314原本/SDK86exports61source-header719410B/glue58933B/runtime91/7通知不変、Web6aa725ed1898f4e9/51modules25entries。次は[保持荷重・秒時間のNative球×静的mesh照会](SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md)を実装する。計画のみで、元F/m+gの区間と曲がる全経路/時間窓・空間幅を別に認証する。[ラボ検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-lab.md)。World進行/一般TOI応答/摩擦・流体/材料損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';s=p.read_text(encoding='utf-8');i=s.index('再開位置:');j=s.index('\n',i);s=s[:i]+resume+s[j:];s+='\n追記: '+resume.removeprefix('再開位置: ')+' 公開時のREPL保存先混線では5証拠ファイルを原状別保存し、元local検証hashとfeatureblobへ完全復元後、公開13packetを明示contextで再取得した。UI/SDK/数学入力や受入条件は変更していない。元の独立mixed65/90負例・GNU API/test sanitizer24と全entry核別76/旧guard69/API25も全工程成功。\n';p.write_text(s,encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md';s=p.read_text(encoding='utf-8');old='UI実装・ローカル受入済み、公開受入確認待ち';assert old in s;p.write_text(s.replace(old,'UI実装・公開受入済み（263d531）',1),encoding='utf-8',newline='\n')
p=root/'reports/2026-11-04-sphere-triangle-mesh-entry-lab.md';s=p.read_text(encoding='utf-8');old='確認待ち。ローカルの実行結果を公開成功として流用しない。';assert old in s
new='''コード263d53127989b3779bcb214ead3c12415449e094のEngine41785159270（job126425511379）、Pages41785158716（build126425513429/deploy126425593830/report126425593942）全job/stepが成功。GNU38CTest/631Node skip0・fresh所有62model3hostの全数値/負零、明示補足mixed65 Fraction/90負例、旧SDK/数学回帰も成功。既存のAPI/test ASan24群（通常strict核archive）と全entry核別76/Release-sanitized fixture bytecmp、旧guard全核69/API25も成功し、既存36warning診断のmultiset/数は不変。

93選定公開ファイル計2506249Bがfeature Gitblobに完全一致。新UIの実公開全25例・追加13packet・2実Blobは180165数値bits5061負零で直接SDKと一致し、全local/public input/result/viewも別にbit照合した。実公開ゲーム1撃破/boostclip1/停止・22全照会完了/3mesh常駐/error0を確認した。UIの入力・全結果・実保存・画面は[public-browser](sphere-triangle-mesh-entry-lab-public-browser)、全job/step・340原log行（全Run/全warning含む）・配信・hashは[公開機械集計](sphere-triangle-mesh-entry-lab-public-verification.json)。ガイド/図/新ソースの公開byte監査はfeature263d531時点を固定し、最新受入状態はこの記録とPLANへ追記する。

公開検証の補助REPLが以前のlocal保存先/配列を保持していたため、最初の3viewの保存で5つのlocal証拠ファイルへ誤保存した。変更後原byteを[routing-attempt-001](sphere-triangle-mesh-entry-lab-browser-routing-attempt-001)へ保存し、全5ファイルを元local検証hash=feature Gitblobへ完全復元。明示contextを渡すdriverで公開13packetを再取得した。復元と元hash/featureblobの三点一致を公開集計でも必須とし、UI/API/モデル/元入力や検証条件は変更しなかった。

[侵入開始窓ラボを起動](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-mesh-entry-lab.html?v=263d531) · [オリジナルゲームを起動](https://tatata93.github.io/pikapikaengine/?v=263d531)。次の数値段は[保持荷重・秒時間の計画](../docs/SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md)。これは未実装で、厳密F/mの自由軌道照会と、丸めたWorld伝播/衝撃後の残時間・応答を別に受け入れる。'''
p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8')+'\n手動entry UI公開受入:263d531のEngine41785159270/Pages41785158716全job/step成功。38CTest/631Node・全owned/数学/旧回帰・既存36warning不変、93配信2506249B blob一致。実公開25例/追加13packet/2実Blob=180165bits5061負零・ゲーム1撃破22照会を別実行。rootdriverの保存先混線は5原byteを別保持してfeature/localhashへ復元し、公開証拠を再取得した。数値/受入条件は不変。新依存/外部資料転載/有料service/本体license選定なし。次の保持荷重・秒時間Native照会は元コード/反例を読取調査して設計文書のみ追加、実装やWorld応答の成功とはしない。\n',encoding='utf-8',newline='\n')
print('Public manual lab acceptance documented; next held-load numeric stage remains a plan.')
