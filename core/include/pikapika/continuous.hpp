#pragma once
#include "pikapika/core.hpp"
#include <optional>

namespace pikapika::continuous {
// SI units, fixed orientation, linear trajectories for 0 <= t <= horizon.
struct MovingSphere { Vec3 center{}, velocity{}; double radius{1}; };
// Solid negative half-space: normal dot (x - velocity*t) <= offset.
// The normal must be unit length within 1e-12; accepted normals are normalized.
struct MovingPlane { Vec3 normal{0,1,0}; double offset{}; Vec3 velocity{}; };
enum class ContactKind { none, initial_overlap, initial_touch, impact, grazing, uncertain };
enum class Motion { stationary, approaching, separating, tangential };
struct ToiResult {
    ContactKind kind{ContactKind::none};
    Motion initial_motion{Motion::stationary};
    // Absent for none; zero for initial events; a candidate time for uncertain.
    std::optional<double> time;
    // Sphere/sphere: A -> B. Plane/sphere: plane -> sphere.
    // For none this is the initial normal; uncertain normals are diagnostic only.
    Vec3 normal{};
    bool normal_valid{};
    // True only when the returned time is exactly the supplied horizon.
    bool at_horizon{};
    // Diagnostic floating-point guard, NOT a rigorous interval certificate.
    bool roundoff_sensitive{};
    double initial_gap{};          // metres; negative means overlap
    double initial_normal_speed{}; // m/s; negative means approaching
    double normal_speed{};         // at returned event, or initially for none
};
// Finite inputs: |coordinate|, |velocity component|, radius, |offset| <= 1e12;
// radius > 0; 0 <= horizon <= 1e6 seconds. Throws invalid_argument for domain
// violations, domain_error for unrepresentable/underflowed derived geometry.
// No state is mutated. Acceleration, rotation and collision response are absent.
ToiResult sphere_sphere(const MovingSphere& a, const MovingSphere& b, double horizon);
ToiResult sphere_plane(const MovingSphere& sphere, const MovingPlane& plane, double horizon);
}
