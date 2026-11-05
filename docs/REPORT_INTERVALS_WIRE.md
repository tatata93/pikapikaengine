# 区間端点と平方根診断のNative取得

2026-11-06。`interval::Interval`の2端点と`interval::SqrtResult`の3memberを取得へ追加し、
合計32型176項目になった。全Report／C API pump／WASM・ゲーム接続は引き続き未完。

| 実型 | 取得対象 | 出力 |
|---|---|---|
| Interval | lower()／upper()のconst noexcept accessor | lower／upperのF64 bit |
| SqrtResult | value／refinements／refinement_limited | Interval／U32／boolean |

Intervalは既存の不変条件を持つ型。構築時に両端の零を−0／+0へ正規化し、NaN・逆順・
無限の点区間を拒否する。取得時は保持済み端点を読むだけで、区間を再構築・正規化しない。
既存の環境probeや区間演算も呼ばない。無限境界は有限実数集合の境界であり、その要素ではない。
意味と既存数値契約は[区間演算](INTERVAL.md)を参照。

専用取得libraryは既存の2TUだけを維持する。試験targetだけに既存`interval.cpp`を追加し、
実Intervalの構築と4件の実sqrt呼出しを行った。旧数値core libraryのbuild／linkは行わず、
製品getterに数値library依存を足していない。取得試験で既存数学核を変更していない。
callerの入力寿命・排他操作・各返却Status・finishの条件は[値取得](REPORT_VALUES_WIRE.md)と同じ。

fresh `build/wfdin1` の実MSVC19.51 x64 Release／真Debugで全1037 byteが一致。
9個の実Intervalと5個のSqrtResult、合計14recordの38scalarを独立参照が照合した。
F64は28個・負零3個、U32とboolは各5個。微小値・最大有限値・片側／両側の無限境界を含む。
SqrtResultの4件は既存sqrt_enclosureの実返却値、1件は公開memberを組み合わせた取得試験用診断値。
後者の最大refinementsや無限valueを、実sqrt呼出しの成功結果とは呼ばない。

全166 callback境界で332停止／例外、332再入拒否を確認した。
実4丸めmodeでgetterのbyteとmodeが保持された。同時に非RNの3modeでは実区間構築が拒否された。
NaN・逆順・無限の点等の不正構築7件も拒否。これは全FPU状態やtrapの試験ではない。
独立参照は文法上有効な81単byte改変とrecordの入替／削除／重複3件を拒否した。
schema gateへinterval.hppを追加し、16header＋manifestの1受理／19変更欠落拒否を確認。

旧12葉型／10設定型／7ledger型／Workも同じfresh構成で再実行し、
旧3112／4587／3706／3937 byteと全実行結果が一致した。
登録CTestはRelease63／Debug61、実行は新区間と旧4種の各5件のみ。
旧20数値構成profile、製品数学核、owner、SDK、ゲームは保持した。
Node693 skip0・構文・Web build25509ed4cc1d87e4／54modulesも成功。

正式要約は`reports/diagnostic-wire-intervals-verification.json`。
新区間取得のGNUは公開CIで別受入する。既存区間／sqrtアルゴリズムの新たな数学証明ではない。
次は球と三角形のCandidateAudit／Geometryの全固定配列と区間値を取得へ対応させる。


GNU失敗と書式修正: 2026-11-06 初GNU sourcefd07b21のportable127443041849はRelease buildで-Werror=misleading-indentation拒否。試験のfor文と終了処理を同じ行に置いた書式が原因。実4command/原decoded log96910B SHA2778494ba2906a0863f90e3f2d8c11646992235494ecbffe3572deddba5f31eeとFAIL JSON/28source照合を保存。区間fixture/Debug/sanitizerは未実行。loopに明示braceと改行だけを追加し、製品getter/数学核/input/閾値/schemaはfd07b21とbyte不変。fresh wfdin2を新受入対象とし各5CTest/1037byte/全assert出力/旧4fixtureをReleaseとDebugで再実行、初wfdin1と全文一致。旧20profileも不変。新GNU再受入は未完、警告抑制は行わない。 GNU driverが比較する初Native001のfixtureも、修正版002と完全一致している。


公開受入追記: 前段修正版Interval sourcead72d7eを実GNU13.3の16command/通常・真Debug・新2production+1harness+旧Interval TU全O1 ASan-UBSanで受入。全1037byte/38scalar/負零3がNative一致、81+3改変/19schema拒否、28sourceをfeatureblobへ照合。decoded1074973B SHAb67360bf110492493784fa2001aa1fc3438783b07420cf1a7c7903900483b57dと実final JSONを保存。Engine42084630642全6job/Pages42084630993成功、portable実1293秒。初fd07b21のGNU警告拒否は別原本保持。child raw/objectはrunner-local。新幾何取得GNUとは別。 正式記録reports/diagnostic-wire-intervals-gnu-verification.json。
