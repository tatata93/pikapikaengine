# M2制作Bの次の受入: 原本メッシュと骨の最小binding

状態: 2026-11-03。pure C++のrest inverse/位置deform、Native/standalone WASMの独立検証と共通SDK63への接続は実装済み。位置計算ラボtools/skinning-lab.htmlで実WASMを照会する。原本bindingの保存/Native CLI往復とengine描画への接続は未実装。現行motionラボはFK線表示である。

目的は既存の安定したscene object ID、mesh原本、bone IDを保持し、同じmotion姿勢でNative/Webの頂点を変形すること。現在mesh v1は頂点配列indexとtriangle indexを使い、永続vertex IDはない。この事実を隠して一般topology編集対応としない。初段bindingは対象object IDと原本mesh fingerprintを持ち、対応不一致・頂点数/順序の変更を明示拒否する。既存原本・既存IRON FIELDの描画規約は変更しない。

## 最小の座標規約

初段はmesh localとskeleton座標を一致させる。G_j(t)を骨のskeleton内world affine、R_jを原本rest poseの同じ行列、I_j=R_jのinverseとし、p_deformed=Σw_j G_j(t) I_j p_source。restで元の頂点へ戻ることを独立に確認する。scene objectのworld変換は最終描画で一度だけ適用する。別のbind-shape座標、glTF node transform規約、複数instanceは後続。

各頂点は1〜4個の一意なbone IDと非負finite weightを持つ。全zero・未知/重複boneを拒否し、weightの正規化方針と許容残差をAPIで明示する。入力weightや原本位置を暗黙に書き換えない。bind生成でのinverseは二進64bitの点近似で、特異/悪条件・非finite・仕事予算を失敗として返す。計算途中の一部頂点を成功として公開しない。姿勢のbone順を変えてもID対応は同じ結果を持つ。

現行meshはflat normalを派生生成するため、初段は変形後triangleからnormalを再生成し、zero-area/Float32 collapseを既存検査で拒否する。線形blendで局所が特異になる場合、shear、skinの体積減少はあり得る。逆転面の方針・smooth normal・接線・dual quaternion skinning・GPU skinning・自動weight付けは別段階。

## 受入順序

1. C++のpure binding/deform核とowned source。既知rest、単一joint、2jointの有理重み、非一様scale/shear、任意bone順、未知/重複ID、weightと行列の不正、上限/overflowの失敗後再利用。原本編集と変形結果は分離する。
2. 自作Fraction affine参照とNative/実WASM比較。逆行列の自己残差だけを独立精度の根拠にしない。点誤差、binary64 parity、Float32描画許容を別集計する。
3. JS原本API・version付きportable往復・CLI。mesh fingerprint/ID/weight/inverse bindを保存再読込し、未選択の原本を保持する。
4. 小さい自作メッシュでWeb/Native描画へ接続。キーを変更→頂点変更→保存再読込、静止restへの復帰、エラー時のstale表示消去をブラウザ/Native実機で確認する。その後オリジナルrobot sampleへの最小適用を行う。

調査: [Khronos glTF 2.0 §3.7.3、§5.28](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#skins)を本文確認（joint/weightとinverse bind、配列対応、node transformとの区別）。上記は独自subsetの予定契約で、glTF importer互換を主張しない。他者のコード・図・素材を導入しない。IK・関節制限・制御グラフ・contact・材料損傷はこの変形と区別する。

有界SDK照会の実装・受入は[SKINNING_SDK_PLAN.md](SKINNING_SDK_PLAN.md)へ記録。SDKの実データ上限は128bone/2048vertex/8192influenceで、Native kernelの65536vertex/262144influenceと区別する。次の最小受入は項目3のowned原本bindingとportable/Native CLI往復。診断JSONの書出しだけで原本再読込を達成したことにしない。
