"""Give the new figure a useful stable deep link."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
a='<figure><img src="diagrams/accelerated-plane-box-coverage.svg"'
b='<figure id="plane-box-coverage"><img src="diagrams/accelerated-plane-box-coverage.svg"'
for name in ['docs/learn/index.html','reports/accelerated-plane-box-coverage-recipes/integrate.py']:
    p=ROOT/name
    text=p.read_text(encoding='utf8')
    assert text.count(a)==1,name
    p.write_text(text.replace(a,b),encoding='utf8')
print('Added stable deep link to the original plane-box figure.')
