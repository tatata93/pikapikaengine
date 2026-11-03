#pragma once
#include "pikapika/polarized_route.hpp"

namespace pikapika::polarized_packet {
using Interval=interval::Interval;
struct Packet {
    optical_bounds::BoundedRay ray;
    polarized_route::Stokes power; // I/Q/U/V in watts, not geometric weights
    Vec3 transverse_reference{1,0,0};
};
struct Input {
    std::span<const Packet> packets;
    std::span<const optical_route::Step> steps;
    Interval initial_index=Interval::point(1);
    double vacuum_wavelength_m{550e-9};
    optical_geometry::PlaneDisk sensor;
    double sensor_minimum_parameter{0},sensor_maximum_parameter{1e6};
};
struct Settings {
    polarized_route::Settings route;
    unsigned max_packets{1024}; // 1..1024
    unsigned max_evaluations{1024}; // 1..1024, one packet route+sensor attempt
    unsigned max_total_sqrt_refinements{1000000}; // 1..4000000, entire batch
};
enum class Status { completed,unresolved,invalid_input,budget_exceeded,numerical_failure };
enum class PacketStatus { not_examined,accepted,route_miss,branch_unavailable,
    sensor_miss,route_unresolved,power_unresolved,sensor_unresolved,invalid_input,
    budget_exceeded,numerical_failure };
struct Record {
    unsigned ordinal{};
    polarized_route::Stokes power; // original caller-supplied watts
    PacketStatus status{PacketStatus::not_examined};
    std::optional<polarized_route::Result> route; // entire original prefix/diagnostics
    std::optional<optical_bounds::Result> sensor;
    std::optional<Interval> sensor_power; // accepted only, no new interface/cosine
};
struct Stats {
    Interval total_source_power=Interval::point(0);
    Interval accepted_source_power=Interval::point(0);
    Interval detected_power=Interval::point(0);
};
struct Result {
    Status status{Status::invalid_input};
    std::vector<Record> records; // every admitted packet in original order
    std::optional<Stats> final_stats; // all accepted or certified route omissions
    unsigned evaluations{},accepted{},route_misses{},branch_unavailable{},sensor_misses{},unknown{};
    unsigned geometry_queries{},interface_queries{},sensor_queries{};
    unsigned geometry_sqrt_refinements{},power_sqrt_refinements{},sensor_sqrt_refinements{};
    bool refinement_limited{};
    std::string message;
};
// Pure finite noninterfering packet POWER measure for ONE prescribed itinerary.
// Caller explicitly supplies each packet's watts; no geometric pupil weight is
// converted to watts here. A packet retains its polarization throughout route.
// Sensor is an ideal absorbing power counter tested geometrically, without a
// fictitious interface, extra cosine or index-squared multiplier.
// Certified route miss/unavailable branch/sensor miss contribute zero to this
// route's detected power; unknown/budget/not-examined prohibit final_stats.
// No radiance/irradiance, continuous-source quadrature error, inter-packet/path
// interference, automatic visibility or proof of mutually exclusive routes.
// Preflights every packet/shape/domain before work. Domains match polarized_route.
// Total reported sqrt updates are audited after one bounded packet, hence a
// failing batch may overshoot by one packet; completed never exceeds budget.
// Primitive exceptions may hide partial counters: numerical failure, not a
// completed work certificate. Allocation failure may propagate if diagnostics
// cannot allocate. Inputs and all external objects remain unchanged.
Result evaluate(const Input&,const Settings& settings={});
}
