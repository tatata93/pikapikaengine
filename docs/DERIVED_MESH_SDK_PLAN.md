# 次の受入: 派生meshの有界SDK接続

2026-11-03。**提案・未実装**。Native純粋核の受入は[DERIVED_MESH.md](DERIVED_MESH.md)と[検証記録](../reports/2026-11-03-derived-mesh.md)。次は既存の実LBS結果を同じ核へ渡し、主WASMとの照合を行う。rendererやrobotの原本を変更する前にこの境界を確認する。

## 実容量と候補ABI

`simulation_api.h`の現行入力F64は49152、U32は98304、出力F64は64。既存63exportsのsignature/容量/API version1を保持し、次の2関数を追加する候補とする。

```c
int32_t pp_sim_derived_mesh(uint32_t f64_count, uint32_t u32_count);
int32_t pp_sim_derived_mesh_record(uint32_t kind, uint32_t index);
```

F64はheader8 `[vertexCount, triangleCount, maxVertices, maxTriangles, sqrtRefinements, 0,0,0]`と位置3N、U32はtriangle3T。SDK実入力上限は2048頂点・32768三角形。最大F64入力6152、U32入力98304で既存領域に収まり、新しいindex packingや容量増加を必要としない。

sourceの131072三角形、Native純粋核のhard131072とSDK32768を区別する。SDKの32769以降、予算/個数の超過、欠損/余剰、非整数、非finite、予約値不一致は交換拒否とし、黙って分割/切捨てしない。Native核の既定32768faceは保持する。

summary候補は20値。status/reason/geometry有無、位置数/面数/audit数/float数、失敗vertex/faceの有無とindex、sqrt総refinement/limited面数、予約0、min3/max3。getter候補はkind0=位置3、1=triangle3、2=faceのinterleaved18、3=audit26。

audit26候補はface、cross6、Q2、normalized有無+6、normal有無+3、error有無+3、sqrtrefinement、limited。未設定のfieldはflagと予約zeroで区別する。Float32値は正確にdoubleへ拡張して返し、JS側で同じFloat32 bitsへ戻す。geometryなし時に描画用getterを成功させず、audit prefixは診断専用に保つ。field順とflag規約は実装前に固定する。

## transactionと原本

既存skin queryと同様に、交換preflight→候補prepare→packet全値監査→snapshot commitとする。不正交換/getterは旧snapshotと出力を保持する。受理したモデル失敗は新しいgeometryなし結果へ更新する。他のskinning/motion/World recordは独立とし、global resetだけ新recordも消す。返すJS arrayはcopied snapshotである。

新Native probeでowned Sourceの全rest/context検査と実`Source::sample`を呼び、その成功位置と元triangleだけをprepareへ渡す。Source parserを主SDKへ移植しない。前段失敗では派生核を呼ばず、失敗のstageを保持する。原本再保存bytesとscene/sample不変を確認する。

## 最小の独立通し試験

1. 通常帯のt0/.5/1/2/3loop。既知rest/90度の解析、全Float32位置/normal/bufferのNative/main比較、保存原本不変。
2. 既存Source::exampleの全頂点をroot7/child19の等重みにし、child19のt1 rotationを`[0,0,1,0]`へ変える。pivotはx1なのでchild paletteは`(-x+2,-y,z)`。実LBSが全xy頂点を厳密に`(1,0,0)`へ写し、sample completed→prepare degenerateを確認する。既存directzero fixtureをこの通し試験の実測と混同しない。
3. 前段underflow/悪いinverse/stale rest、後段Float32 collapse/quality未確定、予算不足と同一instanceでの復帰。失敗時に古い成功geometryを表示しない。
4. 実2048頂点/32768faceの同時上限と1超過、snapshot/getter/reset/World clock保持、元bufferのbit一致。Native65536/131072の受入と混同しない。
5. Pythonの元40fixtureを用い、既存exact丸め/面積/法線checkerで実WASM出力も検査する。NativeとWASMが同じ誤りを返しても参照が検出する負例を保持する。

固定Emscripten6.0.13のstrict flagsで新source/headerを明示リストへ追加し、全source/artifact/license SHAとリンクmemberを監査する。既存63exportsの回帰と新65exportsを区別し、過去のSDK配布物を新核入りとして報告しない。外部packageを追加しない。

その後に小さいmeshの実3D描画を接続する。局所CPU認証をworld/view/clip/GPU算術やraster被覆へ拡張しない。最大容量の参照核はローカルで約31秒の観測で、実時間性能の検証と改善は別の受入を持つ。
