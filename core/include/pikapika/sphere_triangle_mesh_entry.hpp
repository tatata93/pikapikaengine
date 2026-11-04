#pragma once
#include "pikapika/sphere_triangle_mesh.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle_mesh_entry {
using Bounds3=sphere_triangle::Bounds3;
inline constexpr double coordinate_limit=1e12;
struct Settings {
    sphere_triangle_mesh::Settings mesh{};
    double parameter_tolerance=1e-6; // Dimensionless; finite 0<tol<=1.
    std::size_t max_evaluations=256; // 1..256, INCLUDES initial point attempt.
    std::size_t max_leaves=128; // 1..128, entire [0,1] partition, including tail.
    unsigned max_depth=24; // 0..32, root depth0 is evaluated.
    unsigned enclosure_sqrt_refinements=128; // 1..256; each block reserves512.
    std::size_t max_total_sqrt_refinements=1000000; // 1..16777216.
};
enum class Status : unsigned {entry_window,separated,initial_penetration,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {none,settings,surface_count,surface_id,duplicate_id,input_domain,surface_budget,mesh_query_failed,initial_boundary,evaluation_budget,leaf_budget,depth_budget,sqrt_budget,parameter_resolution,nonfinite_intermediate,allocation_failure,environment,coverage_inconsistent};
enum class AuditKind : unsigned {initial_point,cell};
enum class Outcome : unsigned {pending,initial_separated,initial_penetration,initial_uncertain,separated,split,unresolved};
enum class LeafState : unsigned {unqueried,certified,unresolved,current};
struct Cell {
    std::array<double,2> parameter{0,1}; // CLOSED global s bounds.
    unsigned depth{}; // Initial-point audit alone uses [0,0],depth0.
};
struct Snapshot {
    Vec3 start{},end{};double radius{};
    std::vector<sphere_triangle::StaticTriangle> triangles;
    Settings settings; // Complete owned profile; original source order/bits.
};
struct Work {
    std::size_t mesh_queries{},primitive_queries{},candidates_examined{};
    std::size_t primitive_sqrt_refinements{},enclosure_sqrt_refinements{};
    std::size_t sqrt_refinements{},sqrt_refinements_upper{};
    std::size_t mesh_sqrt_limited_rows{},enclosure_sqrt_calls{},enclosure_sqrt_limited_calls{};
    // Known returned work, possibly with an uncounted block. False exact uses
    // conservative sqrt upper, never zero/no work or a recycled reservation.
    bool exact=true;
};
struct CellAudit {
    AuditKind kind=AuditKind::cell;
    Cell cell;double parameter{}; // Initial0 or original cell midpoint.
    Outcome outcome=Outcome::pending;
    std::optional<Bounds3> path_bounds,point_bounds;
    std::optional<Vec3> anchor; // Arbitrary exact binary64; NOT exact p(parameter).
    bool mesh_queried{};
    std::optional<sphere_triangle_mesh::Status> mesh_status;
    std::optional<sphere_triangle_mesh::Reason> mesh_reason;
    std::optional<interval::Interval> distance;
    std::optional<interval::Interval> displacement_squared_bound,error_squared_bound;
    std::optional<interval::Interval> displacement_root,error_root;
    // Enclosed bound expressions, NOT a lower/upper range of the true gap.
    std::optional<interval::Interval> clearance_certificate,penetration_certificate;
    Work work; // This audit's DELTA only. Result.work is the aggregate.
};
struct InitialProof {
    interval::Interval lower_gap_certificate,upper_gap_certificate;
    std::size_t audit_index{}; // Exactly initial_point audit0, when returned.
};
struct CertifiedLeaf {
    Cell cell;interval::Interval lower_gap_certificate;std::size_t audit_index{};
};
struct Witness {
    Cell cell;double parameter{};
    Bounds3 exact_path_bounds;Vec3 anchor;double error_upper{};
    interval::Interval upper_gap_certificate;std::size_t audit_index{};
};
struct EntryWindow {
    std::array<double,2> parameter; // [L,U], closed safe prefix and strict witness.
    interval::Interval width; // Outward enclosure of exact U-L.
    std::size_t witness_audit_index{};
};
struct PartitionLeaf {
    Cell cell;LeafState state=LeafState::unqueried;
    std::optional<std::size_t> audit_index;
    Reason blocked_reason=Reason::none; // Depth/leaf/etc.; no invented query.
};
struct Result {
    Status status=Status::invalid_input;Reason reason=Reason::none;
    std::optional<std::size_t> failed_index;
    std::optional<Snapshot> snapshot;
    std::optional<InitialProof> initial;
    bool initial_separation_proven{};
    // Includes ALL proven islands, sorted in global parameter order, not just
    // the prefix. Initial proof alone gives safe_prefix=[0,0], not a whole cell.
    std::vector<CertifiedLeaf> certified_leaves;
    std::optional<std::array<double,2>> safe_prefix;
    std::optional<Witness> best_witness; // Smallest proven negative s so far.
    std::optional<EntryWindow> window; // Present iff status==entry_window.
    // All original IDs (ascending) only when a window is accepted. This is an
    // unfiltered conservative set, NOT witness-nearest IDs or identified faces.
    std::vector<std::uint64_t> candidate_surface_ids;
    std::vector<PartitionLeaf> partition; // Sorted, gapless entire [0,1], <=128.
    std::vector<Cell> frontier; // ALL unqueried leaves, sorted by parameter.
    // Frontier leaves at/after best_witness.parameter remain owned tail; they
    // are not queried merely to locate the earlier entry. Never silently dropped.
    std::optional<Cell> current; // Attempted/stopped cell; separate from frontier.
    std::vector<CellAudit> audits; // Initial + cell queries/blocked attempts<=256.
    std::optional<sphere_triangle_mesh::Result> last_mesh;
    std::optional<std::size_t> last_mesh_audit_index;
    Work work;std::size_t partition_leaves{};unsigned maximum_depth{};
    std::string message;
};
// Pure, Native-only proof on original exact-binary64 p(s)=start+s(end-start).
// Whole structural/profile validation and environment check precede queries;
// source/profile snapshots own all storage. No old guard/World/SDK mutation.
// A query uses the unchanged mesh kernel. Returned exact-work row_failure is
// an UNKNOWN cell, may be subdivided, and never supplies a geometric proof.
// Initial-point failure cannot prove g(0)>0 and stops. Invalid/environment/
// numerical/null-query/unknown-work failures stop globally with diagnostics.
// Evaluation order: initial point, then lowest-depth UNQUERIED partition leaf,
// ties by lower s, restricted to leaf.lo<bestWitness when one exists. Blocked
// leaves do not prevent later eligible leaves being queried for a witness.
// Split global dyadic cells only. maxDepth/leaf exhaustion retains unresolved
// leaves and continues other eligible work; all tail leaves remain in partition.
// entry_window requires initial g(0)>0, strict certified CLOSED [0,L], an E-
// corrected exact-path g(U)<0 witness, exact work and outward width.upper<=tol.
// It contains the onset inf{s:g(s)<0}; not a unique root, no-grazing theorem,
// exact contact time, per-face event, normal/manifold, CCD/response or dynamics.
// separated requires strict closed cover[0,1]. Initial negative/boundary are
// distinct. d=0/normal-quality failure can still make an initial query unresolved.
// N*512 is reserved BEFORE mesh;512 BEFORE EACH R/E root. At most initial1+
// binarytree255 audits/mesh attempts. Unknown work stops with conservative upper.
Result query(Vec3 start,Vec3 end,double radius,
             std::span<const sphere_triangle::StaticTriangle> triangles,
             const Settings& settings={});
}
