#pragma once
#include "pikapika/optical_geometry.hpp"
#include <array>
#include <optional>

namespace pikapika::optical_bounds {
using Bounds3=optical_geometry::Bounds3;
using Interval=interval::Interval;
// Independent Cartesian boxes of FINITE real inputs. Correlations may be lost
// when transporting a preceding hit, but no bounds are replaced by midpoints.
struct BoundedRay {
    Bounds3 origin{Interval::point(0),Interval::point(0),Interval::point(0)};
    Bounds3 direction{Interval::point(0),Interval::point(0),Interval::point(1)};
    // P(t)=origin+t*direction. Origin [m], direction dimensionless, t [m].
    // Physical distance is t*|direction|. CLOSED domain, no implicit self skip.
    double minimum_parameter{0},maximum_parameter{1e6};
};
struct Settings {
    // Includes genuine variation across the input family, not just rounding.
    double maximum_parameter_width{1e6}; // parameter m
    unsigned max_sqrt_refinements{128}; // per endpoint, 1..256
};
enum class Reason { none,zero_direction,zero_normal,parallel_or_coplanar,
    no_real_roots,tangent_or_discriminant,parameter_boundary,aperture_boundary,
    cap_boundary,orientation,precision_limit,refinement_budget,incident_side,
    critical_angle,numerical_domain };
enum class Status { hit,miss,unresolved };
enum class CandidateState { not_examined,accepted,rejected_parameter,
    rejected_aperture,rejected_cap,unresolved };
struct Candidate {
    Interval parameter=Interval::point(0);
    CandidateState state{CandidateState::not_examined};
    Reason reason{Reason::none};
};
struct Hit {
    Interval parameter=Interval::point(0),physical_distance=Interval::point(0);
    Bounds3 position{Interval::point(0),Interval::point(0),Interval::point(0)};
    // Both enclose the TRUE real unit normals for every accepted family member.
    Bounds3 geometric_normal{Interval::point(0),Interval::point(0),Interval::point(1)};
    Bounds3 incident_normal=geometric_normal;
    bool front_face{};
};
struct Result {
    Status status{Status::unresolved};
    Reason reason{Reason::none};
    std::optional<Hit> nearest;
    // Each candidate encloses the SAME mathematically ordered root across the
    // entire input family. Earlier unresolved roots prohibit a later hit.
    std::array<Candidate,2> candidates;
    unsigned root_count{},considered_count{},sqrt_refinements{};
    bool refinement_limited{};
    std::optional<Interval> discriminant;
};
// hit: EVERY family member has this same first valid root in the requested
// domain, with outputs enclosed. miss: NO member has a valid root there.
// Neither a zero-containing expression nor a sampled hit proves existence.
Result intersect(const BoundedRay&,const optical_geometry::PlaneDisk&,const Settings& settings={});
Result intersect(const BoundedRay&,const optical_geometry::FullSphere&,const Settings& settings={});
Result intersect(const BoundedRay&,const optical_geometry::SphericalCap&,const Settings& settings={});
// Explicit continuation domain. Copies the whole hit-position box and outgoing
// direction box. It does NOT skip the source surface or prove medium assignment.
BoundedRay spawn_ray(const Hit&,const Bounds3& outgoing,double minimum_parameter=0,
                     double maximum_parameter=1e6);
BoundedRay enclose_ray(const optical_geometry::Ray&);
Bounds3 enclose(Vec3);

struct InterfaceInput {
    Bounds3 incident{Interval::point(0),Interval::point(-1),Interval::point(0)};
    Bounds3 normal{Interval::point(0),Interval::point(1),Interval::point(0)};
    // Given values at this wavelength: lossless, isotropic, equal permeability.
    double index_incident{1},index_transmitted{1.5},vacuum_wavelength_m{550e-9};
};
struct IndexBoundsInterfaceInput {
    Bounds3 incident{Interval::point(0),Interval::point(-1),Interval::point(0)};
    Bounds3 normal{Interval::point(0),Interval::point(1),Interval::point(0)};
    // Independent index families at ONE specified vacuum wavelength. Even if
    // these are the same nonpoint interval, ni and nt are NOT correlated equal.
    Interval index_incident=Interval::point(1),index_transmitted=Interval::point(1.5);
    double vacuum_wavelength_m{550e-9};
};
enum class InterfaceKind { transmission,total_internal_reflection,unresolved };
struct Power {
    // NORMAL flux ratios, NOT E amplitudes, radiance or Stokes phase transport.
    Interval reflectance_s=Interval::point(0),transmittance_s=Interval::point(0);
    Interval reflectance_p=Interval::point(0),transmittance_p=Interval::point(0);
    Interval reflectance_unpolarized=Interval::point(0),transmittance_unpolarized=Interval::point(0);
};
struct InterfaceResult {
    InterfaceKind kind{InterfaceKind::unresolved};
    Reason reason{Reason::none};
    std::optional<Bounds3> incident_unit,normal_unit,reflected,transmitted;
    std::optional<Power> power;
    std::optional<Interval> cosine_incident,cosine_transmitted,discriminant;
    Interval incident_dot=Interval::point(0);
    unsigned sqrt_refinements{};
    bool refinement_limited{},exact_grazing{};
    double vacuum_wavelength_m{};
};
// All coefficients, normalization, Snell/reflection and normal-flux powers are
// outward enclosures. Unresolved returns no outgoing direction/power success.
// Strictly wrong incident side throws; mixed/uncertain side is unresolved.
InterfaceResult dielectric_interface(const InterfaceInput&,const Settings& settings={});
// Entire index intervals are retained. The homogeneous shortcut applies ONLY
// when both are the same singleton. No median, endpoint or sampled substitute.
InterfaceResult dielectric_interface_bounds(const IndexBoundsInterfaceInput&,
                                            const Settings& settings={});
// FP contract matches interval.hpp. Finite vector endpoints |component|<=1e6,
// origin <=1e6 m, nonzero vector certification required (otherwise unresolved).
// Radii/shape parameters match optical_geometry; t in [0,1e9], width (0,1e6],
// indices [1e-6,1e6], positive finite wavelength. Invalid domains throw.
}
