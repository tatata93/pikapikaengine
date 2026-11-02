#pragma once
#include "pikapika/core.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace pikapika::dynamics {
// SI units, right-handed coordinates. Rotation maps body coordinates to world.
struct Material {
    double restitution{0}; // Normal speed ratio, 0..1.
    double friction{0.6};  // Coulomb coefficient, 0..10 in this subset.
};
struct RigidBody {
    std::uint64_t id{};
    bool is_static{false};
    double mass{1};
    Vec3 inertia_diagonal{0.4,0.4,0.4}; // Principal body moments, kg m^2.
    double radius{1};                  // Sphere collision proxy, metres.
    Vec3 position{},velocity{},angular_momentum{}; // World frame, L in kg m^2/s.
    Quaternion orientation{};
    Vec3 force{},torque{};             // Held constant in world frame for a step.
    Material material{};
    double inverse_mass() const;
    Vec3 inverse_world_inertia(Vec3 world_vector) const;
    Vec3 angular_velocity() const;
    double kinetic_energy() const;
    void validate() const;
};
RigidBody make_sphere(std::uint64_t id,double radius,double mass,Vec3 position = {},bool is_static = false);

// Static half-space: legal sphere centres satisfy normal.dot(position)-offset >= radius.
struct Plane {
    std::uint64_t id{};
    Vec3 normal{0,1,0};
    double offset{};
    Material material{};
};
struct SolverSettings {
    unsigned velocity_iterations{16}; // Always bounded, 1..128.
    std::size_t max_contacts{16384};   // Budget overflow fails the step, never drops contacts.
    double contact_margin{1e-6};
    double penetration_slop{1e-5};
    double position_correction{0.8};  // Geometric correction; does not modify velocity.
    double max_position_correction{0.2};
    double restitution_velocity_threshold{0.5};
    double max_angular_increment{0.5}; // Radians per step; exceeding this requests smaller dt.
};
struct StepStats {
    std::size_t contacts{};
    unsigned velocity_iterations{};
    double max_penetration{};
    double normal_impulse_sum{};
    double friction_impulse_sum{};
    double max_closing_residual{};
};

class World {
public:
    Vec3 gravity{0,-9.80665,0};
    void add_body(RigidBody body);
    void add_plane(Plane plane);
    RigidBody* find_body(std::uint64_t id);
    const RigidBody* find_body(std::uint64_t id) const;
    const std::vector<RigidBody>& bodies() const { return bodies_; }
    const std::vector<Plane>& planes() const { return planes_; }
    void apply_force(std::uint64_t id,Vec3 force_newtons,Vec3 world_point);
    void apply_torque(std::uint64_t id,Vec3 torque_newton_meters);
    void apply_impulse(std::uint64_t id,Vec3 impulse_newton_seconds,Vec3 world_point);
    // dt in (0,0.1]. Failure leaves body state/accumulated loads unchanged.
    // Successful steps consume force/torque. No cross-step impulse warm starting yet.
    StepStats step(double dt,const SolverSettings& settings = {});
private:
    bool contains_id(std::uint64_t id) const;
    std::vector<RigidBody> bodies_;
    std::vector<Plane> planes_;
};
}
