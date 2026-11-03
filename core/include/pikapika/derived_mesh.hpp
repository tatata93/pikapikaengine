#pragma once
#include "pikapika/core.hpp"
#include "pikapika/interval.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::derived_mesh {
using Triangle=std::array<std::uint32_t,3>;
using Float3=std::array<float,3>;
using Bounds3=std::array<interval::Interval,3>;
inline constexpr double coordinate_limit=1e6;
// These constants denote their exact binary64 values, in m^4 and dimensionless.
inline constexpr double minimum_cross_squared=1e-24;
inline constexpr double maximum_normal_component_error=1e-6;
struct Settings {
    std::size_t max_vertices=2048;
    std::size_t max_triangles=32768;
    unsigned sqrt_refinements=128;
};
enum class Status : unsigned {
    completed, invalid_input, budget_exceeded, degenerate, quality_rejected,
    quality_unresolved, numerical_failure, unsupported_environment
};
enum class Reason : unsigned {
    none, settings, vertex_count, triangle_count, position_domain, index_range,
    duplicate_index, vertex_budget, triangle_budget, zero_cross,
    below_area_floor, cross_uncertain, area_uncertain, normal_uncertain,
    nonfinite_intermediate, allocation_failure, environment
};
struct FaceAudit {
    std::size_t face{};
    Bounds3 cross{interval::Interval::point(0),interval::Interval::point(0),interval::Interval::point(0)};
    interval::Interval squared_cross=interval::Interval::point(0);
    std::optional<Bounds3> normalized;
    std::optional<Float3> normal;
    // Upper bounds on |normal_float[i]-the exact normalized cross[i]|.
    std::optional<std::array<double,3>> normal_error;
    unsigned sqrt_refinements{};
    bool sqrt_refinement_limited{};
};
struct Geometry {
    std::vector<Float3> positions;
    std::vector<Triangle> triangles;
    // Three expanded corners per face, each position3 then flat normal3.
    std::vector<float> interleaved;
    Float3 minimum{}, maximum{};
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<std::size_t> failed_vertex, failed_face;
    std::optional<Geometry> geometry;
    // Diagnostic prefix only; never a partially accepted render buffer.
    std::vector<FaceAudit> audits;
    std::uint64_t sqrt_refinements{};
    unsigned sqrt_limited_faces{};
    std::string message;
};
// Pure local-space conversion. Input binary64 positions must be finite and
// within +/-1e6 metres. Hard count limits: 65536 vertices / 131072 faces.
// Float32 RN-even/gradual-underflow and the existing interval environment are
// required; no caller rounding/control mode is changed. Failure has no geometry.
// Certification concerns the quantized local triangle and approximate normal,
// not world/view/clip arithmetic, raster coverage, foldovers or source topology.
Result prepare(std::span<const Vec3> positions,std::span<const Triangle> triangles,
               const Settings& settings={});
}
