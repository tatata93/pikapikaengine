# 2026-11-04 平面box検査のGNU警告修正

原実装a909323の公開CI run41835425148/job126592955091は、第22工程の新testのWerrorで失敗した。通常44CTest/684Node、67入力の独立包含・16self65拒否、既存のメモリ検査工程までは成功。新plane-boxのWerrorが停止したため、同工程の新ASan/UBSanと最終WASM工程を成功として扱わない。

名前検索helperはcaller所有corpus内のCaseを返すが、検索名が一時std::stringへのconst参照で渡る形に対しGCC13がdangling-reference警告を出した。検索名をstd::string_view値渡しとし、includeと失敗診断文字列の明示変換だけを変更した。警告抑制、数値核、入力、fixture、oracle、判定閾値、compiler flags、SDKの変更はない。

厳密MSVCの5TUを再コンパイルし警告0・74群成功。全67入力の676814B fixtureは原standalone/canonicalとbyte一致、1306全Evaluation・15672端点bits・2496負零を再確認した。旧local-verificationは旧testをhashした履歴として維持し、新testは別のtargeted-postfix-local receiptへ記録する。公開GCCの警告解消・新ASan/UBSan・全工程は再CIで確認するため、現時点では公開受入未完。

元test・計画/実patch・前後13source hash・全4command/raw/acceptanceは accelerated-plane-box-coverage-ci-fix-development/run-001/。初回失敗の全文ログ900113文字とjob/Pages/100byte配信記録を public-ci-development/run-001/、旧9ブラウザcaptureを public-browser-development/run-002/original-captures/ へ保存した。全文ログの最初の一括書込みはtoolの64k上限で実行前に拒否されたため、既知の公開テキストだけを有界なliteralデータとして転送し、長さ・SHA256を照合して保存した。外部ログのコードは実行していない。

## 後続の公開受入（2026-11-04、4b5bf37）

上記の未完表記は初回失敗・修正時点の履歴として残す。修正feature `4b5bf37e5f501088647d735dd45a86ed27d30e5b` のEngine41839162531/job126605836056は全24段成功し、Pages41839160595の3jobも成功した。新3TU Werror、全5TU ASan/UBSan、同一Linux通常/計装fixture byte比較、両67入力の独立7836I/16自己65改変拒否、44CTest/684Node skip0を確認した。旧48GNU診断multisetは不変、新診断0。初回runで未実施だった工程を、初回成功へ書き換えず新runの実結果として受入れた。

[公開集計](accelerated-plane-box-coverage-public-verification.json)と[本体報告](2026-11-04-accelerated-plane-box-coverage.md)へ原receiptと全証拠hashを保存した。99Pages＋完全commit workflow原本1の100件2937015Bは新feature blob一致、図/教材と既存ゲーム互換を実表示確認した。数値核・oracle・物理入力・閾値・SDK・依存・licenseは変更しない。条件付きNative helperの受入であり、World認証・新WASM API・実allocation故障注入の成功ではない。
