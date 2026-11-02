cmake_minimum_required(VERSION 3.24)
project(pikapikaengine VERSION 0.2.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_library(pikapika_core core/src/core.cpp core/src/portable.cpp core/src/dynamics.cpp)
target_include_directories(pikapika_core PUBLIC core/include)
if(MSVC)
  target_compile_options(pikapika_core PRIVATE /W4 /permissive- /fp:precise)
else()
  target_compile_options(pikapika_core PRIVATE -Wall -Wextra -Wpedantic)
endif()
add_executable(pikapika tools/pikapika.cpp)
target_link_libraries(pikapika PRIVATE pikapika_core)
add_executable(pikapika-dynamics tools/dynamics_bench.cpp)
target_link_libraries(pikapika-dynamics PRIVATE pikapika_core)
execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  OUTPUT_VARIABLE PP_DYN_REVISION_BASE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
if(NOT PP_DYN_REVISION_BASE)
  set(PP_DYN_REVISION_BASE "unavailable")
endif()
execute_process(COMMAND git status --porcelain --untracked-files=normal WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  OUTPUT_VARIABLE PP_DYN_WORKTREE_STATUS ERROR_QUIET)
if(PP_DYN_WORKTREE_STATUS)
  set(PP_DYN_DIRTY 1)
else()
  set(PP_DYN_DIRTY 0)
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  core/src/dynamics.cpp core/include/pikapika/dynamics.hpp tools/dynamics_bench.cpp core/src/core.cpp core/include/pikapika/core.hpp)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/core/src/dynamics.cpp" PP_DYN_SOURCE_HASH)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/core/include/pikapika/dynamics.hpp" PP_DYN_HEADER_HASH)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/tools/dynamics_bench.cpp" PP_DYN_BENCH_HASH)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/core/src/core.cpp" PP_DYN_CORE_HASH)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/core/include/pikapika/core.hpp" PP_DYN_CORE_HEADER_HASH)
target_compile_definitions(pikapika-dynamics PRIVATE
  PP_DYN_REVISION_BASE="${PP_DYN_REVISION_BASE}" PP_DYN_DIRTY=${PP_DYN_DIRTY}
  PP_DYN_SOURCE_HASH="${PP_DYN_SOURCE_HASH}" PP_DYN_HEADER_HASH="${PP_DYN_HEADER_HASH}"
  PP_DYN_BENCH_HASH="${PP_DYN_BENCH_HASH}" PP_DYN_CORE_HASH="${PP_DYN_CORE_HASH}"
  PP_DYN_CORE_HEADER_HASH="${PP_DYN_CORE_HEADER_HASH}"
  PP_DYN_COMPILER_ID="${CMAKE_CXX_COMPILER_ID}" PP_DYN_COMPILER_VERSION="${CMAKE_CXX_COMPILER_VERSION}"
  PP_DYN_BUILD_CONFIG="$<CONFIG>")
if(WIN32)
  execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    OUTPUT_VARIABLE PIKAPIKA_REVISION_BASE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
  if(NOT PIKAPIKA_REVISION_BASE)
    set(PIKAPIKA_REVISION_BASE "unavailable")
  endif()
  execute_process(COMMAND git status --porcelain --untracked-files=no WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    OUTPUT_VARIABLE PIKAPIKA_WORKTREE_STATUS ERROR_QUIET)
  if(PIKAPIKA_WORKTREE_STATUS)
    set(PIKAPIKA_WORKTREE_DIRTY 1)
  else()
    set(PIKAPIKA_WORKTREE_DIRTY 0)
  endif()
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    core/src/core.cpp platform/windows/viewer.cpp)
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/core/src/core.cpp" PIKAPIKA_CORE_SOURCE_SHA256)
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/platform/windows/viewer.cpp" PIKAPIKA_VIEWER_SOURCE_SHA256)
  add_executable(pikapika-viewer WIN32 platform/windows/viewer.cpp)
  target_link_libraries(pikapika-viewer PRIVATE pikapika_core d3d12 dxgi d3dcompiler user32 shell32)
  target_compile_definitions(pikapika-viewer PRIVATE UNICODE _UNICODE NOMINMAX
    PIKAPIKA_CODE_REVISION_BASE="${PIKAPIKA_REVISION_BASE}"
    PIKAPIKA_WORKTREE_DIRTY=${PIKAPIKA_WORKTREE_DIRTY}
    PIKAPIKA_CORE_SOURCE_SHA256="${PIKAPIKA_CORE_SOURCE_SHA256}"
    PIKAPIKA_VIEWER_SOURCE_SHA256="${PIKAPIKA_VIEWER_SOURCE_SHA256}")
endif()
include(CTest)
if(BUILD_TESTING)
  add_executable(pikapika_core_tests tests/core_tests.cpp)
  target_link_libraries(pikapika_core_tests PRIVATE pikapika_core)
  add_test(NAME core COMMAND pikapika_core_tests)
  add_executable(pikapika_dynamics_tests tests/dynamics_tests.cpp)
  target_link_libraries(pikapika_dynamics_tests PRIVATE pikapika_core)
  add_test(NAME dynamics COMMAND pikapika_dynamics_tests)
endif()
