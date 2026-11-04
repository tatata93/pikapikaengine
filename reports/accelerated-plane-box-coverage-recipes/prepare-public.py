"""Prepare a read-only exact-feature collector, including this stage's source."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
old = ROOT/'reports/accelerated-pair-coverage-recipes'
out = Path(__file__).resolve().parent
text = (old/'public.py').read_text(encoding='utf8').replace("PREFIX = 'accelerated-pair-coverage'", "PREFIX = 'accelerated-plane-box-coverage'")
extra = [
 'core/include/pikapika/accelerated_plane_box_coverage.hpp',
 'core/src/accelerated_plane_box_coverage.cpp',
 'tests/accelerated_plane_box_coverage_tests.cpp',
 'tests/accelerated_plane_box_coverage_fixtures.cpp',
 'tests/accelerated_plane_box_coverage_test_support.hpp',
 'scripts/verify-accelerated-plane-box-coverage.py',
 'tests/accelerated_plane_box_coverage_reference_tests.py',
 'docs/ACCELERATED_PLANE_BOX_COVERAGE.md',
 'docs/ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md',
 'docs/learn/diagrams/accelerated-plane-box-coverage.svg',
 'docs/WORLD_PREDICATE_FLOATING_POINT_AUDIT.md',
 'docs/WORLD_STATIC_MESH_FLIGHT_SEED_AUDIT.md',
 'docs/WORLD_STATIC_MESH_PLANE_COVERAGE_PLAN.md',
 'reports/accelerated-plane-box-coverage-local-verification.json',
 'reports/2026-11-04-accelerated-plane-box-coverage.md',
 'reports/accelerated-plane-box-coverage-primary-sources.json',
]
assert len(extra)==16
marker = 'assert len(PATHS) == len(set(PATHS)) == 84'
assert text.count(marker)==1
text=text.replace(marker,'PATHS += '+repr(tuple(extra))+'\nassert len(PATHS) == len(set(PATHS)) == 100')
text=text.replace("'pages': 83", "'pages': 99").replace("== 83", "== 99")
(out/'public.py').write_text(text,encoding='utf8')
text=(old/'public-check.py').read_text(encoding='utf8').replace('accelerated-pair-coverage','accelerated-plane-box-coverage')
(out/'public-check.py').write_text(text,encoding='utf8')
print('Prepared exact-feature collector: 99 Pages files + 1 GitHub source workflow.')
