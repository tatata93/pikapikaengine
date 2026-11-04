#pragma once
#include "pikapika/sphere_triangle_mesh_free_flight_guard.hpp"
#include "sphere_triangle_mesh_held_load_test_support.hpp"
#include <optional>
#include <string>
#include <vector>
namespace held_fixture {
void body_json(const pikapika::dynamics::RigidBody& body);
void settings_json(const pikapika::sphere_triangle_mesh_held_load::Settings& settings);
}
namespace free_fixture {
namespace guard=pikapika::sphere_triangle_mesh_free_flight_guard;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using entry_fixture::require;
struct Case {
    std::string name;
    pikapika::dynamics::RigidBody body=[] {auto b=pikapika::dynamics::make_sphere(101,.25,1,{1,1,1});b.inertia_diagonal={1,1,1};return b;}();
    Vec3 gravity{};
    double horizon{.0625};
    std::vector<single::StaticTriangle> triangles{{37,{{{-0.,0,-0.},{4,0,0},{0,0,4}}}}};
    guard::Settings settings;
    guard::Status expected{guard::Status::certified_separated};
    std::optional<guard::Reason> reason;
};
std::vector<Case> cases();
std::vector<Case> binade_cases();
std::vector<Case> supplemental_cases();
Case named_case(const std::string& name);
void result_json(const guard::Result& result);
void input_json(const Case& input);
void emit_fixtures(const std::vector<Case>& corpus);
}
