# World全組flight guardの公開検証

対象は `d302f5b760307b8a3b023658d251bba3d023fc49` の5-source Native guardである。GNU実命令のparser修正を重ねた後、[Engine run41883086801](https://github.com/tatata93/pikapikaengine/actions/runs/41883086801)の全25工程とPages41882793153の全3jobが成功した。先行失敗の原本は削除・成功への置換をせず保持する。

[正式な公開集約](world-static-mesh-flight-guard-public-verification.json)は `PUBLIC_FINITE_ACCEPTED`。必須25工程に加え、最終API原本にある末尾 `Complete job` も成功しており、原本の全26行をそのまま保持した。必須工程数とAPI返却行数を混同しない。

実GNU13.3.0 x64 SSE2の通常artifactで、3つのVec3 leafのobject／linked命令とcaller target、strict非LTO実compile commandを監査した。caller全体の比較graphをsymbolic証明したとはしない。全46CTest、Node684件、Web build25509ed4cc1d87e4、後段の独立検査とWebAssembly工程が成功した。

guardの後段recipeは新3TUのwarnings-as-errors、別Debug profile0の実拒否、全39core依存TUのO1 ASan／UBSanを実行した。通常／計装版の各51入力はbinding.buildIdだけを除き、全key／array順・scalar型・binary64の負零を含め一致した。通常実行物の機械監査と計装版の数値・メモリー検査は別の証拠である。成功子commandのstdout／stderrは親summaryにbytes／SHAとして保存されているため、取得していない子本文をローカル原本として扱わない。

[実ログの集計002](world-static-mesh-flight-guard-public-checks/run-20261105-gnu-collected-002/result.json)では、両側の独立controlsが12自己試験・51入力・138拒否の正規1行出力とbytes／SHA一致することを確認した。これは実child exit0と保存hash commitmentの照合であり、childのraw本文を別downloadした証拠ではない。job本文に実表示された48警告は、直前Sphere公開受入のfile／line／column／diagnostic Counterと同一。helperが捕捉した非表示stderrを含む全警告数とは呼ばない。

[decoded job原本](world-static-mesh-flight-guard-public-checks/run-20261105-gnu-acceptance-001/decoded-job-log.json)は接続GitHub toolが返したtextをJSON wrapperに保存したもの。GitHubの元圧縮download bytesではない。[最終REST状態](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-final-status-001/runs.json)、[最終job状態](world-static-mesh-flight-guard-public-checks/run-20261105-gnu-acceptance-001/jobs.json)と対応させる。

[配信検査](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-public-bytes-001/receipt.json)では、選択201件4856375B（Pages200件＋完全commitのGitHub workflow原本1件）が対象Git blobと一致した。全repositoryの全fileを配信検査したという意味ではない。[別の完全な実ブラウザー記録](world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-public-ready-002/receipt.json)で `C++ WASM / WEBGPU READY` を確認した。このcommitでの出撃は再実行しておらず、過去492の実2撃破操作を今回の戦闘操作と呼ばない。

収集器の初回はAPIが返す末尾Complete行を固定件数へ混ぜて停止した。必須25行と任意の末尾成功行を分離して25／26両API形式を検査し、fresh driver25件と実集計002が成功した。公開集約の最初の実行は保存AXが差分でREADY本文を含まないため停止し、旧差分・receiptを保持したまま完全AX／別画面002を取得して集約した。[初回GNU集計原本](world-static-mesh-flight-guard-public-checks/run-20261105-gnu-collected-001/result.json)と[集約失敗の実行後メモ](world-static-mesh-flight-guard-public-checks/run-20261105-public-aggregate-history-001/observed-failure.json)を残す。後者は保存stderr原本とは呼ばない。製品の数値条件は変えていない。

この新guardはNativeのread-only照会で、元World／時計／荷重を進めない。新Browser数値API、衝突応答、全target／全入力、自然allocator／child非返却faultの動的注入を認証するものではない。別workingにある7-source advanceはWindows有限検証済みだが、今回の公開受入へ含めない。一般接触・摩擦・流体・材料損傷・専門車両モデル・IK／制御・高精度撮像は継続項目である。
