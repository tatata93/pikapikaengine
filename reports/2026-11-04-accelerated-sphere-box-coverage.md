# 2026-11-04 二つの宣言位置boxによる球接触式coverage

Native専用の単体核をローカル・公開受入した。feature63f5d3dのGNU/Linux CI・ASan/UBSan・Pagesと新しい公開証拠を確認した。旧World/SDK/gameの数値経路は変更していない。

## 条件と返却内容

必須5引数 `Input(firstSphere,secondSphere,firstB,secondB,contactMargin)` を使う。元の両radiusへBを重複加算せず、各宣言位置boxを一度ずつ膨らませる。閉秒区間ごとに両方の全3座標box、delta、生の左結合二乗距離、下端だけ0へ切り詰めた非負区間、全SqrtResult、distance、左結合の元radius/margin閾値、gapを所有する。全15区間にはroot.valueと同bitsのdistanceコピーをそれぞれ数える。

全leafでgap.lower()>0、全時間被覆、返却とroot会計の整合が揃う場合だけcertifiedとする。低精錬でlimitedでも包含と正のgapが有効なら認証できる。全query上界130560は反復予約枠で、実heapやstack使用量ではない。valueが返らなければwrapperの正確なattempt/returnを残し、private rootの実行を推測せず2×refのunknown上界・exact=false・currentと全tailを保持する。

この核は宣言されたBに条件付けられる。actual bodyのB導出、外部std::sqrt/compiler binding、全World pair/candidate、応答・TOI・clock/load更新を認証しない。将来のsource_enforced Native x64 World guard契約は未実装の別段であり、このfeatureと公開receiptへ含めない。

## 実測したローカル受入

| 検査 | 実結果 |
|---|---|
| strict MSVC standalone / CMake | 84専用群・75有限入力、45CTest成功 |
| 分類 | certified 20 / not_certified 21 / invalid 34 |
| actual public value由来 | 955全Evaluation、28650端点bits（6371負零）と1910root診断が再照会一致 |
| 独立包含 | 14325区間、5730座標全域極値±B、955root平方包含、28417 downstream整数RN node-pairs |
| root観測 | 返却955 / 精錬96929 / limited 1（正の認証1） / 全自然Work exact |
| 完全metadata | 583 partition / 163 frontier / 7 current、最大255 audit / 128 leaf / 127 tail |
| 参照controls | 16自己群・89改変拒否、Python -O拒否、label/order非依存 |
| 既存Web | Node684成功・skip0、構文、build cd45c7f1ac2ba5e5 / 54 module / 26entry |
| 原本保持 | 376既存raw、26生成HTML、SDK 92 exports / 67 source-header / 32 TU / runtime91 / 7通知 |

Canonical fixture 894178B SHA256 `83a2402cd2a86491f325b1f2345c48218b364f4d372dde405afdfc87f2cc2174` は初回standaloneとbyte一致。全入力fingerprintは `f4f2b48cb4834d95916b5b1a4e9711c27166b65bbc987454af111212416fefbb`。margin、位置差、dot、sqrt、閾値加算順の5反例、双方B、非自明な安全放物線の分割、全容量/未知tail、subnormal、環境拒否と復帰を実行した。

独立Fractionの6座標検査は**真のquadratic全域極値±各B**であり、座標生成I-AST全nodeのRN選択を列挙したものではない。recorded boxesからdelta・square・左和・閾値・gapを整数binary64 RNで検査し、sqrtは非負端点の平方不等式とRNの単調性・端点固定性で監査する。通常libm sqrtを真値として使わない。全15Iとroot診断のNative再照会は由来の別gateであり、この数学検査の代わりではない。

MSVC x64のsizeof×返却capacity観測はvector 97976B＋inline Result 480B＝**98456B**。初回standaloneの97976Bだけを全保持payloadとしない。Snapshotは既にResult内なので二重加算しない。allocator overhead・一時buffer・stack/RSS・使用heapやpeakの上限ではない。全CTestのreal 174.50sは当該実行の所要時間で、一般性能保証ではない。

## 証拠・試行履歴

[集約原本](accelerated-sphere-box-coverage-local-verification.json) は完成した `checks/run-20261104-summary-002/acceptance.json` のbyteexactコピー。canonical native/regressions/reference/summary各ディレクトリに元command/stdout/stderr/前後hashを保持する。図と教材のローカル表示は5captureとobservationsに保存し、ブラウザで新Native APIを実照会したとはしない。

Native初回standalone・canonical・数学包含は成功。正式集約summary001はstandalone streamのrun-local basenameをROOT直下へ誤解決した収集pathエラーで停止し、原stderrを保持した。解決pathとstream hash監査を訂正したsummary002を今回の正式原本とする。参照run003はchecker成功後、negative suiteの開始前にPython IndentationErrorで止まった。run004/005と親canonicalの成功を別に保持し、製品入力/閾値や数学基準を弱めていない。最初の統合script著述時のSyntaxErrorも実行前のstatic parse失敗で、製品や実統合実行の失敗へ付け替えない。人工unknown nonreturnの整合正例、数学的に有効な広いroot正例、コピー改変拒否は、自然なC++ allocator/value/root故障注入と区別する。

## 調査と配布

今回実読した一次資料は [Microsoft sqrt API](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/sqrt-sqrtf-sqrtl?view=msvc-170) と [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)。前者は戻り値/domainの説明であり、外部stdlib全体の正しいRNやactual linked SQRT命令を証明する資料ではない。後者のcompiler flag説明も現artifactのmachine binding検査を代用しない。将来のintrinsics/実命令調査は今回の実装/受入へ混ぜない。

新外部library/package/完成solver/有料契約/転載素材を追加せず、原著C++・Python stdlib Fractionと既存独自Intervalを使う。本体licenseは未選定のまま。92-export SDK/WASM/glue/build manifest、runtime91memberと既存7通知は保持した。一般接触応答・流体・材料損傷・専門シミュレータ・IK制御・高精度撮像の完成ではない。

## 公開受入（feature 63f5d3d）

[公開集計](accelerated-sphere-box-coverage-public-verification.json)は、`checks/run-20261104-public-summary-001/acceptance.json` のbyteそのままを保存する。Engine [41845414301](https://github.com/tatata93/pikapikaengine/actions/runs/41845414301) /job126627509578の全25段、Pages [41845413100](https://github.com/tatata93/pikapikaengine/actions/runs/41845413100) の3jobが成功した。新3TUのWerror、全5TUのASan/UBSan、同一Linuxの通常/計装fixture byte比較、両方の75入力・14325Iの独立数学包含、16自己/89改変拒否が成功。45CTest/684Node skip0・旧回帰も成功し、既存48GNU診断のfile/line/column/message multisetは同一、新診断0である。全返却EvaluationのNative bit由来と独立数学は別gateを維持する。新WASM APIやMSVC/GNU全DTOの厳密bit parityを実施したとはしない。

公開113件3287969Bは完全feature blobに一致した。内訳は112PagesとGitHub完全commit workflow原本1件。Web build cd45c7f1ac2ba5e5/54module/26entry、SDK92exports/67source-header/32TU/WASM800982B/glue61661B/runtime91/7通知、既存376raw/26生成HTMLと新7sourceは保持。新原著図と教材の実表示、既存ゲーム2撃破・boost・pause・21照会すべてchecked/validated/completed・3常駐mesh/error0を9captureで確認した。新Native helperをブラウザで数値照会した証拠ではなく、ゲーム互換だけを示す。

配信取得bytes001は113件の各bodyとfeature blobを比較した後、取得ドライバー末尾に残った99Pages定数のassertで停止した。元script9580B・正確なpatch・correction.jsonと失敗command/stdout/stderrを保持し、読取専用ドライバーの2定数だけを112へ訂正した。bytes002で全113件を最初から再取得し成功を受入れた。最初の取得を完成receipt扱いせず、feature/数値核/oracle/fixture/閾値/CIを変更しない。

公開UI収集のrun001では、role buttonによるAX summaryのcollapseに一致するDOM要素がなくclick前に停止し、続いて親の無いhistory directoryのmkdirがENOENTとなった。既に保存した実game/cover JSONは変更せず、親ディレクトリを作成しfresh AXのexpanded summary116で復旧した。`public-browser-development/run-001/` のnoteとexpanded AXをそのまま保持する。これらはUI証拠収集の失敗であり、数値・製品失敗や実fault注入の成功と数えない。

既読Microsoft sqrt API/GCC資料の範囲を引き継ぎ、新外部資料実読・依存・完成solver・転載素材・有料service・本体license選択はない。宣言B条件、外部std::sqrt/compiler binding未確認、actual World B/全pair/candidate/応答が後続gateであることは公開後も変わらない。将来World guardの未追跡source・383原本準備・native contractはこのfeature/receiptに含めない。
