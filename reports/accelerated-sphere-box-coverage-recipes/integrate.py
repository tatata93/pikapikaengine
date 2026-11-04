"""Integrate ONLY the frozen helper's CMake/CI/raw-report attributes.
Run only after the parent explicitly authorizes postreceipt integration:
python .../integrate.py FULL_NEW_PLANE_RECEIPT_HEAD
All candidates are checked first. Existing lesson, check.py and SDK stay untouched.
"""
from datetime import datetime,timezone
from pathlib import Path
import argparse
import difflib
import json
from prepare import ROOT,PREFIX,BASELINE,INTEGRATIONS,info,file_info,need,validate_base,frozen_sources

CMAKE_SOURCE='''target_sources(pikapika_core PRIVATE core/include/pikapika/accelerated_sphere_box_coverage.hpp core/src/accelerated_sphere_box_coverage.cpp)
if(MSVC)
  set_source_files_properties(core/src/accelerated_sphere_box_coverage.cpp PROPERTIES COMPILE_OPTIONS "/fp:strict")
else()
  set_source_files_properties(core/src/accelerated_sphere_box_coverage.cpp PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-frounding-math")
endif()
'''
CMAKE_TEST='''  add_executable(pikapika_accelerated_sphere_box_coverage_tests tests/accelerated_sphere_box_coverage_tests.cpp tests/accelerated_sphere_box_coverage_fixtures.cpp)
  target_link_libraries(pikapika_accelerated_sphere_box_coverage_tests PRIVATE pikapika_core)
  if(MSVC)
    target_compile_options(pikapika_accelerated_sphere_box_coverage_tests PRIVATE /W4 /permissive- /fp:strict)
  else()
    target_compile_options(pikapika_accelerated_sphere_box_coverage_tests PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -frounding-math)
  endif()
  add_test(NAME accelerated_sphere_box_coverage COMMAND pikapika_accelerated_sphere_box_coverage_tests)
'''
CI_STAGE='''      - name: Audit two-declared-error sphere box coverage independently
        run: |
          build/ci/pikapika_accelerated_sphere_box_coverage_tests --fixtures > build/ci/accelerated-sphere-box-coverage-fixtures.json
          python3 scripts/verify-accelerated-sphere-box-coverage.py build/ci/accelerated-sphere-box-coverage-fixtures.json
          python3 tests/accelerated_sphere_box_coverage_reference_tests.py build/ci/accelerated-sphere-box-coverage-fixtures.json --output build/ci/accelerated-sphere-box-coverage-reference
          for source in core/src/accelerated_sphere_box_coverage.cpp tests/accelerated_sphere_box_coverage_tests.cpp tests/accelerated_sphere_box_coverage_fixtures.cpp; do
            g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -fno-fast-math -ffp-contract=off -frounding-math -Icore/include -c "$source" -o "build/ci/$(basename "$source" .cpp)-warning.o"
          done
          g++ -std=c++20 -O1 -g -Wall -Wextra -fno-fast-math -ffp-contract=off -frounding-math -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer -Icore/include core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_sphere_box_coverage.cpp tests/accelerated_sphere_box_coverage_tests.cpp tests/accelerated_sphere_box_coverage_fixtures.cpp -o build/ci/accelerated-sphere-box-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-sphere-box-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-sphere-box-coverage-sanitized --fixtures > build/ci/accelerated-sphere-box-coverage-sanitized-fixtures.json
          cmp build/ci/accelerated-sphere-box-coverage-fixtures.json build/ci/accelerated-sphere-box-coverage-sanitized-fixtures.json
          python3 scripts/verify-accelerated-sphere-box-coverage.py build/ci/accelerated-sphere-box-coverage-sanitized-fixtures.json
'''
ATTR_LINES='''reports/accelerated-sphere-box-coverage-* -text -whitespace
reports/accelerated-sphere-box-coverage-*/** -text -whitespace
'''


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('base');args=parser.parse_args()
 baseline=json.loads((ROOT/BASELINE).read_text(encoding='utf-8'))
 need(baseline['baseCommit']==args.base,'Integration must use the same FINAL baseline')
 validate_base(args.base)
 need(frozen_sources()==baseline['newSources'],'Frozen source map changed')
 report=ROOT/f'reports/{PREFIX}-integration.json';patchfile=ROOT/f'reports/{PREFIX}-integration.patch.txt'
 need(not report.exists() and not patchfile.exists(),'Do not overwrite integration evidence')
 candidates={};patch=[];counts={};before={}
 for path in INTEGRATIONS:
  raw=(ROOT/path).read_bytes();need(info(raw)==baseline['permittedOldSources'][path]['raw'],'Old integration bytes changed: '+path)
  before[path]=info(raw);text=raw.decode('utf-8').replace('\r\n','\n')
  need('accelerated_sphere_box_coverage' not in text and 'accelerated-sphere-box-coverage' not in text,'Already integrated: '+path)
  if path=='CMakeLists.txt':
   marker='target_sources(pikapika_core PRIVATE core/src/accelerated_plane_box_coverage.cpp)\n'
   need(text.count(marker)==1,'CMake source anchor changed');after=text.replace(marker,marker+CMAKE_SOURCE)
   marker='  add_test(NAME accelerated_plane_box_coverage COMMAND pikapika_accelerated_plane_box_coverage_tests)\n'
   need(after.count(marker)==1,'CMake test anchor changed');after=after.replace(marker,marker+CMAKE_TEST)
   fragments=[CMAKE_SOURCE,CMAKE_TEST];counts[path]=14
  elif path=='.github/workflows/verify.yml':
   marker='      - name: Compile and execute actual WebAssembly core\n'
   need(text.count(marker)==1,'CI anchor changed');after=text.replace(marker,CI_STAGE+marker)
   fragments=[CI_STAGE];counts[path]=13
  else:
   marker='reports/accelerated-plane-box-coverage-*/** -text -whitespace\n'
   need(text.count(marker)==1,'Attribute anchor changed');after=text.replace(marker,marker+ATTR_LINES)
   fragments=[ATTR_LINES];counts[path]=2
  reverse=after
  for fragment in fragments:
   need(reverse.count(fragment)==1,'Exact fragment missing/duplicated');reverse=reverse.replace(fragment,'',1)
  need(reverse==text,'Not an insertion-only integration: '+path)
  need(sum(f.count('\n') for f in fragments)==counts[path],'Unexpected integration line count')
  need(reverse.encode()==baseline['permittedOldSources'][path]['gitBlobUtf8'].encode(),'Stripped integration not original Git blob')
  newline='\r\n' if b'\r\n' in raw else '\n'
  need(newline!='\r\n' or raw.count(b'\n')==raw.count(b'\r\n'),'Mixed original line endings')
  encoded=after.replace('\n',newline).encode('utf-8');candidates[path]=encoded
  need(reverse.replace('\n',newline).encode()==raw,'Raw rollback failed')
  patch.extend(difflib.unified_diff(text.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
 with patchfile.open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(patch))
 for path,raw in candidates.items():(ROOT/path).write_bytes(raw)
 need(frozen_sources()==baseline['newSources'],'Source changed during integration')
 record={'schema':1,'status':'PASS','phase':'integration-only-not-build-acceptance','created':datetime.now(timezone.utc).isoformat(),'baseCommit':args.base,
  'insertedLines':counts,'before':before,'after':{p:file_info(p) for p in INTEGRATIONS},'exactInsertionOnlyRoundtrip':True,
  'allPriorCITextPreserved':True,'newCTestCountPlanned':45,'newNativeTest':'accelerated_sphere_box_coverage','newCIStages':1,'newWerrorTranslationUnits':3,'fullyInstrumentedTranslationUnits':5,
  'referenceControlsExpectedFromFrozenTests':{'selfTestGroups':16,'negativeControls':89,'actualExecution':'not performed by this recipe'},
  'patch':{'path':str(patchfile.relative_to(ROOT)),**file_info(patchfile.relative_to(ROOT))},'newSources':baseline['newSources'],
  'unchanged':{'sdk':'all pre-authoring protected artifacts unchanged; no SDK rebuild','existingSources':376,'generatedEntries':26,'lessonBefore':baseline['lessonBefore']},
  'scope':'Only CMake/CI/raw-report attributes integrated. No build/test/math/public success inferred. Root handles original lesson and all verification.'}
 with report.open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps({'status':'PASS','base':args.base,'insertedLines':counts,'buildRun':False}))
if __name__=='__main__':main()
