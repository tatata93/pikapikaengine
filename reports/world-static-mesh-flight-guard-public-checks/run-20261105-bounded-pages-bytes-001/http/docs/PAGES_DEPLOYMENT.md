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

`.github/workflows/pages.yml` は無料のubuntu-24.04で固定commitを取得し、Web build・専用9試験・選択bundleを実行する。公式upload-pages-artifact v4（7b1f4a764d45c48632c6b24a0339c27f5614fb0b）には `build/pages-site` のみを渡しretention1日とする。deploy-pages v5（368f82528645a54fb793d4d04e342629a3f51346）は既存github-pages環境を使い、pages:write／id-token:writeはdeploy jobだけへ限定する。[公式custom workflow要件](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)に従う。

設定変更recipe `reports/pages-deployment/pages-config.py` は既存Git credentialをメモリ内だけで利用する。GETで現在siteを保存し、workflowを先にpushしたことを確認した後、`--enable-workflow` でbody `{"build_type":"workflow"}` だけをPUTする。資格情報の表示／保存／新規発行、domain／HTTPS／公開URL変更やsite作成をしない。実変更は実行後のreceiptで確認する。`verify-manifest.py` は実公開manifestと全selected blobの宣言hash／全Git inventoryを固定commitへ照合するが、全ファイルのHTTP byte検証とは呼ばない。実HTTPの選定cohort検査は別recipeを用いる。
