# Entry-window手動ラボの実装と検証

2026-11-04 JST。公開確認は下部へ別追記する。

`tools/sphere-triangle-mesh-entry-lab.html`を追加。定義線分・半径・全三角形・品質/予算/toleranceをstrict JSONで編集し、既受入の実C++ WASM所有APIを一回照会する。初期点の証拠、連続安全prefix、後方の証明島、負witness、開始窓、全partition/frontier/tailとlastMesh所属を別表示し、全入力/DTO/負零と閲覧条件をJSON保存する。新幾何solver、Worldや反力をUIへ実装したものではない。

## ローカル受入

- 専用21群/全Node631/631 skip0、Native CTest38/38、構文/Web生成/教材12試験が成功。
- 固定65入力から25例を原入力bitsそのまま採用。24実モデルの内訳は分離2/開始窓5/初期貫通1/未認証12/invalid4。65面のhost拒否1はモデル実行へ数えない。人工環境/未返却work/初期allocation表示試験は自然実行や実Native fault注入ではない。
- 実ブラウザで全25例と追加13packet（容量/所属/入力編集/再読込み）を保存し、完全入力/全owned DTOを直接SDKへ照合。180165数値bits/5061負零が一致。追加viewは同じqueryを使うため、packet数は実query回数ではない。
- 全256auditと末尾255、全128partition/葉、127frontier、64面末尾63と全候補ID、失敗後続行/別所属audit、初期点だけのprefixと後方島、失敗祖先を実表示で確認。全候補ID `[5,37]`を瞬間nearest `[37]`へ縮めない。
- 実Blobダウンロード2件は表示JSONと最終LF込みで完全byte一致。編集で全表示/保存を即消去、不正ID/重複JSONキー拒否、SDK再読込みから復帰を確認。
- 新ビルドの既存ゲームを射撃1撃破/移動/boost/停止で回帰確認。22SDK照会が全checked/validated/completed、clip1を観測、3mesh常駐/error0。新entryをゲーム接触へ接続したとはしない。
- fresh所有SDKの全62model/3host、105056モデル数値bits3239負零・4728原入力bits108負零が一致。出自付きmixed65 Fractionの558leaf/1452audit/3840成分と17解析/90負例が成功。旧SDK回帰は前公開受入と全source/artifactの同一性を確認して継承し、今回再実行したとはしない。
- 314既存原本、86exports/61source-header/719410B WASM/58933B glue/runtime91/7通知不変。旧24HTMLは生成部分だけ更新、新入口1を追加。Web `6aa725ed1898f4e9`、51modules/25entries。既存build試験の入口期待24→25と新module byte改変のcache試験を追加。

原出力は[sphere-triangle-mesh-entry-lab-checks](sphere-triangle-mesh-entry-lab-checks/run-20261104-final)、[専用試行](sphere-triangle-mesh-entry-lab-agent-tests)、[全画面JSON/実保存/画像](sphere-triangle-mesh-entry-lab-local-browser)。[ローカル機械集計](sphere-triangle-mesh-entry-lab-local-verification.json)と[実ブラウザ照合](sphere-triangle-mesh-entry-lab-local-browser-verification.json)を別に保存する。原著図は実表示を目視し、数値の証明や性能測定には使わない。

## 中断・観測訂正

最初の25例をまとめた自動操作は30秒のtool上限で中断し、16完全packetを保持。再取得にも一度時間上限が発生したが、inventoryと新タブで復帰し、5例単位で全25を完了した。エンジンやfixtureの変更で回避していない。

最初の集計は、collectorが非表示の過去hostエラーnodeのinnerTextを最終modelのエラー欄へ採ったため停止。元manifest/失敗command stdout/stderrを保持し、そのmodelの実 `isVisible=false` を再操作で確認して観測metadataだけを訂正した。結果JSONや検証条件は変えていない。[試行記録とhash](sphere-triangle-mesh-entry-lab-attempts.json)を参照。専用試験は初回20/20に人工表示1群を追加して最終21/21で、初回から失敗したとはしない。

## 境界と次段

各座標/半径はm、parameterと窓幅は無次元。説明投影の最小ink幅は実区間を広げる証拠ではない。保存/数学/画面の所属と、物理的な運動軌道や一般TOI/反力を分ける。新外部依存/転載素材/有料serviceなし、本体license未選定。

次は公開CI/Pages/93選定配信/実公開操作を受け入れ、その後Worldの物理運動と三角形接触を結ぶ次の有限数値段を設計する。一般CCD/摩擦/車両航空鉄道/流体/材料損傷・IK制御/高精度撮像は未完。

## 公開受入

コード263d53127989b3779bcb214ead3c12415449e094のEngine41785159270（job126425511379）、Pages41785158716（build126425513429/deploy126425593830/report126425593942）全job/stepが成功。GNU38CTest/631Node skip0・fresh所有62model3hostの全数値/負零、明示補足mixed65 Fraction/90負例、旧SDK/数学回帰も成功。既存のAPI/test ASan24群（通常strict核archive）と全entry核別76/Release-sanitized fixture bytecmp、旧guard全核69/API25も成功し、既存36warning診断のmultiset/数は不変。

93選定公開ファイル計2506249Bがfeature Gitblobに完全一致。新UIの実公開全25例・追加13packet・2実Blobは180165数値bits5061負零で直接SDKと一致し、全local/public input/result/viewも別にbit照合した。実公開ゲーム1撃破/boostclip1/停止・22全照会完了/3mesh常駐/error0を確認した。UIの入力・全結果・実保存・画面は[public-browser](sphere-triangle-mesh-entry-lab-public-browser)、全job/step・340原log行（全Run/全warning含む）・配信・hashは[公開機械集計](sphere-triangle-mesh-entry-lab-public-verification.json)。ガイド/図/新ソースの公開byte監査はfeature263d531時点を固定し、最新受入状態はこの記録とPLANへ追記する。

公開検証の補助REPLが以前のlocal保存先/配列を保持していたため、最初の3viewの保存で5つのlocal証拠ファイルへ誤保存した。変更後原byteを[routing-attempt-001](sphere-triangle-mesh-entry-lab-browser-routing-attempt-001)へ保存し、全5ファイルを元local検証hash=feature Gitblobへ完全復元。明示contextを渡すdriverで公開13packetを再取得した。復元と元hash/featureblobの三点一致を公開集計でも必須とし、UI/API/モデル/元入力や検証条件は変更しなかった。

[侵入開始窓ラボを起動](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-mesh-entry-lab.html?v=263d531) · [オリジナルゲームを起動](https://tatata93.github.io/pikapikaengine/?v=263d531)。次の数値段は[保持荷重・秒時間の計画](../docs/SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md)。これは未実装で、厳密F/mの自由軌道照会と、丸めたWorld伝播/衝撃後の残時間・応答を別に受け入れる。
