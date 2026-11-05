# 一tickの荷重を、全体で置き換えて進める

2026-11-05。**NATIVE_FINITE_CONTROLLED_TICK_PUBLIC_PASS：MSVCとGNU13の通常／全依存ASan-UBSan、49CTest／693Node skip0、公開CI全4jobとPagesを受入。SDK／WASM／ゲーム統合は未完。** 現在の正本は[公開main受入記録](../reports/world-static-mesh-flight-controlled-tick-main-public-verification.json)と[GNU受入](../reports/world-static-mesh-flight-controlled-tick-gnu-verification.json)、local段階は[main受入記録](../reports/world-static-mesh-flight-controlled-tick-main-verification.json)、隔離段階は[prototype履歴](../reports/world-static-mesh-flight-controlled-tick-local-verification.json)。この文書は実ソースの契約を説明し、[原著概念図](learn/diagrams/world-static-mesh-flight-controlled-tick.svg)は実測traceではない。[次段計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_NEXT_PLAN.md)と併読できる。

## 1 tick分の総荷重を渡す

ゲームや制御器は、各物理tickで力を変える。拒否されたtickへ同じ入力を再提出したとき、残っている力へ足し重ねると意味が変わる。そこで `TickLoadPacket` は、世界座標の**総force［N］と総torque［N m］を全bodyについて置き換える**。増分、impulse、世界点への力、ローカル座標変換は扱わない。

説明例として、原WorldのFx=3 NにpacketのFx=5 Nを渡したら、私有Worldの入力は**5 Nであり8 Nではない**。外部commitが成立すると、既存advanceと同じくstaticを含む全bodyのforce／torqueは+0へ消費される。拒否したら元の3 Nとその全bitを保持する。packetを次tickへ自動保持しない。

入口は `world_static_mesh_flight_controlled_tick::advance_with_loads(world, meshes, H, settings, progress, packet)`。modeは明示的な `LoadMode::replace_total_world_loads`。全bodyにIDで対応する一行ずつが必要で、行順とbody順は別に保存する。最大8body／16plane／4mesh／総64faceの範囲を広げない。staticのpacket値は各成分が厳密な零（±0可）でなければ拒否する。

`expected_tick` は `Progress.ticks` と整数で一致する必要がある。拒否時はtickが進まないため同tickへretryできる。成功後に古いpacketを再提出するとstaleとして拒否する。これは同じ論理WorldとProgressをcallerが管理するための条件であり、別World、破棄後の再生成、通信再配送を識別するtokenではない。

## 元Worldと私有Worldを混同しない

1. **原本を保存して検査する。** 環境と独立binding、hard countの後で、World全bodyfield／raw plane／gravity、meshのID・revision・全face、H／settings／Progress／packetを所有copyする。元bodyを置換前にvalidateする。不正な元forceを正常なpacketで消して「修復」しない。captureはnone／partial／completeを区別する。
2. **私有copyだけへ荷重を置換する。** `Mapping` にpacket ordinal→body ordinalとIDを残す。これはID解決済prefixであり、存在だけではその行の荷重検査成功を意味しない。元Worldへ仮storeしてundoする方式を使わない。`staged_before` は置換後の私有originで、置換前の `original.world` とは別物である。
3. **実child advanceを一回だけ呼ぶ。** 私有Worldと私有Progress、所有mesh／settingsを使う。`child` はその実返却 `AdvanceReport`。guardを再照会して診断を補填したり、別stepへfallbackしたりしない。childのguard originは荷重5の私有状態へ結び、元荷重3へ付け替えない。
4. **外側の全検査を終える。** 実 `private_after` とchildの全candidateを照合し、荷重消去後の全bodyをvalidateする。原World／Progress／source／packetの不変、元bodyのdestinationと順序を確認し、候補bufferを準備する。
5. **最後に外部へstoreする。** 投げ得る準備を終えた後、既存body格納先とProgressへのnoexcept代入だけを行う。World全体のswap／moveで格納先を入れ替えない。

**`child.committed=true` だけでは外部Worldは進んでいない。** 後続の外側検査で拒否すれば、outer `committed=false`／`advanced_dt=+0`のまま、元World・時計・荷重を保持する。私有成功の診断は残す。この経路の実fault注入や実行試験を、本教材で済ませたとは主張しない。

これは一回の同期callにおける失敗時の全体保持を意図したtransactionである。並行・reentrant・signal経由のWorld／source編集をcallerが排除する前提で、thread atomicityやcrash recoveryではない。成功後の構造編集までbody pointerの寿命を延長する保証もない。

## 診断と進行の意味

`ControlledReport` は `original`、`mappings`、`staged_before`、`private_after`、`private_progress_after`、実 `child` を別に保持する。負零は同値の+0へ丸めず、原値として照合する。optionalの不在やpartial captureを、成功snapshotで埋めない。独立checkerが導く期待状態と、実private状態の観測も別証拠である。`mappings` はID解決済みのprefixであり、その荷重行の有限値・static条件・validateが受理されたことまでは示さない。

`Work` はcopy／validateのattemptとreturn、child attempt／return、candidate検査、destination解決、外部代入などを数える。childの数値known／upper／exactはchild診断のまま保持し、私有成功後のouter拒否でも費用を落とさない。`Storage` は固定candidate／destination bufferだけの観測で、全Reportのheap、実stack、RSS、実時間deadlineの上限ではない。

Hは一tickの要求物理区間、成功時 `advanced_dt` はH。Progressの保存時刻は既存advanceの丸め条件に従うため、保存時刻同士の差を無条件にHと等しいとはしない。新wrapper identityは旧advanceの7-source bindingやschedulerの2-source identityと別で、数値bindingの実artifact監査をsource名だけで代用しない。

## 現在の境界

隔離MSVCの実9command／94群、全88有限full fixture（外部commit22／not_certified29／invalid_input37）を確認した。実private childは64で、そのうちguard59／clock拒否5。独立参照は全88と209数学child（flight102／metric43／planeBox42／sphereBox22）、26自己群／144改変拒否、名称・順序の独立性、実Python `-O` の不正入力拒否を確認した。詳細と原本hashは[正本](../reports/world-static-mesh-flight-controlled-tick-local-verification.json)を参照。先行の[World copy準備](../reports/world-static-mesh-flight-controlled-tick-copy-preparation/run-001/result.json)とは別の受入である。

defaultとDebugは新TUのprofile0拒否を確認した。Debug側もABI互換のRelease coreをimportしており、full Debug coreの受入ではない。非finite4例はraw unit試験だけで、全88の有限JSONや独立full child検査へ混ぜない。初回001はstrict compileがexit0の後、作成中の独立Pythonをcollectorが誤保護して停止した履歴を保持し、fresh002の実行成功と分けた。

正式CMakeでは新2sourceの独立libraryと1test driverを登録し、実Release全49CTest、88有限記録の独立照合、実Debug core／libraryで4拒否を確認した。実commandの4tlog／22TU entryを照合し、旧7-sourceとschedulerのprofile原本は完全byte一致、旧51／scheduler28の全記録もbyte一致。prototypeとの相違は外側ID88個だけで、負零表記を含む残り全raw byteが一致した。構成IDは実artifactの自己認証ではない。既存3Vec3 leafのobject／linked dataflowとstrict compiler commandも再監査したが、全controlled／clock／commit機械証明へ拡張しない。

prototype版7adef01はPages41977643865が成功し、実archive1710file／63,078,400B、実HTTP248件／5,473,168Bを原本と照合し、新教材と既存WebGPU READYの実表示を確認した。続くmain統合版5df636aもEngine41980744764全4job／全stepとPages41980744714が成功した。実tar1752file／64,040,960B、実HTTP251件／5,500,707Bとmanifest全selected1751を固定原本へ照合し、新教材／旧WebGPU READYを確認した。

GNU13.3 x86_64の新専用job127090030063は実36commandが成功した。通常／全依存O1 ASan-UBSanの各94群／finite88と独立26自己／144拒否、実child64／guard59／209数学child、old9群／18時計／full51／14自己85拒否を確認した。core40TU＋controlled1TU＋target別harness19commandの実計装と新共有4TUのWerrorを確認し、実Debug coreと新libraryのprofile0拒否も成功した。同GNU ABIの全記録は2identity族・4exact pathの299leafだけを除き、型／配列順／負零bits／sizeofまで一致した。source／compiler／通常artifactは前後不変。旧48warningの診断multisetも変わらない。CI実receiptとdecoded job logを保存したが、Linuxのephemeral fixture／全artifactを個別downloadしたとはしない。

実allocation／nonreturn／post-child outer-fault注入、全clock・commit・alias・例外の機械証明、一般の全入力保証は未完。新APIのSDK／WASM／ゲーム統合は未完である。外部資料・ライブラリ・同梱画像の追加はない。

この単一tick入口は現schedulerの複数tick／step budgetへ未接続。packet列の消費、frame creditとretry、owner寿命は次の統合である。現WASMは新World bindingをunsupportedとし、既存SDKやsampleへ同じ保証を付けない。一般の接触応答、支持・摩擦、vehicle／fluid／damage、制御器全体の完成は含まない。

実ソース：[公開型](../core/include/pikapika/world_static_mesh_flight_controlled_tick.hpp) · [試作CPP](../core/src/world_static_mesh_flight_controlled_tick.cpp)。教材のHTML／リンク自己検査と、後続のNative数値受入・実browser表示は別gateで記録する。

次の [tick荷重列scheduler](WORLD_STATIC_MESH_FLIGHT_CONTROLLED_SCHEDULER.md)は別の隔離Native21群だけを受入した試作で、単一tickのGNU受入を新scheduler全体へ転用しない。
