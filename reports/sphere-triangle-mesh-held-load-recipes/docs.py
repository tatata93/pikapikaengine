"""Add an original held-load explanation without modifying legacy math or games."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'docs/learn/index.html'
text=path.read_text(encoding='utf-8')
start=text.index('<article id="accelerated"')
end=text.index('</article>',start)
assert 'sphere-triangle-mesh-held-load.svg' not in text
addition='<figure><img src="diagrams/sphere-triangle-mesh-held-load.svg" width="1040" height="760" alt="元の質量と外力と重力から曲線を区間で囲む。秒の入口窓とメートルの経路箱の広がりを別に返す。"><figcaption>原著の模式図。両端の直線では見逃す途中の侵入を示します。計測結果ではありません。</figcaption></figure><p><a href="../SPHERE_TRIANGLE_MESH_HELD_LOAD.md">保持荷重の球と有限三角形メッシュのNative照会</a>は、元のF/mを区間のまま計算し、閉じた安全prefixと厳密な負の証拠から秒の窓を調べます。時間幅を位置誤差とは呼ばず、窓の経路箱の広がりをメートルで別に返します。Native専用で、現在のブラウザSDKやWorldの衝突応答には接続していません。</p>'
text=text[:end]+addition+text[end:]
path.write_text(text,encoding='utf-8',newline='\n')
for name,paragraph in {
 'docs/RESEARCH.md':'2026-11-04 保持荷重の球×静的三角形メッシュ照会をNative-onlyで追加中。元binary64のF/m+gを区間のまま二次経路へ通し、global秒時間・R/E補正・閉prefix/負witness・全partitionを監査する。外部solver、追加ライブラリ/推移依存、転載コード/図/材質データは使わない。新しい外部文献を実読したという主張はせず、既存原著核とFractionによる独立極値/最短距離の導出を検証する。Worldの通常double伝播や反力・摩擦・流体・塑性損傷の完成と区別する。',
 'docs/legal/REFERENCES.md':'2026-11-04 保持荷重球×mesh: 新外部文献の実読/引用・図/本文/code転載なし。二次coordinateの端点/内部停留点と、独立なface可行解+3clamped辺のFraction距離から原著証拠を検証する。一般quartic solverや全接触応答の完成とはしない。',
 'docs/legal/DEPENDENCIES.md':'2026-11-04 Native保持荷重球×mesh: 新外部依存・有料契約なし。C++20/既存独自Interval/mesh/World const APIとPython stdlib Fractionを利用。既存Emscripten配布物や86exportsの主SDKは再生成しない。本体license未選定を維持する。',
 'docs/legal/ASSETS.md':'2026-11-04 docs/learn/diagrams/sphere-triangle-mesh-held-load.svg は原著SVG。保持荷重の二次経路、chordとの相違、秒幅とメートルの経路箱の上界を説明する1040×760の模式図。外部画像・font・model・図本文の流用なし。測定値や実際の認証packetを図示したものではない。表示QAと数値受入は別に記録する。'
}.items():
 p=root/name
 old=p.read_text(encoding='utf-8')
 assert paragraph not in old
 p.write_text(old.rstrip()+'\n\n'+paragraph+'\n',encoding='utf-8',newline='\n')
