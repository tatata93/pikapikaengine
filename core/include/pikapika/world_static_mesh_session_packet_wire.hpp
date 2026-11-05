#pragma once
#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include <cstdint>
#include <optional>
#include <span>
#include <vector>
namespace pikapika::world_static_mesh_session_packet_wire {
namespace flight=world_static_mesh_flight_controlled_scheduler;
inline constexpr std::uint32_t version=1;
inline constexpr std::size_t max_packets=8,max_loads_per_packet=8,float_stride=6,packet_word_header=4,load_word_stride=2;
inline constexpr std::size_t max_float_values=max_packets*max_loads_per_packet*float_stride;
inline constexpr std::size_t max_word_values=1+max_packets*(packet_word_header+max_loads_per_packet*load_word_stride);
// U32: packetCount; each packet [mode,expectedTickLow,High,loadCount], then
// ordered [bodyIdLow,High] rows. F64: each ordered row forceXYZ,torqueXYZ.
// All IDs/ticks and raw unsigned mode values retain their full integer range.
// Unknown mode, duplicate/zero IDs, invalid tick, static load or ownership are
// model/owner validation, not repaired here. F64 values must be finite.
enum class Status : unsigned {ok,word_count,packet_count,load_count,float_count,nonfinite,allocation_failure,unexpected_exception};
struct Result {
    Status status=Status::unexpected_exception;
    std::optional<std::size_t> packet,row,component;
    std::optional<std::vector<flight::TickLoadPacket>> packets;
};
// Valid readable input spans must stay immutable through the bounded initial
// copy. All input words/values are captured before any packet allocation.
// Success owns all Native vectors; moving/copying the result stores no spans
// into the caller or the old result. Failure publishes no partial packet list.
// No floating arithmetic/environment certification or model call is performed.
Result decode(std::span<const double>,std::span<const std::uint32_t>) noexcept;
}
