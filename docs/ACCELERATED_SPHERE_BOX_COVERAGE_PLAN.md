# 二つの宣言位置boxによる球接触predicate coverage契約

2026-11-04。**Native単体核をローカル・公開受入済み（feature63f5d3d、2026-11-04）**。[header](../core/include/pikapika/accelerated_sphere_box_coverage.hpp)・[ローカル原本](../reports/accelerated-sphere-box-coverage-local-verification.json)・[受入記録](../reports/2026-11-04-accelerated-sphere-box-coverage.md)を分けて保持する。現在のplane-box公開receiptは変更しない。将来のWorld guard契約・外部sqrt/compiler bindingは未実装で、今回のsphere-box公開対象へ含めない。

## 既存のmetricだけでは足りない理由

`dynamics.cpp:233–234` は `delta=other.position-body.position`、`distance=delta.length()`、`radii=body.radius+other.radius` を作り、`distance<=radii+contact_margin` で接触候補を生成する。`core.cpp:23,25,27` はcomponent減算、左結合のdot、`std::sqrt(dot(*this))`。既存metricは正しい実数式の証拠だが、marginとこれらの丸めを含む別predicateの代わりにはならない。

例としてrA=rB=1/4、中心距離17/32、margin=1/16は、真の幾何gapが1/32でもWorld閾値9/16以下で接触範囲となる。全値が厳密dyadicである。さらにmargin0でも、次の厳密な違いがある（既存metricの誤実装を主張する例ではない）。

- A=(-2⁻⁵³,0,0)、B=(1,0,0)、半径和1。真の距離は1より大きいが、位置差のRNは1となる。
- delta=(1,2⁻²⁷,0)。真の二乗距離は1+2⁻⁵⁴だが、dotのRNは1となる。
- delta=(1,2⁻²⁶,0)。RN dotは1+2⁻⁵²でも、その正しいRN平方根は1となる。midpointの平方 `(1+2⁻⁵³)²=1+2⁻⁵²+2⁻¹⁰⁶` より小さいためで、平方根の丸めをdotの丸めと別に扱う必要がある。
- rA=1、rB=2⁻⁵³、margin=2⁻⁵³では、二段RN左結合の閾値は1、先にrB+marginを足すと1+2⁻⁵²。評価順を変えない。

将来World guardは球対で本helperを**既存sphere metricの代わりに一度だけ**使う案とする。planeは既存metricとplane-boxの二証拠を維持する。2dynamic/2mesh/plane1の最小例は、引き続きplane metric2＋plane box2＋sphere box1の計5coverage callである。

## 入力・式・範囲

Inputは **必須5引数** `firstSphere, secondSphere, firstB, secondB, contactMargin`。各Sphereは点係数P/V/aNomと**元radius**。各axis誤差が各B以下であることはcallerの別証拠であり、本helperはBを導かない。guard radiusを渡して同じBを二重に加えることは禁止する。

各componentとradiusは有限絶対値≤1e12、radius>0、両Bは有限 `[0,1e12]`、明示marginは有限 `[0,.1]`。Hはglobal秒 `(0,.1]`。public valueはfinite closed T⊆[0,.1]（点時刻も可）、queryは追加point評価をしない。

```text
Xk = I(PAk)+I(VAk)*T+(I(aAk)*I(.5))*square(T)+[-BA,BA]
Yk = I(PBk)+I(VBk)*T+(I(aBk)*I(.5))*square(T)+[-BB,BB]
Dk = Yk-Xk
Qraw = (square(Dx)+square(Dy))+square(Dz)
Qsafe = [max(0,Qraw.lower), Qraw.upper]
root = sqrt_enclosure(Qsafe, sqrtRefinements)
distance = root.value                         // 全bits同一のcopy
threshold = (I(rA)+I(rB))+I(contactMargin)      // 左結合、別に保持
gap = distance-threshold
```

EvaluationはX/Yの各3box、delta3box、Qraw/Qsafe、**全SqrtResult**（value/refinements/refinement_limited）、distance、threshold、gapを全所有する。Qrawの負下端はoutward演算の過大評価から生じ得るが、実際の非負square/加算族は負にならないため下端のみ0にclampできる。**upper<0は不整合のerror**であり、upperも0へ置換して通さない。通常doubleでaNom/2を先に丸めない。

## exact/RNと平方根の条件

箱上の固定ASTの各nodeで、厳密実数演算かbinary64 RN-evenのどちらも含む拡張族を囲む。位置差・dot・二段閾値と比較両辺を同じ原本から構成する。この包含はASTを保つFMA収縮も含むが、任意再結合、分配、hypot置換、FTZ/DAZ、別丸め、excess precisionを含めない。

sqrt_enclosureが非負binary64端点[l,u]で全√qを包含すれば、RNの単調性とRN(l)=l、RN(u)=uからRN(√q)も[l,u]に入る。追加のnextafterを根拠なく要件へ足さない。ただし**外部std::sqrtがそのRN規約を満たすかは別gate**。source_enforcedを選んだ将来World接続では、実dot/減算/length/sqrtのsupported-target compiler・runtime bindingと既存World/SDK回帰を明示する。本helperの包含・有限例だけでactual World全targetを認証しない。

## 有界探索・所有・root費用

SettingsはE1..255/leaf1..128/depth0..32（既定24）/timeTolerance `(0,.1]`（既定1e−7秒）、追加sqrtRefinements1..256（既定128）。独立したtotal-root設定は足さず、全call上界 `2*E*ref≤130560` を公開する。低refinementでlimitedでも正しい包含なら使えるが、成功条件は常にgap.lower()>0である。

環境FIRST、対応環境では検証前に全元値/−0をSnapshotへcopyする。検証順は設定→H→first sphere→second sphere→first B→second B→margin。failedInputは順に0/1/2/3/4（設定/Hはnull）。invalid captureをvalid tubeへ昇格しない。Result/AuditはIntervalやSqrtResultをoptional Evaluation内に置き、環境確認より先に既定rootを作らない。

root前にaudit/partition/frontierをreserveし、closed `[+0,H]` の全partitionを保持する。BFSは最小depth/左、uncertain停止順はoutward width→depth→strict内点不在→leaf予算。negative/zero/狭い未知は成功でない。eval予算は新audit前にcurrentで止める。value throwはEvaluation無しのblocked audit＋current＋全未照会tailを残し全体停止する。全leaf正、全call正常返却、root会計exact、全被覆/metadata整合の場合だけcertified。

Workのwrapper attempts/returnsは常に正確。`sqrt_results_returned`、`sqrt_refinements_returned`、`sqrt_limited_returns` は**返却された完全Evaluationから観測した分だけ**で、private sqrtの実attempt数ではない。value直前に2refのunknown blockを予約し、正常返却直後に全counterをcommitする。未返却ならroot exact=false、upper=既知refinements＋2ref、当該callの観測rootは0（実内部使用0とは言わない）。返却後のmetadata例外でも返却counterを戻さない。known/upper・観測返却・wrapper実回数を分け、未知費用をexact成功へ変えない。

## 独立受入の契約と確定結果

独立Fractionは全coordinate quadraticの厳密extrema±B、記録boxからのdelta、各square/加算/閾値/gapのexact-or-integer-RN族を検査する。sqrtは全記録rootの非負・平方不等式と、上のRN包含補題を別監査し、通常libm sqrtを参照の真値としない。全SqrtResultの実public value再照会bit保存は、数学的包含とは別のNative provenance gateである。

両B/片B/両0、5種類のpredicate反例、巨大共通offset/取消、接線/途中通過、B>0の実subdivision成功、tiny/−0、全255audit/128leaf/127tail＋current、ref1/128/256、設定/所有/環境復帰をローカルで確認した。実75入力はcertified20 / not_certified21 / invalid34。84専用群と45CTest、全955返却rootの平方包含・96929観測精錬、limitedでも正の1例、16自己/89拒否が成功した。座標の独立参照は真のquadratic extrema±Bであり、座標生成I-ASTの全RN選択を独立列挙したとはしない。recorded boxesからのdelta以降を整数RNで監査し、全15I/root診断のactual返却由来は別のNative再照会gateとする。人工nonreturn/広い有効rootの正例と改変拒否は自然なC++故障注入ではない。sizeof×capacityはvector部分97976B＋inline Result480B＝98456Bの観測で、heap/stack/allocator上限ではない。公開GNUの新3TU Werror・全5TU ASan/UBSan、通常/計装全fixture byte一致と両独立参照、公開配信を下記の別runで確認した。

## 公開受入と次の境界

[公開機械集計](../reports/accelerated-sphere-box-coverage-public-verification.json)・[実測報告](../reports/2026-11-04-accelerated-sphere-box-coverage.md)。Engine41845414301全25段/Pages41845413100全3job、45CTest/84群75入力、全955Evaluation/14325I、16自己89拒否、684Node skip0を確認した。旧48GNU warning multiset同一、新0。112Pages＋GitHub workflow1の113件3287969Bはfeature63f5d3d blob一致。図/教材の実表示と既存ゲーム2撃破・boost/pause・21正常照会3常駐は互換scopeであり、新helperのBrowser数値実行やWorld接触適用ではない。

取得ドライバーの旧99定数2箇所によるbytes001停止は、原script/patch/失敗rawを保持し112への2定数訂正後のfresh bytes002で受入した。UI collectionのrole selector不一致と親mkdir ENOENTも元note/AXを保持し、数値不正や実fault注入と区別する。新7source・既存376raw/26HTML/SDKは不変。次のWorld guard/compiler binding/actual B・pair/candidate統合は別featureで、未追跡の将来sourceを今回へ混ぜない。
