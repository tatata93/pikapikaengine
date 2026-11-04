# scheduler全診断fixtureの次段契約

2026-11-05作成時の契約。**この計画のserializer／全nested checkerは後に局所有限受入した。現在の結果は[実装と検査](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_TRANSACTION.md)を参照。以下は実装前に固定した履歴である。** 再開位置はsource301efa3の隔離試作。 selected credit参照の1382観測・14拒否を、全診断や物理の独立検査完了へ読み替えない。

## 使える原著writerと変更境界

`tests/world_static_mesh_flight_advance_fixture_support.hpp` は既に `world_advance_fixture::report_json(ostream&, const AdvanceReport&)` を公開している。実体は `tests/world_static_mesh_flight_advance_fixtures.cpp:393` で、全Report・実owned guard・outer message・work／storageを保存し、legacy enum-index writerの前にrangeを検査する。同cpp末尾にはstandalone mainがある。

最小の共有化は、このtest-only mainだけを明示library-only macroで除外できるようにする案である。新probeは既存writer本体と7つのguard/child serializerをリンクし、`report_json` を実返却Reportへ呼ぶ。mainをrenameしたり、.cppをincludeしてprivate関数へ侵入したり、別guard queryを生成したりしない。macroなしの旧51serializerをfresh短pathでbuildし、保存raw2979456Bとのbyte一致・旧独立参照／85拒否を改めて確認する。旧buildを再構成しない。共有writer変更は旧51の証拠を無効にせず、当時の原本を保持して新実行を別記録にする。

## 原本と実観測を捏造しない

新fixtureはpump前／後の実World全field・Progress・source／settings、scheduler snapshot、全PumpReportと実AdvanceReport配列、実外部pointer安定観測を所有する。全入力、elapsed bits（非finiteもbits文字列）、binding ID、admission／queue／upper budget／未実行slot／拒否理由を保存する。各入力一pump、current Worldから実内部advanceだけを呼び、出力用の再query・事前に作ったcandidate適用をしない。全JSONをprivate bufferへ完成させ、有限数値・UTF8・enum・構文とstream状態を検査してからstdoutへ出す。

**現APIでは、外側から各内部tick直後のWorldを直接snapshotできない。** hookを足していない以上、candidateから作ったWorldAfterを「実測中間World」として保存してはいけない。実外部観測はpump前／後に限定する。中間については各実owned guardのorigin snapshot（捕捉したNative内部原本）と候補のchain対応を検査し、最後は実外部WorldAfterと照合する。clock先行拒否にはguardを捏造しない。pointer観測もouter前後だけで、各内部tick時の生address独立観測とは呼ばない。

## 独立検査の分け方

既存 `scripts/verify-world-static-mesh-flight-advance.py` のdocument入口は固定51入力・initialProgress=.125/17を要求するため、新pump結果をそこへ偽装しない。`verify_fixture` も実前後World／pointer観測を要求する。構成した中間Worldをその欄へ入れてcheckerを通したことを、実測全transactionの独立受入として報告しない。

新checkerは、元の整数RN helperとguardの数学参照を用いて、(1) elapsed／全queue／時刻／prefix会計、(2) 実Report／実owned guardの全fieldとwork／unknown upper、(3) captured-originのchainと候補、(4) 実pump前後World／source／Progress／pointer観測、を別gateへ分ける。再利用のため既存checkerから純粋なReport検査を抽出するなら、旧51全部と85拒否の回帰を要求する。一般入力・全命令・allocator注入の証明には昇格しない。

最低限の実シナリオは閾値境界／cap4と8／最初guard拒否とretry0／一成功後のplane拒否／荷重初回のみ／入力未受理cap／clock上限である。空Worldのrate列はselected credit原本を保持し、全nested最初のfixtureへ同じ1382件を無条件に複製しない。最終入力件数・実child数・bytes／実行時間は実行後に確定する。各serializerとcheckerの上限を先に設定し、超過・途中失敗rawを保持して別fresh出力で再開する。

## 隔離して進める

新短buildを用い、native／wfa2／wfat1／wfa3／wfs1／wfs2は再構成・再buildしない。schedulerの2source／別ID、既存7-source／SDKは保持する。必要な新mainと共有writerだけの実strict／WX／非LTO command、importしたlibrary／serializer objectのhashを記録する。全nested有限受入の後にGNU／全依存sanitizer／本体CMakeへ進む。現在のEngine CI成功を、未登録schedulerのGNU実行成功へ読み替えない。
