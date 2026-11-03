#pragma once
#include <optional>
#include <span>

// Small independent enclosure kernel, not an IEEE 1788 implementation.
// See docs/INTERVAL.md for the required floating-point build/environment contract.
namespace pikapika::interval {
// A nonempty interval of FINITE real numbers. Infinities are bounds, never members.
// There is no empty/NaI value; invalid construction and undefined division throw.
class Interval {
public:
    Interval(double lower, double upper);
    static Interval point(double finite_value);
    static Interval whole();
    double lower() const noexcept { return lower_; }
    double upper() const noexcept { return upper_; }
    // Comparison-only queries do not probe/throw. Keep the documented valid
    // floating-point environment active here too (notably no DAZ for subnormals).
    bool contains(double finite_value) const noexcept;
    bool contains(const Interval& other) const noexcept;
    bool contains_zero() const noexcept;
    bool strictly_positive() const noexcept { return lower_ > 0; }
    bool strictly_negative() const noexcept { return upper_ < 0; }
private:
    double lower_, upper_;
};

enum class Sign { negative, nonpositive, zero, nonnegative, positive, mixed };
Sign sign(const Interval& value) noexcept;
std::optional<Interval> intersection(const Interval& a, const Interval& b);
Interval hull(const Interval& a, const Interval& b);

// nullptr means the supported runtime probes pass. This is not a formal compiler
// verification: strict build flags and the documented target contract also apply.
const char* environment_issue() noexcept;
void require_environment();

Interval negate(const Interval& value);
Interval add(const Interval& a, const Interval& b);
Interval sub(const Interval& a, const Interval& b);
Interval mul(const Interval& a, const Interval& b);
// Throws domain_error if b contains zero, including [0,0] and a=[0,0].
Interval divide(const Interval& a, const Interval& b);
Interval square(const Interval& value);

struct SqrtResult {
    Interval value=Interval::point(0);
    unsigned refinements{};
    bool refinement_limited{};
};
// Monotone enclosure of the nonnegative finite input family. The iteration
// limit is per endpoint (1..256); a limited result remains an enclosure.
// No libm sqrt accuracy assumption. Exact binary exponent scaling keeps the
// bisection in [1,2], including subnormal inputs and the largest binary64 value.
// This is not a correctly-rounded scalar sqrt or an IEEE 1788 implementation.
SqrtResult sqrt_enclosure(const Interval& value,unsigned maximum_refinements=128);

// Horner enclosure. Coefficients are ordered HIGHEST degree first, constant last.
// Empty coefficients throw invalid_argument. Repeated x occurrences lose
// correlation; a bound containing zero proves neither a root nor a collision.
Interval polynomial(std::span<const Interval> coefficients, const Interval& x);

inline Interval operator+(const Interval& a, const Interval& b) { return add(a,b); }
inline Interval operator-(const Interval& a, const Interval& b) { return sub(a,b); }
inline Interval operator-(const Interval& a) { return negate(a); }
inline Interval operator*(const Interval& a, const Interval& b) { return mul(a,b); }
inline Interval operator/(const Interval& a, const Interval& b) { return divide(a,b); }
}
