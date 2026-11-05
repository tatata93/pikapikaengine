#include "pikapika/world_static_mesh_session.hpp"
#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <bit>
#include <cfenv>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace {
namespace s=pikapika::world_static_mesh_session;
namespace q=s::flight;
namespace c=q::controlled;
namespace f=controlled_tick_fixture;
void need(bool ok,const char* message) {if(!ok) {throw std::runtime_error(message);}}
std::uint64_t bits(double x) {return std::bit_cast<std::uint64_t>(x);}
std::string world(const pikapika::dynamics::World& w) {
    c::WorldState value;value.gravity=w.gravity;value.bodies=w.bodies();value.planes=w.planes();
    std::ostringstream out;out.imbue(std::locale::classic());f::world_state_json(out,value);return out.str();
}
s::Token create(s::Registry& registry,const f::Case& x) {
    auto r=registry.create(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,{.0625,8});
    need(r.status==s::Status::ok&&r.token.generation>0,"Actual owned create failed");return r.token;
}
s::Snapshot read(s::Registry& registry,s::Token token) {
    auto r=registry.read(token);need(r.status==s::Status::ok&&r.snapshot.has_value(),"Actual owned read failed");return std::move(*r.snapshot);
}
c::TickLoadPacket load(const f::Case& x,double force,std::uint64_t tick) {
    auto p=x.packet;p.expected_tick=tick;p.loads[0].force_newtons={force,-0.,0.};p.loads[0].torque_newton_meters={-0.,0.,-0.};return p;
}
void rejected(const s::Pump& p,s::Status status) {
    need(p.status==status&&p.scheduler_calls==0&&!p.report,"Owner refusal called/created a model report");
}
void body(const s::Snapshot& snapshot,double position,double velocity,std::uint64_t ticks) {
    const auto* b=snapshot.world.find_body(101);
    need(b&&b->position.x==position&&b->velocity.x==velocity&&snapshot.progress.ticks==ticks,"Actual owned dyadic body/progress mismatch");
}
unsigned lifecycle() {
    unsigned groups=0;
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);auto initial=read(registry,token);const auto raw=world(initial.world);
        x.scene.world.find_body(101)->position.x=77;x.scene.world.gravity.x=88;x.scene.meshes[0].triangles[0].vertices[0].x=99;x.scene.settings.contact_margin=.1;
        auto current=read(registry,token);need(world(current.world)==raw&&current.meshes[0].triangles[0].vertices[0].x==-64&&current.guard.contact_margin==0,"Owner aliases caller input");
        need(bits(current.world.gravity.x)==bits(-0.)&&bits(current.world.bodies()[0].force.y)==bits(-0.),"Owned negative zero lost");
        initial.world.find_body(101)->position.x=123;initial.meshes[0].triangles[0].vertices[0].x=456;
        need(world(read(registry,token).world)==raw&&read(registry,token).meshes[0].triangles[0].vertices[0].x==-64,"Read aliases active owner");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto a=create(registry,x),b=create(registry,x);const auto before=read(registry,b);std::vector<c::TickLoadPacket> packets{load(x,4,17)};
        rejected(registry.pump(b,{a,.125,packets}),s::Status::foreign_session);
        const auto after=read(registry,b);need(world(before.world)==world(after.world)&&after.scheduler.sequence==0&&after.scheduler.backlog==0&&after.progress.ticks==17,"Foreign envelope changed target");
        need(read(registry,a).progress.ticks==17,"Foreign target advanced request origin");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);
        rejected(registry.pump({4,1},{token,1.,{}}),s::Status::slot_range);
        rejected(registry.pump({0,0},{token,1.,{}}),s::Status::stale_generation);
        need(registry.destroy(token)==s::Status::ok,"Destroy failed");
        rejected(registry.pump(token,{token,1.,{}}),s::Status::not_alive);
        need(registry.read(token).status==s::Status::not_alive&&registry.destroy(token)==s::Status::not_alive,"Dead owner remained reachable");
        auto next=create(registry,x);need(next.slot==token.slot&&next.generation==token.generation+1,"Reused slot did not advance generation");
        rejected(registry.pump(token,{token,0.,{}}),s::Status::stale_generation);
        rejected(registry.pump(next,{token,0.,{}}),s::Status::stale_generation);++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;std::array<s::Token,4> tokens;
        for(std::size_t i=0;i<tokens.size();++i) {tokens[i]=create(registry,x);need(tokens[i].slot==i,"Deterministic fixed slot order changed");}
        auto extra=registry.create(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,{.0625,8});need(extra.status==s::Status::no_free_slot,"Session hard cap bypassed");
        for(auto token:tokens) {need(read(registry,token).progress.ticks==17,"Capacity refusal destroyed an owner");}++groups;
    }
    {
        auto x=f::base_case();s::Registry registry({1});
        for(std::size_t i=0;i<4;++i) {auto token=create(registry,x);need(token.slot==i&&token.generation==1,"Retired slot was reused");need(registry.destroy(token)==s::Status::ok,"Retire destroy failed");}
        need(registry.create(x.scene.world,x.scene.meshes,x.scene.settings,x.progress).status==s::Status::no_free_slot,"Generation wrapped or retired slot revived");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry({2});auto token=create(registry,x);
        auto reset=registry.reset(token,x.scene.world,x.scene.meshes,x.scene.settings,x.progress,{.0625,8});need(reset.status==s::Status::ok&&reset.token.generation==2,"Reset generation did not advance");
        auto before=read(registry,reset.token);auto blocked=registry.reset(reset.token,x.scene.world,x.scene.meshes,x.scene.settings,x.progress,{.0625,8});
        need(blocked.status==s::Status::generation_exhausted&&world(read(registry,reset.token).world)==world(before.world),"Generation overflow changed owner");
        need(registry.destroy(reset.token)==s::Status::ok&&create(registry,x).slot==1,"Saturated slot did not retire");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);const auto before=read(registry,token);
        auto bad=registry.reset(token,x.scene.world,x.scene.meshes,x.scene.settings,x.progress,{0.,8});need(bad.status==s::Status::invalid_settings,"Invalid reset clock accepted");
        auto after=read(registry,token);need(world(after.world)==world(before.world)&&after.token==before.token&&after.scheduler.sequence==0,"Failed staging altered active owner");++groups;
    }
    for(unsigned kind=0;kind<4;++kind) {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);const auto before=read(registry,token);
        if(kind==0) {for(std::uint64_t i=0;i<8;++i) {auto b=x.scene.world.bodies()[0];b.id=1000+i;x.scene.world.add_body(b);}}
        if(kind==1) {for(std::uint64_t i=0;i<16;++i) {auto p=x.scene.world.planes()[0];p.id=2000+i;x.scene.world.add_plane(p);}}
        if(kind==2) {while(x.scene.meshes.size()<5) {auto m=x.scene.meshes[0];m.id+=x.scene.meshes.size();x.scene.meshes.push_back(std::move(m));}}
        if(kind==3) {while(x.scene.meshes[0].triangles.size()<65) {auto t=x.scene.meshes[0].triangles[0];t.id+=x.scene.meshes[0].triangles.size();x.scene.meshes[0].triangles.push_back(t);}}
        need(registry.reset(token,x.scene.world,x.scene.meshes,x.scene.settings,x.progress).status==s::Status::source_counts,"Hard count reset accepted");
        need(registry.create(x.scene.world,x.scene.meshes,x.scene.settings,x.progress).status==s::Status::source_counts,"Hard count create accepted");
        need(world(read(registry,token).world)==world(before.world),"Hard count refusal changed active world");++groups;
    }
    for(auto limit:{std::uint64_t{0},s::maximum_generation+1}) {
        bool refused=false;try {s::Registry registry({limit});}catch(const std::invalid_argument&) {refused=true;}need(refused,"Invalid registry limit accepted");++groups;
    }
    return groups;
}
unsigned numerical() {
    unsigned groups=0;
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);auto initial=read(registry,token);std::vector<c::TickLoadPacket> packets{load(x,4,17),load(x,-4,18)};
        auto r=registry.pump(token,{token,.125,packets});need(r.status==s::Status::ok&&r.scheduler_calls==1&&r.report&&r.report->committed_ticks==2&&r.report->attempts==2,"Actual two-tick delegation failed");
        body(read(registry,token),1./128,0,19);body(initial,0,0,17);need(initial.world.bodies()[0].force.x==3,"Old snapshot was mutated by pump");
        auto after=read(registry,token);need(bits(after.world.bodies()[0].force.x)==0&&bits(after.world.bodies()[0].force.y)==0,"Owned successful load not consumed");
        packets[0].loads[0].force_newtons.x=99;need(r.report->original->packets[0].loads[0].force_newtons.x==4,"Actual returned report aliases request");
        need(registry.destroy(token)==s::Status::ok&&r.report->boundaries[2]->progress.ticks==19,"Actual report did not survive owner destruction");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);std::vector<c::TickLoadPacket> packets{load(x,4,17),load(x,0,18)};packets[1].loads[0].force_newtons.y=-4096;
        auto r=registry.pump(token,{token,.125,packets});need(r.status==s::Status::ok&&r.report&&r.report->status==q::Status::tick_rejected&&r.report->committed_ticks==1&&r.report->attempts==2,"Success prefix hidden by owner");
        body(read(registry,token),1./256,1./8,18);need(read(registry,token).scheduler.backlog==.0625,"Rejected tick consumed owned credit");
        std::vector<c::TickLoadPacket> retry{load(x,-4,18)};auto next=registry.pump(token,{token,0.,retry});need(next.report&&next.report->committed_ticks==1,"Owned retry0 failed");body(read(registry,token),1./128,0,19);++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);std::vector<c::TickLoadPacket> one{load(x,4,17)};
        auto r=registry.pump(token,{token,.125,one});need(r.report&&r.report->status==q::Status::awaiting_input&&r.report->committed_ticks==1,"Owned shortage duplicated last force");
        auto replacement=f::base_case();replacement.scene.world.find_body(101)->position.x=10;replacement.progress={.5,100};
        auto changed=registry.reset(token,replacement.scene.world,replacement.scene.meshes,replacement.scene.settings,replacement.progress,{.0625,8});need(changed.status==s::Status::ok&&changed.token.slot==token.slot&&changed.token.generation==token.generation+1,"Owned reset failed");
        const auto after=read(registry,changed.token);body(after,10,0,100);need(after.scheduler.backlog==0&&after.scheduler.sequence==0,"Reset retained old credit/clock");
        rejected(registry.pump(changed.token,{token,1.,one}),s::Status::stale_generation);rejected(registry.pump(token,{token,1.,one}),s::Status::stale_generation);
        need(r.report->boundaries[1]->progress.ticks==18,"Past actual report changed on reset");++groups;
    }
    {
        auto x=f::base_case();const auto nan=std::bit_cast<double>(0x7ff8000000001234ULL);x.scene.world.gravity.x=nan;s::Registry registry;auto token=create(registry,x);
        need(bits(read(registry,token).world.gravity.x)==bits(nan),"Owner repaired raw invalid numeric input");std::vector<c::TickLoadPacket> packets{load(x,4,17)};
        auto r=registry.pump(token,{token,.0625,packets});need(r.status==s::Status::ok&&r.report&&r.report->committed_ticks==0&&read(registry,token).progress.ticks==17,"Owner creation was confused with model acceptance");++groups;
    }
    {
        auto x=f::base_case();s::Registry registry;auto token=create(registry,x);const auto old=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Cannot set upward rounding");
        auto r=registry.pump(token,{token,.0625,{}});need(std::fesetround(old)==0,"Cannot restore rounding");
        need(r.status==s::Status::ok&&r.report&&r.report->status==q::Status::unsupported_environment&&!r.report->elapsed_accepted&&read(registry,token).scheduler.sequence==0,"Owner bypassed actual FP gate");++groups;
    }
    return groups;
}
void default_profile() {
    need(!q::current_binding().configured,"Expected actual default upstream library");auto x=f::base_case();s::Registry registry;auto token=create(registry,x);const auto before=read(registry,token);std::vector<c::TickLoadPacket> packets{load(x,4,17)};
    auto r=registry.pump(token,{token,.125,packets});need(r.status==s::Status::ok&&r.scheduler_calls==1&&r.report&&r.report->reason==q::Reason::binding_unsupported&&!r.report->elapsed_accepted,"Owner bypassed actual default refusal");
    need(world(read(registry,token).world)==world(before.world)&&read(registry,token).scheduler.sequence==0,"Default model refusal altered owner");
}
}
int main(int argc,char** argv) {
    try {
        const std::string_view mode=argc==2?argv[1]:"--run";
        if(mode=="--unsupported-profile") {default_profile();std::cout<<"Owned session actual default model refusal PASS.\n";return 0;}
        need(mode=="--run"&&q::current_binding().configured,"Actual configured upstream required");
        const auto a=lifecycle(),b=numerical();std::cout<<"Owned session: "<<a<<" lifecycle and "<<b<<" actual numerical groups PASS. Isolated MSVC only; full transcript/reference, GNU, busy/fault injection and SDK pending.\n";return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
