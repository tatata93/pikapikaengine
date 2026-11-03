#pragma once
#include "pikapika/constrained.hpp"
#include "pikapika/trajectory_guard.hpp"

namespace pikapika::supported {
// Normal-only finite-step W2 driver. RATTLE constrains curved geometry; impulses
// handle near-boundary impacts. Every accepted numerical dense path is audited.
// This is NOT an enclosure of the exact continuous nonsmooth mechanical flow.
enum class Failure { none,invalid_input,initial_geometry,pair_budget,contact_budget,
    attempt_budget,segment_budget,event_budget,minimum_step,constraint_failure,
    trajectory_failure,impulse_failure,energy_failure,numerical_failure,guard_budget };
enum class EventKind { impact,velocity_repair,release };
struct Settings {
    double spatial_tolerance{1e-7}; // m, explicit tolerated dense-path penetration
    double contact_band{5e-8}; // m, early/late near-boundary impact/support model
    double velocity_tolerance{1e-9}; // m/s, residual classification guard
    double maximum_substep{1.0/240.0},minimum_substep{1e-10}; // seconds
    // Coarse-vs-two-half-step diagnostics, NOT rigorous continuous error bounds.
    double position_error_tolerance{1e-6},velocity_error_tolerance{1e-5};
    double orientation_error_tolerance{1e-5}; // quaternion chord norm
    double relative_impact_energy_tolerance{1e-10};
    unsigned max_attempts{16384},max_segments{4096},max_events{512};
    std::size_t max_pair_queries{1000000},max_guard_evaluations{4000000};
    constrained::Settings constraint=[] {constrained::Settings s;s.initial_gap_tolerance=1e-7;return s;}();
    trajectory_guard::Settings guard{};
    dynamics::SolverSettings impulse=[] {dynamics::SolverSettings s;
        s.velocity_iterations=128;s.max_contacts=128;s.position_correction=0;
        s.contact_margin=0;s.restitution_velocity_threshold=0;return s;}();
};
struct Event {
    EventKind kind{EventKind::impact};
    double at{};
    std::uint64_t first_id{},second_id{};
    Vec3 normal{}; // pair orientation at the event snapshot
    std::size_t contacts{};
    double impulse_sum{},kinetic_before{},kinetic_after{},maximum_gap{};
};
struct Report {
    bool success{};
    Failure failure{Failure::none};
    std::string message;
    double advanced_dt{},candidate_time{}; // advanced_dt always zero on failure
    std::uint64_t first_id{},second_id{};
    unsigned attempts{},accepted_segments{},rejected_attempts{},constraint_solves{};
    std::size_t pair_queries{},guard_evaluations{},certified_intervals{};
    double minimum_accepted_substep{},maximum_gap_residual{},maximum_velocity_residual{};
    double maximum_position_error_estimate{},maximum_velocity_error_estimate{},maximum_orientation_error_estimate{};
    double support_impulse_sum{},impact_impulse_sum{},maximum_near_contact_gap{};
    double initial_mechanical_energy{},final_mechanical_energy{},held_force_work{},mechanical_energy_change{};
    double time_roundoff{};
    constrained::Failure last_constraint_failure{constrained::Failure::none};
    trajectory_guard::Failure last_guard_failure{trajectory_guard::Failure::none};
    std::vector<Event> events;
};
// dt in [2e-12,0.1], SI, static planes/sphere proxies. Every participating
// material must explicitly have friction==0. Held world forces/torques survive
// all retries; success consumes them ONCE. Failure preserves every original body,
// its address, all loads and gravity. World clocks are owned by the caller.
Report step(dynamics::World& world,double dt,const Settings& settings={});
}
