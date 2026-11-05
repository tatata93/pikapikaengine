#pragma once
#include "pikapika/world_static_mesh_flight_controlled_tick.hpp"
#include "pikapika/world_static_mesh_flight_scheduler.hpp"
#include <array>
#include <optional>
#include <span>
#include <vector>

namespace pikapika::world_static_mesh_flight_controlled_scheduler {
// New isolated Native prototype. Existing scheduler/controlled/advance kernels
// and identities stay unchanged. No SDK, owner session, callback or game hook.
namespace controlled=world_static_mesh_flight_controlled_tick;
namespace clock=world_static_mesh_flight_scheduler;
using Settings=clock::Settings;
using Snapshot=clock::Snapshot;
using QueueStep=clock::QueueStep;
using UpperBudget=clock::UpperBudget;
using Progress=controlled::advance::Progress;
using StaticMeshSource=controlled::StaticMeshSource;
using GuardSettings=controlled::GuardSettings;
using TickLoadPacket=controlled::TickLoadPacket;
inline constexpr std::size_t hard_max_attempts=clock::hard_max_attempts;
inline constexpr std::size_t hard_max_packets=8;
struct Binding {
    unsigned profile{};
    bool configured{};
    std::array<char,65> build_id{},controlled_build_id{},scheduler_build_id{},upstream_build_id{};
};
Binding current_binding() noexcept;

// Only the active prefixes are observations. Unused array entries are storage,
// not additional bodies/planes. Every actual field/order/negative zero is copied.
struct WorldState {
    Vec3 gravity{};
    std::size_t body_count{},plane_count{};
    std::array<dynamics::RigidBody,controlled::hard_max_bodies> bodies;
    std::array<dynamics::Plane,controlled::hard_max_planes> planes;
};
struct Boundary {
    WorldState world;
    Progress progress;
    std::array<bool,controlled::hard_max_bodies> original_body_address_same{};
};
struct Original {
    GuardSettings settings;
    std::vector<StaticMeshSource> meshes;
    std::vector<TickLoadPacket> packets;
    explicit Original(const GuardSettings& source_settings):settings(source_settings) {}
};
enum class CaptureState : unsigned {none,partial,complete};
enum class Status : unsigned {waiting,step_budget,awaiting_input,tick_rejected,invalid_input,unsupported_environment,numerical_failure,reentrant};
enum class Reason : unsigned {none,busy,environment,binding_unsupported,body_count,plane_count,mesh_count,face_count,
    packet_count,packet_load_count,elapsed,backlog_limit,sequence_limit,queue_arithmetic,cost_overflow,
    allocation_failure,unexpected_exception,packet_unavailable,controlled_rejected};
struct Attempt {
    std::size_t queue_index{},packet_ordinal{};
    bool credit_consumed{},packet_consumed{};
    controlled::ControlledReport report; // The ACTUAL call, never a requery.
};
struct CaptureWork {
    std::size_t boundary_captures{},body_observations{},plane_observations{},mesh_copies{},face_copies{},packet_copies{},load_copies{};
};
struct Storage {
    std::size_t boundary_slots{},boundary_sizeof_bytes{},address_slots{},address_sizeof_bytes{};
    // Named fixed buffers only, not complete heap/stack/RSS/deadline bounds.
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
    Progress progress_before{},progress_after{};
    CaptureState capture=CaptureState::none;
    std::optional<Original> original;
    std::array<std::optional<Boundary>,hard_max_attempts+1> boundaries;
    std::array<std::optional<QueueStep>,hard_max_attempts> queue_plan;
    std::array<std::optional<Attempt>,hard_max_attempts> tick_reports;
    std::size_t boundary_count{},planned_attempts{},attempts{},committed_ticks{},packets_consumed{};
    UpperBudget upper_budget;
    CaptureWork work;
    Storage storage;
    double dropped_seconds{}; // Always +0, retain-only.
    bool has_whole_tick_backlog{};
};
class Scheduler {
public:
    explicit Scheduler(Settings settings={});
    Scheduler(const Scheduler&)=delete;
    Scheduler& operator=(const Scheduler&)=delete;
    Scheduler(Scheduler&&)=delete;
    Scheduler& operator=(Scheduler&&)=delete;
    Snapshot snapshot() const noexcept;
    // Captures source and <=8 packets before admitting elapsed ONCE. All
    // throwing outer preparation precedes the first external tick commit.
    // Only successful controlled ticks consume credit AND their packet.
    // On failure/input shortage, keep the successful prefix and unspent credit;
    // retry with elapsed0 and the unconsumed packet suffix (or a corrected row).
    // Future unused packets are captured but semantically checked only when due.
    // No repeated last load, generated zero packet, callback, requery or fallback.
    // Caller excludes concurrent/reentrant/signal access and retains one logical
    // World/Progress per scheduler; no cross-World identity/lifetime guarantee.
    PumpReport pump(dynamics::World& world,std::span<const StaticMeshSource> meshes,
        const GuardSettings& settings,Progress& progress,double elapsed_seconds,
        std::span<const TickLoadPacket> packets) noexcept;
private:
    Settings settings_;
    double backlog_{};
    std::uint64_t sequence_{};
    bool busy_{};
};
}
