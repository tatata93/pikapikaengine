# 波長分散の包含核

独自C++20の `optics::dispersion` は、真空波長の**閉区間全体**について位相屈折率n、解析微分dn/dλ、群屈折率ngを囲む。点サンプルをつないだ曲線から全帯の包含を主張しない。材質データベース、光路トレーサー、色収差/フレアの画像生成ではない。

## モデル・単位・入力域

`Cauchy{a,b,c,valid_band}` は n=A+B/λ²+C/λ⁴。
`Sellmeier{terms,count,valid_band}` は q=n²=1+ΣBⱼλ²/(λ²−Cⱼ)、n=正の√q。
最大8項。CauchyのBはm²、Cはm⁴、SellmeierのBは無次元、Cはm²。λはm、nとngは無次元、dn/dλはm⁻¹。
すべて真空基準の**絶対**位相屈折率を表す数式として解釈する。

指定/宣言波長帯はともに[1e−12,1]m内で開始≦終了、指定帯全体が宣言帯内でなければ例外。
数値入力域は材質の校正済み範囲を意味しない。宣言帯は利用者のモデル有効範囲で、外挿は行わない。
使用する係数は有限で絶対値≦1e12。元のbinary64係数/端点を数学的に正確な実数として扱い、係数測定誤差や温度変動を暗黙に追加しない。
未使用Sellmeier配列要素はC++では無視、ABIでは0を要求する。

µm単位の式からSIへ移す場合、Cauchy B×10⁻¹²/C×10⁻²⁴、Sellmeier C×10⁻¹²。
nmの波長は×10⁻⁹。カタログ値が空気に対する相対屈折率なら、単位変換だけでは絶対屈折率にならない。
空気の分散/基準波長を含む変換・実材質の許諾と誤差を確認するまで、その係数を絶対モデルへ入れない。
今回の例は独自の合成係数で、実在ガラスの係数を配布しない。

## 微分と包含

Cauchy: n′=−2B/λ³−4C/λ⁵、ng=A+3B/λ²+5C/λ⁴。
Sellmeier: q′=−2ΣBⱼCⱼλ/(λ²−Cⱼ)²、n′=q′/(2√q)、ng=√q−λn′。
qの各項は恒等式`Bλ²/(λ²−C)=B+BC/(λ²−C)`へ変形し、反復するλの依存性を一つ減らす。
群指数の符号も数学的な結果としてそのまま返し、負値を正へ丸めない。任意係数の数式が因果的な実材質やパルス伝搬を表すとは保証しない。

独自区間演算の外向き包含を各演算へ適用する。平方根は指数から2冪の上界を作り、区間平方の比較と
`|sqrt(x)−m|=|x−m²|/(sqrt(x)+m)` で囲む。libm sqrtの正確な丸めを証明として使わない。
sqrtは入力帯の下/上端を別々に囲んでから結合する。[INTERVAL.md](INTERVAL.md)の浮動小数点環境契約が必要で、strict/no contractionの専用コンパイル設定を適用する。
λの繰り返し出現による依存性を失うので、包含が実際の範囲より広い場合がある。

`maximum_phase_width` は全波長族のn包含幅の上限（既定1e6、有限正値）。純粋な丸め誤差の指定ではない。
`max_sqrt_refinements` はsqrtの各端点の上限1〜256（既定128）。予算を使い切ると成功値を返さない。返却するsqrt_refinementsは両端点の実行回数の合計で、上限設定の最大2倍となる。
幅を縮めるために波長帯を利用者が明示分割できるが、物理モデルの誤差が小さくなったという意味ではない。

## 失敗と診断

Statusはresolved / nonphysical / unresolved。Reasonは順に none / pole_not_excluded / nonpositive_phase /
nonpositive_squared_phase / positivity_uncertain / refinement_budget / phase_width / numerical_range。
不正入力は例外。q上界≦0やCauchy n上界≦0なら非正のモデルが証明されnonphysical、正負を決められなければunresolved。
Sellmeier分母区間が0を含むとpole_not_excluded。これは**特異点の存在証明ではない**。演算の幅のため除外できない場合も含む。
B=0の項は存在しない振動子として省略し、名目上のCに特異点を作らない。C=0の有効項は定数Bとして厳密に簡約する。

成功時だけ`values`を持ち、phase/derivative/groupは有限の包含。Sellmeierのqは独立診断で、未解決でも存在する場合がある。
数値レンジ超過の診断端点は無限になり得る（実数の構成値ではなく上/下界）。ABIはNaNを出さない。
`within_interface_domain` はn包含全体が[1e−6,1e6]内である場合だけtrue。
falseは「実際の指数が必ず範囲外」の証明ではなく、クランプも点への置換もしない。

## 独立検証

Native MSVC strictと固定Emscripten6.0.13の実WASMで14群を確認。
λ=2⁻²⁰m、A=3/2、B=2⁻⁴⁴m²、C=2⁻⁸⁸m⁴では n=401/256、n′=−147456m⁻¹、ng=437/256。
同λの単一Sellmeier B=9/4、C=2⁻⁴²m²では q=4、n=2、n′=−2¹⁹m⁻¹、ng=5/2。
定数、全帯の端点、0係数の名目極、特異点、不正校正帯、非正/符号未確定、予算/幅不足、負の群指数と無クランプを含む。

`tests/dispersion_tests.cpp --oracle` は320例（点160/連続帯160）を元のbinary64入力と出力端点bitで出す。
`scripts/verify-dispersion.py` は独立のFractionで960包含区間を検査し、sqrt参照も平方の有理不等式へ還元する。
コーパスは正のCauchy B,Cまたは単一の正Sellmeier項でλ²>Cに限定。
前者はn/ngが減少、n′が増加。後者も q>1、q′<0、q″>0、`2q q″−q′²>0`からn″>0、
その分子は`4BC[(λ²−C)(3λ²+C)+3Bλ⁴]/(λ²−C)⁴>0`と展開できる。
したがってn/ng減少・n′増加となり、両端の代数的検査が**連続帯全体**を覆う。
任意符号の多項材質全体に、この端点単調性の証明を一般化しない。
Nativeとstandalone実WASMの320完全入力/出力packetは改行正規化後に一致。
`verify-dispersion-wasm.mjs` は主ABIへ元の入力bitを再送し、1920出力端点bitを比較する。
有限コーパスの一致は任意入力に対する普遍的bit一致の主張ではない。

操作ラボは32小帯ごとの実C++照会を矩形で表示し、失敗時は古い値を消す。描画用座標・nm→mの変換は通常JSの丸めを伴う。
原入力は変換後にC++へ渡した値で、図を数値証明として扱わない。界面へ範囲を渡す接続は中央値で済ませず後続で追加する。

## 閲覧した資料と取り込み範囲

[SCHOTT TIE-29, August 2023 §1/§2.3](https://media.schott.com/api/public/content/aaa572afd854434fb7b3faa4bc46103f?v=7f40e8ec):
位相指数の基準、測定相対指数、Sellmeier式の有効波長範囲とµm規約を確認。
[RP Photonics Encyclopedia “Sellmeier Formula”, Dr. Rüdiger Paschotta](https://www.rp-photonics.com/sellmeier_formula.html):
透明材質の分散モデルと適用条件、[同 “Group Index”](https://www.rp-photonics.com/group_index.html): 真空λのng関係を確認。
本文・図・表・係数・コードは取り込まない。数式の解析とコード/SVG/合成検証値は独自作成。新規実行依存なし。
