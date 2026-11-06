# plane boxの全Resultを保存する

2026-11-06。`accelerated_plane_box_coverage::Result`全12項目を宣言順に取得する原著実装。取得範囲は76record型439項目＋別Input variant1型。coverage依存内21record型93項目、残り8record型49項目。Native・GNU・公開の受入は各実記録で分ける。

| 保存する項目 | 保持する意味 |
| --- | --- |
| status、reason | 元のraw unsigned enum |
| snapshot、snapshot_validated | 元Input・秒・全設定または欠損と、独立した保存flag |
| failed_input、partition_complete | 元の失敗位置または欠損と、独立した保存flag |
| audits、partition、frontier | 全監査・全区画・未照会の残りを原順・重複・全末尾まで保存 |
| current、work、message | 停止中Cellまたは欠損、元の試行／返却数、全メッセージbyte |

取得時に再query、零埋め、位置の再採番、flagや理由の再判定をしない。Snapshotの位置誤差Bとmargin、元の点係数・raw法線を保持する。人工的な不整合値を実数値モデルの生成物とは呼ばない。planeのSnapshotにはInput variantがなく、値なしvariant境界を新設しない。

3つのoptionalと2つのboolの全32組合せを人工32Resultで検査する。初回early試験では全38519byte SHA8cf7a63cf73441f476d1df4cf3c5544cda04c1d3caee47e427e1c314684ca7e4がRelease／Debugと独立仕様で一致した。全1152typed leaf、626F64／負零46、optional存在119／欠損125を含む。最後のResultに元の全20Audit／12PartitionLeafを保持し、ほかのResultで空・1個・2個・順序違い・重複・残りの区間を検査する。

メッセージは空・埋込NUL・非UTF8・全256byteと末尾NULを含む合計437byteを保存する。最後の257byte本文で256byte callback境界も跨ぐ。6015callback、12030停止・例外、12030再入、4丸めmodeをearly試験で確認した。初回単体試験とは別fresh wfdcprl2で全Nativeを検査する。GNUと公開は別受入。

変更検査は有効文法を保ったscalar／key byte、全field値・順序、optional／enum、配列順序・個数、本文長を対象にする。同値の交換は拒否件数と分離する。8分割の各担当範囲と合計を照合し、取りこぼしと二重計数を検査する。全Nativeでは別fresh buildを使い、旧32CTestと新1CTestを別々に実行して計33件を検査する。元の数値モデルの試験とは区別する。

製品2data TU、harness1TU、正当なInterval構築用の既存実装1TUを区別する。製品に数値model libraryを追加しない。Writerと全参照先は送信中に排他的かつ不変とし、停止・例外では送信済みprefixを保持する。返却status・sticky status・finish・完全なtransportを確認する。

実Native受入は`reports/diagnostic-wire-coverage-plane-result-verification.json`以降を参照。sphere boxの8型、World guardの呼出record、最上位World Report、C API pump、WASM／ゲーム接続は後続。[次はsphere boxの元入力とSnapshot](REPORT_COVERAGE_SPHERE_SOURCE_SNAPSHOT_WIRE_PLAN.md)。
