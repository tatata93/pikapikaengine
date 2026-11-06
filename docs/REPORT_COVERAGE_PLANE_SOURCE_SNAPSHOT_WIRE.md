# plane boxの元入力とSnapshotを保存する

2026-11-06。`accelerated_plane_box_coverage::Input`全4項目と`Snapshot`全3項目を宣言順に取得する。実装上の取得範囲は70record型408項目＋別Input variant1型。Native、GNU、公開状態の受入は別の実記録で確認する。coverage依存内は15record型62項目が対応し、残る14record型80項目を依存順に進める。

| 型 | 保存する項目 |
| --- | --- |
| Input | sphere、plane、position_error、contact_margin |
| Snapshot | input、horizon、settings |

position_errorは呼出側が宣言した各軸位置誤差Bの元のスカラー、contact_marginは明示的な接触余裕である。それぞれ独立して保存し、Bの推定、Vec3化、半径への加算を行わない。球の元位置・速度・加速度・半径と、平面のraw法線・offsetを既存の取得経路で保存し、法線を正規化しない。Snapshot内のhorizonは元の秒であり、正規化時刻へ置換しない。

保存済みの不正入力や負零・非有限値・NaN payloadも取得対象とする。この診断の保存試験は、実モデルがその入力を受理したことや、位置誤差Bが実軌道を囲むことの証明ではない。取得時にqueryやtube計算を呼ばない。

人工sourceはInput8件とSnapshot8件。元係数の16種類のbinary64 bitを循環させ、各Inputには16個のF64値を与える。Snapshotでは別の元Input、独立したhorizon・時間許容差と、0／UINT64_MAX／2^53+1／2^63の全64bit計数、0／32／2^31／UINT32_MAXの深さを含める。全8,639byteと296typed leaf（F64 272／負零18、U64 16、U32 8）を独立した仕様と比較する。

全scalar／key byteの4,400変更（うちtyped payload2,336byte）に加え、root順序・個数3、全field値交換472、全objectのfield順序128の計5,003変更を検査する。同じbyteとなる交換は0件。名前付きsphere／plane、position_error／contact_margin、horizon／settingsの交換も一般の全field対検査へ含める。

Sourceの全到達先を生存・不変とし、Writerは排他的に使う。返却値、Writer状態、finish、complete、transportの成否をすべて確認する。停止／例外で送信済みprefixを取り消さない。再入の拒否、4丸めmodeと繰り返し取得の全byte一致も調べる。

製品は2data TU、新harnessは1TU。新対象にはInterval構築用TUや数値model libraryを結合しない。旧回帰harnessの試験専用Interval TUとは区別し、実compile／link閉包を監査する。GNUでは新3TUすべてへO1 ASan／UBSanを適用し、通常・真Debugの結果と別に比較する。

正式な有限受入記録は`reports/diagnostic-wire-coverage-plane-source-snapshot-verification.json`。plane boxのEvaluation、全Result、最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。[次はEvaluation全4項目](REPORT_COVERAGE_PLANE_EVALUATION_WIRE_PLAN.md)。
