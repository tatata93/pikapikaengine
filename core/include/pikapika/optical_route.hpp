#pragma once
#include "pikapika/optical_bounds.hpp"
#include <optional>
#include <span>
#include <string>
#include <variant>
#include <vector>

namespace pikapika::optical_route {
using Interval=interval::Interval;
using Surface=std::variant<optical_geometry::PlaneDisk,optical_geometry::FullSphere,optical_geometry::SphericalCap>;
enum class Branch { reflected,transmitted };
struct Step {
    Surface surface=optical_geometry::PlaneDisk{};
    Branch branch{Branch::transmitted};
    // Index on the OTHER side, including for reflection's Fresnel coefficients.
    Interval next_index=Interval::point(1);
    double minimum_parameter{0},maximum_parameter{1e6};
};
struct Input {
    optical_bounds::BoundedRay ray;
    Interval index=Interval::point(1);
    double vacuum_wavelength_m{550e-9};
    std::span<const Step> steps;
};
struct Settings {
    optical_bounds::Settings primitive;
    unsigned maximum_steps{64}; // 1..64; too many requested steps fail before work
};
struct Totals {
    Interval distance=Interval::point(0); // physical length, metres
    Interval optical_path_length=Interval::point(0); // integral n ds, metres
    // Bounds any polarization's normal-flux ratio on this prescribed branch.
    // No per-surface unpolarized reset and no coherent/phase transport.
    Interval throughput=Interval::point(1);
};
struct Segment {
    optical_bounds::BoundedRay incoming;
    Interval incident_index=Interval::point(1),other_index=Interval::point(1);
    Branch branch{Branch::transmitted};
    optical_bounds::Result geometry;
    std::optional<optical_bounds::InterfaceResult> interface;
    std::optional<optical_bounds::BoundedRay> outgoing;
    std::optional<Interval> factor;
    // Only set after this entire step completed. Failed-step geometry/interface
    // diagnostics remain available, but are not a completed route result.
    std::optional<Totals> accumulated;
};
struct Completion {
    optical_bounds::BoundedRay ray;
    Interval index=Interval::point(1);
    Totals totals;
};
enum class Status { completed,geometry_miss,geometry_unresolved,interface_unresolved,
    branch_unavailable,invalid_input,budget_exceeded,numerical_failure };
struct Result {
    Status status{Status::invalid_input};
    unsigned completed_steps{};
    // First failed/attempted step; equals steps.size() on completion. Invalid
    // global settings and preflight step-budget failure have failed_step=0.
    unsigned failed_step{};
    std::vector<Segment> segments;
    std::optional<Completion> completion;
    std::string message;
};
// Pure read-only calculation. Completed proves this EXPLICIT surface/branch
// itinerary for the full accepted input family, not nearest-world visibility,
// medium geometry consistency or enumeration of other optical paths.
// Each Step supplies the CLOSED parameter domain of its incoming ray. All
// spawned rays retain the entire position/direction boxes with no offset; the
// final ray uses [0,1e6] as an explicit continuation default. Empty routes are
// validated identity routes. Interval target/build contract: docs/INTERVAL.md.
Result trace_route(const Input&,const Settings& settings={});
}
