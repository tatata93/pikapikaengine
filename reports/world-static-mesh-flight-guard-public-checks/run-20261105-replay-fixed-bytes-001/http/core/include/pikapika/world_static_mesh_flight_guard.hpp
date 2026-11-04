#pragma once
#include "pikapika/world_static_mesh_flight.hpp"
#include "pikapika/sphere_triangle_mesh_free_flight_guard.hpp"
#include "pikapika/accelerated_pair_coverage.hpp"
#include "pikapika/accelerated_plane_box_coverage.hpp"
#include "pikapika/accelerated_sphere_box_coverage.hpp"
#include <array>
#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <variant>
#include <vector>

namespace pikapika::world_static_mesh_flight_guard {
// Future Native contract. Actual artifact binding/build acceptance is separate.
// Read-only sphere-proxy motion, not a World step, response, or static overlap test.
using StaticMeshSource=world_static_mesh_flight::StaticMeshSource;
inline constexpr std::size_t hard_max_body_records=8,hard_max_pair_records=256;
inline constexpr std::size_t hard_max_retained_slots=1024;
inline constexpr std::size_t hard_max_last_mesh_rows=512,hard_max_primitive_candidates=3584;
inline constexpr std::size_t hard_max_retained_faces=1600,hard_max_mesh_queries=1024;
inline constexpr std::size_t hard_max_primitive_queries=65536,hard_max_candidates_examined=458752;
inline constexpr std::size_t hard_max_sqrt_refinements=16777216,hard_max_value_attempts=1048576;
inline constexpr std::size_t hard_max_propagations=32,hard_max_logical_payload=16*1024*1024;
struct Limits {
    std::size_t body_records=8,pair_records=256;
    std::size_t held_audits=1024,held_certified_leaves=1024,held_partition=1024,held_frontier=1024;
    std::size_t primitive_audits=1024,primitive_partition=1024,primitive_frontier=1024;
    std::size_t last_mesh_rows=512,primitive_candidates=3584,retained_faces=1600;
    std::size_t mesh_queries=1024,primitive_queries=65536,candidates_examined=458752;
    std::size_t sqrt_refinements=16777216,plane_metric_values=1048576,box_values=1048576;
    std::size_t propagations=32,logical_payload_bytes=16*1024*1024;
};
struct GuardSettings {
    world_static_mesh_flight::Settings preparation{};
    sphere_triangle_mesh_free_flight_guard::Settings mesh{};
    accelerated_pair_coverage::Settings plane_metric{};
    accelerated_plane_box_coverage::Settings plane_box{};
    accelerated_sphere_box_coverage::Settings sphere_box{};
    double contact_margin; // MUST be explicit, finite [0,.1], preserves -0.
    Limits limits{};
    explicit GuardSettings(double margin) noexcept:contact_margin(margin) {}
};
enum class Status : unsigned {certified_separated,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {
    none,preparation_failed,settings,storage_budget,work_budget,seed_failed,
    dependency_failed,mesh_not_separated,metric_not_separated,box_not_separated,
    binding_unsupported,child_environment,unknown_work,child_exception,
    metadata_inconsistent,allocation_failure,environment
};
enum class SeedState : unsigned {static_copy,pending,ready,failed,unexamined};
enum class PairState : unsigned {unexamined,certified,not_certified,dependency_failed};
enum class CallState : unsigned {unexamined,returned,nonreturned};
enum class BindingMode : unsigned {source_enforced};
enum class BindingState : unsigned {unconfigured,unsupported_target,identity_mismatch,environment_unsupported,ready};
struct BindingInfo {
    BindingMode mode=BindingMode::source_enforced;
    BindingState state=BindingState::unconfigured;
    bool checked{};
    unsigned profile{};
    std::array<char,65> build_id{}; // Owned NUL-terminated lowercase 64-hex config identity.
    // A configuration identity is NOT a self-measured object/executable hash.
};
struct Failure {
    std::optional<world_static_mesh_flight::FailureLocation> preparation;
    std::optional<std::size_t> body_ordinal,pair_ordinal;
};
struct Counter {
    std::size_t known{},upper{};
    bool exact=true;
};
struct HeldLedger {
    Counter mesh_queries,primitive_queries,candidates_examined;
    Counter primitive_sqrt_refinements,enclosure_sqrt_refinements,sqrt_refinements;
    Counter mesh_sqrt_limited_rows,enclosure_sqrt_calls,enclosure_sqrt_limited_calls;
};
struct Work {
    // Exact OUTER wrapper attempts/returns. Bridge is an upper, not instrumentation.
    std::size_t child_calls_attempted{},child_calls_returned{};
    std::size_t mesh_calls_attempted{},mesh_calls_returned{};
    std::size_t plane_metric_calls_attempted{},plane_metric_calls_returned{};
    std::size_t plane_box_calls_attempted{},plane_box_calls_returned{};
    std::size_t sphere_box_calls_attempted{},sphere_box_calls_returned{};
    HeldLedger held;
    Counter propagation_attempts,plane_metric_values,box_values;
    std::size_t bridge_calls_upper{},plane_norm_calls_upper{},plane_norm_loop_iterations_upper{};
    std::size_t sphere_root_results_returned{},sphere_root_limited_returns{};
    Counter sphere_sqrt_refinements,sqrt_refinements;
    bool exact=true; // All charged work known, not a mathematical success flag.
};
struct Retained {
    // Requested capacity charges. NEVER refunded merely because actual size is small.
    std::size_t body_records{},pair_records{};
    std::size_t held_audits{},held_certified_leaves{},held_partition{},held_frontier{};
    std::size_t primitive_audits{},primitive_partition{},primitive_frontier{};
    std::size_t last_mesh_rows{},primitive_candidates{},retained_faces{},logical_payload_bytes{};
};
struct WorkGrant {
    std::size_t mesh_queries{},primitive_queries{},candidates_examined{},sqrt_refinements{};
    std::size_t propagations{},plane_metric_values{},box_values{};
    std::size_t plane_norm_loop_iterations_upper{},bridge_calls_upper{};
};
struct Reservation {
    Retained retained;
    WorkGrant granted; // Cumulative original grants; may exceed limits after exact refunds.
    WorkGrant charged; // Settled upper work, including any unknown/nonreturned block.
};
struct Grant {Retained retained;WorkGrant work;};
struct MessageOmission {
    // fields counts EVERY visited message field, including empty; nonempty separately.
    std::size_t fields{},nonempty_fields{},bytes{};
    bool omitted{};
};
template<class SettingsType,class ResultType> struct Call {
    CallState state=CallState::unexamined;
    std::optional<std::size_t> attempt_ordinal; // Across ALL actual child calls, zero based.
    SettingsType requested_settings{},used_settings{};
    bool granted{};
    Grant grant; // Computed request even if granted=false; never charged on refusal.
    std::optional<ResultType> result; // Absent iff unexamined or nonreturned.
    MessageOmission messages;
};
using MeshCall=Call<sphere_triangle_mesh_free_flight_guard::Settings,sphere_triangle_mesh_free_flight_guard::Result>;
using PlaneMetricCall=Call<accelerated_pair_coverage::Settings,accelerated_pair_coverage::Result>;
using PlaneBoxCall=Call<accelerated_plane_box_coverage::Settings,accelerated_plane_box_coverage::Result>;
using SphereCall=Call<accelerated_sphere_box_coverage::Settings,accelerated_sphere_box_coverage::Result>;
struct PlaneCalls {PlaneMetricCall metric;PlaneBoxCall box;};
using Child=std::variant<MeshCall,PlaneCalls,SphereCall>;
struct PairRecord {
    std::size_t pair_ordinal{}; // Full owned preparation.inventory.pairs index.
    PairState state=PairState::unexamined;
    Reason reason=Reason::none;
    std::optional<std::size_t> execution_ordinal; // First actual child call, not storage order.
    Child child;
};
struct BodyRecord {
    std::size_t body_ordinal{};
    bool is_static{};
    SeedState state=SeedState::unexamined;
    std::optional<std::size_t> seed_pair_ordinal;
};
struct GuardResult {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    BindingInfo binding;
    std::optional<GuardSettings> original_settings; // Absent before env/binding acceptance.
    std::optional<Failure> failure;
    std::optional<world_static_mesh_flight::Result> preparation;
    MessageOmission preparation_messages;
    std::vector<BodyRecord> bodies; // Original body order; no duplicate giant seed result.
    std::vector<PairRecord> pairs; // ALL required stable keys, even after global stop.
    Work work;
    Reservation reservation;
    std::optional<Retained> initial_request; // Before base quota/reserve may fail.
    std::optional<std::vector<dynamics::RigidBody>> candidate_bodies; // ALL or absent.
    std::string message; // Fixed short non-normative diagnostic; noexcept fallback empty.
};
// Environment FIRST. Then build binding, fixed original profile, owned prepare,
// complete profile validation, initial record/storage reservations, child calls.
// Only the owned prepare snapshot is read after capture. Caller must exclude
// concurrent World/source mutation; this is NOT an atomic multithread snapshot.
// Seed min mesh ID in dynamic-ID order; then remaining mesh pairs; then primitive
// pairs in saved stable order. Ordinary failure continues independent pairs;
// unsupported environment, unknown work, nonreturn/allocation/inconsistency stops.
// Child numerical data is complete. Only non-normative message text is stripped
// recursively, with counts. Static-static pairs are counted/excluded, not certified.
// Mesh profiles are unchanged; primitive E alone may be visibly granted smaller.
// Whole candidates only after ALL pairs certified, all dynamic seeds ready, exact
// work and complete accounting. Loads remain held, no clock/World advance occurs.
GuardResult query(const dynamics::World& world,std::span<const StaticMeshSource> meshes,
                  double horizon_seconds,const GuardSettings& settings) noexcept;
// No caller unlock. Default builds are unconfigured. Future build protocol:
// PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1 and PIKAPIKA_WORLD_FLIGHT_BUILD_ID="64hex"
// on the actual audited core object AND guard TU. Profile1 also requires matching
// private core bridges (root integrates these later). Initial accepted candidates
// are genuine MSVC x64/GNU x86-64 SSE2, excluding ARM64EC/Clang/WASM. This protocol
// labels an externally audited configuration; runtime does NOT inspect object code.
// An unconfigured/fallback/mismatched/environment-rejected profile yields no child
// query and no candidate. Actual artifact/flag audit remains a separate acceptance.
BindingInfo current_binding() noexcept;
}
