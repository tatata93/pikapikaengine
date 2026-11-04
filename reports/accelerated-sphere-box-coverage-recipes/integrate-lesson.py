"""Append the original sphere-box explanation after the accepted plane receipt."""
from hashlib import sha256
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
base=json.loads((ROOT/'reports/accelerated-sphere-box-coverage-baseline.json').read_text(encoding='utf8'))
lesson=ROOT/'docs/learn/index.html'
raw=lesson.read_bytes()
assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==base['lessonBefore']
text=raw.decode('utf8')
start=text.index('<article id="accelerated"')
end=text.index('</article>',start)
assert 'id="sphere-box-coverage"' not in text
added='<figure id="sphere-box-coverage"><img src="diagrams/accelerated-sphere-box-coverage.svg" width="1120" height="760" alt="二つの宣言位置誤差を箱へ一度ずつ含め、位置差と二乗距離、平方根、左結合の半径と接触余裕を囲む。"><figcaption>原著の概念図。実測の軌道・誤差幅・性能を示す図ではありません。</figcaption></figure><p><a href="../ACCELERATED_SPHERE_BOX_COVERAGE.md">両方の位置誤差を含むNative球接触式の検査</a>は、位置差・二乗和・平方根と接触閾値の丸めを、固定した演算順序で包含します。両方のBとmarginは明示した条件です。全閉時間区画の下限が正のときだけ認証し、未知の区画と返却されなかった計算の予約上界も残します。実WorldのBの由来と外部sqrt/compilerへの接続は、後続の統合条件です。</p>'
lesson.write_bytes((text[:end]+added+text[end:]).encode('utf8'))
print('Added one original sphere-box figure and explanation; old article text preserved.')
