#pragma once
// Test-only serialization of actual returned values. No guard query, World
// reconstruction or profile override. Standalone full84 output remains separate.
#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include <iosfwd>
#include <vector>
namespace controlled_scheduler_fixture {
namespace scheduler=pikapika::world_static_mesh_flight_controlled_scheduler;
void report_json(std::ostream&,const scheduler::PumpReport&);
void snapshot_json(std::ostream&,const scheduler::Snapshot&);
void meshes_json(std::ostream&,const std::vector<scheduler::StaticMeshSource>&);
}
