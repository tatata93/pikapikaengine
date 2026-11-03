# 次の比較: 所有snapshotの読出しコピー

2026-11-04 JST。探索比較を実行し、下記結果により本番置換は採用しなかった。小規模ブラウザ計測の512面では、計測ありSDK中央値25.215msのほか、C ABI照会10.405ms、getter1.025ms、JS output copy4.005ms、未分類残差9.750msを個別に観測した。中央値同士の合計は一trialの会計ではなく、残差を純粋なJS費用とはしない。

次は既存`SimulationRuntime.output()`の所有Array copyを最初の比較候補にする。現行はHEAPF64のsubarrayをArray.fromへ渡す。明示したindexで同じviewから同じ長さの通常Arrayへcopyする原著実装と比較し、速いと未測定で断定しない。C++数値核・ABI/交換容量・snapshot commit・公開DTOの型/所有を維持したまま試せる候補である。

1. 旧実装のraw/hashと全出力を凍結し、同じSDKと同一入力で比較する。孤立したcopyと実prepare全体を別に測り、小さい入力・最大record長・複数の面数で全反復を残す。microbenchmarkの改善をSDK全体の改善へ読み替えない。
2. 通常Array・dense長さ・全値bitsとsigned zero/subnormal、元HEAPと返却値の所有分離、後続queryやHEAP view交換後の既存返却値保持を確認する。subarrayの範囲の扱いを意図せず変えない。公開APIへ借用HEAP viewを漏らさない。
3. 全物理/光学/制作のNode回帰、Native/主WASMの固定40/Source11、独立Fraction/36負例、実ブラウザ3例の全DTOと全byte転送を維持する。計測helperの区間/call件数と分類も変えない。
4. 同環境・同ケース・同反復でbefore/afterを保存し、ばらつき・初回/warmup/観測負荷を明示する。効果が確認できなければ実装の置換を採用せず、証拠を残して別候補を選ぶ。数値の品質条件・不確定拒否は弱めない。

ABIのまとめ読みや内部借用viewによるdecodeは後続候補。既存output容量64の変更、DTO型変化、snapshot寿命/HEAP成長を扱う追加設計と検証が必要なため、まず所有コピーの同一契約で比較する。rendererの更新頻度とrobotへの適用は別受入である。

## 探索比較の結果

同じ実SDKの別runtimeで、候補側だけ所有`output`を一時的に差し替え、終了時に復元した。固定初回1・warmup1・計測3の交互順で30prepareと所有検査用5queryを実行。全DTO・135,470反復数値bits、入力不変、通常dense Array・signed zero/subnormal、後続query/HEAP view交換後の旧copy保持が一致した。孤立copyは実record長3/18/26/20と合成capacity64を各10,000回、計500,000copy。64は実Native recordだとはしない。

SDK全体の中央値msは4面0.589→0.567、64面2.396→3.661、512面15.715→16.000。孤立copyが短縮しても全体の改善は一貫しなかったため、本番の`Array.from`は維持した。3sample、own method差替え・JIT/GC・時刻観測・他プロセス負荷がある探索であり、候補の一般的な優劣を断定しない。追加の本番回帰や実ブラウザ候補測定を実行したとはしない。

[14ファイルのbyte一致archive](../reports/derived-copy-archive.json)に唯一の実行と全raw・監査・原著recipeを保持する。再現時はindexの指示どおり3recipeを`build/derived-copy-pilot/`へ復元し、repo rootからlaunch/auditする。reportsのrecipeを直接起動しない。次は[64 F64容量内の複数record読出し](DERIVED_MESH_BATCH_READ_PLAN.md)を設計し、既存getterと全bit等価・失敗prefix・公開DTO所有を受入に固定してから実装を判断する。
