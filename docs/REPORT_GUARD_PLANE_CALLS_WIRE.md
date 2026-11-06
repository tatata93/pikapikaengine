# 平面の二つの呼出を一組で保存する

2026-11-06。`world_static_mesh_flight_guard::PlaneCalls`全2項目`metric`、`box`のconst取得をNative有限受入。合計89record型522項目＋別Input variant1型。正式記録は`reports/diagnostic-wire-guard-plane-calls-verification.json`。GNUと公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| metric | 元のPlaneMetricCall全8項目。元Input variant、要求／使用設定、許可とGrant、全Resultまたは欠損、省略計数 |
| box | 元のPlaneBoxCall全8項目。元の球・平面係数、宣言B・margin、要求／使用設定、許可とGrant、全Resultまたは欠損、省略計数 |

両方のCallが常に存在し、各Call内のresultの存在／欠損は独立である。metric、boxの宣言順と、元の全child通算attempt_ordinalを保持する。保存順を試行順へ振り直さず、二つの返却結果を突き合わせて修復せず、再queryを行わない。全監査・区画・前線・current・tailを保持する。宣言Bの保存は、実Worldからの誤差導出や数値モデルの認証とは別である。

人工sourceは受入済みの二つのCallの定数定義から、対応が異なる8組・16Callを構成する。独立仕様も両方の既存Call仕様から組み立て、宣言順・型tag・全値・optional・Input variantを照合する。既存のpair Result人工source headerを再利用し、新しい共有headerを増やさない。

初early001 `build/wfdgpc1`は、試験ループの変数誤参照でコンパイル停止した。当時のcpp原本・原logを保存し、試験変数だけを修正した別fresh `build/wfdgpc2` early002で受入。全48,803byte SHA256 `4d00bf11c4dad940991fb5b642ea9a0d33207f55f3eec81ae6ba7a219a77754d`、1,458typed leaf（F64 484／負零37、U64 564、U32 124、bool94、enum184、bytes8）、存在131／欠損135、入れ子Input variant2が独立一致した。

6,707callback境界、停止／例外13,414件、再入13,414件、4丸めmodeを確認。正当な公開emplaceの4操作で、実MSVCは値なし4／旧値保持0を観測した。6種類のWriter位置×4で24状態、親recordとmetric keyを含む正確な送信済みprefix16件、既存sticky失敗20件、値なし再入26,828件を確認した。private byteは変更しない。GNUの実到達結果は別に測定し、Nativeの結果から推定しない。

全35,067の異なる有効文法変更を16分割・各180秒で拒否した。同値交換73件（field69、array4）は分離する。全Nativeは別fresh `build/wfdgpc3`で受入し、旧42＋新1の各43CTestと旧全fixture・全実行出力、20profile、保護原本の不変も確認した。17header gate1受理20拒否、Web693テストskip0・構文・buildは成功した。

製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。GNUの41sourceには、metric／box両枝の実再帰13script閉包を固定する。AST source宣言と実module graphの照合は事前確認であり、実GNUの成功とは区別する。

別Child variant、PairRecord、準備Resultの依存、GuardResult、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続は後続。


記録統合の初回はsource-before初期化漏れのNameErrorで停止し、失敗時recipeと実tool観測を`reports/diagnostic-wire-integration/run-20261106-guard-plane-calls-native-001/`へ保持した。初期化を修正し、保存済みNative・全16変更shard・20profileを再照合したfresh `native-002`で受入。数値核やCpp試験の追加再実行は行っていない。
