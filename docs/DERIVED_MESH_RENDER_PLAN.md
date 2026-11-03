# 次の最小受入: 成功bufferの小さな3D表示

2026-11-03 UTC。実装・ローカル検証済み、公開未検証。SDK接続の次段。原本・C++変形位置・監査済み派生bufferを分けたまま、既存の原著WebGPU rendererへ接続する。他チャットのrobot/game原本はこの受入で変更しない。

1. 既存の編集mesh経路を保持し、成功した派生メッシュを明示的に受け取る経路を追加する。`Float32Array`のposition3/normal3のinterleaved bytesをそのままuploadし、既存`compileMesh`で法線を再計算しない。null/失敗結果を編集meshへfallbackさせない。公開境界は所有copy・finite/形状/容量/全成功を検査し、第三者が作ったbufferへの数学的認証は主張しない。
2. ラボでは小さい帯のmesh-local座標をidentity modelで表示し、camera・near/far・色/照明の条件を固定して明示する。poseは手動照会で、表示だけを再描画してもC++参照計算を毎frame実行しない。実時間animation性能は別に測定する。
3. 時刻・原本・Scene・予算変更、前段/派生失敗で可視meshとGPU resourceを消す。古い成功bufferの表示を継続しない。失敗後の正常照会では同じinstanceで復帰する。数値監査の成否とGPU作成/validation/device-lostの成否を別表示し、GPU失敗で保存原本を失わない。
4. uploadの全bytes/末尾頂点、描画vertex数、resource更新/破棄、既存編集meshとboxの予算/描画互換をmock GPUで検査する。実ブラウザでも帯の3D表示・時刻変更・実LBS collapseによる消去・復帰とGPU errorを確認し、公開配信bytesを照合する。mockだけで実GPU成功を報告しない。
5. 既存rendererはmodel/VPのFloat32算術とshader内normal正規化を行う。C++の局所CPU法線誤差契約をworld/view/clip/GPU/rasterへ拡張しない。一般の非一様scale/shearのnormal変換、反転/自己交差、被覆/接触/損傷の新しい保証は含めない。

SDK/原本形式を変更せず、外部library/素材は追加しない。Web import mapは通常buildで再生成する。小さいbufferの受入が済んでから、robotへの適用と大規模参照計算の性能・更新頻度を別の節目で扱う。

ローカル最終: Node391/391skip0、新renderer18群とlab追加4群。実WebGPUの15操作、4面/288bytes、表示消去/復帰と視点切替を確認。全体の数値監査や原本は維持する。SDK65・7通知・C++/sampleは不変。詳細は[実装契約](DERIVED_MESH_RENDER.md)とreports/2026-11-04-derived-render.md。次はCPU参照計算とuploadの費用を分けて測り、手動小メッシュの受入を実時間animationやrobot全体へ先取りしない。
