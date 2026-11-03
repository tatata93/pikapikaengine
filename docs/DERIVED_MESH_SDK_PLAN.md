# 派生meshの有界SDK接続

2026-11-03。**実装済み・ローカル/公開検証済み**。Native純粋核の受入は[DERIVED_MESH.md](DERIVED_MESH.md)と[検証記録](../reports/2026-11-03-derived-mesh.md)。当初の提案を以下のABIに固定し、既存の実LBS結果を同じC++核へ渡す主WASM接続まで検証した。renderer/GPUおよびrobotへの接続は次の受入で、既存原本は変更していない。

## 実容量と確定ABI

`simulation_api.h`の現行入力F64は49152、U32は98304、出力F64は64。既存63exportsのsignature/容量/API version1を保持し、次の2関数を追加した。主SDKは合計65exports。

```c
int32_t pp_sim_derived_mesh(uint32_t f64_count, uint32_t u32_count);
int32_t pp_sim_derived_mesh_record(uint32_t kind, uint32_t index);
```

F64はheader8 `[vertexCount, triangleCount, maxVertices, maxTriangles, sqrtRefinements, 0,0,0]`と位置3N、U32はtriangle3T。SDK実入力上限は2048頂点・32768三角形。最大F64入力6152、U32入力98304で既存領域に収まり、新しいindex packingや容量増加を必要としない。

sourceの131072三角形、Native純粋核のhard65536頂点/131072三角形とSDK2048/32768を区別する。SDK実個数の上限超過、欠損/余剰、非整数、非finite、予約値不一致は交換拒否とし、黙って分割/切捨てしない。Native核の既定32768faceは保持する。

空のpositions/triangles（個数0）とuint32全域のsettings/indexは交換可能とし、C++のモデル判定へ渡す。例えばmaxVertices=0/65537、sqrtRefinements=0/257、重複indexや実頂点範囲外のuint32 indexは、受理後にinvalid_input等の新しいモデル結果となる。非整数・負数・uint32超過は交換拒否。指定予算を下回ることによるbudget_exceededと、SDK実容量を超える交換拒否も分ける。構造が同じ元40fixtureは全件が実C++モデル結果で、host拒否を合成結果へ置換していない。

summary20は次の順に固定した。

| Offset | 値 |
|---|---|
| 0..2 | status, reason, hasGeometry |
| 3..6 | 出力vertex数, triangle数, audit数, interleavedのfloat数 |
| 7..10 | hasFailedVertex, failedVertexOr0, hasFailedFace, failedFaceOr0 |
| 11..13 | sqrt総refinement, limited面数, reserved0 |
| 14..19 | minimumXYZ, maximumXYZ（geometryなしなら全0） |

getterはkind0=位置3、1=triangle3、2=faceのinterleaved18、3=audit26。status/reasonは[derived_mesh.hpp](../core/include/pikapika/derived_mesh.hpp)のenum順を変更せず転送する。

audit26は `face[0], cross6[1..6], Q2[7..8], hasNormalized[9], normalized6[10..15], hasNormal[16], normal3[17..19], hasError[20], error3[21..23], sqrtRefinements[24], limited[25]`。各intervalは下限/上限の順。未設定のpayloadは0で、flagがない0を法線や誤差の成功値と解釈しない。Float32値は正確にdoubleへ拡張して返し、JS側で同じFloat32 bitsへ戻す。geometryなし時に描画用getterは成功せず、audit prefixは診断専用。

## transactionと原本

既存skin queryと同様に、交換preflight→候補prepare→packet全値監査→snapshot commitとする。不正交換/getterは旧snapshotと出力を保持する。受理したモデル失敗は新しいgeometryなし結果へ更新する。他のskinning/motion/World recordは独立とし、global resetだけ新recordも消す。返すJS arrayはcopied snapshotである。

Native probeでowned Sourceの保存restとC++rest FKを照合し実`Source::sample`を呼び、その成功位置と元triangleだけをprepareへ渡した。Web側でも同じportable原本を読み、C++rest FK/current FK/deformSkinからprepareへ接続して照合した。Source parserは主SDKへ移植していない。前段失敗では派生核を呼ばず、失敗のstageを保持する。原本再保存bytesの不変を確認した。

JS `runtime.prepareDerivedMesh({positions,triangles},{maxVertices=2048,maxTriangles=32768,sqrtRefinements=128})` は `{status,reason,failedVertex,failedFace,geometry,audits,sqrtRefinements,sqrtLimitedFaces}` を返す。geometryは成功時のみ `{positions:[Float32Array(3)],triangles:[Uint32Array(3)],interleaved:Float32Array,minimum:Float32Array(3),maximum:Float32Array(3)}`。auditはinterval配列とoptional normalized/normal/normalErrorを保持する。全配列はcopyで、JSの逆行列/LBS/面法線計算によるfallbackはない。旧SDKでexportがなければ明示的にunavailableとなる。

## 実施した独立通し試験

1. 通常帯のt0/.5/1/2/3loop。既知rest/90度の解析、全Float32位置/normal/bufferのNative/main比較、保存原本不変。
2. 既存Source::exampleの全頂点をroot7/child19の等重みにし、child19のt1 rotationを`[0,0,1,0]`へ変える。pivotはx1なのでchild paletteは`(-x+2,-y,z)`。実LBSが全xy頂点を厳密に`(1,0,0)`へ写し、sample completed→prepare degenerateを確認する。既存directzero fixtureをこの通し試験の実測と混同しない。
3. 前段underflow/悪いinverse/stale rest、後段Float32 collapse/quality未確定、予算不足と同一instanceでの復帰。失敗時に古い成功geometryを表示しない。
4. 実2048頂点/32768faceの同時上限と1超過、snapshot/getter/reset/World clock保持、元bufferのbit一致。Native65536/131072の受入と混同しない。
5. Pythonの元40fixtureを用い、既存exact丸め/面積/法線checkerで実WASM出力も検査する。NativeとWASMが同じ誤りを返しても参照が検出する負例を保持する。

固定Emscripten6.0.13のstrict flagsで新source/headerを明示リストへ追加した。ローカル主SDKはWASM590964B、SHA256 `67daefd24c39af1aefa516d28b35c11808684604bed457c1e16eed15b64e8f73`、glue50029B。既存63exportsと新65exportsを区別し、過去のSDK配布物を新核入りとして扱わない。新しい外部packageは導入していない。

新SDKのNode10/10・skip0が成功した。固定40件は16completed/24期待失敗で、Source通しprobeは11件。Native/main WASMで全2841数値のbitが一致（固定40は1272、Source11は1569）。位置・法線・expanded bufferの全Float32 bits、interval端点、optional値、診断とcounterを含み、signed zeroはhex記録も保存した。実2048頂点/32768面の同時容量と1超過、失敗後の復帰、他kernelのrecord/World clock保持とresetも検証した。

固定40の実WASM packetへ元のFraction checkerを直接適用し、binary32丸め、cross/Q包含、向き付き単位法線と候補誤差を独立に監査した。completed17面/51法線成分に加え、失敗結果内の成功prefix1面/3成分を認証。57候補誤差成分には未確定で失敗した候補も含むため、全57成分の成功とは数えない。認証済み候補の最大誤差上限は `2.384185870951683e-8`。Native/main-wasm各backendで自己試験7群、受入control2件、改変負例36件が成功し、数学条件と固定40入力fingerprintは共通である。

ローカル証拠は `build/derived-mesh-sdk-js/final-g3q0b0o7/`（原本・SDK snapshot、provenance、再現コマンド、全raw/hex）、独立負例は `build/derived-mesh-reference-sdk-native/run-fb54vt3f/` と `build/derived-mesh-reference-sdk-main-wasm/run-1bwlmtmn/`。コードd43dcd4のLinux CI/Pagesと公開ブラウザ12操作が成功。確定記録は[今回の検証](../reports/2026-11-03-derived-mesh-sdk.md)。

次は小さいmeshの実3D描画を接続する。ここでのCPU/WASM局所認証はworld/view/clip/GPU算術・raster被覆の保証を含まない。以前のNative参照核で約31秒のローカル観測は保持するが、新SDKで実時間性能一般が確認されたという意味ではない。実時間性能の検証と改善は別の受入を持つ。
