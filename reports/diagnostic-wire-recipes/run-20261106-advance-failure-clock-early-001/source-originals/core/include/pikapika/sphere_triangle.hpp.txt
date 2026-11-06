#pragma once
#include "pikapika/core.hpp"
#include "pikapika/interval.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace pikapika::sphere_triangle {
using Bounds3=std::array<interval::Interval,3>;
inline constexpr double coordinate_limit=1e150;
struct StaticTriangle {
    std::uint64_t id{}; // Stable surface ID, 1..2^53-1; original vertex order.
    std::array<Vec3,3> vertices{};
};
struct Settings {
    unsigned max_candidates=7; // 1..7; all seven must be examined for success.
    unsigned sqrt_refinements=128; // 1..256 per endpoint.
    unsigned max_total_sqrt_refinements=1024; // 1..1024; post-sqrt audit.
    double maximum_local_width=1e-7; // m, closest_local and delta component widths.
    double maximum_normal_width=1e-8; // dimensionless component widths.
    double minimum_sine_squared=1e-12; // sin^2(angle AB,AC), conditioning gate.
};
enum class Status : unsigned {
    completed,invalid_input,degenerate,ill_conditioned,quality_unresolved,
    budget_exceeded,numerical_failure,unsupported_environment
};
enum class Reason : unsigned {
    none,settings,surface_id,input_domain,zero_cross,cross_uncertain,
    conditioning_rejected,conditioning_uncertain,candidate_budget,no_candidate,
    local_width,zero_distance,distance_uncertain,sqrt_budget,normal_width,
    nonfinite_intermediate,allocation_failure,environment
};
enum class Feature : unsigned {face,edge_ab,edge_bc,edge_ca,vertex_a,vertex_b,vertex_c};
enum class Disposition : unsigned {retained,outside_simplex,kkt_violated};
enum class Relation : unsigned {separated,penetrating,touching,boundary_unresolved};
struct CandidateAudit {
    Feature feature=Feature::face;
    Disposition disposition=Disposition::retained;
    // Pre-clipping barycentric enclosure. Retained candidates additionally have
    // all three coordinates intersected with [0,1] in the accepted hull.
    Bounds3 barycentric{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    // Necessary KKT residuals: each must be <=0. Count is 0/1/2 for face/edge/vertex.
    std::array<interval::Interval,2> kkt{interval::Interval::point(0),interval::Interval::point(0)};
    unsigned kkt_count{};
};
struct Geometry {
    std::uint64_t surface_id{};
    std::uint32_t surviving_features{}; // bit 1<<Feature, not a unique feature claim.
    Bounds3 barycentric{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    Bounds3 closest_local{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)}; // q-A [m]
    Bounds3 closest{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)}; // world q [m]
    Bounds3 delta{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)}; // x-q, formed locally [m]
    Bounds3 normal{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)}; // triangle -> centre
    Bounds3 sphere_point{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)}; // x-r*n [m]
    interval::Interval squared_distance=interval::Interval::point(0); // m^2
    interval::Interval distance=interval::Interval::point(0); // m
    interval::Interval gap=interval::Interval::point(0); // distance-radius [m]
    Relation relation=Relation::boundary_unresolved;
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<Geometry> geometry; // completed only; no accepted failure prefix.
    std::optional<interval::Interval> squared_cross,sine_squared;
    std::vector<CandidateAudit> candidates; // diagnostic prefix only on failure.
    unsigned candidates_examined{},sqrt_refinements{};
    bool sqrt_refinement_limited{};
    std::string message;
};
// Pure instantaneous query of a sphere against one STATIC TWO-SIDED thin face.
// Finite input coordinates/radius <=1e150, radius>0. Exact binary64 inputs;
// strict interval FP/environment contract, no caller rounding/control-mode changes.
// All seven KKT candidates not proved impossible are retained. No point estimate
// or fallback normal. d=0/insufficient quality has no accepted geometry.
// Local width gates do not bound world q width after a huge common translation.
// sqrt budget is audited after one call (at most 2*sqrt_refinements updates).
// Not CCD, a mesh manifold/solid-inside query, or permission to midpoint bounds
// into a point impulse solver. Inputs, World state, loads and clocks are untouched.
Result query_sphere_triangle(Sphere sphere,const StaticTriangle& triangle,const Settings& settings={});
}
