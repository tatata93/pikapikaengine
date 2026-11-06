# 配信待機と既存ジョブ上限の調整

2026-11-07。Pagesの配信処理に`timeout: '660000'`を指定し、処理の期限を既定10分から11分へ変更する。ジョブ全体の12分上限、ビルド8分上限、公開リポジトリ限定、runner、権限、HTTPS／domain、artifact保持1日、384MiB配信上限、16MiB manifest上限、全配信前archive監査は変更しない。

使用中の固定commitの[公式action設定](https://raw.githubusercontent.com/actions/deploy-pages/368f82528645a54fb793d4d04e342629a3f51346/action.yml)で、`timeout`はミリ秒の任意入力、既定値は600000と確認した。新しいactionや外部依存を追加せず、既存の固定SHAを維持する。

c66の初回と同制限の一度だけの再試行、続く20ccの初回は、実logで配信待機の後に同期へ進み、10分の処理期限で取り消された。c66の二回の失敗は正式public-failureと実HTTP8fdの不一致原本に保存済み。20ccの失敗も別記録に保持する。これは物理モデルやNativeの検証失敗ではなく、配信ジョブの実観測である。

既存12分ジョブ内の待機余裕を1分増やす調整であり、配信成功を保証する変更ではない。全体の時間上限やstorage・byte予算、権限を拡大せず、archive監査や既存Pagesテストを省略しない。変更後は新しいsourceの実配信、HTTP manifestと実UIを別途確認し、成功するまで公開成功と報告しない。古い失敗を上書きせず、source c66の第三再実行も行わない。

代案の同一sourceの追加再試行や、既存sample／素材／証拠の削除は採らない。新しい有料service、契約、package、素材、license選定、投稿、メール操作はない。設定と説明は原著、engineのlicenseは引き続き未選定。
