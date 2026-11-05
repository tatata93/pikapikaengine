#include "pikapika/world_static_mesh_session_packet_wire.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <new>
#include <type_traits>
#include <utility>
namespace pikapika::world_static_mesh_session_packet_wire {
namespace {
static_assert(max_packets==flight::hard_max_packets&&max_loads_per_packet==flight::controlled::hard_max_bodies);
static_assert(std::numeric_limits<std::uint32_t>::digits==32&&std::numeric_limits<std::uint64_t>::digits==64);
static_assert(std::numeric_limits<unsigned>::digits==32&&std::is_same_v<std::underlying_type_t<flight::controlled::LoadMode>,unsigned>);
static_assert(sizeof(double)==8&&std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53);
static_assert(std::is_nothrow_move_constructible_v<Result>);
std::uint64_t integer(std::uint32_t low,std::uint32_t high) noexcept {return (std::uint64_t{high}<<32)|low;}
Result refused(Status status,std::optional<std::size_t> packet={},std::optional<std::size_t> row={},std::optional<std::size_t> component={}) noexcept {Result r;r.status=status;r.packet=packet;r.row=row;r.component=component;return r;}
}
Result decode(std::span<const double> floats,std::span<const std::uint32_t> words) noexcept {
    if(words.empty()||words.size()>max_word_values) {return refused(Status::word_count);}
    std::array<std::uint32_t,max_word_values> w{};std::copy(words.begin(),words.end(),w.begin());
    if(w[0]>max_packets) {return refused(Status::packet_count);}
    const std::size_t count=w[0];std::array<std::size_t,max_packets> offsets{},loads{};std::size_t cursor=1,nf=0;
    for(std::size_t i=0;i<count;++i) {
        if(words.size()-cursor<packet_word_header) {return refused(Status::word_count,i);}
        offsets[i]=cursor;const std::size_t n=w[cursor+3];
        if(n>max_loads_per_packet) {return refused(Status::load_count,i);}
        cursor+=packet_word_header;
        if(words.size()-cursor<n*load_word_stride) {return refused(Status::word_count,i);}
        cursor+=n*load_word_stride;loads[i]=n;nf+=n*float_stride;
    }
    if(cursor!=words.size()) {return refused(Status::word_count);}
    if(floats.size()!=nf) {return refused(Status::float_count);}
    std::array<double,max_float_values> f{};std::copy(floats.begin(),floats.end(),f.begin());
    std::size_t a=0;
    for(std::size_t i=0;i<count;++i) {for(std::size_t j=0;j<loads[i];++j) {for(std::size_t k=0;k<float_stride;++k) {if(!std::isfinite(f[a+k])) {return refused(Status::nonfinite,i,j,k);}}a+=float_stride;}}
    try {
        std::vector<flight::TickLoadPacket> candidate;candidate.reserve(count);a=0;
        for(std::size_t i=0;i<count;++i) {
            const auto b=offsets[i];std::vector<flight::controlled::BodyLoad> rows;rows.reserve(loads[i]);
            for(std::size_t j=0;j<loads[i];++j) {
                const auto u=b+packet_word_header+j*load_word_stride;
                rows.push_back({integer(w[u],w[u+1]),{f[a],f[a+1],f[a+2]},{f[a+3],f[a+4],f[a+5]}});a+=float_stride;
            }
            candidate.emplace_back(static_cast<flight::controlled::LoadMode>(w[b]),integer(w[b+1],w[b+2]),std::move(rows));
        }
        Result out;out.packets.emplace(std::move(candidate));out.status=Status::ok;return out;
    }catch(const std::bad_alloc&) {return refused(Status::allocation_failure);}
    catch(...) {return refused(Status::unexpected_exception);}
}
}
