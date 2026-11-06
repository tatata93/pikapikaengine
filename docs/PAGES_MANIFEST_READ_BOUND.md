# 公開manifestの有限読取上限

2026-11-06。Input取得fda5f3adの実公開manifestは8,273,846byteで、従来8MiB上限まで114,762byteだった。検証原本をGitに保持しながら次のSnapshotへ進めるため、検証用readerの固定上限を16MiBへ更新した。

`reports/pages-deployment/verify-manifest.py` の `read_manifest_bytes` は、16MiB＋1byteだけを1回要求し、実取得が16MiBを超えたら拒否する。無制限のreadや可変の上限引数は導入しない。超過した本文をJSONとして解釈しない。

境界試験は、仮想responseの0、8MiB、8MiB＋1、16MiB−1、16MiB、16MiB＋1、2^60byteの7ケース。最初の5ケースはbyte上限だけを通り、後の2ケースは超過拒否となる。空本文や不正JSONを文書として受理したという意味ではない。2^60byteは仮想の長さであり、その量を確保・HTTP転送した試験ではない。

単体試験では要求サイズが常に固定上限＋1の1回であること、上限を差し戻すと新しい境界を通せないことを検査する。また追加した定数とhelperだけを戻したsourceが従来sourceと完全一致することを比較し、従来の全Git blob・schema・cohort・公開先・配布容量の検査を保持する。

実HTTPでも同じfda5f3adを新readerで再取得した。従来と同じ8,273,846byte、SHA256 `5df47fe017b458a877f995e6f088be80ad56977ea92e7047336ca88aaf283f46` となり、全2,278宣言file/62,290,020byteを固定Git treeへ照合した。これは宣言内容とGit blobの全照合であり、全payloadのHTTP転送検査ではない。

配布bundleの固定384MiB上限は保持する。今回の変更は検証用readerだけで、エンジン・ゲーム・数値binding・wire形式を変更しない。原記録は `reports/pages-deployment/run-20261106-manifest-read-bound-001/verification.json` と `run-20261106-report-coverage-input-variant-16m-001/receipt.json`。


2026-11-06 Snapshot機能215d799dのPages42158750400は配布archiveのmanifest読取に旧8MiB上限が残り、upload後の検査で失敗しdeployはskip。HTTP readerだけの先行16MiB更新ではarchive側を通らないことが実CIで判明した。verify-archive.pyも固定16MiBへ1定数だけ更新し、他のpath/entry/size/全payload SHA/hidden/zero tail/384MiB budgetのsource完全保持を確認。実read_manifestの仮想7境界（通過5/拒否2）、実8MiB+1と16MiB JSON入りtar、上限+1 parser拒否、既存archive正常6/異常57検査が成功。実CI失敗logと公開旧source不一致を原記録として保存し、未公開を成功とは報告しない。新package/権限/有料操作なし。Cell/Workの実装検査は継続中でこの公開修正commitに含めない。
