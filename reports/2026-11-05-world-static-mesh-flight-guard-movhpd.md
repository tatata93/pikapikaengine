# GNU MOVHPD loadの限定監査対応

2026-11-05。製品の数式・丸め順序・C++核とSDKは変更しない。外部監査器へ、実GNU13が使用したlegacy MOVHPD memory64 loadの記号的bit移動だけを追加する。

## 実際の停止と入力

commit462742c、Engine41877686157/job126741545025。step3でWeb build25509ed4cc1d87e4/54modulesとELF20/XMM74回帰は成功した。step4のC++build後、early artifact auditは `movhpd xmm1,QWORD PTR [rsp+0x10]` により拒否した。CTest以後のGNU受入は成功していない。

[失敗payload](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-failure-001/audit.json) はVec3 subtractの実11命令・codeHexを保持する。この位置はobject/linked byte対応確認の後、dataflow証明の失敗位置であり、丸め条件を免除した成功ではない。old GNU object91208B/exe952464Bは前回と同hash。linked ELFには392local function entries、16同名衝突があり、最初の8例にはbasic_string assignのisra/cold cloneがある。これにより以前のELF衝突の具体例も観測できた。

## 対応と実行範囲

[実読したIntel MOVHPD節](world-static-mesh-flight-guard-movhpd-primary-source.json) のlegacy SSE2 loadだけを扱う。初期化済みXMMのlow64を保持し、指定m64をhigh64へ移す。演算・丸めは追加しない。未初期化先、未知pointer、幅不一致、VEX/3operand/store/register-register等は引き続き拒否する。

隔離候補では保存11recordを実際に再生し、既存73・歴史比較2・新MOVHPD20（保持2/拒否18）が成功した。初回は検査driverがpatch行番号を厳密に要求して停止したため、その失敗原本を保存し、unique exact context・offset+5・content fuzz0のfresh retryで実行した。親patchや製品sourceを結果へ合わせて変更していない。

その後、[現auditorへのproduction回帰](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-production-001/result.json) も保存11record1・既存73・歴史2・新20が全成功した。record再生は実object/linkファイルの全GNU監査再実行でも、binary実行でもない。歴史比較2件を現auditorの検査件数へ混ぜない。

実旧5-source MSVC19.51 artifact再監査 [run014](world-static-mesh-flight-guard-binding-development/run-014/audit.json) も成功。監査スクリプトの原本はこのcommitでstageする5-source auditorと完全同byteになる。既存三つのVec3 leaf・実caller call先とstrict/non-LTO実commandの監査であり、caller全体の形式証明ではない。

CI production検査は固定保存baselineのhashを確認して読み、古いGit履歴のfetchに依存しない。新しい全GNU監査・3TU Werror・Debug拒否・全依存ASan/UBSan・51fixture比較・WASM/Pages/配信の受入は、次の実runで別に確定する。

[CIの最小7file export](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-ci-001/result.json) は公開予定の5-source auditorを実PRODUCTION位置へ置き、Git履歴の探索が実際に拒否される状態で、workflowと同じproduction CLIの全96件（保存record1/現検査73/歴史2/新20）が成功した。出力先再使用とbaseline copyの改変は拒否し、元159入力と成功済みtreeは不変。ローカル7-source版を使った上記production回帰と、公開予定5-source版のこのexportを区別する。実instructionを再生成/実行した証拠ではない。

## 別のローカル統合

7-sourceのNative advance統合は別working差分に保持する。実CMake Release全target/47CTest/新9群/18clock独立参照/Debug新旧拒否と有限Web互換は成功したが、今回のguard修正の公開sourceへ混ぜない。新しい全clock/commit機械証明・GNU・公開SDK・World応答の完成とはしない。既存ゲームと他チャットの原本を保持する。

## 後続の実公開受入

機能d302f5bのEngine41883086801全25工程とPages41882793153全3jobが成功した。MOVHPDを含む通常GNU13.3 artifact監査と後段数値／Werror／Debug／ASan-UBSan／51fixture／WASM、選択201配信原本と実READYは[公開検証記録](2026-11-05-world-static-mesh-flight-guard-public.md)へ分けて保存した。上記の未確認という記述は各実行時点の状態であり、失敗原本を成功へ書換えていない。7-source advanceの公開受入は依然として別の未完項目である。
