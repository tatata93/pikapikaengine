#pragma once
#include "pikapika/sphere_triangle_mesh.hpp"
#include <array>
#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle_mesh_trajectory {
using Bounds3=sphere_triangle::Bounds3;
inline constexpr double coordinate_limit=1e12;
struct Settings {
    sphere_triangle_mesh::Settings mesh{};
    std::size_t max_evaluations=256; // 1..1024, actual mesh query attempts.
    std::size_t max_leaves=128; // 1..128, certified+current+frontier partition.
    unsigned max_depth=16; // 0..32, root [0,1] depth0 is evaluated.
    unsigned enclosure_sqrt_refinements=128; // 1..256; R/E each use point(upper).
    std::size_t max_total_sqrt_refinements=1000000; // 1..16777216.
};
enum class Status : unsigned {separated,penetration_witness,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {none,settings,surface_count,surface_id,duplicate_id,input_domain,surface_budget,mesh_query_failed,evaluation_budget,leaf_budget,depth_budget,sqrt_budget,parameter_resolution,nonfinite_intermediate,allocation_failure,environment,coverage_inconsistent};
enum class Outcome : unsigned {pending,separated,split,penetration_witness,not_certified};
struct Cell {
    std::array<double,2> parameter{0,1}; // CLOSED dyadic s bounds, dimensionless.
    unsigned depth{};
};
struct Snapshot {
    Vec3 start{},end{};double radius{};
    std::vector<sphere_triangle::StaticTriangle> triangles; // Original order/bits.
    Settings settings; // Complete profile owned with source; never borrowed.
};
struct Work {
    std::size_t mesh_queries{},primitive_queries{},candidates_examined{};
    std::size_t primitive_sqrt_refinements{},enclosure_sqrt_refinements{};
    std::size_t sqrt_refinements{},sqrt_refinements_upper{};
    std::size_t mesh_sqrt_limited_rows{},enclosure_sqrt_calls{},enclosure_sqrt_limited_calls{};
    // False means some executed block might contain unreturned work. Counts
    // above are known returned work, possibly with an uncounted block;
    // sqrt_refinements_upper is conservative, not an exact measurement.
    // No unknown reservation is recycled for later calls. Success requires true.
    bool exact=true;
};
struct CellAudit {
    Cell cell;
    double midpoint{};
    Outcome outcome=Outcome::pending;
    std::optional<Bounds3> path_bounds,point_bounds;
    std::optional<Vec3> anchor; // Arbitrary exact binary64 point, NOT exact p(m).
    bool mesh_queried{}; // Attempted call, even if no Result returned.
    std::optional<sphere_triangle_mesh::Status> mesh_status;
    std::optional<sphere_triangle_mesh::Reason> mesh_reason;
    std::optional<interval::Interval> distance;
    std::optional<interval::Interval> displacement_squared_bound,error_squared_bound;
    std::optional<interval::Interval> displacement_root,error_root;
    // Enclosures of lower-/upper-bound EXPRESSIONS, not a range of actual gaps.
    std::optional<interval::Interval> clearance_certificate,penetration_certificate;
    Work work; // This cell's DELTA only, never cumulative. Result.work is total.
};
struct CertifiedLeaf {
    Cell cell;
    interval::Interval lower_gap_certificate;
    std::size_t audit_index{};
};
struct Witness {
    Cell cell;
    double parameter{};
    Bounds3 exact_path_bounds;
    Vec3 anchor;
    double error_upper{};
    interval::Interval upper_gap_certificate;
    std::size_t audit_index{};
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<std::size_t> failed_index; // Source prevalidation index only.
    std::optional<Snapshot> snapshot; // All valid source copied, or null.
    std::vector<CertifiedLeaf> certified_leaves; // Left-to-right actual proofs.
    std::optional<std::array<double,2>> safe_prefix; // Null does NOT prove s=0.
    std::optional<Witness> witness; // Strict negative upper expression only.
    std::optional<Cell> current; // Evaluated/blocked current cell, NOT certified.
    std::vector<Cell> frontier; // Unexamined, left-to-right, distinct from current.
    std::vector<CellAudit> audits; // Compact, owned; <=max_evaluations.
    std::optional<sphere_triangle_mesh::Result> last_mesh; // Last returned call.
    std::optional<std::size_t> last_mesh_audit_index; // Never attach it to a later cell.
    Work work;
    std::size_t partition_leaves{}; // Current full partition, <=max_leaves.
    unsigned maximum_depth{}; // Maximum popped current cell depth (even blocked).
    std::string message;
};
// Pure guard of p(s)=start+s*(end-start), 0<=s<=1, exact binary64 reals.
// Finite abs coordinates/radius<=1e12 m, radius>0;1..64 static two-sided surfaces.
// No tolerance band, time/force/World state, CCD/TOI/manifold/response semantics.
// Environment is checked FIRST; no caller FP control mutation. Input vectors
// and settings are prevalidated in full. Snapshot/diagnostics own their storage.
// Each mesh failure stops certification; even a remote degenerate row is kept.
// separated iff CLOSED certified leaves cover [0,1], strict lower gap>0,
// and work exact. Positive/negative point samples never certify an entire cell.
// Prior prefix survives failure, but no partial trajectory is global success.
// Work reservation: N*512 before one mesh call and512 before each R/E root.
// Physical update hard bound128 leaves=>255calls, sqrt<=8616960 overall;
// configured total may fail earlier. Exceptions may have unreturned work,
// reported with exact=false/conservative upper, never inferred as zero work.
Result audit(Vec3 start,Vec3 end,double radius,
             std::span<const sphere_triangle::StaticTriangle> triangles,
             const Settings& settings={});
}
