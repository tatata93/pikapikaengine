#include "pikapika/world_static_mesh_session.hpp"
#include <new>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace pikapika::world_static_mesh_session {
namespace {
struct Busy {
    bool& flag;
    explicit Busy(bool& f) noexcept:flag(f) {flag=true;}
    ~Busy() noexcept {flag=false;}
    Busy(const Busy&)=delete;
    Busy& operator=(const Busy&)=delete;
};
bool bounded(const dynamics::World& world,std::span<const flight::StaticMeshSource> meshes) noexcept {
    namespace c=flight::controlled;
    if(world.bodies().size()>c::hard_max_bodies||world.planes().size()>c::hard_max_planes||meshes.size()>c::hard_max_meshes) {return false;}
    std::size_t faces=0;
    for(const auto& mesh:meshes) {
        if(mesh.triangles.size()>c::hard_max_faces-faces) {return false;}
        faces+=mesh.triangles.size();
    }
    return true;
}
static_assert(std::is_nothrow_move_constructible_v<flight::PumpReport>);
static_assert(std::is_nothrow_destructible_v<flight::PumpReport>);
static_assert(std::is_nothrow_move_constructible_v<Pump>);
static_assert(std::is_nothrow_move_constructible_v<Read>);
static_assert(std::is_nothrow_destructible_v<Snapshot>);
}
struct Registry::Session {
    dynamics::World world;
    std::vector<flight::StaticMeshSource> meshes;
    flight::GuardSettings guard;
    flight::Progress progress;
    flight::Scheduler scheduler;
    Session(const dynamics::World& w,std::span<const flight::StaticMeshSource> m,
            const flight::GuardSettings& g,flight::Progress p,flight::Settings s)
        :world(w),guard(g),progress(p),scheduler(s) {
        meshes.reserve(m.size());for(const auto& mesh:m) {meshes.push_back(mesh);}
    }
};
Snapshot::Snapshot(Token t,const dynamics::World& w,std::span<const flight::StaticMeshSource> m,
                   const flight::GuardSettings& g,flight::Progress p,flight::Snapshot s)
    :token(t),world(w),guard(g),progress(p),scheduler(s) {
    meshes.reserve(m.size());for(const auto& mesh:m) {meshes.push_back(mesh);}
}
Registry::Registry(RegistrySettings settings):settings_(settings) {
    if(settings.generation_limit==0||settings.generation_limit>maximum_generation) {
        throw std::invalid_argument("Session generation limit outside finite unsigned domain");
    }
}
Registry::~Registry() noexcept {static_assert(std::is_nothrow_destructible_v<Session>);}
Status Registry::validate(Token token) const noexcept {
    if(token.slot>=slots_.size()) {return Status::slot_range;}
    const auto& slot=slots_[token.slot];
    if(token.generation==0||token.generation!=slot.generation) {return Status::stale_generation;}
    if(!slot.active) {return Status::not_alive;}
    return Status::ok;
}
Created Registry::create(const dynamics::World& world,std::span<const flight::StaticMeshSource> meshes,
                         const flight::GuardSettings& guard,flight::Progress progress,flight::Settings settings) noexcept {
    if(busy_) {return {Status::busy,{}};}
    const Busy busy(busy_);
    if(!bounded(world,meshes)) {return {Status::source_counts,{}};}
    std::size_t index=0;
    while(index<slots_.size()&&(slots_[index].active||slots_[index].generation>=settings_.generation_limit)) {++index;}
    if(index==slots_.size()) {return {Status::no_free_slot,{}};}
    try {
        auto staged=std::make_unique<Session>(world,meshes,guard,progress,settings);
        auto& slot=slots_[index];
        // All throwing work precedes publication. No wrap or partial owner.
        slot.active.swap(staged);++slot.generation;
        return {Status::ok,{static_cast<std::uint32_t>(index),slot.generation}};
    }catch(const std::bad_alloc&) {return {Status::allocation_failure,{}};}
    catch(const std::invalid_argument&) {return {Status::invalid_settings,{}};}
    catch(...) {return {Status::unexpected_exception,{}};}
}
Created Registry::reset(Token token,const dynamics::World& world,std::span<const flight::StaticMeshSource> meshes,
                        const flight::GuardSettings& guard,flight::Progress progress,flight::Settings settings) noexcept {
    if(busy_) {return {Status::busy,{}};}
    const Busy busy(busy_);
    const auto status=validate(token);if(status!=Status::ok) {return {status,{}};}
    auto& slot=slots_[token.slot];
    if(slot.generation>=settings_.generation_limit) {return {Status::generation_exhausted,{}};}
    if(!bounded(world,meshes)) {return {Status::source_counts,{}};}
    try {
        auto staged=std::make_unique<Session>(world,meshes,guard,progress,settings);
        slot.active.swap(staged);++slot.generation;
        return {Status::ok,{token.slot,slot.generation}};
    }catch(const std::bad_alloc&) {return {Status::allocation_failure,{}};}
    catch(const std::invalid_argument&) {return {Status::invalid_settings,{}};}
    catch(...) {return {Status::unexpected_exception,{}};}
}
Status Registry::destroy(Token token) noexcept {
    if(busy_) {return Status::busy;}
    const Busy busy(busy_);
    const auto status=validate(token);if(status!=Status::ok) {return status;}
    // Inactive slots reject immediately; reuse increments the old generation.
    // An inactive slot already at the configured limit stays permanently retired.
    slots_[token.slot].active.reset();return Status::ok;
}
Read Registry::read(Token token) noexcept {
    Read out;
    if(busy_) {out.status=Status::busy;return out;}
    const Busy busy(busy_);
    out.status=validate(token);if(out.status!=Status::ok) {return out;}
    const auto& session=*slots_[token.slot].active;
    try {
        out.snapshot.emplace(token,session.world,session.meshes,session.guard,session.progress,session.scheduler.snapshot());
        out.status=Status::ok;
    }catch(const std::bad_alloc&) {out.status=Status::allocation_failure;}
    catch(...) {out.status=Status::unexpected_exception;}
    return out;
}
Pump Registry::pump(Token token,const Request& request) noexcept {
    Pump out;out.token=token;
    if(busy_) {out.status=Status::busy;return out;}
    const Busy busy(busy_);
    out.status=validate(token);if(out.status!=Status::ok) {return out;}
    if(request.owner.slot!=token.slot) {out.status=Status::foreign_session;return out;}
    if(request.owner.generation!=token.generation) {out.status=Status::stale_generation;return out;}
    auto& session=*slots_[token.slot].active;
    // No catch around the actual call or its already-committed successful prefix.
    // No allocating outer getter/log is created after the call. Report move is
    // statically nothrow. Owner success says the call ran, not that a tick advanced.
    out.report.emplace(session.scheduler.pump(session.world,session.meshes,session.guard,session.progress,request.elapsed,request.packets));
    out.scheduler_calls=1;out.status=Status::ok;return out;
}
}
