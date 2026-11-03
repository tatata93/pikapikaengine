#pragma once
#include "pikapika/optical_route.hpp"
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::optical_spot {
using Interval=interval::Interval;
using Bounds3=optical_bounds::Bounds3;
enum class SourceKind { finite_point,parallel_beam };
struct Source { SourceKind kind{SourceKind::parallel_beam}; Vec3 reference{0,0,1}; };
// finite: O=reference, D=point(launch_point)-point(reference), with outward
// subtraction; parallel: O=launch_point, D=point(reference). No normalization.
// Validates bounded-ray vector/domain limits; throws invalid_argument on bad
// input. A zero direction is representable but cannot later certify a hit.
optical_bounds::BoundedRay make_launch_ray(const Source&,Vec3 launch_point,
                                         double minimum_parameter=0,double maximum_parameter=1e6);
struct Sample { optical_bounds::BoundedRay ray; double weight{1}; };
struct Input {
    std::span<const Sample> samples;
    std::span<const optical_route::Step> steps;
    Interval initial_index=Interval::point(1);
    double vacuum_wavelength_m{550e-9};
    optical_geometry::PlaneDisk sensor;
    double sensor_minimum_parameter{0},sensor_maximum_parameter{1e6};
};
struct Settings {
    optical_route::Settings route;
    unsigned max_samples{1024}; // 1..1024
    unsigned max_evaluations{1024}; // 1..1024, one route+sensor sample attempt
    unsigned max_sqrt_refinements{1000000}; // total reported work, 1..4000000
};
enum class Status { completed,unresolved,invalid_input,budget_exceeded,numerical_failure };
enum class SampleStatus { not_examined,accepted,route_miss,branch_unavailable,
    sensor_miss,route_unresolved,sensor_unresolved,budget_exceeded,
    invalid_input,numerical_failure };
struct RouteSummary {
    optical_route::Status status{optical_route::Status::invalid_input};
    unsigned completed_steps{},failed_step{},geometry_queries{},interface_queries{},sqrt_refinements{};
    bool refinement_limited{};
    std::optional<optical_route::Completion> completion;
};
struct Record {
    unsigned ordinal{};
    double weight{1}; // original positive geometric quadrature weight, never throughput
    SampleStatus status{SampleStatus::not_examined};
    std::optional<RouteSummary> route;
    std::optional<optical_bounds::Result> sensor;
};
struct Moments {
    Bounds3 centroid{Interval::point(0),Interval::point(0),Interval::point(0)};
    Interval mean_squared_radius=Interval::point(0); // sum w |position-centroid|^2 / sum w, m^2
    Bounds3 hull=centroid;
};
struct Stats {
    Interval total_weight=Interval::point(0),accepted_weight=Interval::point(0);
    // No accepted samples => weights remain defined, moments absent.
    std::optional<Moments> moments;
};
struct Result {
    Status status{Status::invalid_input};
    std::vector<Record> records; // every admitted input sample, original order
    unsigned evaluations{},accepted{},route_misses{},branch_unavailable{},sensor_misses{},unknown{};
    unsigned geometry_queries{},interface_queries{},sqrt_refinements{};
    bool refinement_limited{};
    // Present ONLY when every record is accepted or a certified prescribed-path
    // omission. Unknown/budget/not-examined records prohibit final_stats.
    std::optional<Stats> final_stats;
    std::string message;
};
// Pure prescribed-route geometric reference, not a radiometric image/PSF,
// nearest-world visibility query, self-root skip, continuous-pupil integration
// error bound, or globally optimal focus. Entire index/ray boxes are retained.
// Sensor is intersected geometrically, without a fictitious optical interface.
// All shapes/rays/weights/settings are preflighted before evaluations; weights
// are exact binary64 geometric measures in [1e-12,1e6]. Source generation and
// pupil quadrature convergence are separate caller responsibilities.
//
// A sample evaluation runs its finite route, then the sensor iff completed.
// A certified geometry miss or unavailable chosen branch is an omission of this
// prescribed path, not proof of absorption by an unmodeled housing. Unresolved
// records are retained and never converted to zero-power/black samples.
// Total sqrt work sums all counters reported by the existing route/geometry
// results, and is audited after a sample: overshoot is bounded by one sample.
// An exception inside an existing primitive can hide its partial work counter;
// such a failure is numerical_failure, never a completed budget certificate.
// Runtime/work bounds still follow max steps and per-endpoint refinements.
// Result construction/allocation failure may propagate if diagnostics cannot
// allocate. No external object is changed, including on failure.
Result evaluate(const Input&,const Settings& settings={});
}
