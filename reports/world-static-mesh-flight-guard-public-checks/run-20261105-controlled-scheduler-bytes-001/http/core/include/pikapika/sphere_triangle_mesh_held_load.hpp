#pragma once
#include "pikapika/dynamics.hpp"
#include "pikapika/sphere_triangle_mesh.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle_mesh_held_load {
using Bounds3=sphere_triangle::Bounds3;
struct HeldSphere {
    std::uint64_t id{1};
    Vec3 position{},velocity{};
    double mass{1};
    Vec3 force{},gravity{0,-9.80665,0};
    double radius{1};
};
struct Settings {
    sphere_triangle_mesh::Settings mesh{};
    double time_tolerance{1e-7}; // seconds, finite (0,0.1]; NOT a spatial error.
    std::size_t max_evaluations{256},max_leaves{128};
    unsigned max_depth{24},enclosure_sqrt_refinements{128};
    std::size_t max_total_sqrt_refinements{1000000};
};
enum class Status : unsigned {entry_window,separated,initial_penetration,not_certified,invalid_input,unsupported_environment,numerical_failure};
enum class Reason : unsigned {none,settings,surface_count,surface_id,duplicate_id,input_domain,surface_budget,mesh_query_failed,initial_boundary,evaluation_budget,leaf_budget,depth_budget,sqrt_budget,time_resolution,nonfinite_intermediate,allocation_failure,environment,coverage_inconsistent,body_not_found,body_invalid,unsupported_body,derived_domain};
enum class AuditKind : unsigned {initial_point,cell};
enum class Outcome : unsigned {pending,initial_separated,initial_penetration,initial_uncertain,separated,split,unresolved};
enum class LeafState : unsigned {unqueried,certified,unresolved,current};
struct Cell {
    std::array<double,2> time_bounds{}; // CLOSED global seconds, not normalized s.
    unsigned depth{}; // Initial point alone has [0,0]. Time splits need not be uniform dyadics.
};
struct Snapshot {
    HeldSphere input;
    double horizon{}; // exact input binary64 seconds
    std::vector<sphere_triangle::StaticTriangle> triangles;
    Settings settings;
};
struct WorldBodySnapshot {
    dynamics::RigidBody body; // ALL selected-body fields, including ignored rotational fields.
    Vec3 gravity{};
};
struct Work {
    std::size_t mesh_queries{},primitive_queries{},candidates_examined{};
    std::size_t primitive_sqrt_refinements{},enclosure_sqrt_refinements{};
    std::size_t sqrt_refinements{},sqrt_refinements_upper{};
    std::size_t mesh_sqrt_limited_rows{},enclosure_sqrt_calls{},enclosure_sqrt_limited_calls{};
    bool exact=true; // Known returned work; false retains an unreturned block's reservation.
};
struct CellAudit {
    AuditKind kind=AuditKind::cell;
    Cell cell;
    double time{}; // Initial0 or selected representable interior global time.
    Outcome outcome=Outcome::pending;
    std::optional<Bounds3> path_bounds,point_bounds;
    std::optional<Vec3> anchor; // arbitrary exact binary64, NOT exact p(time)
    bool mesh_queried{};
    std::optional<sphere_triangle_mesh::Status> mesh_status;
    std::optional<sphere_triangle_mesh::Reason> mesh_reason;
    std::optional<interval::Interval> distance;
    std::optional<interval::Interval> displacement_squared_bound,error_squared_bound;
    std::optional<interval::Interval> displacement_root,error_root;
    std::optional<interval::Interval> clearance_certificate,penetration_certificate;
    Work work; // This audit's DELTA; Result.work is the aggregate.
};
struct InitialProof {
    interval::Interval lower_gap_certificate,upper_gap_certificate;
    std::size_t audit_index{};
};
struct CertifiedLeaf {
    Cell cell;
    interval::Interval lower_gap_certificate;
    std::size_t audit_index{};
};
struct Witness {
    Cell cell;
    double time{}; // seconds; strict negative exact p(time), including E correction
    Bounds3 exact_path_bounds;
    Vec3 anchor;
    double error_upper{};
    interval::Interval upper_gap_certificate;
    std::size_t audit_index{};
};
struct EntryWindow {
    std::array<double,2> time_bounds;
    interval::Interval time_width; // outward exact U-L [s]
    Bounds3 path_bounds; // Original held-load path on [L,U].
    // Encloses the SUM OF STORED BOX WIDTHS [m]. Its upper bounds path diameter;
    // its lower is NOT a lower bound on physical displacement/penetration/error.
    interval::Interval l1_diameter_bound;
    std::size_t witness_audit_index{};
};
struct PartitionLeaf {
    Cell cell;
    LeafState state=LeafState::unqueried;
    std::optional<std::size_t> audit_index;
    Reason blocked_reason=Reason::none;
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<std::size_t> failed_index;
    std::optional<Snapshot> snapshot;
    // Adapter only: captured after environment check, including invalid/static
    // selected bodies. Raw query and unknown/unsafe body IDs leave this absent.
    std::optional<WorldBodySnapshot> world_body;
    std::optional<Bounds3> acceleration,whole_path_bounds,whole_velocity_bounds;
    std::optional<InitialProof> initial;
    bool initial_separation_proven{};
    std::vector<CertifiedLeaf> certified_leaves; // ALL islands, increasing time
    std::optional<std::array<double,2>> safe_prefix; // CLOSED [0,L] seconds; [0,0] is meaningful
    std::optional<Witness> best_witness;
    std::optional<EntryWindow> window;
    std::vector<std::uint64_t> candidate_surface_ids; // ALL source IDs, sorted, iff window
    std::vector<PartitionLeaf> partition; // Whole [0,H], <=128 including tail
    std::vector<Cell> frontier; // ALL unqueried leaves, including time>=best witness
    std::optional<Cell> current;
    std::vector<CellAudit> audits; // Initial1 + tree255 <=256
    std::optional<sphere_triangle_mesh::Result> last_mesh;
    std::optional<std::size_t> last_mesh_audit_index;
    Work work;
    std::size_t partition_leaves{};
    unsigned maximum_depth{};
    std::string message;
};

// Original binary64 quantities denote exact real SI inputs. Internally enclose
// A=I(g)+I(F)/I(m), then p(t)=I(P0)+I(V0)t+I(.5)A*t^2, never rounded A or a chord.
// H:(0,.1], mass:[1e-12,1e18], radius:(0,1e9], |P0/tri|<=1e12, |V0/g|<=1e9,
// |F|<=1e24. Derived acceleration/path/velocity enclosures must fit respectively
// +/-1e12, +/-1e12, +/-1e9; failure is not_certified/derived_domain.
// Source1..64/unique IDs1..2^53-1; settings eval1..256/leaves1..128/depth0..32,
// enclosure1..256/total1..16777216; primitive retains the existing six domains.
// Environment FIRST; no caller mutation. All ordinary failures return owned
// diagnostics. Snapshot follows full structural preflight, before derived checks.
// Reserve N*512 BEFORE mesh,512 BEFORE EACH R/E sqrt. Work is actual returned
// counts or conservative unknown-block upper. No continuation after unknown work.
// BFS initial0 then min-depth/left unqueried before best witness; keep all tail.
// Recoverable exact row_failure is UNKNOWN, can subdivide but supplies no proof.
// Entry requires strict initial positive/closed prefix/E-negative/time width and
// exact work. Not a unique TOI, normal, point impulse, propagation tube or response.
Result query(const HeldSphere& input,std::span<const sphere_triangle::StaticTriangle> triangles,
             double horizon_seconds,const Settings& settings={});
// Selected dynamic CoM-centred sphere proxy only. const find_body + copy + validate;
// static -> not_certified/unsupported_body. World body/plane/storage/pointers/loads
// remain unchanged. Does NOT audit other World pairs/planes or advance rotation.
Result query_body(const dynamics::World& world,std::uint64_t body_id,
                  std::span<const sphere_triangle::StaticTriangle> triangles,
                  double horizon_seconds,const Settings& settings={});
}
