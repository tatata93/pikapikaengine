#pragma once
#include "pikapika/core.hpp"
#include "pikapika/dynamics.hpp"
#include <optional>

namespace pikapika::hydrostatics {
struct Fluid {
    double density{1000};     // kg/m^3, constant.
    double gravity{9.80665};  // Positive magnitude, force field is -Y.
    double water_level{};    // Horizontal still free surface, world metres.
};
struct Pose {
    Transform transform{};
    std::optional<Vec3> center_of_mass; // World metres; defaults to transform.position.
};
struct Result {
    Vec3 force{},torque{};    // Fluid load only; torque about supplied CoM.
    double wet_area{},submerged_volume{},total_volume{};
    std::optional<Vec3> center_of_buoyancy;
    std::size_t shells{};
};
// Prepares an immutable closed, consistently outward-wound displacement shell.
// Edge topology does not establish absence of self-intersection/overlapping shells.
class Hull {
public:
    explicit Hull(Mesh mesh);
    const Mesh& mesh() const { return mesh_; }
    double volume() const { return volume_; }
    std::size_t shells() const { return shells_; }
private:
    Mesh mesh_;
    double volume_{};
    std::size_t shells_{};
};
double pressure(double depth,const Fluid& fluid = {});
Result forces(const Hull& hull,const Fluid& fluid = {},const Pose& pose = {});

// hull_origin_body is the hull origin relative to body CoM, in body-frame metres.
// scale changes displacement geometry only; caller supplies consistent body mass/inertia.
Result apply_buoyancy(dynamics::World& world,std::uint64_t body_id,const Hull& hull,const Fluid& fluid = {},
                      Vec3 hull_origin_body = {},Vec3 scale = {1,1,1});
struct CoupledStep { Result midpoint_load; dynamics::StepStats dynamics; };
// Two-load midpoint coupling for exactly one dynamic body, no planes/contacts.
// Predicts half a step, re-evaluates hydrostatics, then advances the real step.
// No drag/damping is added. A failure leaves the original world body unchanged.
CoupledStep step_isolated_buoyant_body(dynamics::World& world,std::uint64_t body_id,const Hull& hull,
                                      double dt,const Fluid& fluid = {},Vec3 hull_origin_body = {},
                                      Vec3 scale = {1,1,1},const dynamics::SolverSettings& settings = {});
}
