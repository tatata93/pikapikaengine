# Leaf field/schema review gate, not a numerical binding or runtime unlock.
function(pp_check_report_values_schema root)
  set(expected
    "core/report-values-schema-v1.json|89212e9c6195e2c1efabf0c368adda96f2cb664d0aaa97dbdc72ea1546450931"
    "core/include/pikapika/core.hpp|58d9ef3b812b85840c64bae052cead0d034bf07f4b07e0a53136222846d66efa"
    "core/include/pikapika/dynamics.hpp|2d1d4055a7136d7c779968415ece3579cd79c930f097abdb18b5a2b05c0c4210"
    "core/include/pikapika/sphere_triangle.hpp|570d7f0dc29c622ebb7faa03d6cc9deb28f17b3cfe74af23f7cbe4fa1b8c92a5"
    "core/include/pikapika/world_static_mesh_flight.hpp|93c6bc53537d4647942c41caff53225b417577239cb131cd0639ff05600fd131"
    "core/include/pikapika/world_static_mesh_flight_controlled_tick.hpp|eb745821642e52c579c925b432c2549e876f603a7f9200f9add5c1e8af80d3d1"
    "core/include/pikapika/world_static_mesh_flight_advance.hpp|f04cc18ddbbffdc4706cdd7e4204f97e9b3f0157d6c4d270d11990adaba8df83"
    "core/include/pikapika/world_static_mesh_flight_scheduler.hpp|6ed6a2c9221e09aae4fdd3f4ad52cf7390494c9b14c415eb8989ebb9d0085b27"
    "core/include/pikapika/diagnostic_wire.hpp|ebe417620df054cde85dc2b9158025114a94358e7c8c90dc48df8158288104b9"
    "core/include/pikapika/sphere_triangle_mesh.hpp|0738d8edffd74cdcf7d5593ecb02b4be39fb0f058b46367d20e8c8c70a84c739"
    "core/include/pikapika/sphere_triangle_mesh_held_load.hpp|d01f2e623767bb125379ac3269003c6efa98e14cdbf2815c7f1909c036573d5d"
    "core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp|e2782e2759b8bb87e920fc022b54fbbee4a456b9ca09a961f6bd26a878f5ea7a"
    "core/include/pikapika/accelerated_pair_coverage.hpp|e5de3e36093b8287abab924c5f2cbcd50906e8c046f81ab31ae73b17a78a3e9b"
    "core/include/pikapika/accelerated_plane_box_coverage.hpp|977e0085d30947e46abdd8e5ca3ee1b0328b310689e86efe10d84b697f15b544"
    "core/include/pikapika/accelerated_sphere_box_coverage.hpp|b1095fca311ac2eb4a1b6d464e85945d11ae82d2ae86ab59c5547cef5fbd7ada"
    "core/include/pikapika/world_static_mesh_flight_guard.hpp|6f3b09292d2ea5503d315c1115d4180fb103e389049594dc53b848a4dd65f659"
    "core/include/pikapika/interval.hpp|52d64a7c815a40aab3f3f72ff5b8b7b39e474022fa83a543d093f3f98b64c3ec"
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
