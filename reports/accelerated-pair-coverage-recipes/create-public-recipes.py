"""Derive bounded public verification from the accepted preparation collector."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
old = 'reports/world-static-mesh-preparation-recipes/'
new = 'reports/accelerated-pair-coverage-recipes/'
text = (root/(old+'public.py')).read_text(encoding='utf-8')
before = 'assert len(PATHS) == len(set(PATHS)) == 74'
assert text.count(before)==1
addition = '''PATHS += (
    'core/include/pikapika/accelerated_pair_coverage.hpp',
    'core/src/accelerated_pair_coverage.cpp',
    'tests/accelerated_pair_coverage_tests.cpp',
    'tests/accelerated_pair_coverage_fixtures.cpp',
    'tests/accelerated_pair_coverage_test_support.hpp',
    'scripts/verify-accelerated-pair-coverage.py',
    'tests/accelerated_pair_coverage_reference_tests.py',
    'docs/ACCELERATED_PAIR_COVERAGE.md',
    'docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
    'docs/learn/diagrams/accelerated-pair-coverage.svg',
)
assert len(PATHS) == len(set(PATHS)) == 84'''
text = text.replace(before,addition,1)
assert text.count("PREFIX = 'world-static-mesh-preparation'")==1
text = text.replace("PREFIX = 'world-static-mesh-preparation'", "PREFIX = 'accelerated-pair-coverage'",1)
assert text.count("'pages': 73")==1 and text.count("== 73")==1
text = text.replace("'pages': 73", "'pages': 83",1).replace('== 73','== 83',1)
target = root/(new+'public.py')
assert not target.exists()
target.write_text(text,encoding='utf-8',newline='\n')
wrapper = (root/(old+'public-check.py')).read_text(encoding='utf-8')
assert wrapper.count(old)==1
target = root/(new+'public-check.py')
assert not target.exists()
target.write_text(wrapper.replace(old,new,1),encoding='utf-8',newline='\n')
print('Prepared bounded collector for83 Pages resources plus one exact-feature GitHub workflow source; no network request performed.')
