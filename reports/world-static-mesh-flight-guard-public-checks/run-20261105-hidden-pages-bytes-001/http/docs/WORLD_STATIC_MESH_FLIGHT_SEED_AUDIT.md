# World全pairへ接続するseedの読取監査

後続の平面中心式には [明示B・marginのbox coverage](ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md) を選択した。新しい共有norm/sqrtを必要とする先行案は比較資料として残す。metric coverageとの論理積、実seedのBと同じmargin・compiler規約の検査は引き続きouter統合の条件である。

2026-11-04。**既存ソースの読取だけ。World数値API・seed型・全pair認証は未実装、追加実行なし**。[World計画](WORLD_STATIC_MESH_FLIGHT_PLAN.md)の次の境界を整理する。今回、既存コード・SDK・受入証拠は変更していない。

## 確認できた所有と成功条件

`prepare` は全body/plane/meshをcopy後に再検証し、ready時だけ全typed pairを所有する（[world_static_mesh_flight.cpp](../core/src/world_static_mesh_flight.cpp):116–157, 205–222）。処理元はそのsnapshotの原順配列とtyped ordinalに固定する。以後 `World::find_body`、callerのgravity、mesh spanを再読しない。mesh ID/revisionとmesh内face IDは別の所属であり、revisionだけでgeometry一致とはしない（[header](../core/include/pikapika/world_static_mesh_flight.hpp):41–71）。

旧mesh free-flight guardはsource検証後に全snapshotを所有し、bridge→tube→H候補の伝播/validate→endpoint監査→inflated held queryの順に進む（[guard.cpp](../core/src/sphere_triangle_mesh_free_flight_guard.cpp):103–165）。**status=certified_separatedのseedだけ**を、既存型のまま安全な再利用元にできる。tubeが存在してもderived域検査前、candidate_evaluatedでも伝播/validate失敗の可能性がある。mesh失敗時はcandidateが消されるため、tube/endpointの存在だけから候補を復元しない（同:75–77, 136–151, 162–165）。

## 最小の再利用境界案

1. 全pair一覧とは別に、dynamic body ID順で、そのbody×最小mesh IDのpairをseedとして一度実行する。結果を当該PairRecordへmoveし、BodyRecordはseed pair ordinalだけを持つ。巨大child Resultをbody側へ重複copyしない。最小meshの判定も所有snapshotから行う。
2. sphere/planeへ渡す係数は、元bodyのP/V、seed.tube.nominal_acceleration、seed.tube.guard_radius、同じH。nominal Aは既存W1の丸め `g+F*inverse_mass()` であり、nested heldのInterval加速度の中央値や、新たな通常double `g+F/m` へ置換しない。B/roundoff/rGuardは原値を保持する（[continuous_world.cpp](../core/src/continuous_world.cpp):58–94、[guard.hpp](../core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp):25–38）。
3. 他meshには当面、同じ所有body/gravity/H/設定を旧guardへ渡す。これは**flightと候補を各callで再実行する**。成功child間でtube・endpoint・全candidateのbitsを比較し、伝播費用を省略しない。seedのtubeだけを直接渡せる旧public APIはない。held queryだけへ置換する最適化は、child診断/費用契約を変える後続設計である。
4. static bodyは元全fieldsを保持し、geometry pathだけP固定・V=A=B=0、元radiusとする。既存validateが平方underflowする微小V/Lを許す場合でも、静的物体を動かさない。全必要mesh/球対/plane両predicateが成功してから全body候補を原順へ構成する。seed一件の候補はscene成功ではない。

## 費用・copy・失敗の境界

旧guardのtop-levelに総Workはなく、`candidate_evaluated` は実propagate attempt、nested `inflated.work` はheld/mesh/sqrtの費用である。bridge・候補監査・copy費用をnested Workへ混ぜない（[guard.hpp](../core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp):40–58）。

N面・held評価上限Eなら、call前の保守sqrt枠は `E*(512N+1024)`（mesh N×512、R/E各512）。局所上限との整合とglobal予約が別に必要。旧heldはblock直前に予約し、未返却時はknown＋予約upper/exact=falseを保持する。meshは失敗row後も続けるため、knownは時系列prefixとは限らない（[held.cpp](../core/src/sphere_triangle_mesh_held_load.cpp):70–82, 174–205, 243–247、[mesh.cpp](../core/src/sphere_triangle_mesh.cpp):55–64）。child返却不能を実費用0とせず、外側もattemptとfull grantの不確定上界を残す。

N面の返却sourceはguard snapshot＋held snapshot＋lastMeshで最大3N、次meshを構築中は旧/新lastMesh併存で4N。元World snapshotは別にT面。lastMeshは最後のaudit所属で、任意auditのgeometryへ付け替えない。要求capacityを返却sizeへ精算してメモリ予約を戻さず、全Resultはmoveで一度所有する（guard.cpp:117,154、held.cpp:152–153,179–187）。これは要素数の読取上界で、allocator/heap上限ではない。

## 荷重と残る未確定

`propagate_free` はforce/torqueを消さず、guard候補も保持する（[dynamics.cpp](../core/src/dynamics.cpp):144–155、guard.hpp:56–57）。荷重を消すのは公開tickの `World::step` / W1 commitであり、その処理をread-only guardへ持ち込まない（dynamics.cpp:258–268、continuous_world.cpp:385–387）。

未確定は、sceneの正式BodyRecord/PairRecord、全診断capacity/payload/text予約、外側throw時の上界、seed失敗後の依存pair状態、plane World中心式の別coverageとsqrt未返却予約である。新closed-cell helperはmetric側の全owned Resultを保持できるが、World中心条件を代替しない。primitive pairは両球Bを反映し、planeは両全時間predicateを証明する必要がある。旧kernelsを変更せず、2dynamic×2mesh＋球対/planeを次の非自明な実装受入へ進める案であり、現時点の完成報告ではない。
