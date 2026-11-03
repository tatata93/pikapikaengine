# 描画用の局所Float32 geometry

2026-11-03。Native C++の純粋核を実装・公開受入済み。修正コードa67b0abのLinux CI/Pagesと教材表示を検証記録で確認した。公開済みSDKやrendererへ接続したという意味ではない。[計画](DERIVED_MESH_PLAN.md)から固定した契約を記す。

```cpp
#include "pikapika/derived_mesh.hpp"
auto result = pikapika::derived_mesh::prepare(positions, triangles, settings);
if (result.status == pikapika::derived_mesh::Status::completed) {
    // geometry is an owned snapshot; source and input spans remain unchanged.
    const auto& buffer = result.geometry->interleaved;
}
```

位置はSI metresのmesh-local double列、triangleはuint32 index3個の列。原本の全属性を再構築するAPIではない。出力の`Geometry`はFloat32位置列、同じ順序のtriangles、face順のflat-shaded interleaved float列（各cornerでposition3+normal3）、量子化位置のmin/maxを所有する。各faceは3corner・18float。入力を借用したviewや次の照会で変わるbufferではない。

| 条件 | 初段の扱い |
|---|---|
| 頂点 | 3..2048既定、設定hard上限65536 |
| 三角形 | 1..32768既定、設定hard上限131072 |
| 座標 | 全頂点の全成分がfinite、±1e6 m以内。未参照頂点も検査 |
| indices | 全て範囲内、同一faceの3indexは相異なる |
| sqrt予算 | 既定128、設定1..256。既存sqrt核の端点refinement契約を継承 |
| 面積品質 | exact binary64 `1e-24` m^4をfloorとする |
| 法線精度 | exact binary64 `1e-6`を成分ごとの最大誤差上限とする |

超過を切捨て・自動batchしない。sourceの上限131072triangleより初期描画予算が小さいことを明示する。構造preflight後に一度Float32へnearest-even丸め、その同じFloat32をdoubleへ正確に拡張して、区間edge・cross `C` と `Q=ΣC_i²`を求める。`Q`は面積m²そのものではなくcross norm squared（m^4）。少なくとも一成分のstrict nonzeroと`Q.lower()>floor`を必要とする。

単位法線の参照は区間`C / sqrt_enclosure(Q)`。同じ丸め後の点から作った候補をFloat32へ格納し、候補と参照区間の差の最大絶対端点を成分ごとに監査する。libm候補の精度を無条件に仮定しない。sqrtがlimitedでも誤差条件を満たせば受理し、満たさなければ未確定を返す。各成分の上限、区間、refinement数/limitedをauditへ保持する。

statusはcompleted、invalid_input、budget_exceeded、degenerate、quality_rejected、quality_unresolved、numerical_failure、unsupported_environment。cross全成分が点0ならdegenerate、Q上限<=floorならquality_rejected。crossの非零やfloor/法線精度を確認できない場合はquality_unresolvedで、成功へ変えない。失敗face/vertexと安定したreason enumを返す。メモリー不足時のmessageが空でもreasonを維持する。

失敗時の`geometry`は常に空。`audits`は診断用のprefixであり、描画してよい部分bufferではない。正常な面の後に失敗しても、元の成功snapshotと入力は変わらない。

## 保証の範囲

包含と法線上限は既存[Intervalのstrict build/CPU環境](INTERVAL.md)に加え、binary32 nearest-even/段階的underflowのprobeを満たす条件付きである。丸め/control modeを変更せず、非対応環境を拒否する。通常算術が変える浮動小数exception status flagsの保持までは保証しない。runtime probeはcompilerや全実装の形式検証ではない。

監査対象は量子化された局所三角形である。局所では有効な1mmの辺も、Float32のworld平行移動で1e6mへ加えると潰れ得る。world/view/clip/GPU算術、raster coverage、自己交差、材質・材料損傷の完成とはしない。旧法線と新法線の内積の符号を一般的な反転判定に使わない。flat normalだけで、smooth normal/tangent/UV生成は含まない。

Native試験の`--fixtures`は入力double値・Float32 bits・全audit・全bufferを出力する。独立Python Fractionは丸めとcross/Qを再計算し、法線について平方を用いた有理不等式で参照区間と誤差を検査する。解析LBS-collapse fixtureは既知のcollapsed位置を直接与えるもので、この段では実LBS→描画のend-to-end接続を検証していない。

## 有界SDKと原本からの通し照会

次段の[SDK接続](DERIVED_MESH_SDK_PLAN.md)を実装した。共有WASMの`runtime.prepareDerivedMesh({positions,triangles},settings)`は同じC++核を呼び、最大2048頂点/32768面のcopied snapshotを返す。Native hard上限とSDK交換容量は異なる。失敗はgeometry:nullで、診断auditを描画可能な部分bufferとして扱わない。

新しい`pikapika-derived-probe --fixtures`は実`skinning_io::Source::sample`の成功位置を渡す。11例には等weightの180度LBSによって全頂点が(1,0,0)へ潰れるケースを含み、前段completed・後段degenerateを実測する。既存40例は変更せず、main WASMの実出力にも同じ独立Fraction参照と36負例を適用した。

[原本制作ラボ](../tools/skin-binding-lab.html)の「Float32位置と法線を監査」は手動の別操作。原本・double位置結果・派生結果を分け、時間/原本/Scene変更時に派生結果を破棄する。Canvasの線は従来の位置確認表示で、監査済みbufferの3D描画ではない。このSDK接続時点では3D rendererへ未接続で、次段を以下で区別する。

次段の[小メッシュの手動3D表示](DERIVED_MESH_RENDER.md)を実装・公開受入済み。線表示とは別に、成功bufferの位置・法線を再計算せず既存WebGPU rendererへ渡す。公開WebGPUの受入は新しい記録へ保存し、CPUの局所誤差契約をGPU/world/view/clipや画素へ広げない。
