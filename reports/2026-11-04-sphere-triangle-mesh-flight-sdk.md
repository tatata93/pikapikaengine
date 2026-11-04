# 保持荷重と丸め自由伝播guardのraw共有SDK — ローカル受入

2026-11-04。別modeの保持荷重と丸め自由伝播guardを6つの有界C ABIへ接続し、正式WASMへ追加した。Native200ABI検証群・41CTest・631Node（skip0）と独立参照が成功。公開CI/Pagesは確認待ち。ゲームやWorldの接触応答へ新queryを適用する段階ではない。

## 実際の交換と独立検証

固定79保持荷重＋100guard＋別補足4の完全入力を183行として送った。実際のモデル結果はheld74/guard95/補足4の173行、host拒否は各5/5/0の10行。拒否された行にNative数学結果を埋めて全WASM検証と数えない。Native交換の415506数値bits/5738負零、復号後DTOの272814数値bits/5424負零を比較。Nodeはmode metadata183を含め415689数値bits/5738負零を比較した。10397record、全21kind・source・nested・endpoint・candidate・lastMesh全row/候補を確認。可変messageだけは明示的にwireから除外する。

実WASMから復号した173モデルだけをFraction参照へ渡し、原F/m・二次曲線・全closed被覆・Work・独立RN/ties-even/B・実candidateを再確認した。独立完全入力fingerprintは全183 `4149030bf7278b5a91db1f2739c55491c82f57fc733254ee384153867f19ca54`、実受理173は `684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb`。原reportの各mathematics.fixtures=0はper-fixture verifierが更新しないaggregate初期値で、実監査件数74/95/4は別に集計した。16コピー改ざん拒否とPython-O拒否、Node15操作controlを保存した。synthetic codec6群は実wireとは別の自己試験である。

256audit/128葉・区画/127frontier/64source・保守ID/64lastMesh row・448候補の末尾まで読み、範囲外getterの出力保持も確認。これら独立上限を同時の最悪メモリ達成と数えない。Native追加群は同/別mode・旧entry・World/時計・global reset・static/整数負零・全finite/reserved・不正body capture・成功candidate only・実unsupported FP環境を確認した。実unsupported環境はNativeの実験でありWASMへ移した観測ではない。

## 互換性・正式配布物・実ブラウザ

333旧原本をraw保全し、25生成HTMLはimportmap/build query/CRLFだけ正規化して保持した。旧API本文は新header include/同TU private実装includeとresetの追加loopだけを除けば元と同byte。旧86入口は保持し、新6入口を追加して92。67 source/header hashes・32TUを固定Emscripten6.0.13で安定ソースから再build。WASM800982B SHA `a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d`、glue61661B SHA `d4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55`。runtime91memberと7通知は元のまま。ライセンスは未選定、新外部依存/課金なし。

旧20Native W1の全report/World JSONは変更前後byte一致、既存SDK保存20例4520数値bits24負零も一致。旧entry所有APIの全105056モデル数値bits3239負零、原入力4728bits108負零・90負例もfresh成功。純held79/guard100/補足4の再生成JSONは以前の固定全入力/出力とbyte一致した。

実ローカルゲームはWeb26d4da108a67b9d9/800982B WASMで出撃・2撃破・boostclip1・158km/h表示・停止を確認。22照会すべてchecked/validated/completed、3resident mesh/error0。これは既存ゲーム/SDKの互換性で、新guardのゲーム接触使用を意味しない。原著SVGを全体表示して文字/配置を確認した。[ブラウザ記録](sphere-triangle-mesh-flight-sdk-browser)は表示証拠で数値証拠の代用ではない。

## 残件と失敗履歴

HEAPは前/最大観測/後すべて67108864B、buffer交換0、12915回view再取得を観測。allocator used bytesとstack高水位は現exportに計器がなく未計測、growthも実際には未発生。容量を使用量や最悪case余裕へ読み替えず、計器導入と実growth・allocation fault注入は残件とする。全入力組合せのメモリ上界や60fpsを主張しない。

synthetic初回run001は参照stats helper名の誤りで5PASS/1ERRORとなり、helper参照先のみ訂正して最終run004の6群/ソース前後一致が成功。原stdout/stderr・欠測注記は[attempt archive](sphere-triangle-mesh-flight-sdk-reference-attempts/freeze.json)へ保持した。Native/モデル入力/閾値を緩めていない。prebuilt baselineの最初の実行中に、未使用のsimulation_api.hだけが新API追記で変わった。元authoredStable:falseを保持し、コンパイルを伴わない既存実行ファイルでの比較と明示した。[baseline scope](sphere-triangle-mesh-flight-sdk-checks/run-20261104-before/baseline-scope.json)を参照。最終コンパイル/交換は凍結ソースで別に確認した。

[ローカル機械集計](sphere-triangle-mesh-flight-sdk-local-verification.json)・[再現recipe](sphere-triangle-mesh-flight-sdk-recipes/check.py)・[最終rawログ](sphere-triangle-mesh-flight-sdk-checks/run-20261104-final)。公開GNU・API sanitizer・配信は未確認。既存の純核sanitizer成功を新APIの計装実行と混同しない。

次は[所有JS API](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)。raw6入口を全て検出してから書き込み、全fieldを一度captureし、全21kindを所有copy/監査する。手動UI・World advance/接触順序/衝撃摩擦支持・残時間/tick commit、流体損傷・専門モデル/IK制御/高精度撮像は引き続き未完。

初回の全交換/回帰成功後、未使用flight_same_vector定義1行を削除して最終002のNative build・200群・全交換/独立参照・41CTest/631Nodeを再実行した。正式SDKも再buildし、WASM/glueの全bytesが初回と同一であることを確認。compiled private-header hashを含むmanifestの変化によりWeb buildは055e57b764eb7731から26d4da108a67b9d9へ変わり、最終ビルドでも実ゲームを再確認した。初回の21照会/193kmhと最終22照会/158kmhは別観測として原ブラウザ記録を保持する。
