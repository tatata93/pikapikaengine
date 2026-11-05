#pragma once
#include "pikapika/sphere_triangle_mesh_held_load.hpp"
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle_mesh_free_flight_guard {
using Bounds3=sphere_triangle::Bounds3;
struct Settings {
    sphere_triangle_mesh_held_load::Settings held_load{};
    double max_angular_increment{.5}; // radians, finite (0,pi]
};
enum class Status : unsigned {certified_separated,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {none,settings,body_not_found,body_invalid,unsupported_body,input_domain,surface_count,surface_id,duplicate_id,surface_budget,flight_tube_failure,derived_domain,inflated_radius_domain,propagation_failure,candidate_invalid,endpoint_tube_failure,held_load_not_separated,environment,allocation_failure,nonfinite_intermediate,coverage_inconsistent};
struct Snapshot {
    dynamics::RigidBody body; // ALL original fields, including force/torque and rotation
    Vec3 gravity{};
    double horizon{}; // original exact binary64 seconds
    std::vector<sphere_triangle::StaticTriangle> triangles;
    Settings settings;
};
struct Tube {
    Vec3 nominal_acceleration{}; // original W1 rounded g+F*inverse_mass()
    Bounds3 exact_acceleration; // I(g)+I(F)/I(m), not rounded nominal A
    Bounds3 acceleration_difference; // exact A - point(nominal A)
    double position_error{},roundoff{},guard_radius{}; // W1 returned upper bounds, metres
};
struct EndpointAudit {
    Bounds3 nominal_position; // exact polynomial with W1's rounded A at H
    Bounds3 nominal_allowed;  // nominal_position + [-roundoff,roundoff]
    Bounds3 exact_position;   // original real held-load polynomial at H
    Bounds3 exact_allowed;    // exact_position + [-B,B]
    Bounds3 exact_difference; // point(actual candidate position)-exact_position
    interval::Interval l1_error_bound; // upper independently bounds actual endpoint error
    bool nominal_contained{},exact_contained{},l1_within_tube{};
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<std::size_t> failed_index;
    // Environment first. Captured body is retained even if static/invalid; unsafe
    // or missing lookup ID has no world_body. Raw query captures the same fields.
    std::optional<sphere_triangle_mesh_held_load::WorldBodySnapshot> world_body;
    // Full snapshot only after settings/body/source preflight, before tube work.
    std::optional<Snapshot> snapshot;
    std::optional<Tube> tube;
    std::optional<dynamics::CcdFailure> flight_failure; // private W1 bridge classification
    bool candidate_evaluated{}; // propagate_free attempted on an isolated copy
    std::optional<EndpointAudit> endpoint;
    // Original input snapshot above keeps the original radius. This nested query
    // owns a DIFFERENT input radius=tube.guard_radius; no query_body/World mutation.
    std::optional<sphere_triangle_mesh_held_load::Result> inflated;
    // Published iff final status is certified_separated. Loads remain held in it.
    std::optional<dynamics::RigidBody> candidate;
    std::string message;
};

// Single free interval, H finite (0,.1] s. Same raw/derived/source/profile domains
// as held_load; dynamic CoM-centred sphere proxies only. Environment FIRST.
// The existing W1 flight bridge supplies B and roundoff WITHOUT a copied error
// recurrence. Require finite/nonnegative B and r_guard>=exact r+B, r_guard<=1e9.
// Original body copy is propagated ONCE at H with existing propagate_free and
// validated (including full rotation/L/torque); its actual position is audited.
// Only inflated.status==separated, exact Work, and successful candidate/audits
// yield certified_separated. Inflated entry/penetration is NOT original contact.
// B covers the translation branch for each representable duration [0,H] from
// the SAME initial body, not repeated substeps. Full 6DOF success is checked at H
// only; no continuous orientation/velocity error or success at all internal times
// is claimed. All input/World/storage/pointers/loads/clocks remain unchanged.
// BUILD CONTRACT: the actual dynamics.cpp/propagate_free translation must ALSO
// be compiled with strict binary64 evaluation, no fast math/reassociation and no
// contraction/FMA, matching the documented operation graph (not merely this TU).
// Runtime RN-even/gradual-underflow interval environment must remain active.
// An endpoint sample alone cannot establish that all-duration build contract.
// Other bodies/planes, collisions, response, support and tick commit are absent.
Result query(const dynamics::RigidBody& body,Vec3 gravity,
             std::span<const sphere_triangle::StaticTriangle> triangles,
             double horizon_seconds,const Settings& settings={});
Result query_body(const dynamics::World& world,std::uint64_t body_id,
                  std::span<const sphere_triangle::StaticTriangle> triangles,
                  double horizon_seconds,const Settings& settings={});
}
