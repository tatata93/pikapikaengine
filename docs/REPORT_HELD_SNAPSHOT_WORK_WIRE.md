# 保持荷重の全入力と計算記録を取得する

2026-11-06。Snapshotの4項目とheld::Workの11項目を取得する。取得対応は合計43型247項目。
全held Resultと最上位Report、C API pump、この取得機能のJS/WASM/game接続は後続。

Snapshotはinput、horizon、triangles、settingsを元の値のまま専用sinkへ渡す。
力・質量・重力から加速度を作らず、秒のhorizonのF64 bitを保存する。
全三角形の原順、重複、全64bit ID、各頂点の順序とbitを保持し、並べ替えや入力修復を行わない。
入れ子の設定も全項目を取得する。診断値の取得は、設定や形状の物理モデルへの受理とは別。

held::Workはguard::WorkやHeldLedgerとは別の型。取得するsize_tは以下の10項目で、明示的なU64経路を使う。

- mesh_queries, primitive_queries, candidates_examined
- primitive_sqrt_refinements, enclosure_sqrt_refinements
- sqrt_refinements, sqrt_refinements_upper
- mesh_sqrt_limited_rows, enclosure_sqrt_calls, enclosure_sqrt_limited_calls

exactは別のboolとして保存する。上限を実回数へ置換せず、取得時に和を計算しない。
auditの差分とResultの集計は、それぞれ元の記録を取得する将来の経路で区別する。

既存Record::field/array/countだけでconst値を辿る。製品は2TU、新harnessは1TU。
Intervalの構築や数値モデルのlinkは不要。到達値の寿命・不変性とWriterの排他的使用は呼出側の契約。
返却Statusとfinish/completeを確認し、停止した不完全documentを完了として公開しない。

fixtureは空/3面/別順3面のSnapshot3件とWork2件の人工診断。
頂点逆順と面の重複、53bit超と最大U64、負零・非有限値・NaN payloadも保存する。
これらを実モデルの消費量や有効な計算予算と呼ばない。
独立参照は全typed leafと原順を比較し、各scalar byte、key、root recordとtriangle列の入替・削除・重複を拒否する。

Native Release/真Debugの実検証記録は`reports/diagnostic-wire-held-snapshot-work-verification.json`。
旧10fixtureの全byteとrun出力、旧20profile、数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/全3TU O1 ASan-UBSanは公開CIで別に受け入れる。
次はInitialProof/CertifiedLeaf/Witness/EntryWindowの小型証明recordを対応する。


実受入: Release/真Debugの4907byteが一致。169typed leaf（F64 111/負零9、U64 41、U32 15、bool2）、1402停止・例外と1402再入拒否、4丸めmode保持を確認。独立1480byte改変+3root構造+6triangle列構造を拒否。16header+manifest gateは1受理19拒否。登録69/67のうち各11CTestのみ実行、Node693skip0/構文/Webbuild成功。新GNUは別受入。
