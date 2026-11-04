# Entry-window所有JavaScript APIの実装と検証

2026-11-04 JST。公開受入は下部へ別追記する。

`SimulationRuntime.querySphereTriangleMeshEntry(path, triangles, settings)`を追加。既受入C++の定義線分に対する侵入開始窓と、初期正証拠・closed安全prefix・負witness・全audit/partition/frontier/tail・lastMeshを、原入力と別所有のDTOで返す。全6能力を入力書込前に検査し、旧SDKへfallbackしない。入力を一度captureし、全getterをcopyしてcount/enum/予約+0/所属/幅優先履歴/Workを検査する。[契約](../docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md)と[次の手動ラボ計画](../docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md)を参照。

## ローカルの実行結果

- 専用24群、全Node610/610 skip0、Native CTest38/38、構文・Web生成・教材12試験が成功。
- 凍結pure65入力を実共有WASMへ渡した62モデルと3件のhost拒否を分けた。全モデル105056数値bits/3239負零、原入力4728数値bits/108負零が一致。62件のcaller変更検査と旧DTO保持、追加3実呼出し、scratch/公開output/原入力/Native snapshot/lastMesh sourceの所有分離を確認。
- 62実DTOをenumだけ投影し、host3をpure由来と明記補足したmixed65を独立Fractionへ渡して成功。558認証葉/1452audit/3840lastMesh成分、17解析群・90改ざん拒否。65件全部がWASMモデル実行されたとは報告しない。raw wireの前段件数とowned DTO件数も別である。
- 最大256audit/128partition/127frontier、64全保守候補IDを省略せず保持。人工work予約・allocation形状試験は実C++例外注入ではない。
- 旧owned trajectory59model/3host、旧瞬間mesh/single/共通simulationも回帰成功。312保護原本はraw不変、24既存HTMLは生成import map/build URLだけ更新。
- SDK86exports/61source-header/WASM719410B/glue58933B/runtime91部品/7通知不変。Web build `733ad5671fc0b4b3`、50modules/24entries。

完全なcommand/exit/前後source/hash/stdout/stderrは[sphere-triangle-mesh-entry-js-checks](sphere-triangle-mesh-entry-js-checks/run-20261104-final)と[安定後の旧SDK再試験](sphere-triangle-mesh-entry-js-checks/run-20261104-stable-old)へ保存。機械集計は[sphere-triangle-mesh-entry-js-local-verification.json](sphere-triangle-mesh-entry-js-local-verification.json)。

## 実ブラウザ

固定`analytic-entry-quarter`を公開APIで実行する[確認ページ](sphere-triangle-mesh-entry-js-browser/index.html)を追加。入力編集ラボとは別段階である。画面の完全JSONを保存し、入力/全owned DTO3255数値bits24負零をNodeへ、enum投影したモデル3312数値bits20負零を凍結Native結果へ照合した。結果entry_window/61audits/41partition。原著SVGの文字・配置も実表示で確認。

既存オリジナルゲームで射撃1撃破・ブースト・移動・停止、背面カバー20SDK照会全checked/validated/completed・3mesh常駐/error0を確認。ゲームは回帰試験であり、新entry-windowをゲーム接触へ使ったとはしない。画面と完全JSONは[local-browser](sphere-triangle-mesh-entry-js-local-browser)、[実測集計](sphere-triangle-mesh-entry-js-local-browser-verification.json)。音声の聴感・GPU提示時間は未測定。

## 失敗と訂正の保存

初回owned runnerと専用run001は合法なnorm²区間の微小負下端をdecoderが拒否した。平方上端非負とsqrt下端非負へ検査を訂正し、モデル/数学核/fixtureを変えず成功した。専用run002はfrontier値へ同値を代入する無変異試験が失敗したため、実際にtailを除去する負例へ訂正。run003/004/005は24/24成功、全原出力を[agent-tests](sphere-triangle-mesh-entry-js-agent-tests)へ保持。最後に新facadeだけでnested metadataの−0を拒否し、幾何/原入力の−0は維持した。

最初の旧owned回帰は実装freeze中に開始したため前後sourceが不一致であり、canonical受入へ使わず安定後に全旧SDKを再実行。ブラウザ比較recipe初回はenum文字列とNative数値を直接比較して停止し、既存runnerと同じenumだけの投影へ訂正した。API/出力/数学を変更する訂正ではない。

## 境界と次段

metadata整合監査は幾何solverではなく、数学包含はNativeと独立Fractionに依存する。Native commit後のdecoder拒否にNative recordのrollbackを保証しない。新外部依存/転載素材/有料serviceなし、本体license未選定。

次は手動entry UIの原入力編集・全診断の所属表示・完全strict JSON保存を実装する。World/一般TOI応答/摩擦・車両航空鉄道/流体/弾塑性損傷・IK制御/高精度撮像・全作品60fpsは未完。

## 公開受入

コード578895de6295acf77b2fffd1acb1bd645adc799eのEngine41781369977（job126413438313）、Pages41781369241（build126413439521/deploy126413516133/report126413516156）全job/stepが成功。GNU38CTest/610Node skip0、実owned62model/3hostと全DTO/負零・mixed65 Fraction/90負例、旧SDK回帰が成功した。新test/probe各-Werror、API/test ASan24群（通常strict核archive）と全entry核別76群/Release-sanitized fixture bytecmp、旧guard全核69/API25も成功。既存36warning診断は同一multiset/同数で追加なし。

88選定公開ファイル計2387746Bは当該featureのGit blobと完全一致。実公開固定API3255bits24負零/Native投影3312bits20負零、ゲーム射撃1撃破/boostclip1/停止・20照会全正常/3mesh常駐を確認し、過去操作の継承とは分けた。完全JSON・画面は[public-browser](sphere-triangle-mesh-entry-js-public-browser)。[公開機械集計](sphere-triangle-mesh-entry-js-public-verification.json)へ全job/step・原Run command/全warningを含む有限ログ・配信bytes・原出力のhashを保存。Gitの宣言済みCRLF→LF変換はsource比較の正規化として明記した。

[固定APIを起動](https://tatata93.github.io/pikapikaengine/reports/sphere-triangle-mesh-entry-js-browser/index.html?v=578895d) · [オリジナルゲームを起動](https://tatata93.github.io/pikapikaengine/?v=578895d)。[次ラボの25例と依存調査](sphere-triangle-mesh-entry-js-next-lab-review.md)は未実装UIの準備記録であり、実行したUI結果ではない。
