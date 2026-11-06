# pair coverageのInputをvariant境界ごと保存する

2026-11-06。Native/GNU有限受入済み。`accelerated_pair_coverage::Input` のconst getterを追加し、選択中のchildとordinalを別のvariant境界として保存する。

| 元の型 | v1 variant ordinal | 保存するchild |
| --- | --- | --- |
| SpherePair | 0 | first, secondを元の順で保存 |
| SpherePlane | 1 | sphere, planeを元の係数で保存 |
| 値なし | 出力しない | reject_invalid_valueで拒否 |

既存の62record型369項目と、新しいvariant1型を分けて数える。manifestも`mappedTypes`の架空recordへ混ぜず、`mappedVariants`でordinalとchild型を明示する。v1 tag、Status ordinal、17headerの宣言、既存record取得の形式は保持する。

getterはconst `get_if` で選択中の値を取得し、variant開始・childの取得・endの実returned Statusを順に確認する。子を再構成せず、入力(A,B)/(B,A)を並べ替えず、法線正規化・半径膨張・F/m計算・再queryをしない。

値なしをvariant_nposの切詰め、ordinal0、null、既定値へ変換しない。新しいbyteやcallbackを発生させず拒否する。同じWriterのcallbackからの再入はtransient reentrantで外側を妨げず、既存の失敗は保持する。送信済みprefixや完了済みdocumentを取り消す機能ではない。

Sourceと到達するchildは生存・不変、Writerは排他的に使う。不正pointer、破壊されたprivate領域、並行変更の検知はこのgetterの契約に含めない。

4人工rootを0/0/1/1で保存し、全68F64（負零6）、全key、順序、ordinalを独立仕様と比較する。scalar/key各byte、ordinal各byte、variant→present、wrapper除去、child交換、元入力の名前付き値交換、root順・個数の変更を検出する。停止・例外・再入と4丸めmodeを実行する。

正当な投げる変換引数で実Inputが値なしになるかは各targetで別に測る。旧値を保持したtargetでは元ordinalと全byteの保持を確認し、値なし分岐を実行したとは報告しない。NativeとGNUの比較は共通の正常取得結果を照合し、到達性の件数はtargetごとに保存する。

製品2data TUとharness1TUのみ。Interval実装や数値model libraryを新harnessへ結合しない。最上位Report・物理進行C API・WASM／ゲームへの取得接続は後続。次は[Snapshot](REPORT_COVERAGE_SNAPSHOT_WIRE_PLAN.md)の元input/horizon/settings。


実Native有限受入: Release/真Debug1899byte/全68F64/負零6、336callback/672停止例外/672正常再入/4丸めmode。実MSVC値なし4case×6状態の24拒否は追加0byte/0callback、1344値なし再入はtransient拒否。675独立改変拒否、17header gate1受理20拒否、旧primitive/control/全21record fixture/20profile/351保護原本不変、登録81/79中各24CTest、Node693skip0/構文/Webbuild成功。GNU getterは後述の別記録で受入。


実GNU追加受入: GNU13.3 x86_64-linux-gnuの通常/真Debug/全新3TU O1 ASan-UBSanの全1899byteと正常取得の共通assertionがNative一致。675改変と17header gate1受理20拒否も成功。実targetは元alternativeを4ケースとも保持し、値なし0なので、GNU値なし分岐の実行を主張しない。返却log/全final JSON/28sourceを機能commit fda5f3adに照合した別記録を保存。全7jobの最終状態と全Report・物理進行APIは後続。
