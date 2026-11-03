#pragma once
#include "pikapika/optics.hpp"
#include <complex>
#include <optional>

namespace pikapika::optics::polarization {
// Monochromatic ray-tube POWER coordinates, not irradiance/radiance or E field.
// C = <a a*>; I=Cxx+Cyy, Q=Cxx-Cyy, U=2 Re(Cxy), V=2 Im(Cxy).
// Time convention: Re(E exp(i k.x - i omega t)). No handedness name is implied.
struct Stokes { double i{1}, q{}, u{}, v{}; };
// Approximate right-handed orthonormal axes: first x second = direction.
struct Frame { Vec3 direction{}, first{}, second{}; };
// Direction/reference component max in [1e-6,1e6]. Reference is projected onto
// the transverse plane; its sine to direction must be >=1e-8 (conditioning).
Frame make_frame(Vec3 direction, Vec3 transverse_reference);
void validate(const Stokes& value);
// Both frames must be orthonormal within 2e-12 and directions match within 2e-12.
// This is a numerical consistency condition, not an exact geometric predicate.
Stokes reexpress(const Stokes& value, const Frame& from, const Frame& to);
// C' = diag(a,b) C diag(a,b)*. Passive amplitudes |a|,|b|<=1 (64eps rounding).
// Ordinary-double estimates throughout; no interval guarantee for Stokes values.
Stokes diagonal_jones(const Stokes& value, std::complex<double> a,
                      std::complex<double> b);

struct Branch {
    Frame frame;
    Stokes power;
    // Reflection: electric amplitudes. Transmission: power-normalized amplitudes
    // sqrt(nt cos(t)/(ni cos(i))) * electric amplitude (or grazing limit).
    std::complex<double> amplitude_s{}, amplitude_p{};
};
enum class Failure { none, interface_uncertain, incidence_plane_uncertain, numerical_output };
struct Split {
    InterfaceResult interface;
    Frame input_frame;
    Failure failure{Failure::none};
    std::optional<Branch> reflected, transmitted;
};
// State is expressed in make_frame(input.incident, transverse_reference).
// Local s is n x incident; p=incident x s. Reflected/transmitted frames use the
// SAME s and each ray's own p, preserving a right-handed propagation frame.
// Exact collinear input may use the supplied transverse reference. Near normal
// incidence with uncertifiable plane returns uncertainty rather than inventing s.
// Under TIR, complex reflection phases are retained; no propagating transmitted
// branch. Primitive uncertainty supplies NEITHER branch. Equal media are identity.
// Paths are separate beams: no global path phase, coherent recombination, thin
// films, absorption, scattering, diffraction, lens geometry or renderer implied.
Split dielectric_split(const InterfaceInput& input, Vec3 transverse_reference,
                       const Stokes& power = {});
}
