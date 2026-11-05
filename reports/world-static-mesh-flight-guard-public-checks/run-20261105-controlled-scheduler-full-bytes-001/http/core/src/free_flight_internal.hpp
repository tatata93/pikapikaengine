#pragma once
#include "pikapika/dynamics.hpp"
#include <optional>
#include <string>

// Private read-only bridge, implemented in continuous_world.cpp beside the
// ORIGINAL anonymous flight(). No recurrence copy and no call to World::step.
namespace pikapika::dynamics::detail {
struct FreeFlightTube {
    Vec3 nominal_acceleration{};
    double position_error{},roundoff{},guard_radius{};
};
struct FreeFlightTubeResult {
    std::optional<FreeFlightTube> tube;
    CcdFailure failure=CcdFailure::none;
    std::string message;
};
// Caller validates dynamic body, finite gravity and H in (0,.1], and requires the
// strict interval environment first. Exception/failure is returned, never hidden.
// On success exactly reuses flight(body,gravity,H)'s returned values. No mutation.
FreeFlightTubeResult enclose_free_flight(const RigidBody& body,Vec3 gravity,double horizon) noexcept;
}
