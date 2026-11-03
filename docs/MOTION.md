# M2制作B: 少数ボーンの秒サンプリングとFK

`pikapika::motion::sample` は、安定した数値IDの親木、rest local TRS、TRS keyを受け取り、指定した絶対秒のlocal姿勢とworld affine行列を返す純粋C++ APIである。既存 `core::Transform` の意味を変更せず、共通C++をNative/WASMで利用する。ボーン名、clip名、原本編集・保存形式、GUIは呼出側が保持する。

この段階はkinematicな原本と再生の基盤である。イベント、IK、関節制限、物理関節、トルク制御、制御グラフ、animation blending、skinning、メッシュへのbind、最終ゲーム描画の完成ではない。

## ID・木・入力の域

`Bone{id,parent_id,rest}` のIDは `1..2^53-1` の整数。`parent_id=0` がrootで、非empty・単一rootの木を要求する。forestはこの初段では受理しない。ID重複、親欠損、自己参照、切り離されたcycleを含む循環を拒否する。入力配列は親順でなくてよい。計算ではparentを先にし、複数のready boneがあれば最小のstable IDを選ぶ。`Pose::bones` は元配列順を保ち、`evaluation_order` はこの計算順のID列である。world joint位置は `world_matrix[12..14]`。

局所TRSはSI metres、右手系、Y up、quaternion `[x,y,z,w]`、列ベクトルである。source translation成分は有限 `±1e6 m`、scaleは各軸 **正の `[1e-6,1e6]`** とする。負scale、zero scale、補間中のzero crossing、mirrorの扱いは後続である。quaternionは有限・非zeroで、最大成分絶対値 `<=1e300`。最大成分で先にscaleし、1..4に収まる二乗和からnormを作るため、巨大値のnorm overflowやsubnormalの全成分二乗消失を避ける。既存 `Quaternion::normalized()` は変更も呼出しもしていない。

`Settings` はbone最大1..128、track最大1..128、全track合計key最大1..4096（既定128/128/4096）。骨数ゼロは不正だがtrackゼロはrest再生として有効。trackは既存boneを一意に指定し、各trackのkeyは一つ以上必要。全骨・全keyのTRS、全ID/親木/track、全時刻/設定をサンプリング前に監査する。count予算外の集合は未受理のbudget failureとしてboundedに拒否する。

`Clip.duration` は有限の `(0,1e9]` 秒。key時刻は閉領域 `[0,duration]` 内で厳密増加する。epsilonによる重複時刻の統合、修正、並べ替えはしない。sample時刻は有限・非負で上限は設けない。NaN/Inf/負時刻は拒否する。

## サンプリング

```
sample(Input{bones, Clip{duration, tracks}}, seconds, Playback::clamp|loop, settings)
```

はframe accumulatorを持たない。`clamp` は `min(seconds,duration)`、`loop` は有限の `fmod(seconds,duration)` を使う。clip終端ちょうどはclampなら終端、loopなら0。巨大clockも受理するが、入力binary64自体に存在しない小さな時刻差は復元しない。実時間同期・固定tick・pause・dropped timeの処理は呼出側の責任である。

trackがないboneは正規化したrest local TRSを使う。trackの最初/最後のkeyより外側はfirst/lastをholdする。key時刻ちょうどでは、そのkeyのtranslation/scaleを直接選び、quaternionだけを正規化したposeを返す。端点を近隣keyへepsilon snapしない。

`Interpolation::step` は直前のkeyをholdし、次key時刻でそのkeyへ切り替える。`linear` はtranslation/scaleを `a*(1-alpha)+b*alpha` で線形補間する。rotationは正規化した両端q0/q1のdotが負ならq1を反転し、

```
q = normalize((1-alpha)*q0 + alpha*sign*q1)
```

というshortest-path NLERPを使う。dot=0の180度tieはsourceの符号を採用する。これは定速SLERPではない。key端点ではsource quaternionの正規化した符号を保つため、qと−qの同じ物理姿勢でも保存するquaternionの符号が境界で変わる場合がある。世界の回転を不連続にする意味ではない。

同じ絶対秒を与えれば、呼出し履歴や描画fpsに依存しない。試験では30fpsの各frame時刻と、それに対応する60/120fpsの時刻を直接計算し、共通秒のworld行列がbit一致することを調べる。異なる積算丸めによって異なる秒を渡した場合や、まだ存在しないイベント処理まで同じと主張していない。

## FKとshear

`Mat4` は16個のdouble、column-major、translationは12..14。local行列を `T*R*S` とし、

```
world(root)  = local(root)
world(child) = world(parent) * local(child)
```

で合成する。worldをTRSへ再分解しない。非一様scaleの親と回転する子の組合せはshearを作り得るため、world TRSだけでは保持できない。解析例のparent scale `(2,1,1)` とchild quaternion `(0,0,1,2)`、scale `(.5,3,1)` ではworldの第1/第2列dotが `-54/25` となり、直交化して消してはいけない。

local/world候補の全成分がfiniteかを確認し、overflow等で非finiteになれば `numerical_failure`、`pose` absentを返す。外部状態は不変で、部分的に更新された骨を成功結果として公開しない。

これはordinary binary64の **点計算** であり、光学の区間kernelと異なり厳密実数の包含ではない。一般の長いhierarchy、極端な比、underflow、cancellation、conditioning、inverseの存在・精度までの一様保証はない。入力域が有効でもancestor scaleの積がoverflowし得るため、その時刻のworldを計算してから原子的に失敗する。一般的な分解可能性、Float32/GPUでの表現可能性、実機での定常fpsも別の受入となる。

strictな参照buildではfast-mathとFP縮約を無効にし、subnormalを保持する標準round-to-nearest環境を用いる。quaternion各成分の極端な比の丸めを無限精度へ拡張する主張ではない。

## 結果と失敗

`Result.status` は `completed / invalid_input / budget_exceeded / numerical_failure`。`pose` が存在するのはcompletedだけ。範囲/グラフ/原本の不正と仕事予算外、数値候補の失敗を区別する。入力と全外部オブジェクトは変更しない。allocation failureは診断文字列の割当も失敗すると外へ伝播し得る。

rootの編集/codec層はraw rest/keyと名前/IDを保持し、samplingの正規化poseを勝手に原本へ書き戻さない。保存→再読込の原本保持と、sampling結果の計算は別の操作である。

## 独立検証

`tests/motion_tests.cpp` の通常試験、完全入力の `--fixtures` JSON、`--oracle` hexadecimal binary64 CSVを使う。CSVは128固有時刻 `j/64` で、rootのTRS線形/NLERP clipに固定childを加えたworld affine行列16値を出力する。

```
python scripts/verify-motion.py native-fixtures.json wasm-fixtures.json --oracle native-oracle.csv --wasm-oracle wasm-oracle.csv
```

checkerはNative path必須、WASM/CSVは任意。`-O`、schema/件数/順序/ID/型/有限値/重複JSON key/固定入力fingerprintの破損をfail closedに拒否する。点入力はJSONをbinary64として読んでから、その値を `Fraction` へ変換する。

独立参照はrow-majorの有理数affine行列で構成し、出力のcolumn-majorへ変換する。任意の非zero raw quaternionに対して、rotation行列の分母を `x²+y²+z²+w²` とすればnormのsqrtを消去できる。参照corpusのNLERPは正規化した端点が有理数か、antipodalに比例する例を選び、blendした未正規化quatから同じ有理数行列を作る。局所q自体の参照には120桁Decimalの独立sqrtも使う。旧C++/JS補間コードをoracleとして呼ばない。

点誤差の受入は `256*2^-52*max(1,|reference|)`。これは当該有限集合の比較閾値であり、全入力のforward error保証ではない。Native/WASMのbit比較も観測された集合だけの証拠である。

解析2リンク、任意骨順と分岐順、shear、T/S補間、normalized key端点、first/last hold、step、loop、antipodal、巨大/subnormal q、subnormal duration、最大ID、missing track、bad graph/key/設定、world overflow、30/60/120fps共通時刻、128bone/128track/4096keyの同時上限と失敗後再利用を含む。

最終standalone Native62群 / 実WASM62群が成功した。56固定fixturesと128固有oracle行の全binary64値がbit一致。独立point比較は片側3645項目、両側計7290項目、最大絶対/scale正規化誤差は `2.196740785039233e-15`、このcorpusの閾値 `5.684341886080802e-14` 内だった。検証器の入力/出力/ID/順序/個数/型/有限値/clock/shear/符号/行列を破損した負例144件（`-O` の拒否を含む）を全拒否した。有限集合での実測であり、一般誤差保証ではない。

Native/WASM実行、checker負例、原本/SDK/artifact hashと実コマンドは `build/motion-proof/provenance.json` と `proof-commands.json` に保存する。

## 閲覧した一次資料

[Khronos glTF 2.0 Specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) の§3.5.3、node.matrix/rotation、Appendix C.2–C.4を実閲覧し、T*R*S・親world合成・column-major・xyzwと補間の規約を確認した。ここでのlinear rotationは明示NLERPで、glTFの推奨SLERP互換やglTF importerの実装完了を主張しない。原著の小さなpoint samplerを実装し、資料のコード/図/アセット、外部solver/ライブラリを取り込んでいない。

## 編集原本とNative/Web往復

`engine/motion.mjs` の `createMotionSource` は版1・kind `skeletal-motion` の原本を検査して複製する。名前は256 UTF-8 bytes以内、制御文字/孤立surrogateを拒否する。boneは `{id,name,parentId,rest:{position,rotation,scale}}`、clipは `{name,duration,tracks}`、trackは `{boneId,interpolation,keys}`、keyは `{time,position,rotation,scale}`。未知field・疎配列・不正な親木を拒否する。元の配列順、名前、ID、quaternionの大きさ/符号、未編集のbone/track/keyを保存し、数値−0だけ+0へcanonical化する。

`setMotionKey(source,key)` は同じbone ID・厳密同時刻のkeyを置換し、なければ追加して時刻順にする。`removeMotionKey` は指定keyだけを除き、最後のkeyならtrackを除いてrestへ戻す。入力は不変で、更新した複製を返す。`serializeMotionSource/parseMotionSource` は原本JSONの保存読込、`serializeMotionPortable/parseMotionPortable` は独自テキスト `pikapika_motion 1` のNative/Web往復。JSON/portableは4MiBのtext budget、bone/track/key数は上記共通上限を持つ。JSの文字列budgetはUTF-16 code unit、Native readerはbytesであり、これを同じ計数と呼ばない。

portable v1は `name "..."`、`bones N` に続く `bone ID PARENT "name" TRS10`、`clip "name" duration trackCount`、各 `track boneID linear|step keyCount` と `key time TRS10`、最後に `end`。名前のescapeはquote/backslashのみ、数値は有限decimal。NaN/Inf/overflow・非zero mantissaのzeroへのunderflow、件数超過、余分な後続tokenを拒否する。JS最短decimalとNative17桁decimalは有効binary64原本を往復する。glTF形式ではない。

共通owned sourceは `motion_io::Source`。raw quaternionを正規化して上書きせず、名前/ID/キーを保存する。構造が有効でもworldがoverflowする原本は編集・保存でき、そのsampleはno poseのnumerical failureとなる。保存は全原本検査とメモリserialize後にファイルを開く。不正入力時の指定済み出力を保持するが、disk障害時のtransactional renameや書込みのatomicityは未実装。

```
pikapika-motion init arm.motion
pikapika-motion sample arm.motion 1 clamp
pikapika-motion roundtrip arm.motion restored.motion
pikapika-motion key arm.motion 4 .75 1 0 .5 0 0 0 -2 1 1 1 edited.motion
pikapika-motion remove-key edited.motion 4 .75 removed.motion
```

[制作ラボ](../tools/motion-lab.html)は原本APIで編集し、実C++の返したworld matrixからjointのXY/XZ表示だけを作る。履歴は32変更。dirtyな未適用編集・入力失敗時は姿勢を消し、再生/スクラブを停止する。Undo/Redo/読込/適用は自動再生しない。描画clockは絶対秒でsampleし、物理Worldや120Hz tickを進めない。

## 共通ABIへの接続

ABI版1・output64を保持して `pp_sim_motion` と `pp_sim_motion_bone` の2関数を追加した。header10、bone原本12、track header3、key11 double。128bone/128track/4096keyの同時上限は46986 doubleで、既存入力49152に収まる。summaryは10、各bone getterは45 double（ID/親ID、local TRS10、local matrix16、world matrix16、evaluation rank）。全返値はcopy snapshot。予約値/enum/整数/範囲不正のexchangeを拒否し、以前のrecord/outputを保持する。受理したがモデル検査で失敗した照会は新しいno-pose recordとなる。global resetはmotion recordも消去する。

`runtime.sampleMotion(source,seconds,{loop,maximumBones,maximumTracks,maximumKeys})` は全原本を共通C++へ渡す。JSはFK・回転補間を重複実装しない。`worldPosition` はworld matrixの12..14をコピーした表示用alias。高水準source APIはさらに厳格な原本検査を行う。core56fixture中、zero/unsafe ID・不正mode/interpolation/budgetの5件はABI/JSのexchange拒否になるため、主SDK比較は51モデル結果＋5期待拒否として別記する。
