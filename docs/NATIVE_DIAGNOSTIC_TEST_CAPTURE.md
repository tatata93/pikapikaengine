# CTest出力を利用する検証時間の調査

2026-11-07。現在進行中のPairRecord受入は変更しない。初期調査は完了済みの別ビルド`build/wfdgch2`の3テスト。続いてwfdgpr3の実45件×両構成と14破損log拒否を別受入し、prepare3型のfresh46件へ適用した。検証対象やraw fixture比較を削除しない。

実Child Native記録のcommand秒数を合算すると、CTest群849.093秒とは別に、旧harnessの`--run`出力比較749.980秒がある。後者の多くはCTestで実行した同じbinaryの再実行である。この値は検証処理の実測経過時間であり、ゲーム性能・FPS・将来の短縮時間の実測ではない。

インストール済みCTestの`--help`で`-V`のテスト詳細出力を確認し、primitive、明示拒否、12葉型の3件を一つの実CTest呼出で実行した。実Start／Passed／100%の全3件と、各CTest番号で出力されたJSONを照合。保存済みの直接実行結果と、全JSON objectおよび改行を除くJSON本文が一致した。別ビルドの3実binaryの前後hashも一致。原command／stdout／stderr／recipeと結果は`reports/diagnostic-wire-validation/run-20261106-ctest-extraction-001/`に保存する。

45件向けの実験recipe `reports/diagnostic-wire-recipes/verify-guard-pair-record-ctest-extraction.py`はPairRecordの完了・commit後に実行し、Release／真Debugの全45件と14破損log拒否を受入した。結果のsourceは20cc、全90binaryと参照原本の前後不変を確認。厳密な実行ファイルパスの照合を含むparserについては、上記実3テストの全出力と、JSON欠落・重複・未知のテスト番号・status変更・誤った実行ファイル・Passed欠落・集計不一致の7変更を実際に比較し、全て拒否した。原本と変更logは`run-20261106-ctest-parser-controls-001/`へ保存。この初期parser検査自体は新たなCppテスト実行ではない。続く全45件の実行原本は`run-20261106-pair-record-ctest-extraction-001/`へ分離した。

この方式ではCTestが付けたprefixと改行を除去して比較するため、「直接実行のstdout全raw byteと同一」とは呼ばない。今回の実験は余分・重複・欠落JSON、テスト名／番号／commandの不一致と実テスト失敗を拒否する。前後不変を確認したのは3実binaryであり、全product sourceのbefore／after監査はこの実験の対象ではない。

実45件の両構成と破損logの有限拒否は受入済み。任意の将来の出力形式や全ての実子process障害を検証したという意味ではない。将来採用するときも、全product source監査とprotocol fixtureの全raw byte比較、CTestの登録数・実実行数・実command・全元assertionの照合を別途保持する。PairRecordの従来45CTest／全旧直接runとfixture／20profile／394保護原本は最後まで従来通り受入した。次のprepare3型は新方式のfresh46CTestを全実行し、全assertion JSON本文（改行を除く）・全raw fixture・20profile・397保護原本を受入。直接runの再実行は省いたが、テストそのものと比較対象は保持する。新しい外部package・依存・有料操作・権限変更はない。
