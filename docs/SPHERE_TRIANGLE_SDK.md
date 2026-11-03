# 球×静的三角形の共有SDK照会

2026-11-04 JST。**実装・ローカル/公開Linux CI/Pages検証済み**。Native純粋核を変更せず、同じC++を主WASMの68-export SDKとJSの所有snapshotへ接続した。Native単独段階の受入と、新SDKの受入を分ける。

Nativeのモデルと品質条件は [SPHERE_TRIANGLE.md](SPHERE_TRIANGLE.md)、既存のNative受入は [Native統合報告](../reports/2026-11-04-sphere-triangle.md)、今回の接続は [SDK統合報告](../reports/2026-11-04-sphere-triangle-sdk.md)と[SDK計画](SPHERE_TRIANGLE_SDK_PLAN.md)を参照する。直前の66-export SDKへ本照会が含まれていたと読み替えない。今回のartifact・数値照合と公開結果は末尾および統合報告へ記録した。

## 何を調べるか

world-spaceの球中心と半径、staticな両面三角形1枚を受け、三角形上の最近接点qを調べる瞬間のread-only照会である。面1・辺3・頂点3の候補について否定できるものだけを除き、残り全部を囲むNative核をそのまま呼ぶ。JSのplane/AABB/距離計算へfallbackしない。

距離d=`|x-q|`、gap=`d-r`、normal=`(x-q)/d`を区間で返す。normalは三角形から中心へ向く。world closestの幅は巨大共通offsetの再加算で広がり得て、local幅の品質条件をworld座標へ拡張しない。geometryの区間中点を、保証済みの接触点/単位法線として既存point impulse solverへ渡す許可ではない。

## JS入口と実SDKで確認した使用例

入口名とposition表記は次のとおり。下の3-4-5配置は主WASMの専用試験でも確認した。

```js
const result = runtime.querySphereTriangle(
  {position: [2, 3, -4], radius: 4},
  {id: 17, vertices: [[0, 0, 0], [4, 0, 0], [0, 0, 4]]}
);

if (result.status === 'completed') {
  // 値は点近似ではなく、通常Arrayの[lower, upper]。
  const g = result.geometry;
  console.log({distance: g.distance, gap: g.gap,
               normal: g.normal, relation: g.relation});
} else {
  // この候補prefixは成功geometryではない。
  console.log(result.status, result.reason, result.candidates);
}
```

この解析配置では真のq=`[2,0,0]`、d=5m、gap=1m、normal=`[0,3/5,-4/5]`。例は本来この値を含む区間を得るためのもので、コンソールへ整数の5/1を合成表示するものではない。値が出ない場合も原入力の半径・角度・閾値を勝手に変えない。

inputのposition/verticesは各xyzの有限値、radiusも有限値として交換する。Native物理入力域は座標/半径の絶対値<=1e150、radius>0。surface IDは既存SDKの正のsafe integer規約1..2^53−1を使う。shape/非有限/ID等の交換拒否と、有限だがNativeのモデル域・品質条件を満たさない結果を分ける。

設定名と既定値は次のとおり。Nativeと同じ意味で渡し、妥当な範囲へ自動clampしない。

| JS settings key | 既定 | 単位・Native上の範囲 |
|---|---:|---|
| maxCandidates | 7 | 整数1..7、成功には全7候補の検査が必要 |
| sqrtRefinements | 128 | endpointごとの整数1..256 |
| maxTotalSqrtRefinements | 1024 | 整数1..1024、平方根呼出し後の更新数監査 |
| maximumLocalWidth | 1e-7 | m、正かつ<=1e6。closestLocal/deltaの成分幅 |
| maximumNormalWidth | 1e-8 | 無次元、正かつ<=2。normalの成分幅 |
| minimumSineSquared | 1e-12 | 無次元、正かつ<=1。辺AB/ACの条件検査 |

JSがuint32の型/範囲を検査するのは最初の整数3設定だけである。その交換域内の0やモデル上限超過、有限の幅・半径等の不正値は実C++モデルへ渡し、invalid_input等の実結果とする。非有限値は交換前に拒否する。品質幅は有限contact bandではない。

## copied snapshotのDTO

Native fixturesと同等のcamelCaseへ写す。数値enumの順はNative headerに従い、JSではstatus/reason、relation、候補のfeature/dispositionを同じ英語snake_caseの文字列へ変える。下記fieldの順序は追加済みJSと照合した。モデルmessageはこのDTOへ含めず、JSで詳細文を合成しない。

```text
Result
  status, reason, geometry|null
  squaredCross|null, sineSquared|null
  candidates[]
  candidatesExamined, sqrtRefinements, sqrtRefinementLimited

Geometry
  surfaceId, survivingFeatures
  barycentric, closestLocal, closest, delta, normal, spherePoint
  squaredDistance, distance, gap, relation

Candidate
  feature, disposition, kktCount, barycentric, kkt[2]
```

Bounds3は `[[xlo,xhi],[ylo,yhi],[zlo,zhi]]`、scalar intervalは `[lo,hi]`。この接続では通常Arrayの所有copyを使い、HEAP viewやNative recordへの借用を返さない。getter後には現在のHEAP/pointer/countを取り直し、全decode完了まで部分DTOを返さない。後続query/getterとglobal resetが以前callerへ返したcopyを変えず、callerのcopy改変もNative snapshotを変えない。

Candidateのfeatureはface / edge_ab / edge_bc / edge_ca / vertex_a / vertex_b / vertex_c、dispositionはretained / outside_simplex / kkt_violated。`kktCount` は面0・辺1・頂点2だが、`kkt` は常に2区間を保持する。**未使用KKTの `[-0,+0]` も元bitsのまま残す**。count0を理由に空配列や+0へ正準化しない。通常のJSON.stringifyで再保存すると-0が消え得るため、bit照合や損失なしの保存には原rawと既存のstrict JSON等の符号零を保つ経路を使う。候補barycentricはclip前の診断包含で、geometryのaccepted hullと混同しない。

`survivingFeatures` は候補集合のbit maskで、featureの一意判定ではない。面/辺のtieだけでnormal不定と決めず、逆にd²の厳密正下限や品質が得られなければgeometryを作らない。candidate数とexamined数は失敗時に常に等しいとは限らない。全7候補を調べたcompletedの場合だけ7/7である。

## status・relation・例外を分ける

モデルstatusは completed / invalid_input / degenerate / ill_conditioned / quality_unresolved / budget_exceeded / numerical_failure / unsupported_environment。受理した交換から得たモデル失敗も実C++の結果であり、geometryはnull、新しい診断snapshotになる。候補prefixや以前の成功geometryで埋め合わせない。

completedは最近接幾何・normalの包含と幅品質が成立したことを示す。relationはgapの下限>0ならseparated、上限<0ならpenetrating、両端0だけtouching。それ以外の0跨ぎはboundary_unresolvedで、geometryがcompletedのまま返る場合もある。boundary_unresolvedをseparated・gap=0・衝撃解決済みへ置き換えない。local/normalの品質幅は接触bandではない。

旧SDKに新2exportsが無い場合は入力交換/query前に明示的なhost errorとし、JSの代替計算や古いrecordの再使用をしない。不正shape/交換型・ABIエラー・不正な出力packetも例外で、モデルstatusをJS側で合成して返す経路ではない。

交換不正/候補範囲不正のABI拒否は、直前outputの有効count/prefix bitsと現在snapshotを保持する。input scratchの保持は約束しない。acceptedモデル失敗への更新とは別のatomicityである。JS decoderがprepare後のpacketを不正と判断してthrowしても、Nativeが既にpublishした新snapshotをprepare前へ戻す意味ではない。以前返った所有copyは保持する。

## C ABI 24 / 58 / 13

既存ABI version1、F64 output容量64を変えずに次の2exportsを接続した。主WASMでの提供とローカル数値照合を確認済みである。

```c
int32_t pp_sim_sphere_triangle(uint32_t value_count);
int32_t pp_sim_sphere_triangle_candidate(uint32_t index);
```

入力24は、centerXYZ/radius4、surface ID1、ABC vertices9、整数設定3、幅/条件設定3、reserved zero4。正確なordinalは [SDK計画](SPHERE_TRIANGLE_SDK_PLAN.md)にある。全有限・count24・reserved zero・整数/IDの交換条件を先に検査する。

出力58にはstatus/reason、hasGeometry、ID/feature mask/relation、候補/平方根の件数、optional cross²/sin²、それぞれのboundsとgeometry全体を置く。geometry-null時のpaddingやoptional不在payloadを、ゼロ距離/ゼロ法線/確定接触の証拠にしない。

候補は1件13で、feature/disposition/kktCount3＋barycentric6＋KKT4。indexは実在prefixのordinalだけで、末尾外を要求したら拒否する。新たな候補batch機構や最大7件の切捨てを追加しない。queryから独立recordをcommitしてからgetterでcopyするので、他のmotion/optics/skin/derived snapshotとは分離する。

global resetはこのNative snapshotも消す。個別のWorld resetや他種queryは、このsphere-triangle snapshotの消去操作ではない。本照会自体はWorldの時刻・姿勢・荷重を変えない。共有scratchは同期・非再入という既存条件を維持する。

## ローカルの数値・来歴の受入

Nativeの113有限fixtureに対し、既存ID交換規約でzero-id/unsafe-idの2例をhost拒否へ明示分類した。残り111例は実WASMで照会し、88 completed / 23意図したモデル失敗を確認した。113例全部をWASMのモデル成功/失敗と数えたり、host拒否をgeometry無しの合成モデルとして補填していない。

全field・区間両端・signed zero、unused KKT、候補末尾/件数/optionalを照合した。実WASMのraw packetは22327 numeric bits、JSへ投影したモデルは13432 numeric bitsがNativeと一致し、符号零の比較3472件も保持した。両者は表現の異なる照合範囲であり、足して独立fixture数とはしない。実WASMの成功88 geometryへ独立Fraction参照1848成分と23改ざん負例を適用し、すべて成功した。Nativeとの一致だけを数学的包含の根拠にしていない。交換保持、失敗後復帰、global reset、他snapshot/World不変、旧SDK能力拒否、破損packet拒否、copy所有も専用試験で確認した。

Native API77群・全32CTest、Node502/502（skip0）、構文検査、Web build `f7448823095f375b` / 45 modulesがローカルで成功した。初回Nodeは500/502で、報告リンクの作成前参照と、profile CLI試験の旧source53/export66固定が原因だった。報告を作成し、後者をmanifest/hash/headerの実列挙比較へ更新した後に502件を再実行した。この初回失敗を数値核の誤差や成功件数からの除外として隠さない。Native純粋核のcpp/header bytesは不変である。

| ローカルSDK artifact | 確定値 |
|---|---|
| exports / source・header原本 | 68 / 合計55 |
| WASM | 612824 B |
| WASM SHA256 | `eff93890e4dcf6387ba9fe55e5b15e38f4db817f68dfd112bb1ba503b78fb90d` |
| Emscripten glue | 51085 B |
| glue SHA256 | `0d541bc399cbdd6b55e7f2f848479acd39af408d2dec5b4379d8b1b09fb0a7d0` |

照合の入口は `node scripts/verify-sphere-triangle-sdk.mjs <native-fixtures.json> <native-sdk-probe> <new-output-directory>`、専用JS試験は `node --test tests/sphere-triangle-sdk.test.mjs`。山括弧は実ファイル/新規出力先へ置き換える。原raw・独立参照・実行条件は[SDK統合報告](../reports/2026-11-04-sphere-triangle-sdk.md)へまとめる。コードe100beeの公開Linux CI/Pages全工程が成功し、31ファイル1,330,820Bの配信byte一致を確認した。公開ブラウザの出撃/boostでは21query全成功・3 resident meshを確認し、main WASM612824B/build IDも一致した。ローカルブラウザの既存ゲームREADY・出撃/boost20 query成功・3 resident meshも確認したが、これは既存ゲーム互換の確認であり、三角形接触をゲームへ適用した証拠ではない。

次の最小受入は、入力編集・失敗/候補区間の検査・JSON保存を行う**[手動ブラウザtriangle lab](SPHERE_TRIANGLE_LAB_PLAN.md)**である。ゲームmesh衝突、三角形storage/隣接面/manifold、時間方向CCD、閉固体内部、摩擦支持、流体・損傷は別の未完項目である。有限の照会を一般物理・専門シミュレータの完成や性能保証へ拡張しない。
