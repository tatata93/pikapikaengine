# 一tickの荷重を、全体で置き換えて進める

2026-11-05。**PROTOTYPE_ACCEPTANCE_PENDING：独立Native試作のheader／CPPは作成中で、統合・実行・数値受入・公開確認は未完。** この文書は実ソースの契約を説明する。成功件数や実測の進行図ではない。[次段計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_NEXT_PLAN.md)と[原著概念図](learn/diagrams/world-static-mesh-flight-controlled-tick.svg)を併読できる。

## 1 tick分の総荷重を渡す

ゲームや制御器は、各物理tickで力を変える。拒否されたtickへ同じ入力を再提出したとき、残っている力へ足し重ねると意味が変わる。そこで `TickLoadPacket` は、世界座標の**総force［N］と総torque［N m］を全bodyについて置き換える**。増分、impulse、世界点への力、ローカル座標変換は扱わない。

原WorldのFx=3にpacketのFx=5を渡したら、私有Worldの入力は**5であり8ではない**。外部commitが成立すると、既存advanceと同じくstaticを含む全bodyのforce／torqueは+0へ消費される。拒否したら元の3とその全bitを保持する。packetを次tickへ自動保持しない。

入口は `world_static_mesh_flight_controlled_tick::advance_with_loads(world, meshes, H, settings, progress, packet)`。modeは明示的な `LoadMode::replace_total_world_loads`。全bodyにIDで対応する一行ずつが必要で、行順とbody順は別に保存する。最大8body／16plane／4mesh／総64faceの範囲を広げない。staticのpacket値は各成分が厳密な零（±0可）でなければ拒否する。

`expected_tick` は `Progress.ticks` と整数で一致する必要がある。拒否時はtickが進まないため同tickへretryできる。成功後に古いpacketを再提出するとstaleとして拒否する。これは同じ論理WorldとProgressをcallerが管理するための条件であり、別World、破棄後の再生成、通信再配送を識別するtokenではない。

## 元Worldと私有Worldを混同しない

1. **原本を保存して検査する。** 環境と独立binding、hard countの後で、World全bodyfield／raw plane／gravity、meshのID・revision・全face、H／settings／Progress／packetを所有copyする。元bodyを置換前にvalidateする。不正な元forceを正常なpacketで消して「修復」しない。captureはnone／partial／completeを区別する。
2. **私有copyだけへ荷重を置換する。** `Mapping` にpacket ordinal→body ordinalとIDを残す。元Worldへ仮storeしてundoする方式を使わない。`staged_before` は置換後の私有originで、置換前の `original.world` とは別物である。
3. **実child advanceを一回だけ呼ぶ。** 私有Worldと私有Progress、所有mesh／settingsを使う。`child` はその実返却 `AdvanceReport`。guardを再照会して診断を補填したり、別stepへfallbackしたりしない。childのguard originは荷重5の私有状態へ結び、元荷重3へ付け替えない。
4. **外側の全検査を終える。** 実 `private_after` とchildの全candidateを照合し、荷重消去後の全bodyをvalidateする。原World／Progress／source／packetの不変、元bodyのdestinationと順序を確認し、候補bufferを準備する。
5. **最後に外部へstoreする。** 投げ得る準備を終えた後、既存body格納先とProgressへのnoexcept代入だけを行う。World全体のswap／moveで格納先を入れ替えない。

**`child.committed=true` だけでは外部Worldは進んでいない。** 後続の外側検査で拒否すれば、outer `committed=false`／`advanced_dt=+0`のまま、元World・時計・荷重を保持する。私有成功の診断は残す。この経路の実fault注入や実行試験を、本教材で済ませたとは主張しない。

これは一回の同期callにおける失敗時の全体保持を意図したtransactionである。並行・reentrant・signal経由のWorld／source編集をcallerが排除する前提で、thread atomicityやcrash recoveryではない。成功後の構造編集までbody pointerの寿命を延長する保証もない。

## 診断と進行の意味

`ControlledReport` は `original`、`mappings`、`staged_before`、`private_after`、`private_progress_after`、実 `child` を別に保持する。負零は同値の+0へ丸めず、原値として照合する。optionalの不在やpartial captureを、成功snapshotで埋めない。独立checkerが導く期待状態と、実private状態の観測も別証拠である。

`Work` はcopy／validateのattemptとreturn、child attempt／return、candidate検査、destination解決、外部代入などを数える。childの数値known／upper／exactはchild診断のまま保持し、私有成功後のouter拒否でも費用を落とさない。`Storage` は固定candidate／destination bufferだけの観測で、全Reportのheap、実stack、RSS、実時間deadlineの上限ではない。

Hは一tickの要求物理区間、成功時 `advanced_dt` はH。Progressの保存時刻は既存advanceの丸め条件に従うため、保存時刻同士の差を無条件にHと等しいとはしない。新wrapper identityは旧advanceの7-source bindingやschedulerの2-source identityと別で、数値bindingの実artifact監査をsource名だけで代用しない。

## 現在の境界

有限な[World copy準備の記録](../reports/world-static-mesh-flight-controlled-tick-copy-preparation/run-001/result.json)は存在するが、新packet transactionの受入ではない。新試作のNative実build・全fixture・独立参照・GNU・公開表示は未確認で、図も測定traceではない。外部資料・ライブラリ・同梱画像の追加はない。

この単一tick入口は現schedulerの複数tick／step budgetへ未接続。packet列の消費、frame creditとretry、owner寿命は次の統合である。現WASMは新World bindingをunsupportedとし、既存SDKやsampleへ同じ保証を付けない。一般の接触応答、支持・摩擦、vehicle／fluid／damage、制御器全体の完成は含まない。

実ソース：[公開型](../core/include/pikapika/world_static_mesh_flight_controlled_tick.hpp) · [試作CPP](../core/src/world_static_mesh_flight_controlled_tick.cpp)。教材のHTML／リンク自己検査と、後続のNative数値受入・実browser表示は別gateで記録する。
