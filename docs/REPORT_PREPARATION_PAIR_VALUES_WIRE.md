# 型付き参照・元のペア順・除外計数を保存する

2026-11-07。`world_static_mesh_flight`のColliderRef4、Pair3、StaticOnlyCounts7の3型14項目のconst取得をNative有限受入。合計93record型541項目＋既存Input／Child variant2型。正式記録は`reports/diagnostic-wire-preparation-pair-values-verification.json`。GNUと公開は別受入。

| 元の実型 | 宣言順の全値 | 保存契約 |
| --- | --- | --- |
| ColliderRef | kind, id, ordinal, revision | enum、U64、count、U64。元の型付き位置をidから推測しない |
| Pair | kind, first, second | PairKindと両参照の全値。first／secondを取得時に並べ替えない |
| StaticOnlyCounts | body_body, body_plane, body_mesh, plane_plane, plane_mesh, mesh_mesh, total | 全7countを個別に保存し、totalを計算し直さない |

ColliderRef.ordinalは、所有Snapshot内のbody／plane／meshそれぞれの元配列位置。id、inventory内ペア位置、実child呼出位置、Call試行位置とは異なる。revisionは元のU64で、取得時に計測したobject hashではない。実prepareではbody／planeのrevisionは0だが、人工診断に別の値があっても保存側で修正しない。

実prepareのpair一覧は安定キー順に作られる。一方、getterは返された一覧や各Pairのfirst／secondをそのまま保存し、取得時にsort・query・再captureを行わない。静止のみの6種類を除外した計数も、非接触の数値認証と読み替えない。

人工sourceは6ColliderRef、6Pair、4StaticOnlyCountsの16record。全既知enumと未知ordinal、0／U64最大値／2^53+1／2^63を含む整数境界、異なるfirst／second、互いに異なる全7計数を使う。元のtotalが合計と一致しない場合もそのまま比較する。

新対象のfresh `build/wfdppv1` Release／真Debugで全2,711byte SHA256 `1930a157e75a59af14e757a0200533320a46c5ca2b36b3b4c46e6fdeb240c5a0`が独立一致。106typed leaf＝82U64＋24enum、402callback、停止／例外804件、再入1,206件、4丸めmodeを確認。新harnessは製品2data TU＋試験1TUでInterval TUも数値model libraryも不要である。

全1,737の異なる有効文法変更を一つの180秒上限内で照合し、全て拒否。同値交換は0。内訳はscalar／key byte1,472、root順序・個数3、enum tag24、field値交換210、object field順序28。固定配列・optional・variantを新型に含めたとは数えない。既存の全variant取得は別の受入範囲として保持する。

Webは17header gate1受理20拒否、93record541項目＋variant2、693Nodeテストskip0・構文・buildを受入。GNUは通常／真Debug／全3TU O1 ASan-UBSanのdriver／receiverを準備し、実再帰2script／28sourceのASTとmodule graphを事前照合した段階。実GNU成功とは呼ばない。

全Nativeは別fresh `build/wfdppv2`で旧45＋新1の各46実CTest（登録103／101）と全raw fixture、20profile、397保護原本を受入。[全45件両構成の実験](NATIVE_DIAGNOSTIC_TEST_CAPTURE.md)で確認したparserを使い、実CTestのJSON本文を保存済み直接実行結果へ比較する。改行を除く全JSON本文と全assertionは保持し、直接runのstdout全raw byteと同一とは呼ばない。各CTestは実行し、fixtureの全raw byte比較を省略しない。

Snapshot6／Inventory7、Result7、GuardResult14、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続は後続。これは診断値の保存であり、新しい衝突応答、CFD、摩擦、塑性損傷モデルを完成したという意味ではない。
