# CTest出力を利用する検証時間の調査

2026-11-07。現在進行中のPairRecord受入は変更しない。これは完了済みの別ビルド`build/wfdgch2`を使った3テストだけの実験であり、旧45テスト全体への採用や、検証項目の削除を意味しない。

実Child Native記録のcommand秒数を合算すると、CTest群849.093秒とは別に、旧harnessの`--run`出力比較749.980秒がある。後者の多くはCTestで実行した同じbinaryの再実行である。この値は検証処理の実測経過時間であり、ゲーム性能・FPS・将来の短縮時間の実測ではない。

インストール済みCTestの`--help`で`-V`のテスト詳細出力を確認し、primitive、明示拒否、12葉型の3件を一つの実CTest呼出で実行した。実Start／Passed／100%の全3件と、各CTest番号で出力されたJSONを照合。保存済みの直接実行結果と、全JSON objectおよび改行を除くJSON本文が一致した。別ビルドの3実binaryの前後hashも一致。原command／stdout／stderr／recipeと結果は`reports/diagnostic-wire-validation/run-20261106-ctest-extraction-001/`に保存する。

45件向けの実験recipe `reports/diagnostic-wire-recipes/verify-guard-pair-record-ctest-extraction.py`は準備しただけで、PairRecordの完了・commitを実行前に要求する。厳密な実行ファイルパスの照合を含むparserについては、上記実3テストの全出力と、JSON欠落・重複・未知のテスト番号・status変更・誤った実行ファイル・Passed欠落・集計不一致の7変更を実際に比較し、全て拒否した。原本と変更logは`run-20261106-ctest-parser-controls-001/`へ保存。このparser検査は新たなCppテスト実行や45件全体の受入ではない。

この方式ではCTestが付けたprefixと改行を除去して比較するため、「直接実行のstdout全raw byteと同一」とは呼ばない。今回の実験は余分・重複・欠落JSON、テスト名／番号／commandの不一致と実テスト失敗を拒否する。前後不変を確認したのは3実binaryであり、全product sourceのbefore／after監査はこの実験の対象ではない。

全旧テストの出力形式、複数構成、長い出力と失敗時の挙動への検証は未実施。将来採用するときも、全product source監査とprotocol fixtureの全raw byte比較、CTestの登録数・実実行数・実command・全元assertionの照合を別途保持する。今のPairRecordのsource-before／after、選択45CTest、全旧fixture／実行出力、20profile、394保護原本の検査は従来通り最後まで実行する。後続で全範囲を別受入できた場合だけ、重複した直接実行の削減を検討する。新しい外部package・依存・有料操作・権限変更はない。
