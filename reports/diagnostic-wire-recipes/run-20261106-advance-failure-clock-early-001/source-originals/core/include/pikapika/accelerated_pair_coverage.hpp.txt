#pragma once
#include "pikapika/accelerated.hpp"
#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <variant>
#include <vector>

namespace pikapika::accelerated_pair_coverage {
// Native contract; implementation/build acceptance is recorded separately.
// Defined point-coefficient SI paths, not World propagation or a response model.
inline constexpr std::size_t maximum_evaluations=255,maximum_leaves=128;
inline constexpr unsigned maximum_depth=32;
struct Settings {
    // Stops subdivision of an UNPROVEN cell only. Never relaxes strict positivity.
    double time_tolerance{1e-7}; // seconds, finite (0,.1]
    std::size_t max_evaluations=maximum_evaluations,max_leaves=maximum_leaves;
    unsigned max_depth=24; // 0..32
};
struct SpherePair {accelerated::Sphere first,second;};
struct SpherePlane {accelerated::Sphere sphere;accelerated::StaticPlane plane;};
using Input=std::variant<SpherePair,SpherePlane>;
struct Snapshot {
    Input input; // All ORIGINAL binary64 values, including invalid input and -0.
    double horizon{};
    Settings settings;
};
enum class Status : unsigned {certified,not_certified,invalid_input,unsupported_environment};
enum class Reason : unsigned {
    none,settings,horizon,input_domain,zero_normal,evaluation_budget,leaf_budget,
    depth_budget,width_limit,time_resolution,nonpositive_value,value_exception,
    allocation_failure,environment,coverage_inconsistent
};
enum class LeafState : unsigned {unqueried,certified,blocked,current};
enum class Outcome : unsigned {pending,positive,split,blocked};
struct Cell {
    std::array<double,2> time_bounds{}; // CLOSED global seconds, root [+0,H].
    unsigned depth{};
    std::optional<std::size_t> parent_audit; // Root null; children link a split.
};
struct Audit {
    Cell cell;
    bool call_attempted{}; // Set immediately BEFORE the public value function.
    // Absent on a nonreturned/throwing call; no synthetic whole/zero interval.
    std::optional<interval::Interval> value;
    Outcome outcome=Outcome::pending;
    Reason blocked_reason=Reason::none;
    std::optional<double> split_time; // Present iff split; exact child endpoint.
};
struct PartitionLeaf {
    Cell cell;
    LeafState state=LeafState::unqueried;
    std::optional<std::size_t> audit_index;
    Reason blocked_reason=Reason::none;
};
struct Work {
    // EXACT wrapper-level counts, including attempted calls that throw.
    std::size_t value_calls_attempted{},value_calls_returned{};
    // Plane's PRIVATE norm helper is not instrumented. These are only bounds:
    // attempts and 64*attempts for plane; BOTH zero for sphere pairs.
    std::size_t plane_norm_calls_upper{},plane_norm_loop_iterations_upper{};
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    // Environment rejected => absent. Supported environment => original capture
    // precedes validation; invalid captures must NOT be treated as valid paths.
    std::optional<Snapshot> snapshot;
    bool snapshot_validated{};
    // Source ordinal 0=first sphere,1=second sphere/plane, only on source failure.
    std::optional<std::size_t> failed_input;
    // False only before root installation (e.g. invalid/preallocation failure).
    // When true, partition is the WHOLE gapless closed [0,H], including unknowns.
    bool partition_complete{};
    std::vector<Audit> audits; // <=255, breadth-first minimum-depth/left order.
    std::vector<PartitionLeaf> partition; // <=128, increasing-time full leaves.
    std::vector<Cell> frontier; // ALL unqueried leaves/tail, excluding current.
    std::optional<Cell> current; // Halted/throwing cell, not a partial advance.
    Work work;
    std::string message; // Non-normative diagnostic; allocation may leave it empty.
};

// Independent public-value-only coverage; no old search is called internally.
// Environment FIRST. Then capture all original input before validating settings,
// H in (0,.1], finite point sphere quantities (component/radius <=1e12, radius>0)
// and finite raw plane normal/offset <=1e12 with at least one nonzero component.
// No normal normalization or Vec3::dot is used by the old public value graph.
// Whole-cell value.lower()>0 ALONE certifies a leaf. value.upper()<=0 blocks it;
// the remaining uncertain values subdivide only within explicit finite budgets.
// No point/witness/entry/TOI/response or tolerance-based contact acceptance.
// All leaves positive + complete cover + every call returned => certified.
// Uncertain stop order: width_limit, depth_budget, time_resolution, leaf_budget.
// Width uses outward (point(hi)-point(lo)).upper(). Evaluation exhaustion sets
// current before installing a new audit. Value exceptions stop globally, retain
// attempted/nonreturned blocked audit + current and all unqueried tail, and return
// not_certified. No final audit has outcome=pending. Actual private norm loops
// must never be reported from the upper counters. No old search is called here.
// No B inflation, F/m construction, candidate or World mutation; caller provides
// the exact point coefficients/radii to be covered. Same-initial-state repeated
// call/substep accumulation is not a guarantee of this geometric helper.
Result sphere_sphere(const accelerated::Sphere& first,const accelerated::Sphere& second,
                     double horizon_seconds,const Settings& settings={}) noexcept;
Result sphere_plane(const accelerated::Sphere& sphere,const accelerated::StaticPlane& plane,
                    double horizon_seconds,const Settings& settings={}) noexcept;
}
