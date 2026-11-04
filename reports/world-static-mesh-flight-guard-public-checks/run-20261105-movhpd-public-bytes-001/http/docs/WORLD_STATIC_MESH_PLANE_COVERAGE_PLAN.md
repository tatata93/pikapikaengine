# World raw平面の別coverage案

この章のnorm共有は先行する比較設計で、未実装のまま保持する。次の実装対象には [明示B・marginの座標box方式](ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md) を選んだ。box方式は新しいnorm/sqrtを呼ばず、固定ASTの丸めとthresholdを別に囲む。以下のnorm案が実装済みになったという意味ではない。

未実装・未検証のNative最小案。現在のWorld準備と加速pair coverageを変更せず、同じ所有body–plane pairへ追加の証拠を結ぶ。新API名・正式型・予算値はまだ確定しない。SDK/UI/World進行・接触応答は対象外。

## 証明する式と、既存metric式との違い

元body・重力・raw平面を所有し、既存W1 bridgeの返却 `aNom` と `B=position_error` を一度取得する。`qNom(t)=P+Vt+aNom*t²/2`、`0≤t≤H` とする。既存strict operation graphの全duration並進包含により `|x(t)−qNom(t)|₂≤B` が成立する範囲で、Cauchy–Schwarzから

```text
Ψ(t) = n·qNom(t) − offset − r − |n|B > 0
  ⇒ n·x(t) − offset − r > 0.
```

これを新しい**raw center predicate**の全時間証拠とする。`accelerated.cpp:88–95,182–184` の既存 `sphere_plane_value` は `n·q−offset−r|n|` を囲むmetric式であり、Ψへ置換しない。Worldの平面は近unit判定で入場するだけでraw値を正規化しない（`dynamics.cpp:195–198`、`world_static_mesh_flight.cpp:51–56`）。`n=(1+2⁻³⁰,0,0), x=(1−2⁻³¹,0,0), offset=0,r=1,B=0` はraw式が正、metric式が負になる代数反例。nとxの符号を逆側へ選ぶと逆の不一致も生じる。B=0は式を区別する解析例で、実W1返却値を捏造する入力ではない。

既存metric coverageとΨ coverageはそれぞれgaplessな閉区間 `[0,H]` を持ち、leaf境界は異なってよい。両方の全leafがstrict positiveで、同じowned snapshotのtyped pair・元ordinal/ID・H・aNom/Bへリンクするときだけ論理積を認証する。metric結果を再利用し、Ψのためのmetric value再照会や旧Iの変更は行わない。狭い未知、負のleaf、未照会tail、片側だけの成功を全pair成功へ昇格しない。

## 実在するsqrt APIと、所有normの費用

公開APIは `interval.hpp:46–56` の `SqrtResult{Interval value,unsigned refinements,bool refinement_limited}` と `sqrt_enclosure(value, maximum_refinements=128)`。実装は `interval.cpp:192–238`。環境を先に検査し、入力は有限・非負の順序付き区間、Fは1..256の**endpointごとの**上限。zero/二進の特例は0精錬、同一点区間は片endpointだけ、異なる両端は合算なので正常返却 `refinements≤2F≤512`。隣接値での停止もあり、limitedは予算末尾へ達したことを表す。limitedでも包含は有効で、正しさ/精度成功とは別。libm sqrtの正丸めやIEEE1788の実装ではない。

raw平面ごとにinterval component演算で `N=nₓ²+nᵧ²+n_z²` を囲み、非負部分を使ったsqrt結果とN・F・元plane参照を**一度だけ所有**する案。和の外向き丸めで微小負lowerが出る場合も、平方和の非負性からの切詰めを記録し、負をそのままsqrtへ渡さない。返却上端Sなら `S≥|n|` を証明でき、Ψには上向き `S*B` を引く。正規化や通常double dotを証拠計算へ混ぜない。同じsnapshot内の全body–plane pairがこのnorm recordを参照し、pairごとに再精錬・費用二重計上しない。既存metric valueのprivate normは別実行のまま維持する。

sqrtを呼ぶ直前にplane単位のfull grant `2F` を予約する（固定512を採用する場合は正式契約に明示）。attemptを先に増やす。正常返却後だけactual returned count/limitedを加算し予約を精算する。throwは部分 `SqrtResult` を返さないため、実精錬数を推定せずknown returnedとfull grant込みupperを分け、exact=false・norm absentとして停止する。未返却分を0へ戻す、残予約を別pairへ流用する、私有norm loop上界をshared sqrt実countと呼ぶことを禁止する。`accelerated_pair_coverage.hpp:57–65` の既存plane上界はattempts/64×attemptsで、shared sqrtとは無関係。

## 所有・候補・既存Worldとの境界

World準備の全snapshot/typed参照・static-only除外・profile超過時の非切詰めを継承する（`world_static_mesh_flight.hpp:38–100`）。初期captureと準備readyを数値成功と混同しない。normは元plane一件、body tubeは元body一件に所有し、各coverageは参照と全cell/audit/partition/frontier/current・別Workを保持する。予約/確保失敗は返却済証拠とunknownを保持し、最終化の追加確保を避ける。allocator/stackのbyte保証や実fault到達は型・実試験前に主張しない。

W1原本 `continuous_world.cpp:58–94` と同TU bridge `free_flight_internal.hpp:8–24` の演算/返却を再実装しない。全bodyのH候補はcopyへ `propagate_free`、`validate`、nominal/exact endpoint tube監査を通し、全必要pairの両証拠・exact Work成立後だけ公開する。既存単体guardの同様のgateは `sphere_triangle_mesh_free_flight_guard.cpp:127–165`。候補回転・L/荷重所有は並進全時間証明とは別のNative検査であり、World/time/loadを更新しない。

なお実contact生成は `dynamics.cpp:225–227` の **rounded** `n.dot(position)−offset≤r+contact_margin`。Ψ>0は実数raw predicateの非重なりで、margin>0時のcontact生成無しを保証しない。次の統合にはmargin=0への明示限定、またはmarginを引く別契約と、compiled dot/比較の丸め誤差・strict flagsの監査が必要。外部 `Vec3::dot` の未監査targetや丸め境界を、この式だけで認証済みにしない。metric/raw両coverが通っても応答・繰返substep・全時間の姿勢/速度真解は未認証。

## 最小受入と独立参照

1. Fractionで元nとaNomの二次式を展開し、各返却Iの全cell extremaを端点・域内停留点で監査する。normはNの包含とsqrt端点の二乗不等式、`S≥|n|`、B・上向きsupportを別に確認する。有限sampleを全時間証明にしない。
2. near-unitの両方向反例、非有理norm、−0、低Fのlimitedだがvalid、複数body/一plane共有、両coverが異なる分割で成功する非vacuous例、片側失敗・先行未知/tail・予算拒否を含める。全入力bits・原ordinal/IDと再利用元リンク、実metric call数不増を独立確認する。
3. S/B/support下向き改変、norm費用の二重計上/巻戻し、偽exact、別snapshot・別planeリンク、tail削除、片側成功の昇格を負例にする。正常shared sqrt countは実返却を照合する。人工throw metadataと実allocator/root fault注入を区別し、後者は未実行なら未実行と記録する。

本稿はsource読取と証明設計のみ。C++/旧kernel/SDK/既存試験を変更せず、新しい数値受入・性能・メモリ・公開成功を報告していない。
