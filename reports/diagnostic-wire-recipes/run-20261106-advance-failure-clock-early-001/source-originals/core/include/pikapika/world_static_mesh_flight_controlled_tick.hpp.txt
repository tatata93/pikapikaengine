#pragma once
#include "pikapika/world_static_mesh_flight_advance.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace pikapika::world_static_mesh_flight_controlled_tick {
// Isolated Native prototype. No old seven-source/two-source/SDK changes.
namespace advance=world_static_mesh_flight_advance;
using StaticMeshSource=advance::StaticMeshSource;
using GuardSettings=advance::GuardSettings;
inline constexpr std::size_t hard_max_bodies=8,hard_max_planes=16,hard_max_meshes=4,hard_max_faces=64;
enum class LoadMode : unsigned {replace_total_world_loads};
struct BodyLoad {std::uint64_t body_id{};Vec3 force_newtons{},torque_newton_meters{};};
struct TickLoadPacket {
    LoadMode mode;
    std::uint64_t expected_tick;
    std::vector<BodyLoad> loads;
    TickLoadPacket(LoadMode m,std::uint64_t tick,std::vector<BodyLoad> rows):mode(m),expected_tick(tick),loads(std::move(rows)) {}
};
struct Binding {
    unsigned profile{};
    bool configured{};
    std::array<char,65> build_id{},upstream_build_id{};
};
Binding current_binding() noexcept; // Independent configured identity; not object inspection.
enum class Status : unsigned {committed,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {
    none,environment,binding_unsupported,body_count,plane_count,mesh_count,face_count,packet_count,
    original_body,packet_mode,expected_tick,packet_id,packet_duplicate,packet_load,static_load,
    private_copy,child_failed,child_inconsistent,origin_mismatch,candidate_mismatch,destination_mismatch,
    allocation_failure,unexpected_exception
};
enum class Stage : unsigned {environment,binding,counts,capture,original_validation,packet,staging,child,post_child,commit_preparation};
enum class CaptureState : unsigned {none,partial,complete};
struct Failure {Stage stage=Stage::environment;std::optional<std::size_t> body_ordinal,packet_ordinal,mesh_ordinal;};
struct WorldState {Vec3 gravity{};std::vector<dynamics::RigidBody> bodies;std::vector<dynamics::Plane> planes;};
struct OriginalSnapshot {
    double horizon{};
    GuardSettings settings;
    advance::Progress progress;
    WorldState world;
    std::vector<StaticMeshSource> meshes;
    TickLoadPacket packet;
    OriginalSnapshot(double h,const GuardSettings& s,advance::Progress p,LoadMode mode,std::uint64_t tick)
        :horizon(h),settings(s),progress(p),packet(mode,tick,{}) {}
};
struct Mapping {std::size_t packet_ordinal{},body_ordinal{};std::uint64_t body_id{};};
struct Work {
    std::size_t original_bodies_copied{},original_planes_copied{},original_meshes_copied{},original_faces_copied{},packet_rows_copied{};
    std::size_t original_validations_attempted{},original_validations_returned{},packet_rows_checked{},packet_validations_attempted{},packet_validations_returned{};
    std::size_t private_copies_attempted{},private_copies_returned{},staged_bodies_copied{},staged_planes_copied{},private_after_bodies_copied{},private_after_planes_copied{};
    std::size_t child_attempts{},child_returns{},candidate_bodies_checked{},candidate_validations_attempted{},candidate_validations_returned{};
    std::size_t origin_bodies_checked{},origin_planes_checked{},origin_meshes_checked{},origin_faces_checked{},origin_packet_rows_checked{};
    std::size_t destination_lookups{},destinations_resolved{},body_assignments{},progress_assignments{};
    // Known wrapper operation counts only; numerical child known/upper/exact is
    // retained in child. A throwing copy/validation attempt need not return.
};
struct Storage {
    std::size_t candidate_slots{},destination_slots{},candidate_sizeof_bytes{},destination_sizeof_bytes{};
    // These two fixed local buffers only. Not whole Report heap/stack/RSS bounds.
};
struct ControlledReport {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    bool committed{};
    double requested_dt{},advanced_dt{};
    advance::Progress original_progress;
    LoadMode requested_mode=LoadMode::replace_total_world_loads;
    std::uint64_t requested_tick{};
    Binding binding;
    std::optional<Failure> failure;
    CaptureState capture=CaptureState::none,staged_capture=CaptureState::none,private_after_capture=CaptureState::none;
    bool original_bodies_validated{};
    std::optional<OriginalSnapshot> original;
    std::array<std::optional<Mapping>,hard_max_bodies> mappings;
    std::optional<WorldState> staged_before,private_after;
    std::optional<advance::Progress> private_progress_after;
    std::optional<advance::AdvanceReport> child; // ACTUAL private advance only, at most once.
    Work work;
    Storage storage;
    std::string message;
};
// Env first, profile then hard counts then complete owned capture. Original body
// validation precedes packet validation: replacing bad original loads cannot
// repair invalid input. Mode/tick/complete-ID rows/loads validated in that order.
// All rows replace world-frame TOTAL loads; static rows require exact +/-zero.
// Private World copy, one actual advance, complete post-validation, then no-throw
// original-body stores. No temporary external loads, callbacks, requery or fallback.
// A privately committed child can be retained in an OUTER failed report; it has
// not advanced the external World. All failure paths preserve external loads,
// bodies/order/addresses, Progress, meshes and settings. Success consumes loads.
// Caller excludes concurrent/reentrant/signal access and keeps one logical World.
// expected_tick is not a cross-World lifetime/authentication/transport token.
ControlledReport advance_with_loads(dynamics::World& world,std::span<const StaticMeshSource> meshes,
    double horizon,const GuardSettings& settings,advance::Progress& progress,const TickLoadPacket& packet) noexcept;
}
