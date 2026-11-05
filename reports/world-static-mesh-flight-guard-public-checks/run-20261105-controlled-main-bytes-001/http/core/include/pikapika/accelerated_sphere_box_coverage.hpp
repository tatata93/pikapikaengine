#pragma once
#include "pikapika/accelerated.hpp"
#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace pikapika::accelerated_sphere_box_coverage {
// Native contract. New cpp authored; build/math/public acceptance are pending.
// A conditional two-declared-B predicate certificate, not actual World binding.
inline constexpr std::size_t maximum_evaluations=255,maximum_leaves=128;
inline constexpr unsigned maximum_depth=32,maximum_sqrt_refinements=256;
inline constexpr std::size_t maximum_sqrt_refinement_work=130560; // 255*2*256
struct Settings {
    double time_tolerance{1e-7}; // finite global seconds (0,.1]; stop ONLY
    std::size_t max_evaluations=maximum_evaluations,max_leaves=maximum_leaves;
    unsigned max_depth=24; // 0..32
    unsigned sqrt_refinements=128; // 1..256 per endpoint; no extra total limit
};
struct Input {
    accelerated::Sphere first,second; // Point P,V,aNom and ORIGINAL radii.
    double first_position_error,second_position_error; // Declared axis bounds B.
    double contact_margin; // Explicit, never guessed from a solver/World.
    // Mandatory five arguments. Do not pass inflated guard radii AND B again.
    Input(accelerated::Sphere first_sphere,accelerated::Sphere second_sphere,
          double first_error,double second_error,double margin) noexcept:
        first(first_sphere),second(second_sphere),first_position_error(first_error),
        second_position_error(second_error),contact_margin(margin) {}
};
struct Snapshot {
    Input input; // Fixed-size ALL original values/bits, even invalid data/-0.
    double horizon{}; // Original global seconds.
    Settings settings;
};
struct Evaluation {
    std::array<interval::Interval,3> first_coordinates,second_coordinates;
    std::array<interval::Interval,3> delta; // second-first, exact-or-RN enclosure.
    // Q=((square(dx)+square(dy))+square(dz)). Its interval lower may be negative
    // from outward rounding although the actual product/sum family is >=0.
    interval::Interval raw_squared_distance;
    // Lower=max(0,raw.lower), upper=raw.upper. Negative upper is an ERROR.
    interval::Interval nonnegative_squared_distance;
    interval::SqrtResult root; // Full returned root/value/count/limited flag.
    interval::Interval distance; // Pure copy of root.value: all bits identical.
    interval::Interval threshold; // (I(rFirst)+I(rSecond))+I(explicit margin).
    interval::Interval gap; // distance-threshold; only lower()>0 certifies.
};
enum class Status : unsigned {certified,not_certified,invalid_input,unsupported_environment};
enum class Reason : unsigned {
    none,settings,horizon,input_domain,position_error,contact_margin,
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
    bool call_attempted{}; // Immediately BEFORE public value().
    std::optional<Evaluation> evaluation; // Full record or absent, never filled.
    Outcome outcome=Outcome::pending;
    Reason blocked_reason=Reason::none;
    std::optional<double> split_time; // Present IFF split; shared endpoint bits.
};
struct PartitionLeaf {
    Cell cell;
    LeafState state=LeafState::unqueried;
    std::optional<std::size_t> audit_index;
    Reason blocked_reason=Reason::none;
};
struct Work {
    // Always exact wrapper counters, EVEN when the root-accounting flag is false.
    std::size_t value_calls_attempted{},value_calls_returned{};
    // Observed ONLY through a returned complete Evaluation. A throwing value
    // may have completed a private sqrt; do NOT invent observed root attempts.
    std::size_t sqrt_results_returned{},sqrt_refinements_returned{};
    std::size_t sqrt_limited_returns{},sqrt_refinements_upper{};
    bool exact=true; // ROOT work only; unknown value block retains 2*ref upper.
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<Snapshot> snapshot;
    bool snapshot_validated{};
    // 0=first sphere,1=second sphere,2=first B,3=second B,4=margin; else absent.
    std::optional<std::size_t> failed_input;
    bool partition_complete{};
    std::vector<Audit> audits;
    std::vector<PartitionLeaf> partition;
    std::vector<Cell> frontier; // ALL unqueried leaves, never the current cell.
    std::optional<Cell> current;
    Work work;
    std::string message; // Non-normative; allocation failure may leave empty.
};

// Throwing narrow evaluator. Environment FIRST, then Input, refinement limit,
// and finite time 0<=lo<=hi<=.1; point times are allowed. Input: finite sphere
// components/radii <=1e12 in magnitude, r>0; both B in [0,1e12]; margin [0,.1].
// Each path box is P+V*T+(I(aNom)*I(.5))*square(T)+[-B,B]. No scalar aNom/2.
// Uses original radii, not guard_radius plus the same B a second time.
// No metric query/search, propagation, World, caller-B derivation or norm helper.
// Fixed AST covers exact OR binary64 RN at each arithmetic node. Root enclosure
// has nonnegative binary64 endpoints: monotone RN fixes the endpoints, so exact
// sqrt inclusion ALSO includes correctly rounded binary64 sqrt. Actual external
// std::sqrt/compiler binding is a SEPARATE prerequisite, not established here.
// No arbitrary reassociation, FTZ/DAZ, alternate rounding or excess precision.
Evaluation value(const Input& input,const interval::Interval& time,
                 unsigned sqrt_refinements=128);

// Environment FIRST => absent Snapshot on refusal. Otherwise capture original
// Input/H/Settings BEFORE validating settings,H,first,second,firstB,secondB,margin.
// H in (0,.1]; invalid capture is not a validated path. Reserve audits/partition/
// frontier before root. BFS minimum-depth/left order; uncertain stop priority:
// outward width<=tolerance, depth, strict-time resolution, leaf budget.
// Only gap.lower()>0 is positive; gap.upper()<=0 is blocked. Small tolerance,
// root refinement_limited, endpoint samples or exact nominal metric alone do not
// prove success; a limited but enclosing root MAY certify when its gap is >0.
// Evaluation exhaustion keeps current BEFORE new audit. Before a value call,
// reserve unknown root upper 2*sqrt_refinements, then mark exact wrapper attempt.
// Commit return/root counters immediately after complete value return. On throw:
// evaluation absent, blocked/value_exception + current + full tail, root exact
// false, upper=prior known refinements+2*ref. Root attempts are NOT observed.
// No final pending audit. All positive/full cover/normal returned calls/root work
// and consistent metadata are needed for certified. Whole-call root work cannot
// exceed 2*max_evaluations*sqrt_refinements<=130560; no heap-size guarantee.
// No entry/TOI/response, actual World binding, body/candidate/load/clock update,
// or repeated-substep guarantee. External supported-target sqrt gate stays open.
Result query(const Input& input,double horizon_seconds,const Settings& settings={}) noexcept;
}
