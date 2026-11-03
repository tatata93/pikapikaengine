# 全競合を監査する静的最近傍光学

2026-11-03。複数の静的な円盤・球・球面capから、全ray族で同じ一意な最初の面を選ぶ
[原著C++核](../docs/OPTICAL_SELECTION.md)を追加した。共通ABIへ2関数を追加し48exports。
JS `SimulationRuntime.queryNearestOpticalSurface` は入力boxをそのまま渡し、全診断をコピーする。
[操作ラボ](../tools/optical-selection-lab.html)には9比較例、prefix切替、閉t領域、入力幅と予算、
全競合の状態表と完全JSONを用意した。図解教材は18記事、原著SVGは1833B。

## 証明と適用範囲

元のprimitiveが全族で最初の有効根を証明したhitを候補にする。
他の全ての面を、全領域miss・厳密に後方のhit・閉prefix内missのいずれかで排除してから選ぶ。
閉prefixは `[tMin,candidate.parameter.upper]`。元照会が開口境界で未確定でも、
このprefix全体に交差がないと証明できた場合は、候補以前の競合から除外できる。
接線・同時面・未照会をmissと読み替えず、全未検査面を残して成功しない。
診断はID昇順だが、IDで物理的な面順を決めない。

独立Cartesian boxによる保守的な選択であり、全ての真の最近傍を必ず証明できる方式ではない。
例えば原点0、dZ∈[1,2]、z=2とz=3の面は真には常に前者が先でも、各t包絡は重なる。
現方式は未確定を返す。tMinの変更は要求領域の変更にすぎず、除外した前方の安全を証明しない。
球面から始まるt=0の包絡はparameter境界で未確定になり得る。sphereをsource IDごと捨てない。
元球の出口t=2も保ち、diskの証明可能なt=0はそのまま返す。

これは一回の幾何照会。媒質配置、生成面との相関を保つ自己根除外、自動反射/屈折継続、
全ghost探索、撮像積分、収差/フレア画像・回折の完成ではない。既存の指定routeの契約は維持する。
新しいsolver・依存・ガラス処方・測定データ・他作品の素材は導入していない。
PBRTの単一shape契約・後段根・丸め誤差の一次資料を確認した記録は[出典台帳](../docs/legal/REFERENCES.md)。

## 実行した確認

- Native MSVC19.51.36247 x64、CMake4.3.3、Node24.14.1、Python3.12.10。i5-6500 / GTX1060 6GB / RAM15.94GiB / Win10.0.19045。GPU性能を新測定した記録ではない。
- 最終全Native CTest21/21・384群、Node212/212・skip0、web build/check成功。新核20群、共通ABIは39群（3追加）。
- standalone実WASM19群成功。Nativeだけの20番目はFE_UPWARD環境拒否と復帰。33完全入力fixtureの2956数値がbit一致し、33分類・111有理数包含を独立検査した。
- 軸方向の円盤/球/cap各64、計192連続族を、元binary64をFractionに復元した独立極値/位置で検査。1152包含と192最近傍IDを確認し、Native/standaloneのoracle packetもbit一致。
- 失敗を検出するcheckerの破損入力56種類を全拒否。入力identity、欠落/重複/不正型/非finiteとPython -Oを含む。有限corpusの証拠を任意入力の完全性へ拡張しない。
- 最終主WASMで33fixtureを全実行。31モデル結果の1326数値がbit一致。Native coreのゼロID・ゼロ整数設定の2例は、C/JSの厳しい交換domainで明示的に拒否する。黙って省略せずこの差を記録。主WASMで192解析族の1152出力端点も全bit一致。
- C ABIの不正count・NaN・reserved slot・unsafe ID・getter flag/indexは以前の出力/attempt recordを保持。resetは明示的に消去。他照会後もsnapshotを保持。
- 最終447783B主WASMで旧18回帰＋W2、計19コマンド成功。旧光学/分散/区間光学端点、strict支持、指定route、W1、静水圧と30697値比較を保持した。W2のcounter/微小処理数差も引き続き診断へ残る。
- 実ブラウザで9プリセットとprefix off、query budget2/1、512への同一条件復帰、計13操作を確認。条件変更前後の全入力と結果をJSONへ保存した。

初回主WASMビルドは、ABI追加のauto同時宣言がuint64とsize_tのwasm32幅差で失敗した。
個別宣言へ修正して最終SDKを再生成した。preflight後の数値不支持をinvalid_inputと誤分類しない
修正も加え、その前後で既存33fixture/192oracleのNative数値packetが不変と確認した。

Native統合では、旧self-zero試験objectが再利用されていた。現在原本のdisk+diskに対し、
実exeのfixtureが旧sphere+diskを出すことを確認し、その失敗を合格扱いしなかった。
`cmake --build ... --clean-first` で全体を再生成し全21試験を成功させた。
最終CMake exeとstandalone exeのfixtureは2956値bit一致・改行正規化後byte一致で、
古いobjectと新原本の混在が解消したことも確認した。

[Native全ログ](optical-selection-native-all.txt) / [Node全ログ](optical-selection-node-tests.txt) /
[Native完全入力](optical-selection-native-fixtures.json) / [standalone全出力](optical-selection-wasm-fixtures.json) /
[33fixture解析](optical-selection-fixture-comparison.json) / [192解析族](optical-selection-oracle.csv) /
[有理数包含検証](optical-selection-oracle-comparison.json) / [checker負例](optical-selection-negative-controls.json) /
[共有API比較](optical-selection-main-api-parity.json) / [主WASM入力と全packet](optical-selection-main-api-outputs.json) /
[19回帰](optical-selection-regressions.json) / [ローカル操作](optical-selection-local-cases.json)。

主WASM447783B SHA256 `68aa0ac06168d864d6696ddc5b4c2ec5a79175e0bb2ddb4321e646a27ee36db4`、
glue44500B、web build `33f0384f1e66b9e8` / 28modules。source/artifact/license SHAは
[SDK manifest](../assets/pikapika-simulation.build.json)と[最終記録](optical-selection-verification.json)。

## 公開と継続

この記録の初版はローカル成功・公開前。コードpush後のCI/Pagesと公開ラボの操作を追記する。
次はレンズの媒質境界の整合と、点像・収差の参照計算を制作/描画へ接続する。一般接触・摩擦支持・
車両/流体/材料損傷、共有ゲームコード、制作M2、性能の残件も継続する。ゴール全体は未完である。
