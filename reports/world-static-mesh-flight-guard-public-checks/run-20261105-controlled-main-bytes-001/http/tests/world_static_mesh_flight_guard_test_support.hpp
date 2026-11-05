#pragma once
#include "pikapika/world_static_mesh_flight_guard.hpp"
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>
namespace world_guard_fixture {
namespace guard=pikapika::world_static_mesh_flight_guard;
namespace preparation=pikapika::world_static_mesh_flight;
namespace dynamics=pikapika::dynamics;
struct Case {
    std::string name;
    dynamics::World world;
    std::vector<guard::StaticMeshSource> meshes;
    double horizon{.0625};
    guard::GuardSettings settings{.0625};
    std::optional<guard::Status> expected{guard::Status::certified_separated};
    std::optional<guard::Reason> reason;
};
Case base_case();
std::vector<Case> cases();
void body_json(std::ostream&,const dynamics::RigidBody&);
void world_json(std::ostream&,const dynamics::World&);
void input_json(std::ostream&,const Case&);
void settings_json(std::ostream&,const guard::GuardSettings&);
void binding_json(std::ostream&,const guard::BindingInfo&);
void layout_sizes_json(std::ostream&); // Observed sizeof only, not used heap.
void result_json(std::ostream&,const guard::GuardResult&);
void emit_fixtures(std::ostream&,const std::vector<Case>&);
}
