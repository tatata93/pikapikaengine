# Leaf field/schema review gate, not a numerical binding or runtime unlock.
function(pp_check_report_values_schema root)
  set(expected
    "core/report-values-schema-v1.json|da7410b3a39c42027271266d95be95c2b58fa54735cb3b53924d5dbdd77e4a46"
    "core/include/pikapika/core.hpp|58d9ef3b812b85840c64bae052cead0d034bf07f4b07e0a53136222846d66efa"
    "core/include/pikapika/dynamics.hpp|2d1d4055a7136d7c779968415ece3579cd79c930f097abdb18b5a2b05c0c4210"
    "core/include/pikapika/sphere_triangle.hpp|570d7f0dc29c622ebb7faa03d6cc9deb28f17b3cfe74af23f7cbe4fa1b8c92a5"
    "core/include/pikapika/world_static_mesh_flight.hpp|93c6bc53537d4647942c41caff53225b417577239cb131cd0639ff05600fd131"
    "core/include/pikapika/world_static_mesh_flight_controlled_tick.hpp|eb745821642e52c579c925b432c2549e876f603a7f9200f9add5c1e8af80d3d1"
    "core/include/pikapika/world_static_mesh_flight_advance.hpp|f04cc18ddbbffdc4706cdd7e4204f97e9b3f0157d6c4d270d11990adaba8df83"
    "core/include/pikapika/world_static_mesh_flight_scheduler.hpp|6ed6a2c9221e09aae4fdd3f4ad52cf7390494c9b14c415eb8989ebb9d0085b27"
    "core/include/pikapika/diagnostic_wire.hpp|ebe417620df054cde85dc2b9158025114a94358e7c8c90dc48df8158288104b9"
  )
  foreach(row IN LISTS expected)
    string(REPLACE "|" ";" parts "${row}")
    list(GET parts 0 relative)
    list(GET parts 1 digest)
    if(NOT EXISTS "${root}/${relative}")
      message(FATAL_ERROR "Report values schema source missing: ${relative}")
    endif()
    file(SHA256 "${root}/${relative}" actual)
    if(NOT actual STREQUAL digest)
      message(FATAL_ERROR "Report values schema requires field review: ${relative}")
    endif()
  endforeach()
endfunction()
