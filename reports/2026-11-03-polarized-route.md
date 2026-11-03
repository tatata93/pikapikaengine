# 指定光路の区間偏光POWER・共通sqrtの節目

2026-11-03。共通C++核、Native/実WASM、主C ABI/JS、手動オフラインラボと教材20番を統合した。コードbef623cのLinux CI/Pagesと公開操作も成功。

世界XYZの3×3 Hermitian coherencyを、各面の局所s/p基底と複素Fresnel係数で輸送する。非共面の基底回転、全反射の相対位相、power正規化した透過、厳密法線/同一媒質を扱う。指定面/反射透過列を追うもので、自動媒質配置や全ghost列挙ではない。元の区間幾何/OPLを保持し、光量のprefixと完成を区別する。

主ABI54exports、WASM501808B（SHA256 3200fa8c43a3199f6833a14d4edab8b8417805f7f4536b6454512ba9675f6a4d）、glue46542B。Web build2d4e49f46b6e16b4 /31modules。旧51関数のpacket互換とsnapshotの保持/無効getter/resetを検証した。

## 実行した検証

- Nativeクリーンbuild + 最終テストleaf再build、CTest24/24・453群。Node246/246、skip0。新偏光核はNative/standalone実WASM各37群、主ABI追加3群。
- 偏光32fixtureの3942数値、128個の異なるdyadic入力の3072数値がNative/standaloneでbit一致。独立FractionとQ(sqrt11)の平方bracketにより1539包含/対象（計3078）を確認。検査器の88負例がすべて拒否された。
- 主WASM経由の32fixture2482数値と128入力2560端点bitsがNativeと一致。CMakeとstandaloneの最終fixture/oracleもbyte一致。
- 新しい共通sqrtはNative7/実WASM6群。3327行、全2098個の二の冪指数、subnormal/max-finite、512 point/interval組、192予算不足を含み、6654の平方端点包含/対象とNative/WASM6654端点bit一致。検査器17負例が拒否された。
- 既存21回帰コマンドがPASS。旧物理30697値は最大絶対差6.821210263296962e-12、最大normalized差4.3655745685100546e-12、許容abs1e-8+relative1e-10内。GNUとの観測差は別途記録する。
- Nodeの実WASM UIテストは非共面有理POWER、法線のworld円偏光符号、二段全反射のQ/U/V、未知/予算失敗と復帰を確認。ローカル実ブラウザ13操作の生DTOと画面を保存した。

非共面二反射の無偏光POWERは42544/17294403。各面で無偏光に戻す誤実装の1263376/466948881を区間から排除する。純U+の322768/259416045も独立比較する。二段全反射は相対位相53/75+i16sqrt11/75を保持し、最終局所Q=424/625、U=-10007/15625、V=1696sqrt11/15625を囲む。

法線反射で世界Cxyの虚部を誤って反転しない。最小subnormal POWERの半分が通常doubleの0へ落ちる問題は、上限を外向き区間除算で作るよう修正した。厳密Fractionにより表現不能な2^-1075も包含検査する。丸めmode不適合は成功扱いしない。

## 誤差・予算・残る受入

共通sqrtはlibm sqrtの精度仮定を置かず、厳密な二の冪scalingと[1,2]上の区間平方/refinementで囲む。予算不足でも包含区間を返し、limitedを明示する。高精度設定は計算量の上限であり、任意指定の最終POWER幅を保証する設定ではない。区間幅が広くても完成する場合がある。全sqrt予算の検査は一つの幾何route/一つのsqrtの後なので、失敗時の超過上限と例外時の部分counter限界をdocs/POLARIZED_ROUTE.mdへ明記した。

全ray族の物理状態を囲む世界tensor箱であり、箱から独立に取り出した任意の要素組が正半定値/横波になるとはしない。未知を黒/0として扱わず、完成条件を満たさなければ最終POWER/coherencyを返さない。実ブラウザの描画中央値は表示専用。

POWERはray tubeの量。放射輝度/照度、source/aperture測度・PDFからの有限packet重み、sensor bin境界、連続瞳の求積誤差は別受入。複数経路の相対位相/干渉、回折PSF、coating/吸収、実レンズ校正、自動光路/自己根/媒質証明、撮像/ゲーム描画接続は未完。60fps性能やDCS等相当の完成を示さない。M2制作/一般接触・摩擦・関節・流体・材料損傷も継続する。

次の小段階は合成レンズのprimary/ghost指定経路と偏光POWER、有限packetのsource/sensor測度の接続。現行IRON FIELDの変更は行わず、エンジン改善を後続で還元する。

## 来歴と再現

source/artifact/runtime-license hashはpolarized-route-verification.jsonとassets/pikapika-simulation.build.json。独立核の原provenance/commands、raw fixtures/oracles、負例、主API出力、CTest/Nodeログ、ローカル操作は同prefixのreportsへ保持。元のbuild位置を参照するレシピはpolarized-route-recipesへそのまま保存した。sqrt独立記録はinterval-sqrt-verification.json。

新ライブラリ、SDK、材質データ、処方、外部画像/コードを導入していない。原著SVG1418B、SHA256 11ba65766d24a466530dedf5b79827d916a098bf4a773c63f5dd254da5e7930f。既設Emscripten6.0.13の標準ランタイム通知を維持。エンジンライセンスは未選定。一次資料の実読範囲はdocs/legal/REFERENCES.md。

## 初回Linux CIの移植性修正

コード27d0f86のCI run41605746768/job125815003675は新sqrtテストの直接include不足（std::uint64_tに対する<cstdint>）で失敗。Windows/libc++の推移includeに依存していた。直接includeを追加し、Native/standalone WASMを再build、同じ3327 oracleとbit一致、CTest24/24を再確認した。出荷runtime/sourceは変更せず、WASM/glue/Web buildも同一。初回失敗抜粋と修正後テストログを保持する。

## 公開コードbef623cの検証

[CI run41606005062](https://github.com/tatata93/pikapikaengine/actions/runs/41606005062) / job125815862831が全step success。GNU13.3.0 / Node22.23.4、CTest24/24、Node246/246・skip0。sqrt3327行/6654平方端点、偏光独立1539包含、主WASM32fixture2482数値・128入力2560端点bit一致が成功。Linuxの旧物理30697値の最大絶対差は3.3306690738754696e-16。Windowsの6.821210263296962e-12と環境別に保持する。Linux checkerは第二standalone packetを渡さないためwasmBitsMatch=false（未比較）を返すが、主WASMのbit比較は別のstepで成功。Windowsの両packet比較はtrue。

[Pages run41606004551](https://github.com/tatata93/pikapikaengine/actions/runs/41606004551)のbuild125815866954 / report125815932737 / deploy125815932819もsuccess。公開WASM/glue/manifest/engineJS/labJS/HTMLの計6ファイルがローカル原本とbyte一致した。

[公開偏光ラボ](https://tatata93.github.io/pikapikaengine/tools/polarized-route-lab.html?v=bef623c)は初期手動待機、8プリセット、U+の有理反射と二段全反射、V+法線透過、段1prefixの閲覧、index族、既定復帰、不正入力による旧出力消去、総sqrt予算不足、再読込/既定復帰の17操作を記録。全計算の原入力/全結果/runtime DTOはpolarized-route-public-cases.json。観測最終POWERは有理無偏光[0.0024599866211042786,0.002459986621105866]、U+[0.001244209856023802,0.0012442098560259743]、法線二透過V+[0.9215999999999978,0.9216000000000022]。index半幅0.01の無偏光では[0.002437940639974352,0.002482199427831078]。近傍垂直族は幾何完了/偏光未解決、臨界族/存在しない透過枝も最終POWERなし。総sqrt1では幾何結果を残し、最終POWERを返さない。数値区間・予算・表示中央値を区別する。

公開実測時間は当該一操作の観測で、性能保証や60fps達成ではない。公開原packet/HTTP hash/CI抜粋/画面/ワークフロー状態はpolarized-route-public-*。次はprimary/ghost指定経路とsource/sensor測度を検証し、広い製品目標を継続する。
