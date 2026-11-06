# prepare Result全7項目を保存する次段

2026-11-07。Snapshot6／Inventory7の取得受入後、`world_static_mesh_flight::Result`を追加する計画。実装・実行成功の証拠ではない。

宣言順はstatus、reason、failure、capture、snapshot、inventory、messageの7項目。Status／Reason／CaptureStateはそれぞれの元の型付きordinalを保存する。failure、snapshot、inventoryは欠損と存在を区別し、statusやcaptureからgetter側で書き換えない。messageは元のbyte列を保存し、UTF8やC文字列への変換で埋め込みNUL・非UTF8を失わない。

実prepareはreadyのときだけ完全なinventoryを持つ。一方、complete snapshotでも入力がINVALIDなことがあり、allocation failureではコピー済みvector prefixがpartial snapshotに残り得る。人工保存fixtureでは、この実行契約から外れた元の組合せも補正せず保持する。「不整合な人工値を保存できる」と「prepareが正しい結果を返す」を混同しない。

既存のfailure、Snapshot、Inventoryの独立仕様を使い、実再帰oracle閉包の全pathをsource-before／afterへ固定する。各status／reason／capture、未知ordinal、optionalの存在・欠損と空vector、元の全nested値・元順・重複、空／NUL／非UTF8 messageを有限に検査する。scalar／key byte、field交換、object順序、array順序・個数、optional wrapper、enum tag、message長の異なる有効文法変更は全て比較する。同値交換は別計数とし、byte数・件数・分割数は実測後に固定する。

各callback停止／例外、sink再入、4丸めmode、旧47＋新1のRelease／真Debug実CTest、全assertion JSON本文（改行を除く）と全raw fixture、20profile、保護原本、17header gateとWebbuildを保持する。schema2親のcanonical JSONTextと実CTest原logをbaselineに使い、存在しない単独run出力を作らない。新targetは原則製品2data TU＋harness1で、数値model libraryを結合しない。

受入後の予定は96record型561項目＋別Input／Child variant2。Native、GNU通常・真Debug・全TU O1 ASan-UBSan、Pages・実HTTP・実UIは別受入。次はGuardResult14、最上位World Report／C API pump／今回取得のWASM・ゲーム接続。一般接触・摩擦・CFD・塑性損傷・精密光学の完成とは呼ばない。
