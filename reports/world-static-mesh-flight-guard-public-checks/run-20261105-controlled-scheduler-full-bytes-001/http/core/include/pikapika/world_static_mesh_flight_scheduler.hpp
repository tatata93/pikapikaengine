#pragma once
#include "pikapika/world_static_mesh_flight_advance.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

namespace pikapika::world_static_mesh_flight_scheduler {
// Isolated Native prototype. No FixedClock, seven-source identity, SDK or game
// change. Configuration labels are not an actual instruction/clock proof.
namespace advance=world_static_mesh_flight_advance;
using StaticMeshSource=advance::StaticMeshSource;
using GuardSettings=advance::GuardSettings;
inline constexpr std::size_t hard_max_attempts=8;
inline constexpr double minimum_step=0x1p-20,maximum_step=.1,maximum_backlog=1.,maximum_elapsed=1.;
struct Settings {double step_seconds=1.0/120.0;std::size_t max_attempts_per_pump=4;};
struct Snapshot {Settings settings;double backlog{};std::uint64_t sequence{};bool busy{};};
struct Binding {
    unsigned profile{};
    bool configured{};
    std::array<char,65> build_id{}; // Separate scheduler source/compiler identity.
};
Binding current_binding() noexcept;
enum class Status : unsigned {waiting,step_budget,tick_rejected,invalid_input,unsupported_environment,numerical_failure,reentrant};
enum class Reason : unsigned {none,environment,binding_unsupported,elapsed,backlog_limit,sequence_limit,queue_arithmetic,cost_overflow,allocation_failure,unexpected_exception,busy,advance_rejected};
struct QueueStep {
    double credit_before{},proposed_after{};
    interval::Interval rounding_error; // proposed_after - exact(credit_before-step)
};
struct Attempt {
    std::size_t queue_index{};
    bool credit_consumed{};
    advance::AdvanceReport report; // Only the actual one-call result, full ownership.
};
struct UpperBudget {
    std::size_t attempts{};
    world_static_mesh_flight_guard::WorkGrant guard_work;
    std::size_t guard_logical_payload_bytes{};
    // Checked products of planned slots and EXISTING hard per-call SETTLED
    // charged upper limits, NOT cumulative granted (which can exceed limits
    // after refunds). Unexecuted tail remains reserved after a refused tick.
    // Not observed work, complete Report heap, stack or allocator bounds.
};
struct PumpReport {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    Binding binding;
    Snapshot before{},after{};
    double requested_elapsed{};
    bool elapsed_accepted{};
    std::optional<double> admitted_credit;
    std::optional<interval::Interval> admission_rounding_error;
    advance::Progress progress_before{},progress_after{};
    std::array<std::optional<QueueStep>,hard_max_attempts> queue_plan;
    std::size_t planned_attempts{},attempts{},committed_ticks{};
    std::array<std::optional<Attempt>,hard_max_attempts> tick_reports;
    UpperBudget upper_budget;
    double dropped_seconds{}; // Always +0: retain-only, including step_budget.
    bool has_whole_tick_backlog{};
};

class Scheduler {
public:
    explicit Scheduler(Settings settings={}); // Throws on invalid immutable config.
    Scheduler(const Scheduler&)=delete;
    Scheduler& operator=(const Scheduler&)=delete;
    Scheduler(Scheduler&&)=delete;
    Scheduler& operator=(Scheduler&&)=delete;
    Snapshot snapshot() const noexcept;
    // Accepted elapsed is added ONCE even if the first tick is refused. Retry
    // with elapsed=0. Only committed ticks subtract credit; success prefix stays.
    // No callbacks/requery/fallback/adaptive H/drop. Loads apply to the first
    // successful tick only; advance clears them before any subsequent tick.
    // Caller excludes concurrent/reentrant World/Progress/source access and uses
    // one scheduler for one logical World. No borrowed reference survives return.
    PumpReport pump(dynamics::World& world,std::span<const StaticMeshSource> meshes,
                    const GuardSettings& settings,advance::Progress& progress,
                    double elapsed_seconds) noexcept;
private:
    Settings settings_;
    double backlog_{};
    std::uint64_t sequence_{};
    bool busy_{};
};
}
