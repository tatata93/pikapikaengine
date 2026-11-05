# 計算量・保持量・省略情報7型のNative診断取得

2026-11-06。既存の値・設定取得へ7型43memberを追加した。合計29型149member。
全て実`world_static_mesh_flight_guard.hpp`のconst値から取得する。
全Report、C API pump、WASM／ゲーム接続は引き続き未実装。

| 型 | member数 | 保持する意味 |
|---|---:|---|
| Counter | 3 | known／upper／exactを別々に出す |
| HeldLedger | 9 | 各処理のCounterを省略せず出す |
| Retained | 13 | 要求された保持capacityの会計 |
| WorkGrant | 9 | 処理ごとの割当量 |
| Reservation | 3 | retained／granted／chargedを区別 |
| Grant | 2 | 保持量と処理割当の組 |
| MessageOmission | 4 | 全field数／非空数／byte数／省略flag |

`size_t`はU64、boolはboolean。0、最大整数、2^53超を変換・補正しない。
Counter.exactは計数量の既知性であり、物理的成功の認証ではない。
累積grantedは正確な返金後にlimitsを超え得るため、chargedへ置き換えない。
Retainedは要求capacityであり、現在のvectorサイズや実heap高水位ではない。
MessageOmission.fieldsには空文字も含む。省略された本文を再構成しない。

共通の専用sink／Record経路を使い、新しい確保・演算・World照会を行わない。
callerは入力の生存・不変性と排他的なWriter操作を保ち、各返却Statusを確認してからfinishする。
停止・例外後の途中byte列を完成DTOとして扱わない。詳細は[値取得](REPORT_VALUES_WIRE.md)。

fresh `build/wfdl1` の実MSVC19.51 x64 Release／真Debugで全3706 byteが一致。
独立参照は7recordの全109 scalar leaf（U64 98、bool 11）を照合した。
全401 callback境界の802停止／例外、2807再入拒否、実4丸めmode保持を確認した。
文法上有効な232単byte改変とrecord入替／削除／重複3件を独立参照が拒否。
15header＋manifestの実CMake隔離copyは1受理／18変更欠落拒否。
既存12葉型と10設定型も実再実行し、旧3112／4587 byteと実行結果が完全一致した。

登録CTestはRelease61／Debug59、実行は新ledger・旧設定・旧葉型の各3件だけ。
数値coreはbuild／linkせず、旧20構成profileを全byte保持した。
Node693 skip0、構文検査、Web build25509ed4cc1d87e4／54modulesが成功。
最初のintegration検査はWindows標準libraryも拒否する条件で停止した。原記録を残し、
許容する10標準libraryと2取得libraryを明示して訂正し、fresh002で受け入れた。
製品コードをその失敗に合わせて変更していない。

前段の設定10型はsource457be0aの実GNU13.3通常／真Debug／全新TUのO1 ASan-UBSanを別受入。
16command、4587 byte全文、277＋3改変拒否、18schema拒否を実ログから照合した。
Engine42070956777の全6jobとPages42070956819が成功。child raw／objectはrunner-local。
新ledgerのGNU受入は次のCIで別に確定する。

正式記録は`reports/diagnostic-wire-ledgers-verification.json`。
次はguard::Work、interval端点と全audit／partition／frontier、全Report・未実行tailを対応させる。
この取得層は流体・材料損傷・専門車両モデルの追加ではない。
