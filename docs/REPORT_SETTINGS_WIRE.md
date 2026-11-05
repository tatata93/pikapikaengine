# 設定10型・62memberのNative診断取得

2026-11-06。[12葉型の値取得](REPORT_VALUES_WIRE.md)へ、次の設定10型を追加した。
合計22型・106memberを、実Native member名・原順・型・bitで出力する。
**全Report、C API pump、WASM／ゲーム接続、設定をモデルへ適用するAPIは未実装。**

| 型 | 取得member数 |
|---|---:|
| sphere_triangle::Settings | 6 |
| sphere_triangle_mesh::Settings | 2 |
| sphere_triangle_mesh_held_load::Settings | 7 |
| sphere_triangle_mesh_free_flight_guard::Settings | 2 |
| accelerated_pair_coverage::Settings | 4 |
| accelerated_plane_box_coverage::Settings | 4 |
| accelerated_sphere_box_coverage::Settings | 5 |
| world_static_mesh_flight::Settings | 5 |
| guard::Limits | 20 |
| guard::GuardSettings | 7 |

具体的な全memberは `core/report-values-schema-v1.json` に保持する。
unsignedはU32、size_tはU64、doubleはF64 bitとして区別する。0、最大整数、53bit超のcount、
負零、Infinity、NaNも補正しない。設定の意味や予算の有効性は物理モデルが別に判断する。
診断へ残せることを、当該設定でモデルが動くことと混同しない。

callerがWriterのdocumentを開始し、各`report_values_wire::write`の返却Statusを確認する。
全取得が成功した後にfinishする。生存・不変な入力、排他的なwriter操作、callback内でのbyte copy、
停止／例外／再入の扱いは既存値取得層と同じ。全体byte数や実model memory peakの保証はない。

## 実Native検証

fresh `build/wfdg2` の実MSVC19.51 x64 Release／真Debugで、全4587 byteが一致した。
独立参照は10recordの全131 scalar leafを照合した。内訳はF64 27、U32 29、U64 75。
F64は負零1を含み、Infinityとquiet/signaling NaNも元bitのまま保持した。
実4丸めmodeでbyteとmodeが保持された。全FPU環境やNaN trapを証明したものではない。

全477 callback境界で954停止／例外、4770再入拒否を確認。
独立参照は文法上有効な277単byte改変と、recordの入替／削除／重複3件を拒否した。
既存12型の実テストも同じbuildで再実行し、旧3112 byteと旧実行結果が全一致した。
source review gateを15header＋manifestへ拡大。実CMakeの隔離copyで原本1受理、
変更16／欠落2の18拒否を確認し、製品headerを変更しなかった。

登録CTestはRelease60／Debug58だが、実行は新設定と旧葉型の各2件だけ。旧数値テスト全体の再実行ではない。
旧20数値構成profileを保持し、値取得層は数値coreをbuild／linkしない。
最初のwfdg1は実コード・参照・旧raw比較が成功したが、recipeの集計flagが旧葉型再実行を
正しく表していなかった。原本と訂正理由を保存し、修正後のfresh wfdg2を受入対象にした。
新設定10型の実GNU／ASan-UBSanは次の公開CIで別に受け入れる。
原本は `reports/diagnostic-wire-recipes/`、正式要約は `reports/diagnostic-wire-settings-verification.json`。

前段12葉型の実GNU13.3は通常／真Debug／O1 ASan-UBSanの16commandが成功し、
全3112 byteと96 F64 bit値がNativeと一致した。decoded log 998960 byteと実final JSONを保存し、
実command／source／flagを照合した。child raw／object／schema子logはrunner-local。
Engine42065423071全6jobとPages42065422895の最終成功を確認した。
この前段の受入を、新設定10型や全Reportの成功へ流用しない。

次はinterval端点、Counter／WorkGrant／Retained／MessageOmission、各audit・partition・frontier、
最上位Reportと未実行tailを対応させ、実Report全値の独立比較へ進む。
