# 局所Float32位置と法線のNative参照核

2026-11-03。[原本binding](2026-11-03-skin-binding.md)の次段として、原本を変更せず描画用のFloat32位置とflat normalを作る純粋C++ APIを追加した。[契約](../docs/DERIVED_MESH.md)。この段はNative-onlyで、主SDKのexportやrenderer、robot sampleへは未接続である。

位置を一度Float32へ丸め、その同じ値からedge/crossを既存Intervalで囲む。cross norm squaredの下限がbinary64 `1e-24` m^4を超え、strict nonzero成分がある場合だけ面積を受理する。法線は区間cross/sqrt(Q)とFloat32候補の差を監査し、各成分の誤差上限<=binary64 `1e-6`を必要とする。libm候補の精度を無条件に仮定しない。未確定や品質不足は別理由で拒否し、全face成功時だけ所有bufferを返す。

## ローカル受入

- MSVC19.51 strict FP: 新54群、全733群/CTest30成功。Node24.14.1は355/355・skip0、syntax/build成功。最終教材変更後に教材12試験も再成功。
- standalone NativeとMSVC ASanも各54群、sanitizer stderr空。実CMakeバイナリ、standalone、ASanからの40fixture出力は25841B・SHA256 `a9bd09a6c4b726a63bba681952dd97fd52b98e3d30fac5dd670ddfeb1e9d6dcf`でbyte一致。exe/obj/toolchainは配布せず、hash・command・raw stdout/stderrとrecipeを保持する。
- 65536頂点と131072三角形の同時最大を実処理し、全positions/face/audit/131072×18float、末尾faceと全入力bits/index不変を確認した。standalone prepareの単発観測はNative31.4792726秒、ASan39.0120172秒。別の統合実行は32.4756172秒。環境固有の観測で、60fpsや一般性能の保証ではない。参照検査の高速化は今後の課題となる。
- 40固定入力は16completed/24期待失敗。Python標準ライブラリだけでexact nearest-even Float32丸めを別実装し、147位置成分、81cross/27Q包含、306展開buffer成分を照合した。法線はlibm sqrt一致を正解にせず、符号付き有理平方不等式で向き付きC/sqrt(Q)の包含と誤差を確認した。
- 成功は17面/法線51成分で、最大の認証誤差上限は2.384185870951683e-8。別に失敗結果内の診断prefix1面/3成分を認証したが、描画成功へ数えない。57normal候補成分には拒否された候補も含み、最大reported誤差約0.2は失敗側である。
- checker自己試験7群、受入control2件、負例36件が期待どおり。両buffer内のnormalを一貫して偽造しても数学参照が拒否する。重複/脱落/順序/区間/bit/部分buffer/counter/非有限decimal/非零decimal underflow/Python -Oを含む。
- 既知XY、法線(0,3/5,4/5)、winding反転、180度剛体回転、shear、subnormal/signed zero/丸めtie、Float32 collapse、面積floorの両側と未確定、sqrt予算不足とlimited成功、失敗後復帰、FP環境拒否・control mode保持を確認した。

Native APIのfailure message代入は、メモリー不足による二重例外を防ぐため、reason/statusを確定してから非throwで試みる。checkerレビューでdecimal underflowが既定JSON float parserから黙ってzeroへ変わる点を修正し、元出力のzeroを1e-999/1e999に置き換える負例で解析時の拒否を確認した。

完全入力・結果は`derived-mesh-native-fixtures.json`、集計/原本hashと実command対応は`derived-mesh-verification.json`。CMake/raw CTestのcp932原本とUTF-8変換、standalone ASan/Native rawは`derived-mesh-*`と`derived-mesh-recipes/core/`。独立checkerのraw/負例logは`derived-mesh-reference-*`。変異入力は公開control scriptから新しいbuildディレクトリへ再生成する。元の実測rawを上書きしない。

## 配布と範囲

SDK63/WASM574261B/glue49388Bを再buildせず、51source/header・7通知・2artifactを全hash照合した。全tracked samples/assets/tests/fixturesの9ファイルは前HEADとbyte不変。Web39modules/build `51c633e84fbbf290`。教材25番と原著SVG1999Bを追加し、前段24番の目次link/初期件数表示も補った。外部package/素材/rendererは追加せず、本体licenseは未選定。

LBS-collapse fixtureは既知のzero位置を直接与え、実LBS呼出しとのend-to-end確認ではない。1e300入力は座標domainで拒否し、範囲外Float32 conversionを実行した試験ではない。包含は既存strict build/IEEE環境の条件付きで、probeや有限corpusはcompiler全体の形式証明ではない。

局所の1mm辺がworldのFloat32平行移動で潰れる別例も実行した。局所CPU監査をGPU/clip/raster被覆、自己交差、接触・材料損傷へ拡張しない。旧/新normalの内積の符号を一般の面反転判定には使わない。次は主SDKへの有界接続と実LBSからの照会、その後に3D renderer/robotへ進む。

## 公開受入

コードのLinux CI、ASan/UBSanとPages、教材の実ブラウザ表示は確認待ち。未確認を成功として数えない。

最初の公開CI（1d08122、run41652778212）はC++ build/CTest30と独立40fixtureまで成功した後、negative-control runnerの出力先guardで停止した。rootがCIへ設定したbuild/ci/derived-mesh-referenceは、runnerの許可したbuild直下derived-mesh-reference*と一致しなかった。runnerの安全制限は変えず、CIの出力先をbuild/derived-mesh-reference-ciへ訂正した。同じ修正引数でローカル7自己群/2受入/36負例が再成功。失敗job log/step一覧を保持し、その後skipされたNode/sanitizerを成功へ数えない。新しいCIで全stepを確認する。
