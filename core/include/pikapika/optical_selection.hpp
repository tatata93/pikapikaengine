#pragma once
#include "pikapika/optical_bounds.hpp"
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <variant>
#include <vector>

namespace pikapika::optical_selection {
using Surface=std::variant<optical_geometry::PlaneDisk,optical_geometry::FullSphere,optical_geometry::SphericalCap>;
struct SurfaceRecord { std::uint64_t id{}; Surface surface=optical_geometry::PlaneDisk{}; };
struct Settings {
    optical_bounds::Settings primitive;
    unsigned max_surfaces{128}; // 1..1024
    unsigned max_queries{512}; // 1..4096, original plus prefix queries
    unsigned max_sqrt_refinements{16384}; // total actual work; 1..1000000
    bool allow_prefix_exclusion{true};
};
enum class Status { hit,miss,unresolved,invalid_input,budget_exceeded,numerical_failure };
struct Selection { std::uint64_t id{}; optical_bounds::Hit hit; };
struct SurfaceDiagnostic {
    std::uint64_t id{};
    unsigned ordinal{}; // canonical increasing-ID order, never caller order
    // Absent when a budget stops work before this original query.
    std::optional<optical_bounds::Result> geometry;
    // At most one prefix query per surface, against the selected hit candidate.
    std::optional<optical_bounds::Result> prefix;
    bool excluded_by_prefix{};
};
struct Result {
    Status status{Status::invalid_input};
    // Set ONLY for hit: all input-family members have this same unique first
    // valid surface/root in the requested CLOSED parameter domain.
    std::optional<Selection> nearest;
    std::vector<SurfaceDiagnostic> surfaces; // canonical increasing-ID order
    unsigned queries{},prefix_queries{},sqrt_refinements{};
    bool refinement_limited{};
    std::string message;
};
// Pure read-only query. Every shape/ray/ID/setting is validated before queries,
// including an empty scene. Positive uint64 IDs must be unique. Inputs inherit
// optical_bounds domains/strict FP contract. An unsupported environment is a
// numerical_failure, not invalid input. No midpoint or hidden epsilon/source skip.
//
// Selection requires a primitive HIT (not merely candidate root bounds), and
// every rival must MISS, have its hit strictly later, or MISS on the CLOSED
// prefix [ray.minimum_parameter, winner.parameter.upper()]. Only all original
// MISS results yield miss. The earliest-upper-endpoint hit is the sole candidate;
// conservative overlap/uncertainty is unresolved, not sampled/order tie-broken.
//
// Total actual sqrt work is audited after each bounded primitive invocation:
// exceeding the total budget atomically fails the selection, retaining actual
// work diagnostics. Overshoot is bounded by one primitive invocation. Query and
// shape budgets stop before invoking an excess query. No unchecked surface can
// yield success. Allocation failure may propagate if diagnostics cannot allocate.
//
// tMin changes the requested domain only; visibility before tMin, self-root
// exclusion, medium topology, automatic continuation and optical transport are
// NOT guaranteed. Independent Cartesian boxes can lose genuine correlations;
// unresolved may remain even with arbitrarily refined arithmetic.
Result find_nearest(const optical_bounds::BoundedRay&,std::span<const SurfaceRecord>,const Settings& settings={});
}
