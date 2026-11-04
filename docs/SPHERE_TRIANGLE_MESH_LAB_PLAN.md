# 静的三角形集合の手動ラボ: 次の有限受入案

2026-11-04 JST。**設計のみ・UI未実装**。共有SDKの公開受入後、最大64面の原本・全行診断・可能な最近接IDを操作して保存する。既存の単一面ラボと別URLの案 `tools/sphere-triangle-mesh-lab.html` とし、現時点ではリンクを公開機能として案内しない。World/時間発展/ゲーム接触の操作ラボではない。

## 入力と結果

入力は `{sphere:{position,radius},triangles:[{id,vertices}],settings:{maxSurfaces,primitive:{...6設定}}}`。既存strict JSONを用いてsigned zero・duplicate key拒否を維持し、数値を丸めず実 `querySphereTriangleMesh` へ渡す。source JSONの予算案は64KiB/depth10/6000 nodes。65面の交換拒否例を編集可能にする場合も実SDK容量は64と明記し、切り詰めや自動予算変更をしない。input shape/host拒否、Nativeモデル失敗、SDK読込失敗を別に表示する。

結果は集合status/reason、failedIndex/firstFailedRow、全workとnearest区間/全possible IDsを表示。ID一覧が複数でも全て真の同率と宣言せず、「最小になり得る面」と呼ぶ。距離区間の中点や最小IDから一面を確定しない。

全sourceを元順に示すtableを最大64行まで表示し、最後のIDと実query有無を確認できるようにする。preflightでDTO.rowsが空なら、元入力の面は「事前拒否で未照会」と表示し、架空のNative rowを作らない。各実行rowのstatus/reason/workを隠さず、閲覧用の面選択から各面固有のgeometryと最大7候補のprefix/KKTを検査する。閲覧選択はnearestの確定ではない。集合がrow_failureでも、実行済みの個別診断を集合成功へ昇格させない形で見せる。

## 2Dの説明表示

XY/XZ/YZ投影で元三角形を表示し、閲覧対象面に返ったclosestの区間rectangleを描く。64枚の同形面が重なることと、面が消えたことを区別できるID/tableを残す。集合失敗時に個別成功rowの図を表示するなら、面別診断であることと集合nearest不在を併記する。異なる面のclosest/normal/barycentricを一つへ平均しない。

描画は説明用で、world/view/clip/GPUの精度証明ではない。極小区間のinkを見える線幅まで広げる場合は、数値DTOとrectangleの元boundsを変えず表示上の幅だと説明する。巨大/域外座標で有限の投影縮尺を作れなければ「説明図を表示できない」とし、数値query結果を成功/失敗へ書き換えない。描画用の相殺・overflowを、物理モデルの結果として扱わない。

## 原本変更・retry・保存

source変更/preset変更/reset/retry開始で、前のgeometry・候補・図・JSON保存可能状態を即座に消す。新しい入力の照会前に古い候補を残さない。投影/閲覧面の変更は同じ所有結果の表示条件変更で、モデルを再照会したことにしない。

loadの同時呼出しをcoalesceし、同期throw/rejected promise後もretry可能にする。世代をまたぐ遅延成功・失敗とdispose後の復活を拒否し、再読込中に旧runtimeでqueryを走らせない。旧68-export SDKは明示拒否し、JS幾何fallbackを追加しない。

保存形式案はschema1/kind `sphere-triangle-mesh-lab`、完全な正規化input・実result・SDK diagnostics・projection/閲覧面ID。未照会やhost拒否を成功packetとして保存しない。モデル失敗の実resultはnearest:nullのまま保存する。完全な64行/全候補を含む所有copyをstrict serializerで出し、output予算案4MiB/depth20/200000 nodesを検査する。DOM表示を切り詰めても保存dataを省かない。実Blob downloadと表示JSON/所有packetの全数値bitsを確認する。

## 有限の受入

preset候補はsingleton、明確な優劣、共有辺/共有頂点、左右の離れた多重closest、面順反転、区間の重なりで順序未確定、巨大共通offset、実64面全同率、途中/遠方の退化面、候補予算、幅品質、重複ID、空入力、65面host拒否。採用する正確な件数と実結果は実行後に確定する。

試験は原本edit即消去→明示照会、モデル失敗でnearest不在/後続row保持、host拒否→修正/再試行、全64面と最後の7候補、全possible ID、signed zero、入力/結果の独立所有、投影・閲覧変更、download、load/retry/coalescing/generation/disposeを含む。Native48入力・実WASM45modelとの既存SDK照合/独立有理数参照を継承し、新ラボが同じ実SDKを呼ぶことと、UIが成功を捏造しないことを別に検査する。

専用Node/DOM試験、全Node/構文/Web build、実ローカル/公開ブラウザと配信byte照合をそろえ、数値比較や単なるREADYを全操作の成功として報告しない。原著図と教材25記事を維持し、SDK/C++核とゲーム原本はこのUI段階で変更しない。一般応答・流体/損傷・専門シミュレータ・IK/制御・高精度撮像等の未完scopeも維持する。
