# 静的光学面の最近傍を確定する核

`optical_selection::find_nearest` は、明示された静的 `PlaneDisk` / `FullSphere` /
`SphericalCap` の集合に対する、read-onlyな1回の幾何照会である。
指定された面列だけを調べる [optical_route](OPTICAL_ROUTE.md) と異なり、集合内の
全競合面を監査する。自動光路追跡、媒質領域の整合、全ghost、撮像、位相・回折は
この受入に含めない。演算は [INTERVAL.md](INTERVAL.md) のstrict binary64包含であり、
任意桁数の多倍長演算や、あらゆる入力を必ず確定できるアルゴリズムではない。

## 入力と返り値

`find_nearest(BoundedRay, span<const SurfaceRecord>, Settings)` は入力を書き換えない。
`SurfaceRecord{id, surface}` のIDは正のuint64で、同一照会内で一意である。
Native核はuint64全域を扱う。doubleでIDを渡すABIは別途exact-integer制約を課す。
計算・診断はID昇順であり、`ordinal` はその順の0始まり番号である。
元の配列順による物理的tie-breakはない。

ray・形状・primitive設定の範囲は [OPTICAL_BOUNDS.md](OPTICAL_BOUNDS.md) と同じ。
位置はm、方向は無次元、P(t)=origin+t*direction のtはm単位のparameterである。
物理距離はt*|direction|。要求domainは閉区間 `[tMin,tMax]`、0<=tMin<=tMax<=1e9。
空の面集合でもray/設定を検査し、ゼロ方向をcertifyできなければunresolvedを返す。
形状数制限を超えた入力は、巨大な集合を走査せずbudgetで停止する。
それ以外は全ID/形状をpreflightしてから交差照会を行うため、遠い不正形状が近いhitで
隠されることはない。不正入力はinvalid_input、未対応FP環境やpreflight後の数値例外は
numerical_failureである。

返り値のstatusは次の順で定義する。

| 値 | 意味 |
|---|---|
| hit | 全ray族員で同じ面が一意の最初の有効交差を持つ |
| miss | 要求domain内で全ての面が全族員について交差なしと証明された |
| unresolved | 面順・開口・接線・境界・族の相関喪失等により確定できない |
| invalid_input | ID、形状、ray、設定が入力範囲に反する |
| budget_exceeded | 面数、照会数、総sqrt処理数、必要なprimitive refinementが不足 |
| numerical_failure | サポートしない数値環境または計算中の例外 |

`nearest` はhit時だけ設定され、IDと**全Hit包含**を返す。失敗後に暫定候補を成功値として
残さない。各面の`geometry`は元domainの完全なprimitive結果で、未照会ならoptionalなし。
`prefix`は実行した閉prefixの完全な結果、`excluded_by_prefix`はそのmiss証明を使った印である。
query/prefix/sqrtの実カウンタ、refinement-limited flag、メッセージも保持する。

## 最近傍の証明

既存primitiveのhitは、各族員の同じ順序の**最初の有効根**が存在するという契約である。
単なる候補根の包絡やゼロを含む判別式を、hitに昇格しない。

1. 全面を元domainで照会する。全結果がmissなら全体miss。
2. primitive hitのうち、t上端が最小の面Aを暫定候補にする。hitがなければ未確定。
3. A以外の各Bについて、元結果がmiss、またはA.t.upper<B.t.lowerなら競合を排除する。
4. それ以外でprefix照会が有効なら、同じrayを閉区間 `[tMin,A.t.upper]` に制限してBを
   再照会する。この結果がmissのときだけBを排除する。各面にprefix照会は最大1回。
5. 全競合を排除できたときだけAをhitとして返す。残る競合があれば未確定または予算失敗。

これにより、各実rayについて tA<=A.upper より前または同時のBの交差はない。
他のprimitive-hit候補CはC.upper>=A.upperである。A自身に全族員の根が存在するため、
この十分条件でAを排除してCの方を証明することもできない。よって候補を何度も替えて
同じ面を再照会する探索は不要である。ただしこれは完全な順序判定ではない。

例えばorigin=0、dZ=[1,2]、A:z=2、B:z=3では、数学的には全rayでAが先である。
それでもtA=[1,2]、tB=[1.5,3]は重なる。同じ方向との相関を扱わない本核はunresolvedを返す。
primitiveの算術sqrtを精錬しても、本物の族幅による重なりは解消しない。

後方Bの開口境界が混在しても、BがA.upperまで存在しないことをprefixで証明できればhitにできる。
一方、後方の接球はprimitiveが判別式をdomain判定より先に調べるため、prefixでも未確定になり得る。
この場合は「後ろのはず」という推定で無視しない。独立したcertified broadphaseは将来の拡張である。

## 境界とself-hit

source IDの除外、epsilon offset、暗黙の正t cutoffはない。t=0のplane hitも返す。
単位球の表面から内向きの根は0と2であり、球ID全体を除外すると出口2も失われる。
現primitiveは球の0根の丸め包絡がdomain境界を跨ぐとunresolvedになる。
それを0へclampしたり後方根で置き換えたりしない。明示tMin=1e-6の照会では出口2を検証する。

1/2^30 m先の別面も照会対象である。tMinを1/2^29へ変えればそれ以前の面はdomain外になるが、
その結果を原点からの最近傍保証とは呼ばない。spawnした独立位置箱は、元面上との相関を失い得る。
sourceタグだけから厳密な0根の同一性を仮定する自動継続は実装していない。

開口内/外が混在、正確な開口端、接線、同時面は未確定として保持する。
capは先行する棄却根と後方の有効根を区別する。開口外を筐体や遮光面に置き換えない。
back faceも幾何hitであり、暗黙のback-face cullingはない。

## 予算と失敗

既定はmax_surfaces=128、max_queries=512、総max_sqrt_refinements=16384。
許可範囲はそれぞれ1..1024、1..4096、1..1000000。primitiveのsqrt予算は別の1..256で、
root/法線/距離等の各端点の精錬を制限する。照会数はoriginalとprefixをともに数える。
上限を超える照会を呼ぶ前に止め、未照会の面を診断で明示する。

総sqrt予算は、各有限primitive呼出しの**実際の処理数**を加えて監査する。
上限を超えた呼出しの結果も診断へ残すが、selectionは設定しない。
処理の超過は1回のprimitive呼出しに限られる。現形状では1回最大1536回のscalar refinementで、
厳密なinstruction中断型の予算ではない。primitiveがrefinement-limitedでも、残る包含から十分な
証明が得られるなら成功し得る。未解決の競合が必要なrefinementを使い切ったときはbudgetとする。
無理に包含を狭めたり品質を下げたりして成功にはしない。

## 独立検証と再現

`tests/optical_selection_tests.cpp` はNative20群、standalone実WASM19群である。
Native専用1群ではround-to-nearestを外し、numerical_failureと復旧後の再利用を確認する。
最初の試験設計では球のt=0を必ずhitと期待したが、既存primitiveの境界包絡による未確定を
確認し、planeの厳密0 hit・球の未確定・明示domain後の球出口を分けて試験した。
同様にrefinement=1だけでは広い包含のhitを証明できる場合があるため、精度幅も要求する
別の予算不足例を設けた。数値をclampする修正や許容誤差の拡大は行っていない。

`--fixtures` は33の完全入力と全primitive診断をJSONで出力する。
`--oracle` はplane/sphere/capを各64、合計192の軸方向ray族で出力する。
入力端点・出力端点はbinary64の16桁hexであり、入力を丸めた係数に置き換えない。
[verify-optical-selection.py](../scripts/verify-optical-selection.py) はNative入力必須、任意のWASM入力を
独立に検証し、与えられた場合はbit比較する。JSON入力の全数値tokenもbinary64として解釈する。
schema・全ケースidentity・分類・ID・有限値・根順・成功証明・counterを監査し、Python -Oは拒否する。

fixtureでは既知のt/距離/位置/法線に対する111有理数包含と33分類を確認する。
oracleでは exact Fractionで (z-o)/d の族全体の極値、物理距離、交差位置zを計算し、
1152包含と192最近傍IDを照合する。対抗planeは同じrayで交差座標が厳密に後方にあることも確認する。
これはこの有限の解析族に対する独立検証であり、任意形状での完全性の実証ではない。

最終standalone比較はfixture2956数値がbit一致、oracle192行も入力/出力hexが一致した。
検証器は正常4通りと破損入力56通りを実行し、欠落・重複・非有限・誤ID/分類・誤った
包含/証明・予算診断・Python -Oをすべて期待どおり処理した。fresh CMake Nativeの
`--fixtures` とstandalone実WASMの出力も2956数値がbit一致した。rawバイトの差は末尾改行の
CRLF対LFの1 byteのみで、改行正規化後の全バイトが一致している。

```text
selection-tests --fixtures > native-fixtures.json
selection-tests --oracle > native-oracle.csv
python scripts/verify-optical-selection.py native-fixtures.json [wasm-fixtures.json]
python scripts/verify-optical-selection.py native-oracle.csv [wasm-oracle.csv]
```

固定toolchain、strict flags、Native/WASM原本出力、比較、負例、SHAは
`build/optical-selection-proof/` に保持する。共有ABI・ブラウザUIとの接続証拠は親統合で記録する。
媒質ID照合は後続層の責務であり、媒質が合わない近い面を飛ばして遠い面を選ぶことは許さない。
