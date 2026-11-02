# 静的配信・CIの費用条件確認

確認日: 2026-11-03。ユーザーは課金を許可していません。有料プラン、支払方法、予算、larger runner、外部有料ホスティングを追加・変更する権限はありません。

## GitHub公式資料で確認できた対象条件

- [What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages): GitHub FreeおよびGitHub Free for organizationsでは公開リポジトリでPagesを利用可能。HTML/CSS/JavaScriptを公開する静的ホスティングで、常時稼働の対戦サーバーを提供する機能ではない。
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): 公開リポジトリの標準GitHub-hosted runnerは無料と記載。標準runnerのGitHub Pages用途も無料と記載。larger runnerは公開リポジトリでも課金対象。artifact・cache storageには別の利用枠・課金条件があるため、標準runnerの実行料が無料という記述を、任意の保存量まで無料という保証にはしない。
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits): 公開サイト1GB、帯域soft上限100GB/月、ビルドsoft上限10回/時。独自Actionsによる公開は最後のビルド回数制限の対象外。制限に達すると配信停止や制限があり得る。上限超過時に自動で有料プランへ移行してよいという意味ではない。

## このプロジェクトで守る配備境界

既存の公開リポジトリに対する静的Pages配信を候補とし、GitHub提供ドメインを利用する。カスタムドメインの購入、課金設定の変更、クラウド対戦サーバーの契約は行わない。CIを採るなら標準runnerに限定し、不要なcache・長期artifactを作成しない。既定のブランチ配信で成立する場合は、独自の成果物保存を増やさない。

この資料は実際のアカウントの請求状態、既存の使用量、将来の価格改定まで保証するものではありません。公開URLの有効化や配信状態は、その時点のPages設定とデプロイ結果で別に検証します。
