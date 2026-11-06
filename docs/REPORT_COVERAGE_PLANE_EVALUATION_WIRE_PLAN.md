# plane boxのEvaluationを保存する次段

2026-11-06。plane Input／Snapshot後の未実装計画。`accelerated_plane_box_coverage::Evaluation`の全4項目を取得する。

| 宣言順 | 取得formと保持する境界 |
| --- | --- |
| tube_coordinates | array。3軸すべてのIntervalを元のx／y／z順で保存 |
| distance | field。保存済みIntervalの両端 |
| threshold | field。distanceから作り直さない独立したInterval |
| gap | field。保存済みの差Intervalを再減算せず保持 |

getterはtubeやdistance、r+margin、gapを計算せず、既存Intervalのconst取得だけを使う。全3軸と各区間の元の両端・順序を独立仕様で比較する。distanceとthresholdの相殺や、負のgapを0へ丸める修復を加えない。

人工Intervalは既存の正当なpublic constructorだけで作る。whole、point(0)、有限の正負区間、subnormal端点等を含める。既存構築契約の下端零-0／上端+0と、元入力のraw負零保存を混同しない。NaN端点、逆転区間、private byte書換による不正objectは使わない。

試験sourceの構築に必要な既存interval.cppはharness用の追加1TUに限る。製品2data TUに演算は追加しない。全scalar／key byte、全3軸の順序・個数、名前付きIntervalの全対交換を検査する。同値交換は拒否数へ混ぜない。停止・例外・再入、4丸めmode、17header gate、旧全fixture・全出力・20profile・保護原本を確認する。Nativeと実GNUを別受入とし、fixture長やcallback数は実測まで未定とする。

以後はplane Cell／Work、Audit／PartitionLeaf、全Resultへ進む。Evaluation保存だけで実Bの妥当性、whole World認証、物理進行C APIやWASM／ゲーム接続を完了扱いしない。
