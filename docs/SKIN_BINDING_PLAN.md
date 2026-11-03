# 所有するskin binding原本: 計画と受入

2026-11-03。**実装・公開受入済み（4356c8a）**。確定した形式・APIは[SKIN_BINDING_FORMAT.md](SKIN_BINDING_FORMAT.md)、数値と原本の検証は[記録](../reports/2026-11-03-skin-binding.md)。以下の候補節は実装前の設計記録として残す。実装では独自strict JSON scanner、fingerprint、restBones snapshot、既存出力を置換しないNative CLIを採用した。既存scene v1/v2とIRON FIELD原本は変更しない。

## 最初の原本

一つのsidecarが一つのmesh・全author influence・全joint・motion原本全体を所有する。参照先fileを探索せず、保存/再読込だけで位置照会の入力を再構成できることを目標にする。sceneとの対応は必要な時に明示的なcontext照合として行う。形状やjointを共有するasset database、複数clip、scene階層、外部format importはこの初段へ含めない。

候補schema（未固定）は次の形とする。

```js
{
  version: 1,
  kind: "mesh-skin-binding",
  name: "Original arm",
  units: "m-s-kg",
  axes: "right-handed-y-up",
  space: "mesh-local-is-skeleton",
  target: { objectId: "arm-mesh", nativeId: "42" },
  mesh: { version: 1, positions: [], triangles: [] },
  influences: [ [{ boneId: 7, weight: 1 }] ],
  joints: [ { id: 7, restWorld: [], inverseBind: [] } ],
  motion: { /* 既存skeletal-motion v1原本の全フィールド */ }
}
```

空配列は構造を示す例示で、実際の有効原本ではない。位置はmeshに一度だけ保存し、influencesの件数/順をpositionsと一致させる。永続vertex IDは導入せず、現mesh v1の配列indexを使う。triangle配列とその順序も保持する。motionは既存のbones/clip/tracks/keysをすべて持ち、非選択boneやtrackを落とさない。jointのrestWorldとinverseBindはcolumn-major16値、保存した値を正規化・再生成しない。weightはauthor値のままで、作業用正規化を原本へ書き戻さない。

## IDと全形状の対応

- browser objectIdは文字列、Native側の保存は正準十進文字列nativeId。Native Entity.idの型はuint64でも、現Sceneと共通SDKの受理域は1..2^53−1であり、全uint64を扱えるとはしない。
- browserの作成時は既存portable scene変換が解決したmappingを使い、objectId/nativeIdの両方を確認する。既存のFNV由来mappingの衝突はエラーで、自動再番号付けや別objectへの転送をしない。
- Native Sceneはbrowser-metaをopaque annotationとして保持する。Native側のcontext照合はnumeric IDとmeshを確認し、browser aliasは宣言値として保存する限界を明示する。
- contextの対象が未知、非mesh、または全positions/trianglesと両配列順が異なる場合は拒否する。頂点数だけ、境界だけ、形状hashだけで一致としない。配列内容として観測できる位置編集・頂点並べ替え・triangle順変更をdirtyとする。
- fingerprintの算法/格納形式は未決定。索引・選択・診断に使っても、hash一致で全形状比較を省略しない。衝突を模擬した試験でもdirty meshを受け入れない。

形状の±0比較規約は実装前に固定する。全値/順序を比較し、epsilonによる近似一致は導入しない。object位置・yaw・scale・色の変更はmesh/rest変更と分離し、位置変形後のobject world変換を一度だけ適用する後段の契約とする。boxをmeshへ暗黙変換したりscene v1を勝手にv2へ更新しない。

内容が完全に同一な重複頂点の概念的な入替や、同じ配列へ戻った編集履歴はこの形式に記録されない。full比較でもその違いは検出できず、「全てのindex変更を検出する」とはしない。persistent vertex IDと編集履歴の対応は別versionの受入として残す。

## restの一致と数値評価

全motion boneのrestと親木を共通C++へ渡し、trackを除いたrest FKを計算する。その全IDと行列をstored restWorldと比較する。bone/rest/親関係の変更、追加、欠損、対応する行列の不一致はstaleとして拒否し、inverse bindの再計算で隠さない。キー編集だけでrestが同じならbindingを維持する。原本のquaternionの符号/大きさは既存motion契約を継承し、JSでFKやinverseを再実装しない。

sourceとして保存できること、context/restが一致すること、deformがnumerically completedになることを分ける。保存したinverseの品質・正weightのunderflow・極端な値による失敗を、codecが黙って修復/丸め/正規化しない。未検証sourceから有効な変形位置を表示せず、C++のcompleted結果だけを派生表示へ渡す。構造parseとruntimeを要するrest検査をどのpublic APIで分けるかは、実装開始前にNative側と固定する。

## JSONとportableの候補

JSONはschemaの未知/重複キー、sparse配列、非有限値、非零decimalのzeroへのunderflow、壊れたUnicodeを拒否する。通常のJSON.parseだけでは重複キーや数値化前のunderflowを検出できない。**原著の字句scannerを置くか、数値をtagged bitsで保存するかは未決定**であり、ここでは実装済みとしない。author weightとinverseBindのsigned zeroは保存する。通常のJSON.stringifyに任せて-0を失わないことを受入に含める。既存motionのzero正準化契約を変更する計画ではない。

portableは既存motion原本をUTF-8の長さ付きblockへ内包する案とする。

```text
pikapika_skin 1
name "Original arm"
object "arm-mesh" "42"
space mesh-local-is-skeleton
mesh <vertexCount> <triangleCount>
... vertex/triangle records ...
influences <vertexCount>
... per-vertex count and boneID/authorWeight records ...
joints <jointCount>
... id, restWorld16, inverseBind16 records ...
motion_bytes <N>
<既存pikapika_motion 1のUTF-8 N bytes>
end_skin
```

NはJSのUTF-16文字数ではない。block境界とUTF-8を検査し、その部分だけを既存motion parserへ渡す。内部のendと外部のend_skinを混同しない。全体の余剰token、途中EOF、長さ不一致、未許可escapeを拒否する。Nativeへ新JSONライブラリを導入せず、Web JSON→portable→Native→portable→Web JSONを最初の往復とする。

## 初段の予算と候補path

| 項目 | 提案上限・扱い |
|---|---|
| 全source text | UTF-8 8MiB。超過は拒否 |
| 内包motion | 既存4MiB、128bone、128track、合計4096key |
| source mesh | 3..2048vertex、1..131072triangle。triangle上限は既存meshと同じだがtext予算で拒否され得る |
| influence | 各頂点1..4、全体8192。重複/未知IDはweight0でも拒否 |
| joint | 1..128、全motion boneとのID対応 |
| JSON | 候補depth16。token/文字列/escape予算の詳細はparser方式とともに固定 |
| portable | 外側recordの候補line上限4096B。motion blockは既存parserの4MiB契約を使う |

countとbyte数を検査してから確保/乗算し、末尾まで消費してから候補をcommitする。Native核65536vertex/262144 influenceをsidecar初段の成功域へ広げず、超過時に分割/切捨てしない。

候補pathは `engine/skin-binding.mjs`、`core/include/pikapika/skinning_io.hpp`、`core/src/skinning_io.cpp`、`tools/skinning_cli.cpp`。所有原本は値を保持し、kernel用spanは照会中だけ作る。既存scene/motion形式や共通ABIの変更は最初のcodec往復には必要としない。Native側との確認項目はschema/key名、ID域、zero規約、full geometry比較、rest行列比較、長さ付きblockと予算、保存可能/数値成功の二段階を優先する。

## 最小受入の順序

1. 所有原本とstrict JSON/portable codec、全context/rest照合を実装する。外部fileを自動解決しない。
2. Native CLIでroundtrip、明示weight編集、embedded motionのsample、任意scene context照合を行う。scene/motionを保存先にせず、出力を開く前に候補全体を検査する。入力と同じpathや既存出力の置換規約は先に固定する。
3. Webで読込→照合→実C++ sample/deform→別名保存を検証する。確認用ラボJSONとは別の原本formatにする。

受入には全原本往復、Unicode/最大ID/signed zero/subnormal、隠れたtrack保持、キー編集によるbinding維持、rest/形状/順序変更拒否、fingerprint衝突模擬、未知ID、ファイル予算境界と途中EOF、失敗時の既存出力保持を含める。scene v1/v2とsample原本のbyte不変も確認する。法線再生成、Float32 collapse/反転面、GPU/ゲーム描画、接触形状・材料損傷、IK/物理制御は次段の別受入である。

新規外部コード/素材/ライブラリを導入する計画ではない。既存Khronos等の調査範囲と原著位置核は [SKINNING.md](SKINNING.md)、実装済みSDKは [SKINNING_SDK_PLAN.md](SKINNING_SDK_PLAN.md)。本体ライセンスは未選定のまま。

## 実装後の次段

JSON/portable/Native往復、全形状照合、全rest照合とブラウザ編集は初段を満たした。次は原本を変更しない派生meshとして、位置のFloat32変換、有限性・面積退化・法線生成の条件を定義し、小さい3D描画へ接続する。単なる旧法線との内積の符号を一般の面反転判定としない。接触・塑性変形・IKは別の物理/制御受入を持つ。
