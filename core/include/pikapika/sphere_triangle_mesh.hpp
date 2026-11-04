#pragma once
#include "pikapika/sphere_triangle.hpp"
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle_mesh {
inline constexpr std::size_t maximum_surfaces=64;
struct Settings {
    std::size_t max_surfaces=maximum_surfaces; // 1..64, a smaller caller budget.
    sphere_triangle::Settings primitive{}; // Same domains and defaults as single query.
};
enum class Status : unsigned {completed,invalid_input,budget_exceeded,row_failure,numerical_failure,unsupported_environment};
enum class Reason : unsigned {none,settings,surface_count,surface_budget,surface_id,duplicate_id,input_domain,row_failed,aggregate_inconsistent,nonfinite_intermediate,allocation_failure,environment};
struct Row {
    sphere_triangle::StaticTriangle triangle; // Owned original order/ID/binary64 bits.
    // Every ordinary attempt has the actual single-kernel Result, even failure.
    // Null means NOT EXAMINED after a fatal outer exception, never a geometry miss.
    std::optional<sphere_triangle::Result> query;
};
struct Nearest {
    interval::Interval squared_distance=interval::Interval::point(0); // m^2
    interval::Interval distance=interval::Interval::point(0); // m
    interval::Interval gap=interval::Interval::point(0); // m
    // ALL d_i^2.lower <= min_j(d_j^2.upper), ascending stable IDs.
    // A set of possible minimizers, not a claim each is an exact tie.
    std::vector<std::uint64_t> possible_surface_ids;
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<std::size_t> failed_index; // Structural source preflight location.
    std::optional<std::size_t> first_failed_row; // Actual first non-completed query.
    std::vector<Row> rows; // Owned source order. Empty for preflight/environment rejection.
    std::optional<Nearest> nearest; // ALL rows completed, only; no partial nearest.
    std::size_t queries{},candidates_examined{},sqrt_refinements{},sqrt_limited_rows{},failed_rows{};
    std::string message;
};
// No resource builder/handle: pure finite-set query, no borrowed output storage.
// Strict interval environment is checked FIRST. Empty/>64 source sets are invalid;
// n>max_surfaces is a budget failure. All IDs/finite source domains and settings
// are prevalidated before any single query. Degeneracy/conditioning are geometry
// outcomes of that unchanged single kernel, not structural source rejection.
// Valid sources are ALL copied before enumeration. Every ordinary row failure is
// retained and all remaining rows are still queried. Allocation/fatal exceptions
// may leave an actual owned diagnostic prefix/null rows; nearest stays absent.
// Maximum work:64 queries,448 candidates,32768 actual sqrt updates. Per-row sqrt
// budget retains the single kernel's post-call audit/possible one-call overshoot.
// Aggregate endpoints are min of the respective row lower/upper endpoints; no
// new sqrt, midpoint winner, averaged normal/barycentric, or AABB skip is used.
// Not mesh adjacency/manifold/solid-inside, World, CCD, dynamic triangles, response,
// mass properties, or permission to turn these intervals into point impulses.
Result query(Sphere sphere,std::span<const sphere_triangle::StaticTriangle> triangles,const Settings& settings={});
}
