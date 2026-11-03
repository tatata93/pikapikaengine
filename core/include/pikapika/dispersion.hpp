#pragma once
#include "pikapika/interval.hpp"
#include <array>
#include <optional>

namespace pikapika::optics::dispersion {
// Vacuum wavelength in metres, absolute (vacuum-referenced) refractive index.
// These are mathematical models, not a supplied/calibrated glass catalogue.
struct Band { double minimum{1e-12},maximum{1}; };
struct Cauchy {
    double a{1},b{},c{}; // n=A+B/lambda^2+C/lambda^4; B:m^2, C:m^4
    Band valid_band{};
};
struct Oscillator { double b{},c{}; }; // dimensionless B, C:m^2
struct Sellmeier {
    std::array<Oscillator,8> terms{};
    unsigned count{};
    Band valid_band{};
};
struct Settings {
    // Width of the FULL wavelength-family enclosure, not just rounding error.
    double maximum_phase_width{1e6};
    unsigned max_sqrt_refinements{128}; // per sqrt endpoint, 1..256
};
enum class Status { resolved,nonphysical,unresolved };
enum class Reason { none,pole_not_excluded,nonpositive_phase,nonpositive_squared_phase,
    positivity_uncertain,refinement_budget,phase_width,numerical_range };
struct Values {
    interval::Interval phase=interval::Interval::point(1);
    interval::Interval derivative=interval::Interval::point(0); // dn/dlambda: 1/m
    interval::Interval group=interval::Interval::point(1); // n-lambda*dn/dlambda
    bool within_interface_domain{}; // WHOLE phase bound lies in [1e-6,1e6]
};
struct Result {
    Status status{Status::unresolved};Reason reason{Reason::none};
    std::optional<Values> values;
    std::optional<interval::Interval> squared_phase; // Sellmeier diagnostic
    unsigned sqrt_refinements{};
};
// Entire closed wavelength band is enclosed, without point sampling. Invalid
// input throws: requested/declared bands in [1e-12,1]m, request within declared
// band; finite coefficients |value|<=1e12; <=8 oscillators; finite width>0.
// Original binary64 inputs are exact real model parameters. Measurement/model
// error, absorption, temperature and causal material validity are not certified.
Result evaluate(const Cauchy&,Band wavelength,const Settings& settings={});
Result evaluate(const Sellmeier&,Band wavelength,const Settings& settings={});
}
