#pragma once
#include "pikapika/world_static_mesh_flight_controlled_tick.hpp"
#include "world_static_mesh_flight_advance_fixture_support.hpp"
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>
namespace controlled_tick_fixture {
namespace c=pikapika::world_static_mesh_flight_controlled_tick;
struct Case {
    std::string name;
    world_guard_fixture::Case scene;
    c::advance::Progress progress{.125,17};
    c::TickLoadPacket packet{c::LoadMode::replace_total_world_loads,17,{}};
    std::optional<c::Status> expected;
    std::optional<c::Reason> reason;
};
Case base_case();
std::vector<Case> cases();
void report_json(std::ostream&,const c::ControlledReport&);
void packet_json(std::ostream&,const c::TickLoadPacket&);
void world_state_json(std::ostream&,const c::WorldState&);
void emit_fixtures(std::ostream&);
}
