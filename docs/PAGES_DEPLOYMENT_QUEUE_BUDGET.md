# Pagesの実効10分上限と配信記録の訂正

2026-11-07。以前、`timeout: '660000'`でactionの期限を11分へ延ばせると説明したが、これは誤りだった。action.ymlの入力定義だけを確認し、実装の上限を見落としていた。固定した[公式実装](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/dist/index.js#L149922)は最大600000msを定義し、入力値をその上限へ丸める。実ログにも警告があり、660000msを指定したa95／cd6／7715の実効上限が11分になったという証拠にはならない。

今回は入力を対応範囲の`600000`へ戻す。実効上限は10分のままで、ジョブ全体12分、build8分、public限定、runner、権限、HTTPS／domain、保持1日、384MiB archive／16MiB manifest、全archive監査は維持する。更なる上限緩和や同sourceの再試行は行わない。

公式bundleは読み取りで取得し、contents APIのGit blob SHA1 `57024fc2da852a9f3b75f71d25784149cb1ec65b`と一致した。全5855429byteのSHA256は`63fd34d89cd23d8848618a019f978f2225880a38afe2328e6e7d72f20fc44e89`。bundleの実行・インストール・全体再配布はしていない。必要な設定抜粋と取得記録だけを保存した。最初の抜粋helperは定数参照を含まない範囲を要求して失敗し、旧recipeとtool観測を保持して別fresh002で取得した。

旧queue-budget-verification.jsonと各public-failure、旧guide原本を改変せず、訂正票で「入力値がログに現れた」と「実効期限を延長できた」を区別する。cd6は全14Engine CI／実archive成功、実効10分でsyncing_files timeout失敗。7715はNative95型／GNUと実archive成功、deploy128069596791が開始直後に配信側の失敗を返した。後者をtimeoutと読み替えない。HTTP／実UIと全Engine CIは、それぞれ別に確認する。

既存の無料・公開Pages配信以外のservice、契約、package、素材、権限は追加しない。原著の訂正文と検証コードであり、engineのlicenseは未選定のまま。設定の訂正を配信成功とは呼ばない。
