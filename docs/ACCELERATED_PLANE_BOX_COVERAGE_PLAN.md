# 明示B・marginによる平面box coverage案

**契約固定・制作中、ローカル/公開受入は未完。** [新ヘッダ](../core/include/pikapika/accelerated_plane_box_coverage.hpp) の契約から新Native helperと独立参照を作り、既存C++/World/SDK/旧coverageを変更しない。新依存・外部コード/図・license選択はない。これはcallerが宣言したBの条件付き証明であり、実WorldのB、compiler、全pair、候補公開、接触応答を認証するAPIではない。

## 入力と返す証拠

`Input={sphere,plane,position_error,contact_margin}`。sphereは点係数P/V/aNom/r、planeはraw n/offset。全component/offsetとrは有限絶対値≤1e12、r>0、nはcomponent比較で非zero、`0≤B≤1e12`。marginはcaller明示の有限 `0≤margin≤.1`（.1はbinary64値）。Worldはmarginを保存していないため既定solver値を推測しない。Hはglobal秒の `(0,.1]`。SettingsはE1..255、leaf1..128、depth0..32（既定24）、timeTolerance `(0,.1]`（既定1e−7s）。

`Input(Sphere,StaticPlane,B,margin) noexcept` は4必須引数でdefault constructor/既定B・marginを持たず、public fieldの可変性と−0を保つ。`Snapshot={input,horizon,settings}` は固定サイズ・全原値/−0を所有する。environmentを最初に拒否した場合だけsnapshot無し。supported環境では検証前captureし、設定→H→sphere→plane/zero normal→B→marginの順で検証する。不正原本の完全captureとvalid tubeを区別し、failedInputはsphere0/plane1/B2/margin3。型と幅の公開契約は新ヘッダを正とする。

各closed cell Tにpublic throwing `value(Input,T)` が全Evaluationを返す。point時刻も許すがqueryは追加point評価を行わない。

```text
Xk(T) = I(Pk) + I(Vk)*T + (I(aNomk)*I(.5))*square(T) + [-B,B]
distance = ((I(nx)*Xx + I(ny)*Xy) + I(nz)*Xz) - I(offset)
threshold = I(r) + I(margin)                 // 別に保持
gap = distance - threshold
```

`tubeCoordinates[3],distance,threshold,gap` を全返却auditにそのまま所有する。通常doubleでaNom/2を先に丸めず、radiusとmarginを別々に逐次引く式へ変更しない。`gap.lower()>0` のみpositive。元nominal quadraticに対して各axis誤差≤Bとcallerが別途証明すれば、このtubeの中の全中心へ適用できる。L1/Euclidean誤差上界もaxis上界として使えるが、本helperはBの由来を検査しない。

既存 `accelerated.cpp:88–95,182–184` のmetric `n·p−offset−r|n|` を呼ばず、norm/sqrtも計算しない。本box証拠をmetric全被覆の代わりに使わない。将来outerが同じowned pairへ両結果をリンクし、それぞれが全 `[0,H]` を被覆するとき論理積を取れる。leaf境界は一致不要、metric二重照会も不要。

## 丸めを含める範囲と含めない範囲

distanceは `core.cpp:25` のdot左結合とoffset減算、thresholdは `dynamics.cpp:225–226` のr+marginに対応する。各AST nodeをexactまたはbinary64 RN-evenとする有限な拡張族を包含する。Intervalのmul/add/sub（`interval.cpp:141–165`）はexact結果とRN結果を囲むため、product丸めを省き親addで丸めるassociation-preserving FMA収縮も帰納的に入る。これは任意再結合/fast-math/FTZ/excess precisionを許可する証明ではない。core.cppは現在個別strict対象外で、外部Worldのcompiler全般やdot実体を認証済みとしない。

strict環境/新TUの演算条件は後の実buildで検査する。raw nを正規化しない。近unit判定はunitという実数等式ではない。boxは相関を捨てるため、正しいBでも予算内成功は保証しない。Worldの全body候補/回転/荷重所有/時間進行、actual Bとcompiler規約、同marginでの接触生成との対応はouterの後続gateである。

## 全被覆・費用・例外

既存独立coverageと同じE255/L128/depth32の有界BFSを新型で持つ。rootは `[+0,H]`、最小depth/同率最左を選び、blockedがあっても他pendingを調べる。uncertain停止順は外向き幅upper≤tol→depth→representable内点無し→leaf予算。strict内点を両子へ共有し、全partition/parent/audit/frontier/currentと未照会tailを所有する。全leafがpositive・全call正常返却・全閉被覆/metadata整合のときだけcertified。負・zero・接線・狭い未知を成功にしない。

Auditはoptionalの**全Evaluation**を持ち、非返却時はnull。time Interval構築後、value直前にattemptを増やし、正常返却直後にreturnを増やす。後続metadata例外でもreturnを巻き戻さない。throwはattemptedだがevaluation無しのblocked/valueExceptionとcurrentを残して全体停止。eval予算はcurrentへ選んだ後、新audit前に停止する。通常blocked後の最終reasonは時間順最初のblocked理由。pendingを最終返却しない。

Workは正確なvalueCallsAttempted/Returnedのみ。sqrtやprivate norm上界、metric呼出しを偽計上しない。固定snapshot/recordのnothrow性、root前の全vector reserve、capacity内split/最終frontier、noexcept失敗message/return moveを実装時に監査する。allocation前失敗ではpartitionComplete=false。メモリbyte上限・自然に未到達のthrow/allocator故障注入を実施済みとしない。

## 独立参照と最小受入

原binary64をFractionへ復元し、各coordinate quadraticの端点・域内停留点から厳密rangeを得て、全記録tubeが真のrange±Bを囲むことを監査する。記録されたbox上ではnの符号からdot extremaのcornersを選び、固定ASTの各nodeでexactまたは**integer実装のRN-even**を取る有限choicesを列挙する。これでdistance/threshold/gapの全記録Iが丸め/非丸め/FMAを含む拡張族を囲むことを検査する。通常double再演算・有限時刻sample・粗いgamma上界だけを正解にせず、同符号の単調性とcorner極値を証明する。全被覆/BFS/幅/Work/原値bitsは別監査する。

数学的にvalidな広いIと、実public `value` が返したIの完全bit保存は別gate。Native試験は全返却Evaluationを同owned入力/cellから直接再照会して全端点bitsを照合する。数学oracleは同等の広い包含を偽の由来だと断定しない。

最小corpusはnear-unitのmetric/raw両方向不一致、margin0/正/閾値丸め、dotのlost-low-term/FMA差、相殺・巨大offset・denorm/−0、B0/正/不正、実subdivision成功、255audit/128leaf/未照会127tailと全停止理由。負例はB/margin/sourcebit変更、内部極値欠落、distance/threshold混同、丸めchoice除去、偽positive、parent/leaf/tail削除、attempt巻戻しを含む。故意nonreturn recordの自己試験は実C++ faultとは呼ばない。固定corpusの実結果・独立全I/負例・strict/sanitizer/環境・原本保持が揃うまで、新数値/公開受入を報告しない。
