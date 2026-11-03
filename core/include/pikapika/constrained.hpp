#pragma once
#include "pikapika/dynamics.hpp"
#include <array>
#include <span>

namespace pikapika::constrained {
// Explicit ACTIVE equality contacts only. The driver owns unilateral activation,
// release, impact response, inactive-pair CCD, remaining time and whole-tick commit.
struct Pair {
    std::uint64_t first_id{},second_id{}; // plane->sphere, or lower->higher sphere ID
    bool operator==(const Pair&) const = default;
};
enum class Failure { none,invalid_input,initial_geometry,initial_velocity,
    static_constraint,ill_conditioned,newton_budget,linear_budget,line_search,
    normal_rotation,release_required,residual,numerical_failure,contact_budget };
struct Settings {
    double initial_gap_tolerance{1e-8}; // m; explicit finite-error initial model
    double initial_velocity_tolerance{1e-8}; // m/s; NOT support::solve's zero policy
    double position_tolerance{1e-10}; // m, active final gap enclosure
    double velocity_tolerance{1e-10}; // m/s, final normal velocity enclosure
    double position_equation_tolerance{1e-10}; // m
    double velocity_equation_tolerance{1e-10}; // m/s
    double minimum_scaled_pivot{1e-10}; // dimensionless, no regularisation
    double maximum_normal_rotation{0.5}; // rad, (0,1]; endpoint/trial guard
    double maximum_impulse{1e24}; // N s, absolute signed stage impulse
    double maximum_angular_increment{0.5}; // rad, same world-L midpoint rotation
    unsigned max_newton_iterations{32},max_linear_solves{64},max_line_search_steps{16};
    std::size_t max_contacts{128}; // 1..256, dense coupled solve
};
struct Constraint {
    Pair pair;
    Vec3 initial_normal{},final_normal{};
    std::array<double,2> initial_gap{},final_gap{},initial_normal_velocity{},final_normal_velocity{};
    // SIGNED coefficients of J0^T and J1^T, respectively; N s, NOT force N.
    double impulse_position{},impulse_velocity{};
};
struct Residuals {
    double initial_gap{},initial_normal_velocity{},final_gap{},final_normal_velocity{};
    double position_equation{},velocity_equation{};
    double maximum_normal_rotation{},minimum_scaled_pivot{1};
};
struct Result {
    bool success{};
    Failure failure{Failure::none};
    std::string message;
    // Populated ONLY on success. Original body loads are retained, not consumed.
    std::vector<dynamics::RigidBody> candidate_bodies;
    std::vector<Constraint> constraints; // diagnostics may survive failure
    std::vector<Pair> release_pairs; // either signed stage impulse is negative
    Residuals residuals;
    unsigned newton_iterations{},linear_solves{},line_search_trials{};
    std::size_t geometry_evaluations{};
};
// Pure candidate segment, dt in [1e-12,0.1] s, <=1024 bodies and <=64 planes.
// Active rows are fully coupled through all shared dynamic bodies. Friction and
// restitution are not applied here. Normal sphere forces exert no spin torque.
// Numerical RATTLE endpoint/residual contract; NO continuous-solution enclosure,
// dense-path safety, inactive collision handling or automatic unilateral driver.
Result advance(std::span<const dynamics::RigidBody> bodies,
    std::span<const dynamics::Plane> planes,Vec3 gravity,double dt,
    std::span<const Pair> active,const Settings& settings={});
inline Result advance(const dynamics::World& world,double dt,std::span<const Pair> active,
                      const Settings& settings={}){
    return advance(world.bodies(),world.planes(),world.gravity,dt,active,settings);
}
}
