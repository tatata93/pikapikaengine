# Skin binding v1: 実装契約

2026-11-03。実装・公開受入済み。コード4356c8aのCI/Pagesと18公開操作を検証記録で確認した。既存scene/motion本体は変えず、sidecarが原本mesh/weight/joint/rest snapshot/full motionを所有する。

```
{version:1, kind:'mesh-skin-binding', name,
 units:'m-s-kg', axes:'right-handed-y-up', space:'mesh-local-is-skeleton',
 target:{objectId,nativeId}, fingerprint,
 mesh:{version:1,positions,triangles},
 influences:[[{boneId,weight}]],
 joints:[{id,restWorld,inverseBind}],
 restBones:[{id,parentId,rest:{position,rotation,scale}}],
 motion:<既存skeletal-motion原本全体>}
```

全keyは必須で、未知keyは拒否する。型・所有copy・配列順を保存する。weightsやinverse bindを正規化・再構築しない。restBonesはbind時のlocal rest/parentのsnapshotで、名前は含まない。motionの全bone ID/parent/local TRSをIDでsnapshotと数値exact比較し、rest変更を拒否する。±0は比較上同値。motion骨配列の並べ替え、名前、キーの編集はこのsnapshotを変更しない。評価時にはさらにC++のtrack無しrest FKとstored restWorldを全ID/matrixで照合する。world行列だけでは同じworldとなる親編集を検出できないためlocal snapshotも持つ。手動で全snapshotを整合するよう書き直した履歴まで識別する形式ではない。

数値構造と評価成功を分ける。affineはcolumn-major16値、最後の行0,0,0,1、要素有限±1e150。singular rest、不良inverseの構造保存は可能で、数値照会時に品質失敗となり得る。weightは有限非負、各頂点1..4個の一意な既知bone ID、少なくとも1positive。positive underflowを起こすauthor値も保存し、CPPのnumerical_failureを隠さない。weight/inverse/restWorld/meshのsigned zeroは保存する。embedded motion自身のzero正準化は既存契約を継承する。

上記meshのsigned zeroはpositionのdoubleを指す。triangle indexとparentIdの整数zeroはNativeのuint型に合わせ+0へ正準化し、doubleの保存規約と区別する。

source meshは既存Mesh v1妥当性に加えて3..2048vertex、1..131072triangle、合計8192influence。joint/restBones/motion boneは1..128でID集合一致。IDは1..2^53−1。全source text UTF-8 8MiB、motion portable block4MiB、外行4096B。上限は確保/乗算前に検査し、分割/切捨てしない。namesは既存motionと同じvalid UTF-8・control禁止・256bytes以下。objectIdは非空、UTF-16 units96以下かつUTF-8 384bytes以下、control禁止。nativeIdは正準十進文字列1..2^53−1。

fingerprintは非暗号FNV1a64の小文字hex16文字。offset cbf29ce484222325、prime100000001b3、64bit wrap。入力bytesはASCII `pikapika_mesh_fingerprint 1\n`、u32LEのmesh.version/positionCount/triangleCount、その後全positionsのIEEE754 binary64 little endian、全trianglesのu32LE。座標zeroだけhashの際+0へ正準化する。原本のzeroは変更しない。hash照合後も対象contextの全position/triangleと観測可能な配列順をexact比較する。±0は同値でepsilon一致は導入しない。同一内容の重複頂点の概念的入替は検出できない。

Webは既存savePortableScene→parsePortableSceneでobjectId/nativeId mappingを解決する。Native contextはnumeric IDとmeshを照合し、browser objectIdは宣言aliasとして保持する。objectのworld transform/色の変更は形状照合と分離する。boxの自動mesh化、scene format更新、外部file探索はしない。

## Portable v1

```
pikapika_skin 1
name "Original arm"
object "arm-mesh" "42"
space mesh-local-is-skeleton
fingerprint <hex16>
mesh <N> <T>
vertex <x> <y> <z>
... N行
triangle <i> <j> <k>
... T行
influences <N>
weights <C> <boneId> <weight> ...
... N行
joints <J>
joint <id> <R16> <I16>
... J行
rest_bones <B>
rest_bone <id> <parentId> <P3> <Q4> <S3>
... B行
motion_bytes <M>
<既存pikapika_motion 1のexact UTF-8 M bytes>
end_skin
```

MはJSの文字数でなくUTF-8 bytes。blockは既存motion serializerの終端LFを含み、直後にend_skin行を置く。quote escapeは既存motion portableと同じquote/backslashのみ。decimalは有限値とsigned zeroをroundtripし、非zero mantissaがzeroへunderflowすれば拒否する。unknown/trailing token、壊れたUTF-8、長さ違い、途中EOF、余剰keyを拒否する。Nativeへ新しいJSON parserは入れず、Web JSON→portable→Native→portable→Web JSONを検証する。

JSONは原著strict scannerを用い、重複key・nonfinite・decimal underflow・unpaired surrogate・trailingを拒否する。出力も独自のfinite number emitterで-0を保持する。rootの`engine/strict-json.mjs`は`parseStrictJson(text,{maxBytes=8388608,maxDepth=16,maxNodes=1000000})`、`stringifyStrictJson(value,同options)`、`utf8Length(text)`を提供する。JSONはcompact出力である。

## Web API

- `meshFingerprint(mesh)` → hex16。
- `createSkinBindingSource(input)` → 全schemaを検査した所有copy。fingerprintは必須で再計算照合する。runtime/contextの数値照会はしない。
- `parseSkinBindingSource(text)` / `serializeSkinBindingSource(source)` → strict JSON。
- `parseSkinBindingPortable(text)` / `serializeSkinBindingPortable(source)` → 上記portable。
- `setSkinInfluences(source,vertexIndex,influences)` → 原本を変更せず、全候補を検査した新source。
- `setSkinWeight(source,vertexIndex,boneId,weight)` → 既存influenceだけ編集し、同様に新source。
- `validateSkinBindingContext(source,sceneDataOrScene)` → true / 明示例外。scene原本を変更しない。
- `evaluateSkinBinding(runtime,source,seconds,{loop=false,scene}={})` → `{rest,pose,deformation}`。runtimeのsampleMotion/deformSkinだけで計算。rest mismatch/context/pose failureは例外、deformationのC++モデル失敗はpositions:nullを含むresultとして保持する。source保存をcompletedへ読み替えない。
- `defaultSkinBindingSource(runtime)` → オリジナル2骨6頂点の帯とfull motionをC++rest FK/bindから作成する。targetはobjectId='arm-mesh',nativeId='42'。可視三角形/法線/Float32/接触の完成とはしない。

## Native APIとCLI

`skinning_io::Source`はowned値を保持し、kernel spanは照会中だけ生成する。validateは構造/rest snapshot/fingerprint、sampleはrest FK照合/current FK→deform、scene matchはnumeric ID/full geometryを扱う。変更はcandidate.validate後にcommitする。

CLI候補: `init newfile`、`inspect file`、`roundtrip in newout`、`weight in newout vertex boneId weight`、`sample file seconds [loop]`、`match file scene`。数値sampleはJSON等のstdoutへ出す。出力は入力と同じpath/既存pathを拒否し、全候補をserializeしてから排他的createを行う。既存出力を破損させず、不正データを成功として保存しない。Windows/POSIXの既存OS機能だけを使う。Web側の原本再読込とNative CLIの独立再読込を別々に検証する。
