# pair coverage Inputのvariant境界を保存する後続段

2026-11-06。未実装計画。record2型の取得と明示拒否APIの有限受入後に対応する。
Inputはstd::variant<SpherePair,SpherePlane>で、active alternativeをSpherePair=0/SpherePlane=1の既存variant tagへ保存する。
record風の架空fieldを追加せず、manifestにmappedVariantsの別境界として型・ordinal・child型を明示する。
既存62record型369項目とvariant1型を別々に数え、最上位Reportの取得済みとは呼ばない。

const get_ifで元のactive childを取得し、ordinalに対応したgetterへ渡す。子の実returned Statusを確認してからendする。
値なしはreject_invalid_valueでbyteなしに拒否し、variant_nposをU32へ切り詰めたり、alternative0/null/既定値へ修復したりしない。
同じwriterへの再入では最初のgateによるtransient reentrantを保持し、外側をpoisonしない。
Source値は生存・不変、Writerは排他的という前提を維持する。並行変更や不正pointerの検知は追加しない。

4人工rootはPair(A,B)/(B,A)とPlane(A,Plane A)/(B,Plane B)。全68F64/負零6にvariant tag/ordinalを加えて独立比較する。
ordinal各byte、variant→別tag、child入れ替え、rootの順序/個数、全callback停止/例外/再入、4丸めmodeを検証する。
17header+manifest gateと旧primitive/全record fixture/全run出力/20profile、数値核/owner/SDK/sampleを維持する。
製品2data TU+harness1TUで数値model library/Interval TUを新harnessへ結合しない。新GNU O1 ASan-UBSanは別受入。

実Inputの値なし到達性は、正当なemplaceへの投げる変換引数などを各実targetで試す。
先行のcopy/moveがnothrowでも、標準の許容と特定実装の挙動を混同しない。private byteを壊さない。
各targetが旧alternativeを保持した場合はその事実を保存し、値なし分岐を実行済みと報告しない。
明示拒否API単体の実検証、2active alternativeの取得、実Input値なし分岐の到達性を分けて受入する。
その後Snapshot、Cell/Work、Evaluation、Audit/Partition、全Resultへ進む。
