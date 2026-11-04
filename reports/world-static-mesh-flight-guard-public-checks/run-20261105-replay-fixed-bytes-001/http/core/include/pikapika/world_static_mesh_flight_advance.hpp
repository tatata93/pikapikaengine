#pragma once
#include "pikapika/world_static_mesh_flight_guard.hpp"
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace pikapika::world_static_mesh_flight_advance {
// Native prototype: integration, actual clock-TU flags/artifact audit and tests
// are separate acceptance gates. Existing SDK/World/FixedClock are unchanged.
// See docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md.
using StaticMeshSource=world_static_mesh_flight_guard::StaticMeshSource;
using GuardSettings=world_static_mesh_flight_guard::GuardSettings;
inline constexpr std::size_t hard_max_bodies=8;
inline constexpr double maximum_time=1e9,maximum_horizon=.1;
inline constexpr std::uint64_t maximum_ticks=9007199254740991ULL;

struct Progress {
    double time{}; // Original binary64 seconds; -0 is retained in diagnostics.
    std::uint64_t ticks{};
};
enum class Status : unsigned {committed,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {
    none,environment,binding_unsupported,horizon,progress_time,progress_ticks,
    tick_limit,time_overflow,time_limit,time_resolution,clock_enclosure,
    guard_failed,guard_incomplete,origin_mismatch,candidate_mismatch,
    candidate_validation,destination_mismatch,allocation_failure,unexpected_exception
};
enum class Stage : unsigned {environment,binding,clock,guard,commit_preparation,candidate_validation};
struct Failure {
    Stage stage=Stage::environment;
    // Original owned preparation ordinals, not stable-ID storage order.
    std::optional<world_static_mesh_flight::FailureLocation> object;
};
struct ClockAudit {
    // Each interval contains the exact real expression in its name. These are
    // diagnostics, not corrections to RN(time+H) or exact cumulative physical time.
    interval::Interval time_sum; // original time + requested H
    interval::Interval represented_difference; // proposed time - original time
    interval::Interval sum_rounding_error; // proposed time - (original time + H)
    double represented_dt{}; // RN(proposed time - original time), may differ from H.
};
struct CommitWork {
    std::size_t guard_queries_attempted{},guard_queries_returned{};
    std::size_t pair_records_checked{},call_records_checked{};
    std::size_t origin_bodies_checked{},origin_planes_checked{},origin_meshes_checked{},origin_faces_checked{};
    // Origin counts include BOTH full checks (before and after private candidate
    // validation), including the actual checked prefix if a comparison fails.
    std::size_t candidates_copied{},candidate_validations_attempted{},candidates_validated{};
    std::size_t destination_lookups{},destinations_resolved{};
    // Both zero on EVERY failure. They are populated only for the final
    // statically no-throw store phase; numerical child work stays in guard.work.
    std::size_t body_assignments{},progress_assignments{};
};
struct CommitStorage {
    std::size_t body_buffer_slots{},destination_slots{};
    std::size_t body_buffer_sizeof_bytes{},destination_buffer_sizeof_bytes{};
    // The two named fixed local buffers only, not the entire call frame or Report;
    // separate from guard.reservation. No allocator,
    // used stack/heap, process RSS or physical peak-memory guarantee is implied.
};
struct AdvanceReport {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    bool committed{};
    double requested_dt{},advanced_dt{}; // advanced_dt is ALWAYS +0 on failure.
    Progress original_progress;
    std::optional<Progress> proposed_progress; // A proposal, even when guard fails.
    std::optional<ClockAudit> clock; // No Interval construction before env acceptance.
    world_static_mesh_flight_guard::BindingInfo binding;
    // binding above describes the existing guard. The new clock TU must ALSO
    // pass its own matching configuration gate; ready guard alone is insufficient.
    bool advance_profile_checked{},advance_profile_matches{};
    std::optional<Failure> failure;
    std::optional<world_static_mesh_flight_guard::GuardResult> guard;
    CommitWork work;
    CommitStorage storage;
    std::string message; // Non-normative, allocation-failure fallback may be empty.
};

// Environment FIRST, then the new TU's declared audited configuration must match
// current_binding(). Default builds refuse: a currently accepted guard artifact
// alone does not certify this new source or its clock arithmetic. Future build
// integration must provide strict binary64 flags plus the same profile1/64hex
// PIKAPIKA_WORLD_FLIGHT_BUILD_ID and audit the expanded source/configuration set.
//
// After clock preflight, invokes the CURRENT owned guard exactly once. No external
// certificate/candidate commit entry, fallback, smaller H or partial advance.
// All candidate/source/destination checks and potentially failing work precede
// a separate no-throw commit. All bodies keep their existing address/order.
// Success consumes force/torque once on every body (including static), solely in
// a private commit buffer; the complete owned guard evidence is unchanged.
//
// This is failure atomic within ONE synchronous call, not hardware/thread atomic.
// Caller must exclude concurrent/reentrant observation or mutation of World,
// meshes, settings and Progress, and provide distinct live valid objects.
// No World step/response/TOI, FixedClock scheduler integration or SDK API is added.
AdvanceReport advance(dynamics::World& world,std::span<const StaticMeshSource> meshes,
                      double horizon_seconds,const GuardSettings& settings,
                      Progress& progress) noexcept;
}
