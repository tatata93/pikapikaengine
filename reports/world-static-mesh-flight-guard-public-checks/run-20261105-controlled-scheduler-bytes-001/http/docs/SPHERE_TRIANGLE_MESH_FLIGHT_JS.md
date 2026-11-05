# 保持荷重・丸め自由伝播guardの所有JavaScript API

2026-11-04。ローカル受入成功。公開CI/Pagesは別途確認する。[検証記録](../reports/2026-11-04-sphere-triangle-mesh-flight-js.md)に全結果と初回失敗を保存した。[事前契約](SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)と[raw ABI](SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md)を継承し、既存92-export SDKを使用する。C++核・SDK artifact・World・ゲームの計算は変更しない。

```js
const sphere = {
  id: 1, position: [1, 3, 1], velocity: [0, 0, 0],
  mass: 2, force: [0, 0, 0], gravity: [0, -4, 0], radius: 0.25,
};
const triangles = [{id: 37, vertices: [[0, 0, 0], [4, 0, 0], [0, 0, 4]]}];
const result = runtime.querySphereTriangleMeshHeldLoad(sphere, triangles, 0.25);
```

距離・半径はm、時間は秒、質量はkg、外力はN。元の質量・外力・重力をNativeへ渡し、JavaScriptでF/mや距離を再計算しない。保持荷重の二次曲線の安全prefix・貫通開始窓と、丸めた伝播を囲む非接触guardを区別する。`not_certified`は安全を意味しない。

```js
const body = {
  id: 1, isStatic: false, mass: 2, radius: 0.25,
  inertiaDiagonal: [1, 1, 1], position: [1, 3, 1],
  orientation: [0, 0, 0, 1], velocity: [0, 0, 0],
  angularMomentum: [0, 0, 0], force: [0, 0, 0], torque: [0, 0, 0],
  material: {restitution: 0, friction: 0},
};
const guarded = runtime.querySphereTriangleMeshFreeFlightGuard(
  body, [0, -4, 0], triangles, 0.25,
);
```

bodyは全field必須。既存World DTOの`linearVelocity`/`inertia`を暗黙変換しない。guardは元body・荷重を保ち、成功時にHでの完全candidateを返すread-only照会である。全pairの順序選択・時間進行・衝突応答・摩擦・Worldへの反映は後続となる。

## 入力captureと所有

全6能力を最初の書込前に確認する。旧86-export SDKや欠損を拒否し、別solverへのfallbackや隠れた再queryを行わない。全原本・設定・配列長・成分・ネスト参照を一度読み取り、同じ値を検査とencodeへ使用する。0..64面、正確な配列長、有限数値とsafe IDを要求する。空集合・重複ID・有限の物理域外・uint32範囲内の設定0などはNativeのモデル診断へ渡す。

`originalInput`に全入力と32値/48値echoをコピーする。元入力の負零と、Native整数設定が正零へ変換されたsnapshotを分ける。guardの`isStatic`はbooleanであり、raw static flagの負零をこの入口から入力できるとは扱わない。

結果は全audit・証明島・partition/frontier/tail/current・Work・lastMesh全行と候補・snapshotを所有する。guardでは元body、inflated held-load照会、候補bodyの所属を分ける。caller、originalInput、Native snapshot、別時点のDTO、共有scratchの配列やobjectを共有しない。所有は編集禁止を意味しない。

元runtime/native/export/prototypeを置き換えず、元receiverで呼ぶ。getter出力は次call前にコピーし、ptr/viewを再取得する。module共有scratchの同期・非再入契約を継承し、同じmoduleへの並行交換は対象外。

## metadataと数学の受入境界

packet長・全数値・enum/count/flag・予約正零・不在payload・原本echo/source・所属・closedな秒区間の全被覆・幅優先履歴・Workの既知値/上限を検査する。旧entryの無次元dyadic parameterへ変換しない。プリミティブのmetadataに負零を認めず、実区間/KKT/原入力の合法な負零は保存する。

これは交換と所有の監査であり、幾何・sqrt・KKT・F/m・丸め上界をJavaScriptで解き直す数学solverではない。実WASMの所有DTOを固定Native結果へbit照合し、WASM由来DTOだけを独立Fraction参照へ送る。host拒否を実モデルへ数えず、Native補填で成功件数を作らない。

queryの24値summaryは正式decoderが読み取り検査する。共有出力は後続getterで上書きされ、summary専用getterはない。所有APIの後から実raw summaryを取得できたとは主張しない。全21kind/lastMesh/candidateの実getter照合、全DTO照合、summaryの人工改ざん試験、前段raw wire試験を出自別に記録する。

入力/能力拒否は書込前に止まる。正常query後のdecoder拒否ではDTOを返さないが、Native record/outputのrollbackを保証しない。人工packetの例外・view差替え試験は、実allocation faultや実memory growthの注入とは区別する。HEAP容量の観測をused heap・stack高水位へ読み替えない。

新外部依存・転載素材・有料serviceなし。本体license未選定。流体・材料損傷・車両航空鉄道・IK制御・高精度撮像の残件は維持する。
