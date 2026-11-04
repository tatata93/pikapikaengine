# Git原本と軽量Pages配信を分ける

2026-11-05。Gitには全raw証拠を保持し、Pagesには実行・教材・公開要約に必要なファイルだけを送る。[公式制限](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)を当日実読し、公開siteの1GB上限と10分を超えるdeployのtimeoutを確認した。source301efa3のdeployはupdating_pagesで600000ms後に停止したが、この観測だけで容量エラーが原因だったとは断定しない。軽量bundleのローカル生成成功も、実deploy成功とは別のgateである。

```sh
npm run build
node --test tests/pages.test.mjs
node scripts/build-pages.mjs
```

builderはfresh `build/pages-site/` と、その直下の `pages-manifest.json` を生成する。指定する場合は `--output build/<fresh-directory>`、より小さい枠は `--budget-bytes INTEGER`。既定かつ最大の枠は384MiB（402653184B）、manifestも含む。既存outputは空でも拒否し、自動削除・上書き・容量超過後の別規則fallbackをしない。workflow／Pages APIの切替と実deployは別作業である。

builder自身はbuild-webを実行せず、runtime・WASM・import map・build hash・生成HTMLを一切書き換えない。前段の通常Web buildで決まった**現在のworking tree bytes**をcopyする。tracked inventoryの取得にGitを使い、未追跡ファイルは含めない。新規公開ファイルはstage／commitしてから正式bundleを作る。過去receiptのhashへ現在のdocsを戻さない。

## 明示的な選択規則

| 選択 | 理由 |
|---|---|
| `.git`／`.github`以外の全tracked regular非reportsファイル | runtime、assets、source、教材・原著図をまとめて保持する。未追跡privateファイルは拾わない。 |
| `reports/**/*.md` | 過去・現在の説明と検証報告を保持する。 |
| `reports/`直下の全JSON | canonical summary／verificationを取りこぼさないsuperset。nested巨大fixtureとは区別する。 |
| `reports/<directory>/<file>.html` を直接持つdirectoryと、その全兄弟・子孫 | 実Web report入口と必要なmodule／data／画像を保持する。HTTP保存鏡像やrecipe内source copyを入口と誤認しない。 |
| advance受入の217件receiptにあるPages216path | 既存公開cohortを確実に含める。残り1件はGitHub配信のworkflow原本で、Pages側へ移さない。 |
| 実HTML／module／CSSからのliteral依存closure | HTML URL、import map、import／export、dynamic import、fetch、新URL、CSS url／importの参照先を追加する。存在しないtracked依存は拒否する。 |

cohort入力は `reports/world-static-mesh-flight-advance-public-checks/run-20261105-bytes-001/receipt.json`。既存216pathの**coverageと現在bytes**を保つ規則であり、全ファイルが古いfeatureのbytesのままだという主張ではない。新しいJSON/Markdownやsourceの正当な更新を禁止しない。

既存の実Web report入口はentry／trajectory／flight各 `*-js-browser/index.html` の3箇所だった。`reports/**/http/`、recipe内の過去HTML／MJS copy、巨大nested log／fixtureをすべてWeb入口とみなす規則は採らない。必要な明示依存・cohortは除外より優先する。各選択ファイルには理由を複数保存する。

静的抽出は任意JavaScript実行の証明ではない。通常runtime treeと宣言したreport Web directoryを丸ごと保持し、現在のliteral参照を検査する。HTML教材の非実行コード例をimportとして読まない。唯一の明示endpoint例外は、既存float-labのHTTP localhostかつcapture=1限定 `/__capture/float` POST。静的assetではなく、公開時にこの条件で無効になる既存機能である。source内の既知guardが変わったらbuilderも再レビューが必要となる。未知endpointを広く無視する規則はない。

## 安全性とmanifest

trackedのstage0／通常file modeだけを認め、Git symlink・conflict・case衝突、path traversal、Windows device名、symlink／junction祖先を拒否する。outputは実repoのbuild配下の新directoryに限定する。全選択ファイルはsourceとcopyのSHA256／bytesを比較し、copy後にsourceを再読して一致を確認する。最後にGit inventoryとHEADが変わっていないことを確認し、成功manifestを最後に書く。途中失敗のpartial directoryを成功artifactとして扱わない。敵対的な並行filesystem変更を許すsandboxやlockの代用ではなく、呼出し中はsource／outputを変更しない。

manifestは全selectedのpath／bytes／SHA256／Git blob／選択理由、全excludedのpath／bytes／Git blob／理由、cohort情報、runtime参照、Markdown linkへの影響を持つ。選択bytes＋manifest bytesが予算内かをcopy前に検査する。非選択rawをGitから削除する処理はない。

## 既存reportリンクへの具体的な影響

実行入口と教材の必要assetは保持する。一方、Pages上のMarkdown／canonical JSONに記されたnested raw evidenceの相対pathは、bundleへ選択されなければPagesでは取得できなくなる。本文やJSONを改変して成功linkに見せず、原本GitHubの同commitへ辿る。manifestの `linkImpact` は、選択済みMarkdownから除外tracked fileへ向く具体的な各リンクとGitHub代替URLを列挙する。directory参照、JSON内の任意path、動的文字列の全リンクを網羅した一覧ではない。`excluded` は全除外pathを列挙する。

初回の実inventoryでは11003tracked・1008329843Bに対し、1530file／54238120Bを選択、9473file／954091723BをGit原本側だけに残した。manifest3464837Bを含むbundleは57702957B（約55MiB）で、384MiB枠内。旧Pages216pathを保持し、Markdownの除外raw参照332件を記録した。これは新3sourceが未追跡の時点のローカル観測であり、正式stage後の件数・bytesは新manifestを正本とする。公開成功・timeout解消をまだ示さない。

専用試験では選択／literal依存／byte一致、未追跡除外、fresh output／予算超過、symlink mode／merge conflict／junction、危険path／case衝突、cohort欠落・不成功を検査する。初回はWindows case aliasの先行拒否による期待診断不一致を保持し、全name／modeを先に検査して9群成功を確認した。実bundleの先行2試行は教材コード例の誤検出とlocalhost endpointを検出してcopy前に停止し、規則を明示修正して再生成した。最終実行と公開確認は親の正式記録へ保存する。

## 専用workflowの切替

`.github/workflows/pages.yml` は無料のubuntu-24.04で固定commitを取得し、Web build・専用9試験・選択bundleを実行する。修正版は公式upload-pages-artifact **v3（56afc609e74202658d3ffba0e8f6dda462b719fa）**へ `build/pages-site` のみを渡し、retention1日とする。deploy-pages v5（368f82528645a54fb793d4d04e342629a3f51346）は既存github-pages環境を使い、pages:write／id-token:writeはdeploy jobだけへ限定する。[公式custom workflow要件](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)に従う。

設定変更recipe `reports/pages-deployment/pages-config.py` は既存Git credentialをメモリ内だけで利用する。GETで現在siteを保存し、workflowを先にpushしたことを確認した後、`--enable-workflow` でbody `{"build_type":"workflow"}` だけをPUTする。資格情報の表示／保存／新規発行、domain／HTTPS／公開URL変更やsite作成をしない。実変更は実行後のreceiptで確認する。`verify-manifest.py` は実公開manifestと全selected blobの宣言hash／全Git inventoryを固定commitへ照合するが、全ファイルのHTTP byte検証とは呼ばない。実HTTPの選定cohort検査は別recipeを用いる。

## 初回公開の失敗とarchiveの修正

source0861b597027e0169549eaa519816e044c1423c02のcustom run41904803522は初回successだったが、旧legacy run41904801605も重なり、公開manifestの404を観測した。旧run完了後、既存artifactを使うcustom deploy jobだけを再実行した。connectorでの再実行は403、既存Git credentialをメモリ内で使う経路は201となり、その後manifestの実HTTP200を取得した。これは競合した公開順序の収集履歴であり、先の600000ms timeoutの原因証明ではない。

[manifest原本](../reports/pages-deployment/run-20261105-public-manifest-002/receipt.json)では、1545宣言sourceのhashと11138件のGit inventoryを固定sourceへ照合した。選択54396530B＋manifest3502399B＝bundle57898929B、除外9593file／976295492B、旧216pathを保持した。**これはmanifest宣言の検査成功であり、実archiveへの全収録や全fileの実HTTP取得成功ではない。**

続く[237件の実HTTP原本](../reports/world-static-mesh-flight-guard-public-checks/run-20261105-bounded-pages-bytes-001/receipt.json)は235件成功／2件失敗で、全体FAILのまま保存した。`.gitattributes` は404、`reports/accelerated-plane-box-coverage-primary-sources.json` は503だった。503をhidden除外や恒久欠落と断定せず、別の実再取得で確認する。

初版のupload-pages-artifact **v4（7b1f4a764d45c48632c6b24a0339c27f5614fb0b）は履歴**とする。[固定v4の公式action.yml](https://raw.githubusercontent.com/actions/upload-pages-artifact/7b1f4a764d45c48632c6b24a0339c27f5614fb0b/action.yml)を実読すると、Linux archiveにhidden全般を落とす追加excludeがある。実runのtar commandにもこの規則が出ており、builderが選択・copyした `.gitattributes` がtarから落ちた。builderのbyte比較だけを配信全体の保証と解釈したのが検証境界の不足だった。

[固定v3の公式action.yml](https://raw.githubusercontent.com/actions/upload-pages-artifact/56afc609e74202658d3ffba0e8f6dda462b719fa/action.yml)も当日実読し、archive除外は `.git`／`.github` で、上記hidden全般の追加除外がないことを確認した。v3へ戻すだけでHTTP成功を推定せず、**actionが実際に作ったtar**を次のcheckerへ渡す。outer actionのSHA固定を、内部で参照するupload-artifactの推移依存まで全SHA固定したという意味にはしない。

## 選択・実tar・公開HTTPの三つのgate

1. builderは現在source→選択manifestとcopy bytesを照合する。
2. archive checkerはactionが実生成した非圧縮tarの全file集合を、selected全file＋`pages-manifest.json`自身のrawへsize／SHAで照合する。省略・余分・重複・逸脱path・link・nonregular・不正trailerを拒否する契約で、384MiB payload等の読取上限を持つ。
3. 公開後にmanifest→固定Git treeを照合し、選定cohortの**実HTTP bytes**を別に検査する。tarに存在することも、任意の瞬間のHTTP200・cache・公開順序の保証ではない。

新checkerのCLIは次のとおり。作業中の試験・実tar検査は結果確定後に記録する。

```sh
python3 tests/pages_archive_tests.py --output FRESH
python3 reports/pages-deployment/verify-archive.py "$RUNNER_TEMP/artifact.tar" build/pages-site/pages-manifest.json
```

**修正版の公開完全受入は未完。** 元237件FAILとraw HTTP、旧manifest404、両deployの履歴を保持し、再試行が成功しても元記録を上書きしない。loader・WASM・素材・本体licenseを変える修正ではなく、外部actionコードをengineへ転載しない。

2026-11-05局所追記: 実tar検査器は正常6／拒否57のtiny controlsに成功し、hidden欠落は実Python -O子processでもexit1・Missing selected filesで拒否した。別のWindows Python GNU-format tarでは旧local bundle1545選択＋manifestの1546file、57899621Bの全payload、hidden3を確認。tar59238400B／SHAab0785280d2e6c7a04d6dcc4872d7de1e6f298a528fae1aa720e9106f91c4c7e。既存bundle前後hashは不変。これは公式Linux action実tarの受入や修正版HTTP成功とは別である。正本は[局所receipt](../reports/pages-archive-local-verification.json)と[凍結記録](../reports/pages-deployment/archive-development/run004/freeze.json)。先行503の単独再取得はHTTP200／1000BがGit原本へ一致したが、元237件runはFAILのまま保持する。
