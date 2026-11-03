#pragma once
#include "pikapika/dynamics.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace pikapika::support {
// Read-only, acceleration-level, normal-only support query. It neither integrates
// a World nor applies forces, impulses, position correction or load consumption.
enum class Failure { none,invalid_input,geometry_incompatible,geometry_uncertain,
    impact_required,velocity_uncertain,static_constraint,pair_budget,contact_budget,
    ill_conditioned,iteration_budget,numerical_uncertainty,numerical_failure };
enum class Phase { resting,separating };
struct Settings {
    // Explicit guarded-contact MODEL: a gap enclosure wholly inside +/- this
    // band may be solved as a boundary. The actual positions are never changed.
    double gap_tolerance{1e-8}; // m, <= 0.001 of every radius
    double velocity_interval_tolerance{1e-9}; // m/s, uncertainty-width guard ONLY
    // A provably negative vn is an impact even if |vn| is much smaller than this.
    double acceleration_tolerance{1e-8}; // m/s^2, bound on negative acceleration
    double complementarity_tolerance{1e-7}; // N m/s^2, bound on |lambda*a_n|
    double projected_force_tolerance{1e-8}; // N, projected fixed-point residual
    double minimum_scaled_pivot{1e-10}; // dimensionless conditioning rejection
    double maximum_force{1e24}; // N
    unsigned max_iterations{20000};
    std::size_t max_contacts{128},max_pair_queries{100000};
};
struct Constraint {
    std::uint64_t first_id{},second_id{}; // plane->body or lower-ID sphere->sphere
    Phase phase{Phase::resting};
    Vec3 normal{}; // from first to second; +lambda*n acts on second
    Vec3 normal_lower{},normal_upper{};
    std::array<double,2> gap{},normal_velocity{},curvature{}; // m, m/s, m/s^2
    bool guarded_geometry{true}; // finite band, not an exact-contact assertion
    double free_normal_acceleration{},lambda{},normal_acceleration{};
    std::array<double,2> acceleration_bounds{};
};
struct BodyReaction {
    std::uint64_t id{};
    Vec3 force{},normal_torque{}; // N, N m; radial sphere normal torque is zero
    Vec3 force_lower{},force_upper{};
    Vec3 acceleration{},acceleration_lower{},acceleration_upper{}; // m/s^2
};
struct Residuals {
    double negative_force{},negative_acceleration{},complementarity{},projected_force{};
    double maximum_acceleration_interval_width{};
};
struct Result {
    bool success{};
    Failure failure{Failure::none};
    std::string message;
    std::uint64_t first_id{},second_id{};
    std::size_t pair_queries{},separated_pairs{},resting_constraints{},separating_constraints{};
    unsigned iterations{};
    double maximum_geometry_offset{},maximum_velocity_interval_width{},minimum_scaled_pivot{1};
    Residuals residuals{};
    std::vector<Constraint> constraints;
    std::vector<BodyReaction> bodies;
};
Result solve(const dynamics::World& world,const Settings& settings={});
}
