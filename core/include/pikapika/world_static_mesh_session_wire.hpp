#pragma once
#include "pikapika/world_static_mesh_session.hpp"
#include <array>
#include <cstdint>
#include <limits>
#include <span>

namespace pikapika::world_static_mesh_session_wire {
// Integer exchange words, not the C++ Token object representation or a legacy
// pp_sim_handle. Syntax validation does not establish a live Registry session.
inline constexpr std::uint32_t token_version=1;
inline constexpr std::size_t token_word_count=3;
using Token=world_static_mesh_session::Token;
using TokenWords=std::array<std::uint32_t,token_word_count>;
enum class TokenStatus : std::uint32_t {ok=0,word_count=1,slot_range=2,generation_zero=3,generation_range=4};
static_assert(std::numeric_limits<std::uint32_t>::digits==32);
static_assert(std::numeric_limits<std::uint64_t>::digits==64);
static_assert(world_static_mesh_session::maximum_generation==(std::uint64_t{1}<<53)-1);
inline constexpr auto maximum_high_word=static_cast<std::uint32_t>(world_static_mesh_session::maximum_generation>>32);

// Both functions retain all output fields/words on failure. The declared span
// must refer to valid readable storage. No allocation, floating point or model
// call is performed. Precedence: exact count, slot, high/range, zero generation.
inline TokenStatus encode_token(Token token,TokenWords& output) noexcept {
    if(token.slot>=world_static_mesh_session::hard_max_sessions)return TokenStatus::slot_range;
    if(token.generation>world_static_mesh_session::maximum_generation)return TokenStatus::generation_range;
    if(token.generation==0)return TokenStatus::generation_zero;
    const TokenWords staged{token.slot,static_cast<std::uint32_t>(token.generation),
                            static_cast<std::uint32_t>(token.generation>>32)};
    output=staged;
    return TokenStatus::ok;
}

inline TokenStatus decode_token(std::span<const std::uint32_t> words,Token& output) noexcept {
    if(words.size()!=token_word_count)return TokenStatus::word_count;
    if(words[0]>=world_static_mesh_session::hard_max_sessions)return TokenStatus::slot_range;
    if(words[2]>maximum_high_word)return TokenStatus::generation_range;
    const auto generation=(std::uint64_t{words[2]}<<32)|std::uint64_t{words[1]};
    if(generation==0)return TokenStatus::generation_zero;
    const Token staged{words[0],generation};
    output=staged;
    return TokenStatus::ok;
}
}
