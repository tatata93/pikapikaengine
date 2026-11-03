# 次の最小受入: ブラウザの照会と転送

2026-11-04 JST。小規模ラボを実装・ローカル受入。[契約](DERIVED_MESH_GPU_PROFILE.md)と[検証記録](../reports/2026-11-04-derived-gpu.md)へ結果を保存した。Node段階計測の次に、小さい成功bufferを現在のWebGPU rendererへ渡す費用を明示操作で測る。ゲーム原本や通常rendererの挙動は変更していない。公開CI/Pagesと実公開操作は別に確定する。

1. 同じ配布SDK、原著runtime/rendererを使用。原本帯4面と、保存可能な非軸の有限合成入力64/512面を用い、原本/入力/設定と全数値出力の同一性を照合する。小規模の受入であり最大容量や実キャラクターの代表性を主張しない。
2. SDK起動、原本FK/LBS、baseline prepare、instrumented prepare、token構造検査/所有copyを分ける。Nodeと異なるブラウザ環境として、全初回/warmup/有限計測、バージョン/OS/解像度/DPR/可視状態を保存する。clockのtimer分解能や観測費用は補正したと扱わない。
3. 新tokenへの全byte uploadを含む同期render呼出しと、その後のqueue完了/validation待ちを区別する。同じtokenのcache再描画は別caseとし、uploadの成功時間へ混ぜない。queue待ちもCPUから見た待時間で、GPU kernelのtimestampやディスプレイ提示時間ではない。pipeline/device初期化も別にする。
4. adapterから実際に取得できた情報だけを保存し、取得不能/分類不能はunknown。request可能なfeature/limitと実使用を区別する。timestamp queryや外部profilerを必須にしない。GPU不在やdevice lostを数値照会の成功/失敗と混同しない。
5. 初回1、warmup1、計測3程度の有界手動runから始め、raw/中央値/p95/最大を全て書き出す。1runずつ実行し、case間に資源を解放する。失敗・途中中止・古い非同期結果は成功統計へ入れず、sourceやnumeric packetは保持する。終端でdisposeし、次のrunで正常復帰を確認する。
6. stub GPUで全bytes/呼出順・古いtokenの退役・同期失敗/validation/queue失敗と時計異常を検査し、実ブラウザで小さい全byte uploadとqueue完了、再描画、正常復帰を確認する。実機の故障を誘発したとはしない。Node407群・既存独立数値参照・SDK53source/7notice/2artifact保持も維持する。

実GPU計測の結果を見てから、batch snapshot読出しや更新頻度の改善を選ぶ。精度条件、面積floor、未確定拒否、原本保存を弱めない。robotへの変形mesh適用は、その後に時間/更新頻度/失敗表示と他チャットの改変統合を固定する別受入である。
