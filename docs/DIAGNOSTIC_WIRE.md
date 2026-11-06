# 診断の型とbitを保持するNative出力 v1

2026-11-06。物理進行の全Report取得に向けた、独立したprimitive出力層。
実装は `core/include/pikapika/diagnostic_wire.hpp` と `core/src/diagnostic_wire.cpp`。
**全Reportのfield対応、C API pump、WASM export、ゲーム接続はまだない。**

## 出力と所有寿命

`Writer(Sink, user)` はcallbackへ最大256 byteずつ渡す。callback内で必要なbyteをcopyする。
Writerは最大64階層の固定配列だけを保持し、動的確保、World再照会、数値計算、
標準出力の全体差替えを行わない。sink自身は確保や外部I/Oを行ってよい。
有効で不変の入力spanと、呼出し終了まで生存するwriter/userが必要。排他的な単一caller用で、
別threadからの同時操作、callbackからのwriter破棄、不正pointerの検出は契約外。

callbackのfalseは`sink_stopped`、例外は`sink_exception`となり、以後出力を停止する。
sinkは拒否したchunkも既に消費しているかもしれない。送ったbyteや物理状態のrollbackを意味しない。
`finish()==ok`、`status()==ok`、`complete()==true`を確認し、transportも完了したdocumentだけを公開する。
不正操作はstickyなエラー。finish後の不正操作でも、それ以前に送ったbyteは取り消されない。
callbackから同じwriterへ再入すると、その呼出しだけ`reentrant`で拒否し、外側は継続できる。
別writerへの出力は独立。これはthread atomicityの保証ではない。

## byte契約

先頭はASCII `PPDR`、U32 version=1、U32 nonzero schema ID。整数payloadはlittle endian。
root値は一つ。その後にfinish tag一つとEOFが必要。chunk境界は文法上の境界ではない。
schemaはfield名・enumの意味・variantの対応を別途固定するための識別子で、
現時点では全Report schemaの宣言や自動field網羅検査ではない。

| Tag | 値 | Payload |
|---|---|---|
| 0 | finish | なし。root終了後のみ |
| 1 / 2 | null / boolean | なし / U8 0か1 |
| 3 / 4 / 5 | U32 / U64 / I64 | 4 / 8 / 8 byte。I64は2の補数表現 |
| 6 | F64 | IEEE binary64のbitをU64で保持。丸め・decimal化・finite分類なし |
| 7 | bytes | U64 byte長、そのままのbyte列 |
| 8 | enum ordinal | U32。未知値を修復しない |
| 9 / 10 | object / array開始 | なし。14で終了 |
| 11 / 12 | optional absent / present開始 | なし。presentには値一つと14が必要 |
| 13 | variant開始 | U32 ordinal、値一つ、14 |
| 14 | container終了 | なし |
| 15 | object key | U64 byte長、そのままのbyte列、続いて値一つ |

2026-11-06のReport field schemaで明示したsignedEnumFieldsでは、enum tag8のU32 payloadを
int32値のmodulo2^32として保存する。復元はpayloadが2^31未満ならその値、それ以外はpayload−2^32。
汎用decoderは引き続きU32 payloadを返し、値の大きさだけから符号を推測しない。
Reportのint32基底専用private経路で扱い、primitiveのtag/versionや従来のunsigned enum出力は変更しない。
詳細は[自由飛行Result](REPORT_FLIGHT_RESULT_WIRE.md)。

objectはkeyと値の原順を保持し、arrayは値の原順を保持する。keyの重複はここでは禁止しない。
文字列はbyte列で、NULや不正UTF-8も改変しない。UIへ表示する際の文字コード判定は別層。
absentとnull、enumとU32、boolと整数を区別する。NaN payload、Infinity、負零、subnormalを
F64のbitとして扱う。これはそれらを物理モデルの有効入力として受理するという意味ではない。

## 実行した有限検証

fresh `build/wfdw2` の正式CMake targetをMSVC19.51 x64のRelease/真Debugで実行。
両1148 byteの全出力は一致。16個のF64 bit patternには±0、subnormal、有限極値、±Infinity、
符号・payloadの異なるquiet/signaling NaNを含む。full64整数、2^53超、I64最小・最大、
enum最大、optional/variant、原順、769 byteのchunk分割とopaque keyを確認した。
全66 callback境界で停止と例外の132件、17操作ずつの1122再入拒否、
15不正文法、64階層の境界、別writerを挟む出力を確認。

独立Python decoderは1148個の全切詰めと14不正文法、合計1162件を拒否し、
期待した全typed値・key・順序・bitを照合した。実Python `-O`も拒否する。
最初の`wfdw1`は両実行・参照成功後、recipeのWindowsPathをJSON化する最後の処理で失敗した。
失敗receiptを保存し、修正後のfresh `wfdw2`を受入対象にした。
登録CTestはRelease58/Debug56だが、ローカルで実行したのは各新1件。旧coreをbuild/linkしていない。
既存305 source/assetのraw不変を確認。実GNU13.3は通常／真Debug／O1 ASan-UBSanの14commandと全1148 byte一致を別途受入。
返却decoded log 983135 byteとsource／実commandを照合し、child raw/objectはrunner-localと区別した。
新しい[12葉型の取得](REPORT_VALUES_WIRE.md)や全ReportのGNU受入ではない。
allocator fault、全FPU環境・NaN trap、性能、全Report field網羅の証明ではない。

原本とcommandは `reports/diagnostic-wire-recipes/`、正式要約は
`reports/diagnostic-wire-verification.json`。fixtureは可逆hexで保存し、元byte数とSHA256も記録する。
次はこの形式へ所有Reportを全field対応させ、旧finite writerの全値と独立復号比較する。
既存writerや数値bindingを変更して部分出力を全Reportに見せない。


固定char配列の取得: BindingInfo.build_idは65要素をopaque bytes tagで保存し、末尾と途中NULも含める。sourceのconst char spanからstd::as_bytesで参照し、strlen・文字コード修復・hex正規化を行わない。manifest.fixedBytesFieldsでsource型/長さ/順序を固定する。設定identityであり実object hashの自己測定ではない。
