# 有限幾何点像・合成レンズprofileの節目

2026-11-03。コードa5b086dのローカル統合検証、Linux CI/Pagesと公開9操作が成功。

指定した面/反射透過列を共有する有限ray集合を共通C++で追跡し、sensor円盤を幾何投影する。
全位置/方向/index区間と元の幾何重みを保持し、重心・平均二乗半径・hullを囲む。
未知や未実行が一つでもあれば最終統計を返さない。既知欠落の元重みも保持し、条件付き到達統計と区別する。

合成両凸レンズprofile、有限物点/平行光、等r²層の瞳節点、同じ節点の3波長と全phase区間を接続。
保存読込と明示オフライン計算のラボ、原著SVG、教材19番を追加。実レンズ処方・材質データ・外部実装/依存は導入していない。

## 検証

- NativeクリーンビルドとCTest22/22・406群。新核19群、主C ABI追加3群。
- standalone実WASM18群。25fixture+launch2+近軸3段の4767数値がNativeとbit一致。
- 独立Fraction166包含、実binary64処方の近軸行列との3段収束、128個の相異なるdyadic配置/1408包含。
- 主WASM経由で25fixture/launch2の2921数値、128配置/2048端点がNativeとbit一致。
- Node229/229、skip0。保存読込、等面積の解析的r²平均、対称性、波長差、有限sourceの消える下位項、未知統計禁止、UIエラー復帰を含む。
- 既存19回帰コマンドもPASS。旧物理30697値比較は最大絶対差6.821210263296962e−12、最大normalized差4.3655745685100546e−12（許容abs1e−8+relative1e−10）（今回の有限入力観測）。
- 新verifier負例72/正常4の生出力を保存。CMakeとstandaloneの最終fixture/oracleは原packet一致。

主WASM466449B / glue45479B、51exports。Web build01a2c63326a8f0af / 30modules。
source/artifact/licenseの具体hashは `optical-spot-verification.json` とSDK manifestへ保持。
生packet、commands、Native/Nodeログ、checker負例、主API出力を同prefixのreportsへ保存する。

## 標本数・予算の観測

同じ550nm/半径15mm profileで、16/64/256/1024点のMSR²は約
1.422917764e−6 / 1.635652829e−6 / 1.691223275e−6 / 1.705271533e−6m²。
各数値区間幅より標本数差が大きい。これは有限中点求積の収束観測で、連続瞳の誤差包含ではない。
この比較は総sqrt予算4000000を明示。既定1000000の1024点では3波長ともbudget_exceededでstats空となる。
Nodeの単独操作は16点約30ms〜1024点約859ms、ブラウザ既定64点は一操作約154ms。
実測機はi5-6500/15.94GiB/Win10、Node24.14.1。オフライン参照の有限観測であり、60fpsの合格根拠にしない。

レシピ `node scripts/observe-lens-spot.mjs`、全profile/予算/観測区間は
`optical-spot-profile-observations.json`。ローカル画面では開口/焦点/軸外/有限source/最大点数予算失敗/既定復帰/不正入力消去を操作した。
保存済み要約はbudget/finite復帰/不正入力/既定復帰の4操作。初回4操作はブラウザ検証セッションの再初期化で要約未保存のため、独立な生証拠と区別する。

## 残る受入

点像図の色は波長ラベル、点は位置区間の表示中央値で、放射RGB/明るさではない。
今回の重みは幾何面積測度で、routeの任意偏光power包絡は掛けない。
放射測定・多面偏光/位相輸送、全ghost経路、散乱/coating、回折PSF、連続瞳積分誤差、実レンズ校正、一般媒質配置と自動光路、ゲーム描画接続は残る。
M2制作、一般接触/摩擦・車両航空鉄道・流体/材料損傷も別の継続受入として保持する。


## 公開コードa5b086dの検証

[CI run41599747047](https://github.com/tatata93/pikapikaengine/actions/runs/41599747047) / job125795411992がsuccess。
Linux GNU13.3.0 / Node22.23.4、CTest22/22、Node229/229・skip0。
Fraction166と128配置/1408包含、主光学2921数値+2048端点bit一致も成功。
旧物理30697値のLinux比較は最大絶対差3.3306690738754696e−16。
Windowsの同比較値との差は対象/コンパイラ差として生ログへ残す。

[Pages run41599746652](https://github.com/tatata93/pikapikaengine/actions/runs/41599746652)のbuild125795414627 / status125795468255 / deploy125795468340がすべてsuccess。
公開WASM/glue/engine2原本/labJS/HTMLの計6ファイルがローカルとbyte一致。
[公開点像ラボ](https://tatata93.github.io/pikapikaengine/tools/lens-spot-lab.html?v=a5b086d)で初期手動待機、既定3λ、小開口、焦点面変更、軸外入射、1024点予算失敗、有限source復帰、不正入力消去、既定復帰の9操作を確認。
未知/未実行では統計なし、軸外では各50到達/14欠落と元重みを保持した。
公開の生要約・画面・HTTP hash・実測時間・CI抜粋は `optical-spot-public-*` に保存。
継続開発では媒質配置/自動継続と、光量/偏光輸送を明示したghost/描画接続を検討する。有限幾何点像を完成画像としない。
