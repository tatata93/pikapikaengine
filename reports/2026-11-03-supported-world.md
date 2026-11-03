# 支持・衝撃・離脱を進める共通World

2026-11-03。独自C++のW2 `supported::step` とJS `World.stepSupported` を追加した。
対象は球proxyと静的平面、全参加materialの摩擦係数0。床上の運動、stack、非直交の共有接触、
球面に沿う運動、支持を伴う衝撃、離脱と再接触を一つのtickで進める。
成功時だけ全状態をcommitして保持荷重を一度消費し、失敗では荷重・時計を含めて保持する。

[実行ラボ](../tools/supported-world-lab.html)は7プリセット、手動120Hz、1/12/96tick、
同じWorldの予算変更・再試行を持つ。実際のbody姿勢と取得位置を描き、完全な前後状態・設定・イベントをJSONに残す。
図解教材は17記事。元のread-only支持照会とゲームの既存挙動は維持する。

## 数値モデルと修正した反例

[RATTLE候補](../docs/CONSTRAINED.md)で位置/速度の拘束を連成solveし、
private有限速度支持LCPがactive集合を選ぶ。[World契約](../docs/SUPPORTED_WORLD.md)に設定と遷移を記録した。
負の段階乗数は一行ずつ外して再計算し、inactive接触の再追加を行う。
`A=[[1,-.8],[-.8,1]], b=(-7,9.2)` では全拘束の係数が(-1,-10)でも片側解は(7,0)となる。
負の行を全削除して必要な床支持まで失う実装を修正し、独立解析値で回帰検査した。
tick末尾ちょうどの衝撃もcommit前に解き、反発後の速度を返して次tickで重複反発しない。
Cold inputの−1e−20 m/sも小ささだけで反発係数を0にしない。

受理する数値曲線を `q(s)=q0+h*v0*s+(q1-q0-h*v0)*s²` と定義し、
[全区間幾何監査](../docs/TRAJECTORY_GUARD.md)で全動的pairの `gap >= -spatial_tolerance` を証明する。
これは定義した候補曲線の幾何であり、真の連続力学軌道を囲む保証ではない。
粗い1歩と細かい2歩の差も別に記録し、厳密な連続解誤差上限とはしない。
途中の微小速度guardは物理的新接触も含み得る有限残差モデルで、丸め起因を証明したものではない。
支持係数の和はNs、保持並進力の仕事はFΔqでありトルク仕事推定を含まない。

初期の区間監査では依存性により試験processが162.61 CPU秒まで進み、対象exeを確認して中断した。
その実行を合格とはせず、座標包絡とquartic係数Horner包絡の交差で改良し、最終全試験を実行し直した。

## 実測した検証

- Windows/MSVC19.51.36247、CMake4.3.3、Node24.14.1、Python3.12.10。i5-6500 / GTX1060 6GB / RAM15.94GiB / Windows10.0.19045。GPU性能の新測定ではない。
- Native CTest20/20、361群。RATTLE17、guard24、driver13、private有限速度policy8、共通ABI36群を含む。Node193/193、skip0。build/check成功。
- RATTLE standalone実WASM17群。14完全入力fixture・1744値、最大差4.440892098500626e−15、1694値bit一致・145 ID/enum/counter一致。各対象39独立参照項目。
- 滑らかな固定active球面の刻み0.04/0.02/0.01秒で位置誤差3.2683e−4/8.1707e−5/2.0427e−5m。約二次の観測であり、衝撃/離脱driver全体の収束次数保証ではない。
- guard standalone実WASM23群（Native24群のうちFE_UPWARD拒否はNativeのみ）。Native/WASM各640例、320安全・320負witnessをFractionによる厳密極小値と比較。入力binary64のidentityも確認。
- 拘束checkerの破損入力38種類、軌道checker26種類を全拒否。Python -Oによる検証無効化も拒否する。
- 最終主WASMでW2の17完全入力fixture・25tick・3238値を比較、最大差1.432187701766452e−14。反復/分割counter差6、微小速度処理回数の差5tickを生証拠に保持。強い衝撃・離脱のID/時刻と最終状態を比較し、微小処理は合計impulse/energy効果も比較した。全ビット一致や実行回数の決定性は主張しない。
- 既存18回帰コマンドも全成功。30697値比較maxAbs6.821210263296962e−12。光学4116・面交差2400・分散1920・区間光学5980端点bit一致。strict支持12fixture/689値・光路15fixture/1560値・W1 41値の差0。支持public fixtureは内部policy追加前後で28281Bのバイト一致（元CRLF保持）。
- 実ブラウザは7プリセット成功、曲面96tick/0.8秒で離脱、予算1の失敗で全状態保持、同じWorldを4096で再試行して成功。手動動作なので落ちた時間0、実時間120Hz性能の証明ではない。

[Native全ログ](supported-world-native-verbose.txt) / [Node全ログ](supported-world-node-tests.txt) /
[W2完全入力](supported-world-native-fixtures.json) / [WASM全出力](supported-world-wasm-fixtures.json) /
[比較](supported-world-main-api-parity.json) / [既存回帰の全コマンド](supported-world-regressions.json) /
[ローカルUI入力と状態](supported-world-local-cases.json)。

[拘束解析](constrained-verification.json) / [拘束負例](constrained-negative-controls.json) /
[軌道解析](trajectory-guard-verification.json) / [軌道負例](trajectory-guard-negative-controls.json)。
全原本/成果物のhashは[SDK build manifest](../assets/pikapika-simulation.build.json)と
[今回の記録](supported-world-verification.json)に保持する。主WASM430397B、glue43782B、46exports、web build `4ba0bda196575a16`。
新しい第三者solver・実測材質・素材の導入はない。リンクmath通知を実memberに合わせ更新した。

## 公開と継続

この記録の初版はローカル検証済み・公開前。コードpush後のLinux CI、Pages、公開ブラウザの結果を追記する。
次は一般形状/摩擦支持・関節と、光学の明示面列を超える形状/媒質・遮蔽/経路選択へ進む。
流体連成・弾塑性損傷・車両/航空/鉄道・撮像/収差画像・波動光学とゲーム接続は未完。
製品全体の完成や、任意シミュレータの厳密再現、60fps達成をこの節目で宣言しない。
