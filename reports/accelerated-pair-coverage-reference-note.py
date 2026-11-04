"""Record the actual post-design primary-source reading without importing code."""
from datetime import datetime, timezone
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
url = 'https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node9.html'
note = {'schema':1,'read':datetime.now(timezone.utc).isoformat(),
        'title':'Shape Interrogation for Computer Aided Design and Manufacturing —1.3.1 Bernstein polynomials',
        'url':url,'scope':'Read the authors\' MIT-hosted section after initial design/Native implementation: basis non-negativity and partition of unity support the sign-certificate argument. No program, diagram, expression image or prose copied; no library/package/license/runtime dependency added.',
        'inference':'For a polynomial expressed in a nonnegative basis, nonnegative coefficients are a sufficient nonnegativity certificate. This does not prove that finite subdivision must certify every polynomial with zeros. Unresolved reference work remains failure.'}
(root/'reports/accelerated-pair-coverage-primary-source.json').write_text(json.dumps(note,indent=2)+'\n',encoding='utf-8')
path = root/'docs/ACCELERATED_PAIR_COVERAGE_PLAN.md'
text = path.read_text(encoding='utf-8')
before = '今回外部資料は閲覧せず、実ソースと以下の数学式から設計する。'
assert text.count(before)==1
text = text.replace(before,'初期設計は実ソースと以下の数学式から行った。その後、[著者のMIT公開教材1.3.1]('+url+')でBernstein基底の非負性・partition of unityを確認した。プログラム・図・本文は転載せず、新依存も追加しない。',1)
path.write_text(text,encoding='utf-8',newline='\n')
path = root/'docs/legal/REFERENCES.md'
text = path.read_text(encoding='utf-8')
before = '2026-11-04 Native accelerated pair coverage: 新外部資料の実読・引用・図/codeの移植はない。'
assert text.count(before)==1
text = text.replace(before,'2026-11-04 Native accelerated pair coverage: 初期設計・Native実装は外部資料を実読せず行った。続く数学監査の確認で、著者による[MIT公開教材1.3.1 Bernstein polynomials]('+url+')の基底非負性・partition of unityを実読した。式画像・本文・図/codeは移植しない。',1)
path.write_text(text,encoding='utf-8',newline='\n')
with (root/'docs/RESEARCH.md').open('a',encoding='utf-8',newline='\n') as stream:
    stream.write('\n\ncoverageの外部一次資料確認追記: 初期実装後、[著者のMIT公開教材1.3.1]('+url+')でBernstein基底の非負性・partition of unityを確認した。非負係数が非負多項式の十分条件になる根拠を確認する範囲であり、有限分割の全入力成功や重根処理を資料から保証したとはしない。独立実装と有限checker失敗時の未認証方針を維持し、外部code/図/本文や依存は取り込まない。\n')
print('Recorded one actual primary-source reading; no code, asset or dependency imported.')
