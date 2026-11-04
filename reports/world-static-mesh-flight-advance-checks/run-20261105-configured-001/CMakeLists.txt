cmake_minimum_required(VERSION 3.24)
project(WorldFlightAdvanceConfiguredPrototype LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" OR NOT MSVC_VERSION EQUAL 1951)
  message(FATAL_ERROR "This experiment supports genuine MSVC 19.51 only.")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR NOT CMAKE_GENERATOR_PLATFORM STREQUAL "x64" OR CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "This experiment requires native MSVC x64, not ARM64EC/cross compilation.")
endif()
function(proto_json_quote output input)
  string(REPLACE "\\" "\\\\" escaped "${input}")
  string(REPLACE "\"" "\\\"" escaped "${escaped}")
  string(REPLACE "\n" "\\n" escaped "${escaped}")
  string(REPLACE "\r" "\\r" escaped "${escaped}")
  set(${output} "\"${escaped}\"" PARENT_SCOPE)
endfunction()
set(proto_json "{\n")
foreach(key IN ITEMS CMAKE_VERSION CMAKE_CXX_COMPILER_ID CMAKE_CXX_COMPILER_VERSION CMAKE_CXX_COMPILER
    MSVC_VERSION MSVC_CXX_ARCHITECTURE_ID CMAKE_SIZEOF_VOID_P CMAKE_SYSTEM_NAME
    CMAKE_SYSTEM_PROCESSOR CMAKE_GENERATOR CMAKE_GENERATOR_PLATFORM CMAKE_GENERATOR_TOOLSET
    CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_RELEASE CMAKE_MSVC_RUNTIME_LIBRARY)
  proto_json_quote(encoded "${${key}}")
  string(APPEND proto_json "  \"${key}\":${encoded},\n")
endforeach()
string(APPEND proto_json "  \"configuration\":\"Release\"\n}\n")
file(WRITE "${CMAKE_BINARY_DIR}/compiler-facts.json" "${proto_json}")

add_library(advance_prototype_core STATIC
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/accelerated.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/accelerated_pair_coverage.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/accelerated_plane_box_coverage.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/accelerated_sphere_box_coverage.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/constrained.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/continuous.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/continuous_world.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/core.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/derived_mesh.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/dispersion.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/dynamics.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/hydrostatics.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/interval.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/motion.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/motion_io.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optical_bounds.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optical_geometry.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optical_route.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optical_selection.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optical_spot.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/optics.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/polarization.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/polarized_packet.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/polarized_route.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/portable.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/simulation_api.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/skinning.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/skinning_io.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle_mesh.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle_mesh_entry.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle_mesh_free_flight_guard.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle_mesh_held_load.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/sphere_triangle_mesh_trajectory.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/support.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/supported_world.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/trajectory_guard.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight_advance.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight_guard.cpp"
)
target_include_directories(advance_prototype_core PUBLIC "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/include")
target_compile_options(advance_prototype_core PRIVATE /fp:strict /GL-)
set_property(TARGET advance_prototype_core PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)
set_source_files_properties(
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/core.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight_guard.cpp"
  "C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight_advance.cpp"
  PROPERTIES COMPILE_DEFINITIONS "PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1;PIKAPIKA_WORLD_FLIGHT_BUILD_ID=\"f9444505eb353f9864773d49bf99d0bda04125d12424ebc8675295fa035f9f3b\"")
set_source_files_properties("C:/Users/tak01/github/pikapikaengine/pikapikaengine/core/src/world_static_mesh_flight_advance.cpp" PROPERTIES COMPILE_OPTIONS "/W4;/WX;/permissive-")
add_executable(advance_configured "C:/Users/tak01/github/pikapikaengine/pikapikaengine/tests/world_static_mesh_flight_advance_tests.cpp")
target_link_libraries(advance_configured PRIVATE advance_prototype_core)
target_compile_options(advance_configured PRIVATE /fp:strict /GL- /W4 /WX /permissive-)
target_compile_definitions(advance_configured PRIVATE "PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1;PIKAPIKA_WORLD_FLIGHT_BUILD_ID=\"f9444505eb353f9864773d49bf99d0bda04125d12424ebc8675295fa035f9f3b\"")
target_link_options(advance_configured PRIVATE /LTCG:OFF)
set_property(TARGET advance_configured PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)
