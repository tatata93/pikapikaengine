#pragma once
#include "pikapika/optical_route.hpp"
#include <array>

namespace pikapika::polarized_route {
using Interval=interval::Interval;
using Bounds3=optical_bounds::Bounds3;
struct Stokes { double i{1},q{},u{},v{}; };
struct ComplexBounds { Interval real=Interval::point(0),imag=Interval::point(0); };
// World XYZ C=<a a*>. upper order: xy,xz,yz; lower entries are conjugates.
// The box contains the true PSD/transverse family; arbitrary independent box
// members need not themselves be PSD, transverse, or jointly attainable.
struct Coherency {
    std::array<Interval,3> diagonal{Interval::point(0),Interval::point(0),Interval::point(0)};
    std::array<ComplexBounds,3> upper;
};
struct State { Coherency coherency; Interval power=Interval::point(0); };
struct Frame { Bounds3 direction,first,second; };
struct Input {
    optical_route::Input route;
    Stokes initial;
    Vec3 transverse_reference{1,0,0};
};
struct Settings {
    optical_route::Settings route;
    unsigned max_sqrt_refinements{128}; // 1..256 per endpoint of a NEW sqrt
    unsigned max_total_sqrt_refinements{1000000}; // 1..4000000, includes geometry
};
enum class Status { completed,geometry_failed,power_unresolved,invalid_input,
    budget_exceeded,numerical_failure };
enum class PowerFailure { none,initial_state_uncertain,initial_frame_uncertain,
    incidence_frame_uncertain,amplitude_uncertain,numerical_domain };
struct Segment {
    unsigned ordinal{};
    optical_route::Branch branch{optical_route::Branch::transmitted};
    std::optional<ComplexBounds> s,p;
    bool exact_normal{},homogeneous{};
    std::optional<State> outgoing;
};
struct Completion {
    State state;
    optical_bounds::BoundedRay ray;
    Interval index=Interval::point(1);
};
struct Result {
    Status status{Status::invalid_input};
    PowerFailure power_failure{PowerFailure::none};
    std::optional<optical_route::Result> geometry;
    std::optional<Frame> initial_frame;
    std::optional<State> initial_state;
    std::vector<Segment> segments;
    unsigned completed_power_steps{},failed_power_step{};
    std::optional<Completion> completion;
    unsigned geometry_queries{},interface_queries{},geometry_sqrt_refinements{},power_sqrt_refinements{};
    bool refinement_limited{};
    std::string message;
};
// Pure prescribed-route ray-tube POWER transport in lossless isotropic media.
// Point Stokes: I in [0,1e12], |Q/U/V|<=1e12, exact physical cone required.
// C12=(U+iV)/2; time dependence exp(-i omega t); first x second=direction.
// No reference-axis fallback, midpoint substitution, per-interface polarization
// reset, radiance/irradiance, global path phase or interference between routes.
// All ray/shape/index domains match optical_bounds. Reference components finite
// within +/-1e6. Geometry is evaluated once; only its completed prefix is used.
// Total sqrt work is checked after one bounded route and each new sqrt call;
// a failing call may overshoot by that one route/call, never succeed over budget.
Result trace_route(const Input&,const Settings& settings={});
}
