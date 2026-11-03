#pragma once
#include "pikapika/dynamics.hpp"

// Implementation detail for candidate states, not a public dynamics/CCD API.
namespace pikapika::dynamics::detail {
void validate_solver_settings(const SolverSettings& settings);
inline constexpr std::size_t absent_body=static_cast<std::size_t>(-1);
struct ImpactContact {
    std::size_t a{absent_body},b{absent_body};
    Vec3 point{},normal{};
    Material material_a{},material_b{};
};
// Explicit selected contacts, candidate-only. No propagation, projection or load
// consumption. All contacts are prepared before solving in the supplied order.
StepStats solve_selected_impacts(std::vector<RigidBody>& candidates,
    const std::vector<ImpactContact>& contacts,const SolverSettings& settings);
// Advance one already validated candidate under its held world force/torque.
// No contact generation/response, projection, or load consumption. Static bodies
// are unchanged. Uses the same world-L and midpoint orientation update as step.
// The caller supplies valid finite gravity, 0 < dt <= 0.1 and max_angle settings,
// and validates the propagated state before using or committing it.
// May partly mutate the candidate on failure: discard it, never publish it.
void propagate_free(RigidBody& candidate,Vec3 gravity,double dt,double max_angle);

// Generate, prepare and solve existing sphere/plane contacts at the current
// candidate poses. Does NOT advance time or consume force/torque. Orientation
// is unchanged. Position CAN change if position_correction is nonzero.
// Preconditions: validated settings and stable-ID-ordered validated bodies/planes
// as stored by World. Validates the resulting candidates after solving.
// This mutates candidates only; an exception does not promise candidate rollback.
// The public tick owns load consumption, whole-step validation and commit.
StepStats solve_contacts_at_current_state(std::vector<RigidBody>& candidates,
    const std::vector<Plane>& planes,const SolverSettings& settings);
}
