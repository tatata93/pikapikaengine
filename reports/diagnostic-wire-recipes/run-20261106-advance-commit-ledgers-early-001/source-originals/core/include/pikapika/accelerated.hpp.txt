#pragma once
#include "pikapika/core.hpp"
#include "pikapika/interval.hpp"
#include <cstddef>
#include <optional>

namespace pikapika::accelerated {
// Exact input binary64 values interpreted as real SI quantities. No state update.
struct Sphere { Vec3 center{},velocity{},acceleration{}; double radius{1}; };
// Static solid negative half-space normal.dot(x) <= offset. Any nonzero normal;
// its REAL Euclidean magnitude is enclosed, never rounded into an exact unit n.
struct StaticPlane { Vec3 normal{0,1,0}; double offset{}; };
struct Settings {
    double time_tolerance{1e-8}; // seconds; limits certified bracket width only
    std::size_t max_evaluations{32768}; // all time-range AND point evaluations
    std::size_t max_frontier{4096};
    unsigned max_depth{64};
};
enum class Kind { none, entry_bracket, unresolved };
enum class Reason { none, initial_overlap, initial_boundary, evaluation_budget,
                    frontier_budget, depth_limit, time_resolution, numerical_uncertainty };
struct Result {
    Kind kind{Kind::unresolved};
    Reason reason{Reason::none};
    // When true, the CLOSED continuous prefix [0,safe_until] is strictly outside.
    bool initial_separation_proven{};
    double safe_until{};
    std::optional<interval::Interval> value_at_safe;
    std::optional<interval::Interval> initial_value;
    // Present only for entry_bracket. First zero and at least one entry lie here;
    // value_at_safe>0 and negative_value<0 certify existence, not zero membership.
    std::optional<interval::Interval> bracket;
    // Can exist for unresolved: a negative witness alone is not an isolated entry.
    std::optional<double> negative_witness;
    std::optional<interval::Interval> negative_value;
    std::size_t evaluations{},excluded_intervals{};
    unsigned depth_reached{};
};
// Finite |centre/velocity/acceleration component|, radius, |offset| and |normal
// component| <= 1e12; radius>0, 0<=horizon<=1e6 s. time_tolerance in (0,1e6],
// max_evaluations 1..1e6, max_frontier 1..65536, max_depth 0..128.
// Invalid input throws invalid_argument; invalid FP environment throws as in
// interval.hpp. Tangency, initial boundaries and insufficient proof are unresolved.
Result sphere_sphere(const Sphere& a,const Sphere& b,double horizon,const Settings& settings={});
Result sphere_plane(const Sphere& sphere,const StaticPlane& plane,double horizon,const Settings& settings={});

// Reusable enclosures of the same real-valued equations on a finite time interval
// in [0,1e6]. Pair: |r+vt+at²/2|²-(ra+rb)² [m²]. Plane: n.dot(p(t))-d-r*|n| [|n| m].
// Geometric and coefficient/Horner enclosures are both formed from input points.
interval::Interval sphere_sphere_value(const Sphere& a,const Sphere& b,const interval::Interval& time);
interval::Interval sphere_plane_value(const Sphere& sphere,const StaticPlane& plane,const interval::Interval& time);
}
