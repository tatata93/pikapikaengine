#include "pikapika/world_static_mesh_session_source_wire.hpp"
#include "pikapika/interval.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <exception>
#include <new>
#include <type_traits>
#include <utility>

namespace pikapika::world_static_mesh_session_source_wire {
namespace {
static_assert(max_bodies==flight::controlled::hard_max_bodies);
static_assert(max_planes==flight::controlled::hard_max_planes);
static_assert(std::is_nothrow_move_constructible_v<PlainSource>);
static_assert(std::is_nothrow_move_constructible_v<Result>);
static_assert(std::is_nothrow_copy_assignable_v<dynamics::RigidBody>);
std::uint64_t integer(std::uint32_t low,std::uint32_t high) noexcept {return (std::uint64_t{high}<<32)|std::uint64_t{low};}
Result refused(Status status,Part part=Part::none,std::optional<std::size_t> index=std::nullopt) noexcept {
    Result out;out.status=status;out.part=part;out.index=index;return out;
}
Vec3 vector_at(const std::array<double,max_float_values>& f,std::size_t offset) noexcept {return {f[offset],f[offset+1],f[offset+2]};}
dynamics::RigidBody body_at(const std::array<double,max_float_values>& f,const std::array<std::uint32_t,max_word_values>& w,std::size_t i) noexcept {
    const auto a=float_header+body_float_stride*i,b=word_header+body_word_stride*i;
    dynamics::RigidBody body;body.id=integer(w[b],w[b+1]);body.is_static=w[b+2]==1;
    body.mass=f[a];body.radius=f[a+1];body.inertia_diagonal=vector_at(f,a+2);body.position=vector_at(f,a+5);
    body.orientation={f[a+8],f[a+9],f[a+10],f[a+11]};body.velocity=vector_at(f,a+12);body.angular_momentum=vector_at(f,a+15);
    body.force=vector_at(f,a+18);body.torque=vector_at(f,a+21);body.material={f[a+24],f[a+25]};return body;
}
}
Result decode(std::span<const double> floats,std::span<const std::uint32_t> words) noexcept {
    if(words.size()<word_header)return refused(Status::word_count,Part::words);
    const std::size_t bodies=words[0],planes=words[1];
    if(bodies>max_bodies)return refused(Status::body_count,Part::words,0);
    if(planes>max_planes)return refused(Status::plane_count,Part::words,1);
    const auto nf=float_header+bodies*body_float_stride+planes*plane_float_stride;
    const auto nw=word_header+bodies*body_word_stride+planes*plane_word_stride;
    if(words.size()!=nw)return refused(Status::word_count,Part::words);
    if(floats.size()!=nf)return refused(Status::float_count,Part::floats);
    if(interval::environment_issue())return refused(Status::environment);
    std::array<double,max_float_values> f{};
    std::array<std::uint32_t,max_word_values> w{};
    std::copy(floats.begin(),floats.end(),f.begin());std::copy(words.begin(),words.end(),w.begin());
    for(std::size_t i=0;i<nf;++i)if(!std::isfinite(f[i]))return refused(Status::nonfinite,Part::floats,i);
    for(std::size_t i=0;i<bodies;++i)if(w[word_header+body_word_stride*i+2]>1)return refused(Status::static_flag,Part::body,i);
    std::uint64_t previous{};
    for(std::size_t i=0;i<planes;++i) {
        const auto a=word_header+bodies*body_word_stride+i*plane_word_stride;const auto id=integer(w[a],w[a+1]);
        if(id==0||id>maximum_plane_id)return refused(Status::plane_id,Part::plane,i);
        if(i&&id<=previous)return refused(Status::plane_order,Part::plane,i);
        previous=id;
    }
    try {
        PlainSource candidate(f[4]);candidate.world.gravity=vector_at(f,0);candidate.progress={f[3],integer(w[3],w[4])};candidate.clock={f[5],w[2]};
        for(std::size_t i=0;i<planes;++i) {
            const auto a=float_header+bodies*body_float_stride+i*plane_float_stride,b=word_header+bodies*body_word_stride+i*plane_word_stride;
            dynamics::Plane plane;plane.id=integer(w[b],w[b+1]);plane.normal=vector_at(f,a);plane.offset=f[a+3];plane.material={f[a+4],f[a+5]};
            try {candidate.world.add_plane(plane);}
            catch(const std::bad_alloc&) {throw;}
            catch(const std::exception&) {return refused(Status::plane_rejected,Part::plane,i);}
        }
        // World::add_body sorts by ID. Allocate valid placeholder bodies first,
        // capture all pointers after the last insertion, then assign raw input
        // fields once. No observed World is rebuilt from a model candidate.
        std::array<std::uint64_t,max_bodies> ids{};std::uint64_t next=1;
        for(std::size_t i=0;i<bodies;++i) {
            while(std::any_of(candidate.world.planes().begin(),candidate.world.planes().end(),[&](const auto& p){return p.id==next;}))++next;
            dynamics::RigidBody placeholder;placeholder.id=next;ids[i]=next++;candidate.world.add_body(placeholder);
        }
        std::array<dynamics::RigidBody*,max_bodies> pointers{};
        for(std::size_t i=0;i<bodies;++i) {pointers[i]=candidate.world.find_body(ids[i]);if(!pointers[i])return refused(Status::unexpected_exception);}
        for(std::size_t i=0;i<bodies;++i)*pointers[i]=body_at(f,w,i);
        Result out;out.source.emplace(std::move(candidate));out.status=Status::ok;return out;
    }catch(const std::bad_alloc&) {return refused(Status::allocation_failure);}
    catch(...) {return refused(Status::unexpected_exception);}
}
}
