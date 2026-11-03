#pragma once
#include "pikapika/dynamics.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>

namespace pikapika::trajectory_guard {
// Geometry of a DEFINED numerical path, not an enclosure of a continuous
// constrained mechanical solution. All input binary64 values denote exact reals.
// q(s)=q0+dt*v0*s+(q1-q0-dt*v0)*s^2, 0<=s<=1; t=dt*s seconds.
enum class Failure { none, invalid_input, penetration_witness, pair_budget,
    evaluation_budget, depth_budget, numerical_uncertainty, numerical_failure };
enum class Predicate { none, sphere_squared_clearance, plane_signed_offset,
    plane_squared_clearance };
struct Settings {
    double spatial_tolerance{1e-6}; // metres; 0 <= tolerance < every body radius
    bool include_static_pairs{true}; // false explicitly omits ONLY immobile pairs
    std::size_t max_pair_queries{100000},max_evaluations{1000000};
    unsigned max_depth{48}; // 0..52; depth zero still checks the whole interval
};
struct Result {
    bool success{};
    Failure failure{Failure::none};
    std::string message;
    // Plane->body, or input-order sphere->sphere. Zero on global invalid input.
    // For success these IDs and diagnostic parameter/predicate fields are zero.
    std::uint64_t first_id{},second_id{};
    std::size_t pair_queries{},skipped_static_pairs{},evaluations{},certified_intervals{};
    unsigned maximum_depth{};
    std::array<double,2> parameter_bounds{}; // s in [0,1], NOT seconds
    bool has_point_witness{};
    double witness_parameter{};
    Predicate predicate{Predicate::none};
    // Negative UPPER endpoint at an exact point proves forbidden penetration.
    // Sphere/squared plane predicates have m^2 units if the plane normal is
    // dimensionless; signed plane offset has m units. These are not gap bounds.
    std::array<double,2> predicate_bounds{};
};
// Matching array size/order/IDs, radii and static flags are required. Static
// bodies must have unchanged positions and zero initial/final linear velocity.
// Geometry-only validation: other body/material/rotation fields are ignored.
// Coordinates, velocities, radii, plane normal/offset: finite, abs <=1e12;
// radii >0, dt in (0,0.1], unique nonzero IDs across bodies and planes.
// Planes are STATIC halfspaces n.x<=offset (solid), with any nonzero raw n.
// The tolerated legal centre condition is (n.q-offset)/|n| >= radius-tolerance.
// By default all sphere/plane and sphere/sphere pairs are checked. If
// include_static_pairs=false, only static-body/plane and static/static-sphere
// pairs are skipped and counted. Every pair involving a dynamic body is checked.
// No mutation, projection, impulses, endpoint-only acceptance or dropped pairs.
// Requires interval.hpp's strict-FP/environment contract throughout the call.
Result audit(std::span<const dynamics::RigidBody> initial,
             std::span<const dynamics::RigidBody> final,
             std::span<const dynamics::Plane> planes,double dt,
             const Settings& settings={});
}
