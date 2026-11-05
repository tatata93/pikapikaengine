#include "pikapika/world_static_mesh_session_api.h"
#include "pikapika/world_static_mesh_session_source_wire.hpp"
#include "pikapika/world_static_mesh_session_wire.hpp"
#include <algorithm>
#include <array>
#include <limits>
#include <type_traits>
#include <utility>
namespace owner=pikapika::world_static_mesh_session;
namespace source=pikapika::world_static_mesh_session_source_wire;
namespace wire=pikapika::world_static_mesh_session_wire;
struct pp_ws_context {
    owner::Registry registry;
    std::array<double,PP_WS_INPUT_F64_CAPACITY> input_f{};
    std::array<std::uint32_t,PP_WS_INPUT_U32_CAPACITY> input_w{};
    std::optional<source::PlainSource> staged;
    std::uint64_t revision{};
    bool busy{};
    std::array<double,source::max_float_values> read_f{};
    std::array<std::uint32_t,source::max_word_values> read_w{};
    pp_ws_snapshot_info read_info{};
    explicit pp_ws_context(std::uint64_t limit):registry({limit}) {}
};
namespace {
#define PP_WS_MAP(c,n) static_assert(static_cast<unsigned>(n)==c)
PP_WS_MAP(PP_WS_OWNER_OK,owner::Status::ok);
PP_WS_MAP(PP_WS_OWNER_BUSY,owner::Status::busy);
PP_WS_MAP(PP_WS_OWNER_SLOT_RANGE,owner::Status::slot_range);
PP_WS_MAP(PP_WS_OWNER_NOT_ALIVE,owner::Status::not_alive);
PP_WS_MAP(PP_WS_OWNER_STALE,owner::Status::stale_generation);
PP_WS_MAP(PP_WS_OWNER_FOREIGN,owner::Status::foreign_session);
PP_WS_MAP(PP_WS_OWNER_FULL,owner::Status::no_free_slot);
PP_WS_MAP(PP_WS_OWNER_RETIRED,owner::Status::generation_exhausted);
PP_WS_MAP(PP_WS_OWNER_SOURCE_COUNTS,owner::Status::source_counts);
PP_WS_MAP(PP_WS_OWNER_SETTINGS,owner::Status::invalid_settings);
PP_WS_MAP(PP_WS_OWNER_ALLOCATION,owner::Status::allocation_failure);
PP_WS_MAP(PP_WS_OWNER_EXCEPTION,owner::Status::unexpected_exception);
PP_WS_MAP(PP_WS_SOURCE_OK,source::Status::ok);
PP_WS_MAP(PP_WS_SOURCE_WORD_COUNT,source::Status::word_count);
PP_WS_MAP(PP_WS_SOURCE_BODY_COUNT,source::Status::body_count);
PP_WS_MAP(PP_WS_SOURCE_PLANE_COUNT,source::Status::plane_count);
PP_WS_MAP(PP_WS_SOURCE_FLOAT_COUNT,source::Status::float_count);
PP_WS_MAP(PP_WS_SOURCE_NONFINITE,source::Status::nonfinite);
PP_WS_MAP(PP_WS_SOURCE_STATIC,source::Status::static_flag);
PP_WS_MAP(PP_WS_SOURCE_PLANE_ID,source::Status::plane_id);
PP_WS_MAP(PP_WS_SOURCE_PLANE_ORDER,source::Status::plane_order);
PP_WS_MAP(PP_WS_SOURCE_PLANE_INVALID,source::Status::plane_rejected);
PP_WS_MAP(PP_WS_SOURCE_ENVIRONMENT,source::Status::environment);
PP_WS_MAP(PP_WS_SOURCE_ALLOCATION,source::Status::allocation_failure);
PP_WS_MAP(PP_WS_SOURCE_EXCEPTION,source::Status::unexpected_exception);
PP_WS_MAP(PP_WS_PART_NONE,source::Part::none);
PP_WS_MAP(PP_WS_PART_WORDS,source::Part::words);
PP_WS_MAP(PP_WS_PART_FLOATS,source::Part::floats);
PP_WS_MAP(PP_WS_PART_BODY,source::Part::body);
PP_WS_MAP(PP_WS_PART_PLANE,source::Part::plane);
PP_WS_MAP(PP_WS_TOKEN_OK,wire::TokenStatus::ok);
PP_WS_MAP(PP_WS_TOKEN_WORD_COUNT,wire::TokenStatus::word_count);
PP_WS_MAP(PP_WS_TOKEN_SLOT,wire::TokenStatus::slot_range);
PP_WS_MAP(PP_WS_TOKEN_ZERO,wire::TokenStatus::generation_zero);
PP_WS_MAP(PP_WS_TOKEN_RANGE,wire::TokenStatus::generation_range);
#undef PP_WS_MAP
static_assert(std::is_nothrow_move_constructible_v<source::PlainSource>);
static_assert(std::is_nothrow_move_constructible_v<owner::Read>);
struct Busy {bool& flag;explicit Busy(bool& f) noexcept:flag(f){flag=true;}~Busy() noexcept{flag=false;}};
std::uint64_t integer(std::uint32_t low,std::uint32_t high) noexcept {return (std::uint64_t{high}<<32)|low;}
pp_ws_result result(std::uint32_t host=PP_WS_OK) noexcept {
    pp_ws_result r{};r.host=host;r.owner=r.source=r.token_status=r.index=PP_WS_NOT_CALLED;return r;
}
pp_ws_result gate(pp_ws_context* c) noexcept {return result(!c?PP_WS_NULL_CONTEXT:c->busy?PP_WS_BUSY:PP_WS_OK);}
bool staged(pp_ws_context& c,std::uint32_t low,std::uint32_t high,pp_ws_result& r) noexcept {
    if(!c.staged) {r.host=PP_WS_NO_SOURCE;return false;}
    if(integer(low,high)!=c.revision) {r.host=PP_WS_SOURCE_REVISION;return false;}
    return true;
}
bool token(std::uint32_t slot,std::uint32_t low,std::uint32_t high,owner::Token& t,pp_ws_result& r) noexcept {
    const std::array<std::uint32_t,3> words{slot,low,high};const auto status=wire::decode_token(words,t);
    r.token_status=static_cast<std::uint32_t>(status);
    if(status!=wire::TokenStatus::ok) {r.host=PP_WS_TOKEN_REJECTED;return false;}
    return true;
}
void created(owner::Created value,pp_ws_result& r) noexcept {
    r.owner=static_cast<std::uint32_t>(value.status);
    if(value.status!=owner::Status::ok) {r.host=PP_WS_OWNER_REJECTED;return;}
    wire::TokenWords words{};wire::encode_token(value.token,words);std::copy(words.begin(),words.end(),r.token);
}
void words64(std::uint64_t v,std::uint32_t* w) noexcept {w[0]=static_cast<std::uint32_t>(v);w[1]=static_cast<std::uint32_t>(v>>32);}
void vector(pikapika::Vec3 v,double* f) noexcept {f[0]=v.x;f[1]=v.y;f[2]=v.z;}
void publish(pp_ws_context& c,const owner::Snapshot& s) noexcept {
    std::array<double,source::max_float_values> f{};std::array<std::uint32_t,source::max_word_values> w{};
    vector(s.world.gravity,f.data());f[3]=s.progress.time;f[4]=s.guard.contact_margin;f[5]=s.scheduler.settings.step_seconds;
    w[0]=static_cast<std::uint32_t>(s.world.bodies().size());w[1]=static_cast<std::uint32_t>(s.world.planes().size());w[2]=static_cast<std::uint32_t>(s.scheduler.settings.max_attempts_per_pump);words64(s.progress.ticks,w.data()+3);
    std::size_t nf=source::float_header,nw=source::word_header;
    for(const auto& b:s.world.bodies()) {
        auto* a=f.data()+nf;auto* u=w.data()+nw;words64(b.id,u);u[2]=b.is_static?1U:0U;
        a[0]=b.mass;a[1]=b.radius;vector(b.inertia_diagonal,a+2);vector(b.position,a+5);
        a[8]=b.orientation.x;a[9]=b.orientation.y;a[10]=b.orientation.z;a[11]=b.orientation.w;
        vector(b.velocity,a+12);vector(b.angular_momentum,a+15);vector(b.force,a+18);vector(b.torque,a+21);
        a[24]=b.material.restitution;a[25]=b.material.friction;nf+=source::body_float_stride;nw+=source::body_word_stride;
    }
    for(const auto& p:s.world.planes()) {
        auto* a=f.data()+nf;words64(p.id,w.data()+nw);vector(p.normal,a);a[3]=p.offset;a[4]=p.material.restitution;a[5]=p.material.friction;
        nf+=source::plane_float_stride;nw+=source::plane_word_stride;
    }
    pp_ws_snapshot_info info{};info.available=1;info.float_count=static_cast<std::uint32_t>(nf);info.word_count=static_cast<std::uint32_t>(nw);
    wire::TokenWords t{};wire::encode_token(s.token,t);std::copy(t.begin(),t.end(),info.token);words64(s.scheduler.sequence,info.sequence);info.backlog=s.scheduler.backlog;
    c.read_f=f;c.read_w=w;c.read_info=info;
}
}
extern "C" {
std::uint32_t pp_ws_api_version() noexcept {return PP_WS_API_VERSION;}
pp_ws_context* pp_ws_context_create(std::uint32_t low,std::uint32_t high) noexcept {
    try {return new pp_ws_context(integer(low,high));}catch(...) {return nullptr;}
}
void pp_ws_context_delete(pp_ws_context* c) noexcept {delete c;}
double* pp_ws_input_f64(pp_ws_context* c) noexcept {return c?c->input_f.data():nullptr;}
std::uint32_t* pp_ws_input_u32(pp_ws_context* c) noexcept {return c?c->input_w.data():nullptr;}
pp_ws_result pp_ws_stage(pp_ws_context* c,std::uint32_t nf,std::uint32_t nw) noexcept {
    auto r=gate(c);if(r.host!=PP_WS_OK) {return r;}const Busy busy(c->busy);c->staged.reset();
    if(nf>c->input_f.size()||nw>c->input_w.size()) {r.host=PP_WS_INPUT_COUNT;return r;}
    if(c->revision==std::numeric_limits<std::uint64_t>::max()) {r.host=PP_WS_REVISION_EXHAUSTED;return r;}
    auto decoded=source::decode({c->input_f.data(),nf},{c->input_w.data(),nw});
    r.source=static_cast<std::uint32_t>(decoded.status);r.part=static_cast<std::uint32_t>(decoded.part);
    if(decoded.index) {r.index=static_cast<std::uint32_t>(*decoded.index);}
    if(decoded.status!=source::Status::ok) {r.host=PP_WS_SOURCE_REJECTED;return r;}
    c->staged.emplace(std::move(*decoded.source));++c->revision;words64(c->revision,r.revision);return r;
}
pp_ws_result pp_ws_create(pp_ws_context* c,std::uint32_t low,std::uint32_t high) noexcept {
    auto r=gate(c);if(r.host!=PP_WS_OK) {return r;}const Busy busy(c->busy);if(!staged(*c,low,high,r)) {return r;}
    const auto& s=*c->staged;created(c->registry.create(s.world,{},s.guard,s.progress,s.clock),r);return r;
}
pp_ws_result pp_ws_reset(pp_ws_context* c,std::uint32_t rl,std::uint32_t rh,std::uint32_t slot,std::uint32_t low,std::uint32_t high) noexcept {
    auto r=gate(c);if(r.host!=PP_WS_OK) {return r;}const Busy busy(c->busy);if(!staged(*c,rl,rh,r)) {return r;}
    owner::Token t{};if(!token(slot,low,high,t,r)) {return r;}
    const auto& s=*c->staged;created(c->registry.reset(t,s.world,{},s.guard,s.progress,s.clock),r);return r;
}
pp_ws_result pp_ws_destroy(pp_ws_context* c,std::uint32_t slot,std::uint32_t low,std::uint32_t high) noexcept {
    auto r=gate(c);if(r.host!=PP_WS_OK) {return r;}const Busy busy(c->busy);owner::Token t{};if(!token(slot,low,high,t,r)) {return r;}
    const auto status=c->registry.destroy(t);r.owner=static_cast<std::uint32_t>(status);if(status!=owner::Status::ok) {r.host=PP_WS_OWNER_REJECTED;}return r;
}
pp_ws_result pp_ws_read(pp_ws_context* c,std::uint32_t slot,std::uint32_t low,std::uint32_t high) noexcept {
    auto r=gate(c);if(r.host!=PP_WS_OK) {return r;}const Busy busy(c->busy);owner::Token t{};if(!token(slot,low,high,t,r)) {return r;}
    auto read=c->registry.read(t);r.owner=static_cast<std::uint32_t>(read.status);
    if(read.status!=owner::Status::ok) {r.host=PP_WS_OWNER_REJECTED;return r;}
    publish(*c,*read.snapshot);std::copy(std::begin(c->read_info.token),std::end(c->read_info.token),r.token);return r;
}
pp_ws_snapshot_info pp_ws_snapshot_info_get(const pp_ws_context* c) noexcept {return c?c->read_info:pp_ws_snapshot_info{};}
const double* pp_ws_snapshot_f64(const pp_ws_context* c) noexcept {return c?c->read_f.data():nullptr;}
const std::uint32_t* pp_ws_snapshot_u32(const pp_ws_context* c) noexcept {return c?c->read_w.data():nullptr;}
}
