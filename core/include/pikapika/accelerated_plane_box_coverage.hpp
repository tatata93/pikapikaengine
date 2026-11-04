#pragma once
#include "pikapika/accelerated.hpp"
#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace pikapika::accelerated_plane_box_coverage {
// Native helper contract; implementation/build acceptance is recorded separately.
// Conditional declared-B box certificate, not an actual World/body guarantee.
inline constexpr std::size_t maximum_evaluations=255,maximum_leaves=128;
inline constexpr unsigned maximum_depth=32;
struct Settings {
    double time_tolerance{1e-7}; // finite seconds (0,.1]; UNPROVEN-cell stop only
    std::size_t max_evaluations=maximum_evaluations,max_leaves=maximum_leaves;
    unsigned max_depth=24; // 0..32
};
struct Input {
    accelerated::Sphere sphere; // Point nominal P,V,aNom,r; NOT F/m or a body.
    accelerated::StaticPlane plane; // Raw finite nonzero normal; no normalization.
    double position_error; // Caller-declared per-axis bound B, finite [0,1e12].
    double contact_margin; // Explicit caller value, finite [0,.1].
    // No default constructor/arguments: B and margin must be supplied explicitly.
    // Value copies preserve -0 and all source bits without allocation.
    Input(accelerated::Sphere point_sphere,accelerated::StaticPlane raw_plane,
          double error,double margin) noexcept:
        sphere(point_sphere),plane(raw_plane),position_error(error),contact_margin(margin) {}
};
struct Snapshot {
    Input input; // ALL original values/bits, including invalid inputs and -0.
    double horizon{}; // Global seconds, never a normalized parameter.
    Settings settings;
};
struct Evaluation {
    // X_k(T)=P_k+V_k*T+(aNom_k/2)*T^2+[-B,B], using Interval operations.
    std::array<interval::Interval,3> tube_coordinates;
    // Fixed association: ((nx*Xx+ny*Xy)+nz*Xz)-offset.
    interval::Interval distance;
    interval::Interval threshold; // r+contact_margin, computed SEPARATELY.
    interval::Interval gap; // distance-threshold; only lower()>0 certifies.
};
enum class Status : unsigned {certified,not_certified,invalid_input,unsupported_environment};
enum class Reason : unsigned {
    none,settings,horizon,input_domain,zero_normal,position_error,contact_margin,
    evaluation_budget,leaf_budget,depth_budget,width_limit,time_resolution,
    nonpositive_value,value_exception,allocation_failure,environment,coverage_inconsistent
};
enum class LeafState : unsigned {unqueried,certified,blocked,current};
enum class Outcome : unsigned {pending,positive,split,blocked};
struct Cell {
    std::array<double,2> time_bounds{}; // CLOSED global seconds, root [+0,H].
    unsigned depth{};
    std::optional<std::size_t> parent_audit;
};
struct Audit {
    Cell cell;
    bool call_attempted{}; // Set immediately BEFORE public value().
    // Whole returned record or absent; no partial/fabricated zero/whole Eval.
    std::optional<Evaluation> evaluation;
    Outcome outcome=Outcome::pending;
    Reason blocked_reason=Reason::none;
    std::optional<double> split_time; // Present IFF split; shared child endpoint.
};
struct PartitionLeaf {
    Cell cell;
    LeafState state=LeafState::unqueried;
    std::optional<std::size_t> audit_index;
    Reason blocked_reason=Reason::none;
};
struct Work {
    // Exact WRAPPER call counts, including an attempted call that throws.
    // No sqrt, private norm iteration, propagation or metric value call occurs.
    std::size_t value_calls_attempted{},value_calls_returned{};
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<Snapshot> snapshot;
    bool snapshot_validated{};
    // Source 0=sphere,1=plane,2=position_error,3=contact_margin; otherwise absent.
    std::optional<std::size_t> failed_input;
    bool partition_complete{};
    std::vector<Audit> audits; // <=255; breadth-first minimum-depth/left order.
    std::vector<PartitionLeaf> partition; // <=128; WHOLE sorted closed [0,H].
    std::vector<Cell> frontier; // ALL unqueried leaves, never current.
    std::optional<Cell> current;
    Work work;
    std::string message; // Non-normative; allocation may leave empty.
};

// Throwing narrow evaluator. Environment FIRST; validates Input and finite time
// bounds 0<=lo<=hi<=.1, including point times. Input domain: sphere components,
// radius, raw normal components/offset <=1e12 in magnitude; r>0; nonzero normal;
// B in [0,1e12], margin in [0,.1]. No old metric/public-value/search call or sqrt.
// Keeps coordinate/half-acceleration operations in Interval, never scalar rounds
// aNom/2 first. Covers real arithmetic AND fixed-AST exact-or-binary64-RN nodes,
// hence association-preserving FMA contractions. No arbitrary reassociation,
// fast-math/FTZ/excess-precision target, actual B derivation or World claim.
Evaluation value(const Input& input,const interval::Interval& time);

// Environment FIRST => absent snapshot on refusal. Otherwise fixed-size owned
// capture precedes validation: settings,H,sphere,plane (including zero normal),
// B,margin. H in (0,.1]. Invalid captured data is not a valid declared tube.
// Reserve audits/partition/frontier before root installation. Gap.lower()>0
// alone certifies a leaf; gap.upper()<=0 blocks it. Uncertain stop order:
// outward width upper<=tolerance, depth, time resolution, leaf budget.
// Minimum-depth/leftmost pending leaf is selected even after earlier blocking.
// Eval budget stops at current BEFORE new audit. A value throw retains attempted
// audit without Evaluation, current and all tail, then stops not_certified.
// Return count commits immediately on value return; subsequent errors do not
// erase it. No final pending outcome. All leaves positive, complete coverage,
// every call returned and consistent metadata are required for certified.
// No witness/TOI, metric sphere-plane proof, body/candidate, clock/load mutation,
// outer World flag/B/pair certification, or repeated-substep guarantee is added.
Result query(const Input& input,double horizon_seconds,const Settings& settings={}) noexcept;
}
