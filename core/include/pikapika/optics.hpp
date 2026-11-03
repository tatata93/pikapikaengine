#pragma once
#include "pikapika/core.hpp"
#include "pikapika/interval.hpp"
#include <optional>

namespace pikapika::optics {
// One flat, lossless, isotropic interface; equal magnetic permeability on both
// sides. Index values are supplied at vacuum_wavelength_m; no dispersion model.
struct InterfaceInput {
    // Propagation TOWARD interface, normal points INTO INCIDENT medium.
    // Directions need not be unit length. The exact input vectors define their
    // mathematical unit directions; output normalization is a double estimate.
    Vec3 incident{0,-1,0}, normal{0,1,0};
    double index_incident{1}, index_transmitted{1.5};
    double vacuum_wavelength_m{550e-9};
};
enum class InterfaceKind { transmission, total_internal_reflection, uncertain };
enum class Uncertainty { none, incident_side, critical_angle, numerical_output };
struct PowerSplit {
    // Ratios of time-averaged NORMAL power flux, not electric amplitudes,
    // radiance multipliers, or complex phase/polarization transport.
    double reflectance_s{}, transmittance_s{};
    double reflectance_p{}, transmittance_p{};
    double reflectance_unpolarized{}, transmittance_unpolarized{};
};
struct InterfaceResult {
    InterfaceKind kind{InterfaceKind::uncertain};
    Uncertainty uncertainty{Uncertainty::none};
    Vec3 incident_unit{}, normal_unit{}, reflected{};
    std::optional<Vec3> transmitted;
    std::optional<PowerSplit> power;
    double cosine_incident{};
    std::optional<double> cosine_transmitted;
    double vacuum_wavelength_m{};
    // Complete interval construction from the ORIGINAL finite input doubles:
    // D = nt^2 |incident|^2 |normal|^2 - ni^2 |incident x normal|^2.
    // D<0 is TIR, D>0 transmission. Zero-containing D is unresolved, except
    // the analytically homogeneous equal-index case. Directions/power above
    // are approximate doubles, NOT rigorous interval enclosures.
    interval::Interval discriminant=interval::Interval::point(0);
    interval::Interval incident_dot=interval::Interval::point(0);
    bool exact_grazing{}; // incident_dot proved exactly [0,0], one-sided limit
};

// Inputs: finite vector components, 1e-6 <= max(abs(component)) <= 1e6 for EACH
// vector; indices in [1e-6,1e6]; finite positive vacuum wavelength in metres.
// Wrong incident side (exact dot>0 proved) throws invalid_argument. If dot's
// sign is unresolved, returns uncertain BEFORE the equal-index special case.
// Exact grazing is accepted only when the dot enclosure is the point zero.
// uncertain never supplies transmitted/power/cosine_transmitted success values.
// Requires the documented strict interval FP environment/build contract.
InterfaceResult dielectric_interface(const InterfaceInput& input);
}
