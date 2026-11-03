#pragma once
#include "pikapika/support.hpp"

namespace pikapika::support::detail {
// W2 candidate-driver policy, NOT the public support::solve zero-speed policy.
// The WHOLE raw vn interval inside [-tol,tol] is eligible for a resting LCP.
// Outside it: positive vn separates, vn.upper() < -tol requires an impact,
// negative-side band ambiguity is unresolved. Original vn bounds are retained.
// Static-body/plane and static/static-sphere pairs are skipped, as in World.
// tol must be finite in (0,1e-3] m/s. All existing Settings guards still apply.
// positive_gap_limit must be finite in (0,settings.gap_tolerance]; a gap LOWER
// bound above it is separated, while tolerated negative geometry uses Settings.
// No state, force/torque, geometry or storage mutation; no time integration.
Result solve_finite_velocity(const dynamics::World&,const Settings&,
                             double velocity_residual_tolerance,double positive_gap_limit);
}
