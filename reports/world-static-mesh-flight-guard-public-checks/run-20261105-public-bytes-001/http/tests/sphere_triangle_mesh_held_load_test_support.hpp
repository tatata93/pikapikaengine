#pragma once
// Original, bounded complete-input corpus shared by this new test executable.
#include "pikapika/sphere_triangle_mesh_held_load.hpp"
#include "sphere_triangle_mesh_entry_fixture.hpp"
#include <optional>
#include <string>
#include <vector>

namespace held_fixture {
namespace held=pikapika::sphere_triangle_mesh_held_load;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using entry_fixture::require;
struct Case {
    std::string name;
    held::HeldSphere sphere{101,{1,1,1},{0,0,0},1,{0,0,0},{0,0,0},.25};
    double horizon{.0625};
    std::vector<single::StaticTriangle> triangles{{37,{{{-0.,0,-0.},{4,0,0},{0,0,4}}}}};
    held::Settings settings;
    held::Status expected{held::Status::separated};
    std::optional<held::Reason> why{held::Reason::none};
};
single::StaticTriangle flat(std::uint64_t id,double y=0);
std::vector<Case> cases();
Case named_case(const std::string& name);
void result_json(const held::Result& result);
void input_json(const Case& input);
void emit_fixtures(const std::vector<Case>& corpus);
}
