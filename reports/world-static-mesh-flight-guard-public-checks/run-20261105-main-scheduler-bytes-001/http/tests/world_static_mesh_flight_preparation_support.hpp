#pragma once
#include "pikapika/world_static_mesh_flight.hpp"
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>

namespace preparation_fixture {
namespace preparation=pikapika::world_static_mesh_flight;
namespace dynamics=pikapika::dynamics;
struct Case {
    std::string name;
    dynamics::World world;
    std::vector<preparation::StaticMeshSource> meshes;
    double horizon{.0625};
    preparation::Settings settings;
    preparation::Status expected{preparation::Status::ready};
    preparation::Reason reason{preparation::Reason::none};
    std::optional<preparation::FailureLocation> failure;
};
Case base_case();
std::vector<Case> cases();
void input_json(std::ostream&,const Case&);
void snapshot_json(std::ostream&,const preparation::Snapshot&);
void result_json(std::ostream&,const preparation::Result&);
void emit_fixtures(std::ostream&,const std::vector<Case>&);
}
