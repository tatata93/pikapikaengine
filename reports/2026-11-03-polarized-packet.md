# 明示有限POWER packet・合成レンズ二経路の節目

2026-11-03。各光線に明示するStokes I/Q/U/V [W]を共通C++で輸送し、理想センサーへ到達した有限光束を区間集計する核を追加。合成両凸レンズの通常T前/T後と、T前/R後/R前/T後の最初の内部反射経路へ接続した。任意選択・手動オフライン参照であり、ゲームの既定描画へ挿入していない。コード84d2cdcのLinux CI/Pagesと公開11操作も成功。

## 検証

- Native全targetクリーンbuild、CTest25/25・498群。新核42群、C ABI追加3群（ABI全体48群）。Node272/272、skip0。新profile/UI18群と主API8群を含む。
- standalone実WASM42群。36fixture全6665数値と128固有oracle入力1280数値がNativeとbit一致。
- 独立Fractionの包含501/対象（fixture117+oracle384、両対象計1002）。検査器の負例107件がすべて拒否された。
- 主WASM経由で36fixture4418数値と128入力768端点bit一致。snapshotは既存偏光route64/initial40/geometry64/power35をそのまま使用する。旧偏光route32fixture2482数値+2560端点bitsも再検証した。
- 既存22回帰コマンドがPASS。旧物理30697値の最大絶対差6.821210263296962e-12、最大normalized差4.3655745685100546e-12、許容abs1e-8+relative1e-10内。
- 法線板の通常経路576/625、内部反射経路576/390625、非共面二反射の独立有理POWER、偏光prefix、subnormal、傾斜sensorに追加cosなし、空集合0W、後続不正packetの事前拒否、0W未知/センサー境界未知・予算未実行と復帰を検証。

主ABIは57exports、APIv1/output64維持。WASM524148B / SHA256 f7ceddd9b0cafaf0246bb559a784a594f8e4046737d5b896dd310c2aa39b3b92、glue47619B。Web build c12da9b0334d7c62 /33modules、教材21記事。source/artifact/runtime-license hashはpolarized-packet-verification.jsonとSDK manifestへ保持。新外部library/SDK/package/素材/実レンズ処方は導入していない。エンジンライセンスは未選定、既設Emscripten6.0.13の通知を維持する。

## モデル・measure・計算予算

各packetが明示するWを有限の非干渉measureとする。幾何求積weightを無断でWへ変換しない。profileはNを二の冪へ限定しP/Nで正確に等分する。Pの範囲1e-6..1e6ではnormal値として正確にscalingできる。各波長は独立した単色P W実験で、波長間も二経路間も自動加算しない。光路間の共通位相/相互相関を保持しないため干渉画像にはならない。

理想的な両面吸収sensorを幾何判定し、輸送済みray-tube POWERへ追加cos/index²/Fresnelを掛けない。known miss/選択枝なしはこの指定経路の到達なし。unknown/not-examined/予算不足が一つでもあれば最終tallyなし、0Wも監査を省略しない。boxは相関を含む真の物理状態を囲むが任意端点の組合せがPSD/横波とはしない。

per-routeとbatchのsqrt予算を明示。全体workは一packet終了後に監査するため失敗時にその一packet分だけ超過し得る。例外中のprimitive部分counterは取得できない場合があり、numerical_failureを完成したwork証明にしない。幅の広い有効包含がlimited=trueで完成することと、未解決/予算失敗を区別する。

## 観測と操作

550nm、既定開口5mm/64packet/P=1Wでは主経路[0.9215920745489504,0.9215920745492953]W、内部反射[0.001486171538191627,0.0014861715382053994]W。4/16/64/256点で内部反射の値は約0.0014831605 /0.0014855751 /0.0014861715 /0.0014863201W。有限節点の変更による差で、数値区間より大きく、連続瞳の求積誤差上限ではない。

1024packetは既定総sqrt予算1mで主経路unknown561、内部反射unknown762となりtallyなし。明示4mでは両方1024到達/unknown0となり、主経路[0.921591951040701,0.921591951041172]W、内部反射[0.0014863571833868014,0.0014863571834009056]W。標本数を黙って減らさず、部分結果を正規化しない。レシピscripts/observe-lens-power.mjsと全profile/実測はpolarized-packet-profile-observations.json。Node24/i5-6500/15.94GiB/Win10の一操作観測で、1024/4m/1波長は約1564ms、60fps保証ではない。

ローカル実ブラウザ11操作を保存:既定64、小開口、小sensor、軸外U、2W円偏光、実download→reset→file読込のprofile一致/手動待機、読込後再計算、packet予算1、総sqrt予算1、不正sourceによる旧結果消去、再読込/既定復帰。保存読込のブラウザ操作には長い待ちが発生したが、その時間をエンジン計算時間と解釈しない。ローカルcompact証拠は操作概要で、初期のobject転送に丸め/深さ制限があるため端点bit比較には使わない。公開版はDOM JSON文字列から元profile/runtime/全経路counts/tally・first/last全prefixを正確に保存し直した。全packetの実値はNode/C++検証でも別途保持する。

## 次の受入

照度画像のsensor bin区間配分、連続sourceの測度/PDF/積分誤差、全ghost自動列挙・最近傍/媒質/自己根の証明、coating/吸収・経路間干渉/回折・実在レンズ校正/ゲーム描画接続は未完。図の点色はλラベル、位置中央値は表示専用で物理RGB/Wの濃淡ではない。

次はM2制作Bのボーン/キー原本・FK時間サンプリング/保存へ戻る。一般接触/摩擦・関節・制御、車両航空鉄道・流体・材料損傷も広いエンジン目標として保持する。既存IRON FIELDには今回変更を加えていない。

## 公開コード84d2cdcの検証

[CI run41624057458](https://github.com/tatata93/pikapikaengine/actions/runs/41624057458) / job125876804201が全step success。GNU13.3.0 / Node22.23.4、CTest25/25、Node272/272・skip0。独立Fraction501包含、主WASM36fixture4418数値と128入力768端点bit一致が成功。Linuxの旧物理30697値は最大絶対/normalized差3.3306690738754696e-16。Windowsの観測差と区別して保持する。Linux checkerのwasmBitsMatch=falseは第二standalone packetを渡さない未比較で、主WASM比較は別stepで成功。

[Pages run41624055948](https://github.com/tatata93/pikapikaengine/actions/runs/41624055948) build125876806564 / deploy125876901578 / status125876901827はすべてsuccess。公開WASM/glue/manifest/共通JS/profileJS/labJS/HTMLの7ファイルがローカル原本とbyte一致した。

[公開光束ラボ](https://tatata93.github.io/pikapikaengine/tools/lens-power-lab.html?v=84d2cdc)の初期手動待機と11操作を記録した:既定64、小開口、小sensor、軸外U、2W円偏光、ghost最後のpacket63のprefix/coherency閲覧、packet予算1、sqrt予算1、段数予算1、不正sourceによる旧結果消去、再読込/既定復帰。小sensor半径0.01mmの550nmはprimary16到達/48missで検出[0.23039990907988794,0.23039990907997304]W、ghost0到達/64missで[0,0]W。packet予算1は到達prefix1/未実行63、sqrt1は未知64/未実行63で最終tallyなし。段数1の事前budget失敗はrecords空で、UIは未受理64を原packetから表示し0光源と解釈しない。公開原JSON・画面・HTTP hash・CI抜粋はpolarized-packet-public-*。

公開既定550nmのPOWERはprimary[0.9215920745489502,0.9215920745492955]W、ghost[0.0014861715381916257,0.0014861715382054005]WでNodeの生成値と末尾が少し異なる。ブラウザの2W円偏光/軸外入力で192節点座標を比較し8座標がNodeのsin/cos生成と異なった。同じブラウザ丸め済み光線をNodeの主WASMへ再投入すると両経路の全tally6端点ずつが完全一致した。これは丸め節点を入力とする契約の範囲で、連続瞳/超越関数を厳密包含した主張ではない。polarized-packet-browser-nodes.json / sampling-comparison.jsonへ実入力と再照合結果を保持する。

なお初期の検証用object転送では数値の追加丸め/MaxDepth省略も観測したため、公開数値証拠はDOM JSON文字列経由で取り直した。これはエンジンの計算差と区別する。保存profileはP/材質/λ/参照軸/予算を保存するが、将来の完全なcross-platform再現には丸め済みpacket原本の保存/厳密生成という別受入を残す。
