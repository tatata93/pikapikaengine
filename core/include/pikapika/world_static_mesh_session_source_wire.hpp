#pragma once
#include "pikapika/world_static_mesh_session.hpp"
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

namespace pikapika::world_static_mesh_session_source_wire {
// Native plain-World input format only: no mesh packets or C ABI exports yet.
// F64: gravityXYZ,time,contactMargin,step; then body26, plane6.
// U32: bodyCount,planeCount,maxAttempts,tickLow,tickHigh;
//      then body[idLow,idHigh,staticFlag], plane[idLow,idHigh].
// Body F64 matches mass,radius,inertiaXYZ,positionXYZ,quaternionXYZW,
// velocityXYZ,angularMomentumXYZ,forceXYZ,torqueXYZ,restitution,friction.
// Plane F64 is normalXYZ,offset,restitution,friction. Plane IDs must be strictly
// increasing legal World IDs; raw body IDs retain all64 bits and original order.
inline constexpr std::uint32_t version=1;
inline constexpr std::size_t float_header=6,word_header=5,body_float_stride=26,body_word_stride=3;
inline constexpr std::size_t plane_float_stride=6,plane_word_stride=2,max_bodies=8,max_planes=16;
inline constexpr std::uint64_t maximum_plane_id=(std::uint64_t{1}<<53)-1;
inline constexpr std::size_t max_float_values=float_header+max_bodies*body_float_stride+max_planes*plane_float_stride;
inline constexpr std::size_t max_word_values=word_header+max_bodies*body_word_stride+max_planes*plane_word_stride;
namespace flight=world_static_mesh_session::flight;
struct PlainSource {
    dynamics::World world;
    flight::GuardSettings guard; // Current Native defaults except explicit margin.
    flight::Progress progress;
    flight::Settings clock;
    explicit PlainSource(double margin) noexcept:guard(margin) {}
};
enum class Status : unsigned {ok,word_count,body_count,plane_count,float_count,nonfinite,static_flag,
    plane_id,plane_order,plane_rejected,environment,allocation_failure,unexpected_exception};
enum class Part : unsigned {none,words,floats,body,plane};
struct Result {
    Status status=Status::unexpected_exception;
    Part part=Part::none;
    std::optional<std::size_t> index;
    std::optional<PlainSource> source;
};
// Valid readable spans, immutable during the initial fixed copy, are required.
// All admitted input words/values are copied before World allocation. Rejected
// input publishes no partial source. This is data admission, not model success.
Result decode(std::span<const double>,std::span<const std::uint32_t>) noexcept;
}
