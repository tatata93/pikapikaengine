# GNUメモリオペランドとXMM registerの識別修正

2026-11-05。World数値核・候補・閾値・演算順序は変更しない。外部artifact監査器のoperand分類と失敗診断を修正する段階である。

## 実際に観測した失敗

feature `9306e4ca4cd4dc95975a86b5b3248ec7eccbfaac`、Engine run `41873125549`、job `126725337841`。step1–23成功、step24のnormal-artifact-auditがexit1、step25 WASMはskip。前回のELF duplicate function段階を通過したが、inner errorは `ValueError: Uninitialized XMM register: xmmword ptr [rsi]`。

完全なdecoded connector log文字列・失敗childのstdout/stderr・job状態は [原記録](world-static-mesh-flight-guard-public-checks/run-20261105-elf-failure-001/failed-child.json) に保存した。圧縮されたGitHub download原bytesではない。child stdoutは7812B、SHA256 `6cf4df888cce35024cb7583cb83ef5dec4c488f11d81d5a63cf84d548b6f3170`。actual GNU object91208B・exe952464Bとprofileは492の失敗時と同hashで、数値コード生成を変更した結果ではない。

## 修正の境界

既存`Dataflow.vector`がprefixだけでregisterと判定していた。`XMMWORD PTR [...]`は同じ文字列で始まるがメモリoperandなので、`xmm0`〜`xmm15`の完全一致だけをregisterとする。scalar moveの上位lane保持の判定にも同じ修正を適用する。メモリアドレス・入力の初期化・全演算のdataflow条件は既存検査を通す。

未対応命令や誤ったdataflowは引き続き拒否する。GNU leafのdataflow失敗時だけ、object/linkedのbyte対応を検査済みの当該leafから最大128命令を失敗JSONへ添付する。全命令数と切詰め有無、外部target lookupのlocal/nonlocal診断も添える。これは失敗の診断であり、未対応コード生成を許可する処理ではない。

workflowは新operand回帰を事前に実行し、本体ビルド直後に実artifactの早期監査を追加する。後半の正式レシピは別のfresh証拠を取り、3TU Werror・Debug拒否・全依存ASan/UBSan・全51fixture比較を引き続き要求する。

## 実行済みと残件

最終MSVC実機再監査 [run013](world-static-mesh-flight-guard-binding-development/run-013/audit.json) はPASS。既存exe/core.objと5source、compiler/dumpbin、actual command記録は前後不変。三つのVec3 leafと実caller call先・strict/non-LTO契約の監査であり、caller全体のsymbolic証明ではない。ELF synthetic20例のfresh回帰もPASS。新Web buildは既存25509ed4cc1d87e4/54modulesを保持する。

新operandの [有限回帰74例](world-static-mesh-flight-guard-public-checks/run-20261105-xmm-operands-001/result.json) は59正例・15拒否が成功した。同じ合成XMMWORDメモリfixtureをGit HEAD9306の旧auditorは実際に拒否し、修正版は成功するbefore/afterも保存した。GNU/MSVCのsubtract/dot/length、scalar moveの上位lane、未知pointer/register/opcode・演算順序変更の拒否と128命令診断の上限・順序・JSON往復を検査した。instruction bytesはplaceholderの合成fixtureであり、実GNU機械語の再生や数値モデルの独立証明ではない。source/recipeの前後hashは不変。

9306の公開Pages全3jobは成功。配信 [201件4849182B](world-static-mesh-flight-guard-public-checks/run-20261105-elf-public-bytes-001/receipt.json) はGit blobに完全一致した。公開ゲームのREADY・教材図1120×800の実表示を [別記録](world-static-mesh-flight-guard-public-browser-9306e4c/observation.json) へ保存。492の2撃破/boost/pause操作は別cohortの既存互換証拠として保持し、この9306で再出撃したとはしない。背景rAF約1秒を60fps検証としない。

新修正のGNU実機成功・全後段の検査・新revisionの配信は未確認。World guardはNative-onlyのread-only候補照会であり、advance試作の正式受入、一般衝突応答、流体・損傷・専門シミュレータの完成を意味しない。

## CI接続の失敗とdriver訂正

operand修正`c082e6f`のrun `41876723680`/job `126737989932`はstep3で停止した。追加recipeの固定出力先run001とworkflowの`build/ci-xmm-operands`が一致していなかった。ローカル成功だけを確認してCIへ登録したrootの見落としで、実C++ビルド以後はすべてskipした。[完全decoded log](world-static-mesh-flight-guard-public-checks/run-20261105-xmm-ci-failure-001/decoded-job-log.json)を保持する。

recipeはfreshなbuildまたはpublic-checksの子directoryに出力できるよう訂正した。さらに旧auditorは、元run001がGit blobから実取得・保存した49724B/SHA256 aa4787419dea4dd085a9d9fa1e2c3376e142111cca9d18c703c7f1068228b1c9のcommit済みfixtureを読み、そのbyte数とhashを検査する。CIに旧commit履歴を追加fetchする必要はない。旧比較のsourceを編集して作り直さず、固定hashが違えば拒否する。実auditorや数学条件は変更しない。fresh run002の74例は成功した。

[最小exportの実行](world-static-mesh-flight-guard-public-checks/run-20261105-xmm-ci-integration-001/attempt-002/result.json) は10検査/10子commandが成功。必要3fileだけの別source treeで、Git repositoryの探索と旧commitの参照が実際に拒否されることを先に確認し、workflowと同じ `python reports/world-static-mesh-flight-guard-recipes/check-xmm-operands.py --output build/ci-xmm-operands` で74群が成功した。同じ出力先の再使用は全保存treeを変えず拒否、root自身・許可rootそのもの・外への逸脱と、scratch旧fixtureのLF追加は拒否した。元3sourceとrecipeのhashは前後不変。C++実機監査やLinux jobの代用ではない。

export検証driverの最初の試行は、証拠コピーへ長い原pathをさらに入れ子にしてWindowsのpath制約で停止し、子実行は0だった。元sourceは不変、失敗rawをrun001直下へ保持した。証拠コピーをflat fileと元path mappingへ直したdriverで、fresh attempt-002を実行した。XMM recipe/auditorやモデル入力を変更した訂正ではない。
