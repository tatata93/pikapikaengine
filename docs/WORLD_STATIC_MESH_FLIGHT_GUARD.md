# 全Worldの非接触候補を調べるNative照会

2026-11-05。MSVC x64のローカル検証とGNU13 x64の公開CIを受入。機能d302f5bのEngine全25工程・Pages全3jobが成功し、選択201配信原本と実READYを確認した。[公開検証記録](../reports/2026-11-05-world-static-mesh-flight-guard-public.md)を参照する。Native C++の照会であり、新Browser数値APIは追加していない。詳細な入力域と失敗条件は[Native契約](WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md)、既存の原本準備は[prepare](WORLD_STATIC_MESH_PREPARATION.md)を参照する。

元のWorldから各物体を自由伝播させたとき、指定した全時間で必要な組がすべて非接触かを調べる。対象は球proxyの動的物体、静的球・平面・有限三角形mesh。衝撃応答を実行する機能ではなく、元World・時計・保持荷重を変えない。静的同士の組は除外数を記録し、非接触を証明した組へ混ぜない。

## 全組の証拠と候補

原本のID・順序・revision・負零を所有し、必要な組を最初に確定する。動的bodyのID順に最小mesh IDとの照会から誤差Bと終点候補を得る。その後、残りのmesh照会と、保存した順序のprimitive照会を行う。別meshから得た同一bodyの伝播情報も照合する。

平面との組は、同じ原本に対する幾何の検査と、位置誤差Bを含む丸めた接触式の検査の両方が必要。球同士は元の各半径・各B・明示marginを一度ずつ使う。すでに膨張した半径へ同じBを再度加えない。どの検査でも端点だけの観測を全時間の証拠にせず、閉時間区画の全被覆と正の下限を要求する。

必要な全組が認証され、全動的bodyのseedと費用会計が整合した場合だけ、元body順の完全な候補配列を返す。未認証・依存失敗・予算不足の場合は外側候補を返さず、得られた証拠と未照会の末尾を残す。候補を返す場合も、query自体はWorldへcommitしない。

## 計算枠と保持枠

子照会の前に費用上界と要求capacityを予約する。正常かつ費用が確定した返却では未使用の計算枠を精算できる。保持枠は、返った実要素数が少ないだけでは返却しない。primitiveの評価上限だけは残枠に合わせて減らせ、その実設定を結果に残す。

たとえば共有audit枠1024に対し、5回の既定要求255は最後を4へ減らす。さらに照会が必要なら、実際のauditが少なくても保持予約が尽きる場合がある。その結果は予算不足であり、安全判定ではない。16MiBのlogical payload枠は型のsizeofと要求slotの計算であり、allocator overhead・一時領域・stack・RSSの保証ではない。

全数値診断を所有し、子の非規範的なmessage本文だけを再帰的に除く。省略したfield数とbyte数は別記録する。返却しなかった子の実費を0とせず、既知量・予約上界・確定性を分ける。自然な故障経路の実行と人工的な診断改ざん試験も区別する。

## 実機の演算との接続

最初の対応候補はReleaseのMSVC 19.51 x64とGNU 13 x86-64 SSE2。actual core.cppの位置差・左結合dot・平方根、dynamics.cppの接触式をsource固有のstrict設定へ固定する。x64の平方根はSSE2 intrinsicを使用し、他targetの既存fallbackは残す。新Native gateの成功をWASMへ継承しない。

設定identityはsourceとcompiler設定の識別子であり、実行ファイルが自己測定したhashではない。実objectとlinked artifactの命令、呼出し経路、実compile commandを外部の検証記録へ結び付ける。RN-even・FTZ/DAZ無し等の環境検査も必要。未構成・非対応・identity不整合・環境不適合では子照会も候補生成も行わない。compiler名だけで実機監査の成功を主張しない。

現MSVC監査で機械命令のdataflowを確認した範囲は位置差・dot・lengthの3関数である。呼出し側はその3関数への実call先とFMA/x87不使用を調べ、平面の減算・閾値加算・比較の順序は固定した原著sourceとactual strict compile commandから判断する。呼出し側全体をsymbolic実行した証拠とはしない。

## 使用と検証の境界

入口は `world_static_mesh_flight_guard::query(world, meshes, horizon, GuardSettings(margin))`。marginは必須、horizonは秒の `(0,.1]`。同期capture中の入力変更はcaller側で排他する。最大body8・plane16・mesh4・全face64。最大188必要組を列挙できることと、その全組を既定予算で認証できることは別である。

既存World/W1/W2の全fieldとSDKを変更前後で比較し、実返却の出自・独立有理数による数学的包含・実機命令の監査を別々に実行した。51入力・58群・184実childとその完全再照会、12自己/138改変拒否、46CTest/684Node skip0を確認。[検証記録](../reports/2026-11-05-world-static-mesh-flight-guard.md)・[正式local receipt](../reports/world-static-mesh-flight-guard-local-verification.json)に原本の対応を保持し、公開受入は別に確定する。

一般形状の接触応答、meshのTOI応答、摩擦支持、変形・材料損傷、CFD、車両/航空/鉄道モデル、IK・制御設計は本照会の完成に含めない。新しいブラウザ数値APIとゲームへの接触適用も後続となる。
