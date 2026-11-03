# 波長分散の独立核と共通Web出力

## 実装と範囲

独自C++20のCauchy/Sellmeierモデルから、真空波長の閉区間全体について
位相屈折率・解析微分・群屈折率を外向きに囲む。SI係数、宣言した有効帯、最大8項、
正値・特異点を除外できない条件・幅・計算予算を[契約](../docs/DISPERSION.md)へ記録。
モデルが返す不確かさを中央値や近似材質へ差し替えない。

共通C ABIはv1への追加で37関数。実WASM298291B、glue40733B。
WASM SHA256 `d5618218c3af2cfde1a117b6e24d9dd0cf6b71c7975461f9d21c67c32660abd3`。
主ビルドの全原本/通知/生成物hashは[build manifest](../assets/pikapika-simulation.build.json)。
web build `bbc6487a7ebb83f9`、24 modules。

[操作ラボ](../tools/dispersion-lab.html)は独自の合成材質だけを使い、全帯の照会と
同じ境界を共有する32小帯の包含を示す。矩形は帯全体を表し、測定点をつないだ線ではない。
独自SVGと図解14項目、[資料/配布台帳](../docs/legal/REFERENCES.md)を更新した。
新規の外部アルゴリズム/材質データ/実行ライブラリは取り込まない。

## 実行した検証

- Native MSVC19.51 strictと実Emscripten6.0.13/Node24.14.1 WASMで分散14群。
- 独立Fractionによる320例・960区間。点160/連続帯160。帯の単調性を解析して端点検査を全帯へ拡張できる限定コーパスであり、サンプル点だけの全域主張ではない。
- Native/standalone実WASMの320完全入出力packetは改行正規化後一致。主WASM ABIでも元入力bitから1920出力端点bit一致。
- 319例へ切り詰めたコーパスとPython -O実行を、検証器が拒否する負例を実行。
- Native CTest13/13、全227検証群。Node153/153、skip0。web build/check成功。
- 既存30697値のNative/WASM比較: 最大絶対差6.821210263296962e−12、正規化差4.3655745685100546e−12で規定許容内。
- 既存光学4116/面交差2400端点bitとW1 World41値も再確認。分散source/checkerの独立読取レビューで公開を止める問題なし。

[Native分散](dispersion-native-tests.txt) / [実WASM分散](dispersion-wasm-tests.txt) /
[生コーパス](dispersion-oracle.csv) / [Native全試験ログ](dispersion-native-ctest.txt) /
[Node全試験ログ](dispersion-node-tests.txt) / [原本・証拠のhash](dispersion-verification.json)。

ローカル実ブラウザでCauchy/Sellmeier、各端点sqrt予算1の未解決、極を含む帯、
全帯幅不足、宣言有効帯外のエラーと古い値消去、正常復帰を操作した。
[入力/結果](dispersion-local-cases.json)、[画面](dispersion-local.png)。
ブラウザ確認でゲーム用CSSとの衝突を見つけ、教材用CSSへ統一してグラフ/設定の配置を修正した。
操作欄の数値はinput時にも即再照会する。

## 残りと次

数式/丸めの包含は実ガラスの校正や係数測定誤差を保証しない。群指数の任意符号も、
吸収・因果性を満たす物理材質の証明とはしない。実ガラスの基準（相対/絶対）・許諾・温度・波長域の確認は残る。
複数面の像形成、収差・ゴースト・フレア・回折/干渉の画像生成はこの公開段階では未実装。

次の区間光学（交点/法線/方向の全boxを次の面へ継続）とread-only法線支持核は独立試験済みだが、
今回の共通ビルド/公開版へは含めていない。レビューして順次接続する。
継続開発goalはactiveのまま。課金・フォーラム・メールの操作なし。

公開CI/Pagesおよび公開ブラウザの確認結果は、配信後に追記する。
