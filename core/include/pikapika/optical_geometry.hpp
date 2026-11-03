#pragma once
#include "pikapika/core.hpp"
#include "pikapika/interval.hpp"
#include <array>
#include <optional>

namespace pikapika::optical_geometry {
using Bounds3=std::array<interval::Interval,3>;
struct Ray {
    Vec3 origin{},direction{0,0,1};
    // P(t)=origin+t*direction. Origin is metres; direction is dimensionless.
    // t is a metre-valued PARAMETER, distance=t*|direction| (not generally t).
    // CLOSED requested domain. No hidden offset/epsilon or automatic self-skip.
    double minimum_parameter{0},maximum_parameter{1e6};
};
struct PlaneDisk { Vec3 center{},normal{0,0,1};double aperture_radius{1}; };
struct FullSphere { Vec3 center{};double radius{1}; };
struct SphericalCap {
    Vec3 vertex{},axis{0,0,1};
    // Exact mathematical center = vertex + signed_radius * axis/|axis|.
    // Keep ONLY the vertex hemisphere and circular projected aperture.
    // This is not the whole sphere and has no aperture-rim wall or housing.
    double signed_radius{1},aperture_radius{0.5};
};
struct Settings {
    double parameter_tolerance{1e-8}; // max accepted enclosure width, parameter m
    unsigned max_sqrt_refinements{128}; // per square-root enclosure, 1..256
};
enum class Status { hit,miss,unresolved };
enum class Reason { none,no_real_roots,parallel,filtered_roots,parallel_or_coplanar,
    tangent_or_discriminant,parameter_boundary,aperture_boundary,cap_boundary,
    orientation,precision_limit,refinement_budget,numerical_output };
enum class CandidateState { not_examined,accepted,rejected_parameter,rejected_aperture,rejected_cap,unresolved };
struct Candidate {
    interval::Interval parameter=interval::Interval::point(0);
    CandidateState state{CandidateState::not_examined};
    Reason reason{Reason::none};
};
struct Hit {
    interval::Interval parameter=interval::Interval::point(0);
    interval::Interval physical_distance=interval::Interval::point(0);
    Bounds3 position{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    Bounds3 geometric_normal{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    Bounds3 incident_normal{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    // Approximate doubles only. Do not replace the bounds with these estimates
    // when spawning another rigorous ray or composing an optical transport path.
    double parameter_estimate{},physical_distance_estimate{};
    Vec3 position_estimate{},geometric_normal_estimate{},incident_normal_estimate{};
    // Plane: given normal. Sphere/cap: outward from the full sphere center.
    // front_face certifies direction dot geometric_normal < 0. incident_normal
    // is flipped on back faces, so it points toward the incident medium.
    bool front_face{};
};
struct Result {
    Status status{Status::unresolved};Reason reason{Reason::none};
    std::optional<Hit> nearest;
    // True quadratic roots are ordered, even if enclosures overlap. Stop at an
    // unresolved earlier root: a later valid root cannot certify nearest-hit.
    std::array<Candidate,2> candidates;
    unsigned root_count{},considered_count{},sqrt_refinements{};
    bool refinement_limited{};
    std::optional<interval::Interval> discriminant; // H^2-A*C for sphere/cap
};
// Finite positions/centers/vertices, each |component|<=1e6 m. Direction and axis:
// 1e-6<=max|component|<=1e6. Radii/apertures in [1e-6,1e6] m; cap aperture <=
// |signed_radius|. 0<=tMin<=tMax<=1e9 parameter m; tolerance in (0,1e6].
// Invalid domain throws invalid_argument; interval's FP contract also applies.
// A miss concerns ONLY this surface within the requested parameter domain.
Result intersect(const Ray&,const PlaneDisk&,const Settings& settings={});
Result intersect(const Ray&,const FullSphere&,const Settings& settings={});
Result intersect(const Ray&,const SphericalCap&,const Settings& settings={});
}
