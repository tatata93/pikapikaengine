"""Add only this helper's CI stage and original lesson, preserving prior text."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ci = ROOT/'.github/workflows/verify.yml'
text = ci.read_text(encoding='utf8')
marker = '      - name: Compile and execute actual WebAssembly core\n'
assert text.count(marker)==1 and 'Audit declared-error plane box coverage' not in text
stage = '''      - name: Audit declared-error plane box coverage independently
        run: |
          build/ci/pikapika_accelerated_plane_box_coverage_tests --fixtures > build/ci/accelerated-plane-box-coverage-fixtures.json
          python3 scripts/verify-accelerated-plane-box-coverage.py build/ci/accelerated-plane-box-coverage-fixtures.json
          python3 tests/accelerated_plane_box_coverage_reference_tests.py build/ci/accelerated-plane-box-coverage-fixtures.json --output build/ci/accelerated-plane-box-coverage-reference
          for source in core/src/accelerated_plane_box_coverage.cpp tests/accelerated_plane_box_coverage_tests.cpp tests/accelerated_plane_box_coverage_fixtures.cpp; do
            g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -fno-fast-math -ffp-contract=off -frounding-math -Icore/include -c "$source" -o "build/ci/$(basename "$source" .cpp)-warning.o"
          done
          g++ -std=c++20 -O1 -g -Wall -Wextra -fno-fast-math -ffp-contract=off -frounding-math -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer -Icore/include core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_plane_box_coverage.cpp tests/accelerated_plane_box_coverage_tests.cpp tests/accelerated_plane_box_coverage_fixtures.cpp -o build/ci/accelerated-plane-box-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-plane-box-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-plane-box-coverage-sanitized --fixtures > build/ci/accelerated-plane-box-coverage-sanitized-fixtures.json
          cmp build/ci/accelerated-plane-box-coverage-fixtures.json build/ci/accelerated-plane-box-coverage-sanitized-fixtures.json
          python3 scripts/verify-accelerated-plane-box-coverage.py build/ci/accelerated-plane-box-coverage-sanitized-fixtures.json
'''
ci.write_text(text.replace(marker,stage+marker),encoding='utf8')
lesson = ROOT/'docs/learn/index.html'
text = lesson.read_text(encoding='utf8')
start = text.index('<article id="accelerated"')
end = text.index('</article>',start)
assert 'diagrams/accelerated-plane-box-coverage.svg' not in text
added = '<figure id="plane-box-coverage"><img src="diagrams/accelerated-plane-box-coverage.svg" width="1120" height="750" alt="宣言された位置誤差Bと接触余裕を平面の判定式へ含め、全閉時間区画の正の下限と未照会tailを別に保持する。"><figcaption>原著の概念図。実測の軌道や性能を示す図ではありません。</figcaption></figure><p><a href="../ACCELERATED_PLANE_BOX_COVERAGE.md">位置誤差と接触余裕を明示したNative平面検査</a>は、箱に囲まれた全中心について、固定演算順序の実数計算とbinary64丸めの両方を含めます。Bとmarginは呼び出し側が明示します。実Worldの誤差上限や全pair・接触応答を自動で保証する段階は後続です。</p>'
lesson.write_text(text[:end]+added+text[end:],encoding='utf8')
print('Added one Native CI stage and one original lesson figure/paragraph.')
