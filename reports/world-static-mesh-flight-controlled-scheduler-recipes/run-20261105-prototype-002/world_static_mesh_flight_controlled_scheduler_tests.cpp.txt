#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace {
namespace s=pikapika::world_static_mesh_flight_controlled_scheduler;
namespace c=s::controlled;
namespace f=controlled_tick_fixture;
void need(bool ok,const char* text) {if(!ok) {throw std::runtime_error(text);}}
std::uint64_t bits(double x) {return std::bit_cast<std::uint64_t>(x);}
std::string world(const pikapika::dynamics::World& w) {
    c::WorldState x;x.gravity=w.gravity;x.bodies=w.bodies();x.planes=w.planes();
    std::ostringstream out;out.imbue(std::locale::classic());f::world_state_json(out,x);return out.str();
}
c::TickLoadPacket load(const f::Case& x,double force,std::uint64_t tick) {
    auto p=x.packet;p.expected_tick=tick;p.loads[0].force_newtons={force,-0.,0.};p.loads[0].torque_newton_meters={-0.,0.,-0.};return p;
}
void body(const f::Case& x,double position,double velocity,std::uint64_t ticks) {
    const auto* b=x.scene.world.find_body(101);need(b&&b->position.x==position&&b->velocity.x==velocity&&x.progress.ticks==ticks,"Actual dyadic World/Progress mismatch");
    need(bits(b->force.x)==0&&bits(b->force.y)==0&&bits(b->torque.x)==0,"Successful loads not consumed as +0");
}
void envelope(const s::PumpReport& r) {
    need(r.elapsed_accepted&&r.capture==s::CaptureState::complete&&r.original&&r.packets_consumed==r.committed_ticks,"Admission/owned input/consumption mismatch");
    need(r.attempts<=r.planned_attempts&&r.boundary_count==r.attempts+1&&r.boundary_count==r.work.boundary_captures,"Actual child boundary accounting");
    need(bits(r.dropped_seconds)==0&&r.upper_budget.attempts==r.planned_attempts,"Dropped time or wrong reservation");
    need(r.storage.boundary_slots==9&&r.storage.boundary_sizeof_bytes==sizeof(r.boundaries),"Named fixed buffer sizeof");
    std::size_t commits=0;
    for(std::size_t i=0;i<r.attempts;++i) {
        need(r.tick_reports[i]&&r.tick_reports[i]->queue_index==i&&r.tick_reports[i]->packet_ordinal==i,"Actual indexed child missing");
        const auto& t=*r.tick_reports[i];need(t.credit_consumed==t.report.committed&&t.packet_consumed==t.report.committed,"Private/external controlled success confused");
        commits+=t.report.committed?1:0;
    }
    need(commits==r.committed_ticks,"Committed prefix counter");
    for(std::size_t i=0;i<r.boundary_count;++i) {
        need(r.boundaries[i].has_value(),"Actual boundary missing");const auto& b=*r.boundaries[i];
        for(std::size_t j=0;j<b.world.body_count;++j) {need(b.original_body_address_same[j],"External body address changed");}
    }
    need(r.boundaries[0]->progress.ticks==r.progress_before.ticks&&r.boundaries[r.boundary_count-1]->progress.ticks==r.progress_after.ticks,"Actual initial/final Progress boundaries");
}
unsigned directed() {
    unsigned groups=0;
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,4,17),load(x,-4,18)};
        const auto* address=x.scene.world.find_body(101);auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.status==s::Status::waiting&&r.committed_ticks==2&&r.attempts==2&&r.after.backlog==0&&r.before.sequence==0&&r.after.sequence==1,"Two actual controlled ticks/accounting");
        body(x,1.0/128,0,19);need(x.scene.world.find_body(101)==address,"Body pointer not retained");
        need(r.boundaries[0]->world.bodies[0].force.x==3&&r.boundaries[1]->world.bodies[0].position.x==1.0/256,"Original force/private progress snapshots");
        need(bits(r.boundaries[0]->world.gravity.x)==bits(-0.)&&bits(r.boundaries[0]->world.bodies[0].force.y)==bits(-0.),"Original negative zero lost");
        p[0].loads[0].force_newtons.x=99;x.scene.meshes[0].triangles[0].vertices[0].x=99;
        need(r.original->packets[0].loads[0].force_newtons.x==4&&r.original->meshes[0].triangles[0].vertices[0].x==-64,"Captured source aliases caller");
        need(r.tick_reports[0]->report.original&&r.tick_reports[0]->report.original->packet.loads[0].force_newtons.x==4,"Actual controlled report missing");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,4,17)};
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.status==s::Status::awaiting_input&&r.planned_attempts==2&&r.attempts==1&&r.packets_consumed==1&&r.after.backlog==1.0/16&&!r.tick_reports[1],"Missing input fabricated a second tick");body(x,1.0/256,1.0/8,18);
        p={load(x,-4,18)};r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);
        need(r.committed_ticks==1&&r.after.backlog==0&&r.before.backlog==1.0/16&&r.after.sequence==2,"Retry0 lost/doubled credit");body(x,1.0/128,0,19);++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});auto bad=load(x,0,18);bad.loads[0].force_newtons={0,-4096,0};
        std::vector<c::TickLoadPacket> p{load(x,4,17),bad};auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.status==s::Status::tick_rejected&&r.attempts==2&&r.committed_ticks==1&&r.after.backlog==1.0/16,"Guard rejection lost success prefix/credit");
        need(!r.tick_reports[1]->report.committed&&r.tick_reports[1]->report.status==c::Status::not_certified,"Not actual guard refusal");
        need(r.boundaries[1]->world.bodies[0].position.x==r.boundaries[2]->world.bodies[0].position.x,"Refused controlled child changed external state");body(x,1.0/256,1.0/8,18);
        p={load(x,-4,18)};r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);body(x,1.0/128,0,19);++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,4,17)};
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);const auto original=world(x.scene.world);
        r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);
        need(r.status==s::Status::tick_rejected&&r.committed_ticks==0&&r.after.backlog==1.0/16&&r.tick_reports[0]->report.reason==c::Reason::expected_tick&&r.tick_reports[0]->report.work.child_attempts==0,"Stale input accepted/requeried");
        need(world(x.scene.world)==original&&x.progress.ticks==18,"Stale retry changed World/clock");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});auto bad=load(x,-4,18);bad.mode=static_cast<c::LoadMode>(99);
        std::vector<c::TickLoadPacket> p{load(x,4,17),bad};auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.committed_ticks==1&&r.tick_reports[1]->report.reason==c::Reason::packet_mode&&r.tick_reports[1]->report.work.child_attempts==0,"Invalid second packet invalidated prefix or was repaired");body(x,1.0/256,1.0/8,18);++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});auto bad=load(x,0,999);bad.mode=static_cast<c::LoadMode>(99);std::vector<c::TickLoadPacket> p{bad};const auto original=world(x.scene.world);
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);
        need(r.status==s::Status::waiting&&r.attempts==0&&r.packets_consumed==0&&r.original->packets[0].expected_tick==999&&world(x.scene.world)==original,"Unused future packet applied/validated/repaired");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,1});std::vector<c::TickLoadPacket> p{load(x,4,17),load(x,-4,18)};
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.status==s::Status::step_budget&&r.planned_attempts==1&&r.committed_ticks==1&&r.after.backlog==1.0/16,"Step budget dropped/reused packet");
        p.erase(p.begin());r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);body(x,1.0/128,0,19);++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p;const auto original=world(x.scene.world);
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);envelope(r);
        need(r.status==s::Status::awaiting_input&&r.attempts==0&&r.planned_attempts==2&&r.after.backlog==.125&&world(x.scene.world)==original,"Empty input generated zero-force ticks");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p;
        for(std::uint64_t i=0;i<8;++i) {p.push_back(load(x,0,17+i));}
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.5,p);envelope(r);
        need(r.attempts==8&&r.committed_ticks==8&&r.boundary_count==9&&r.after.backlog==0&&x.progress.ticks==25,"Maximum slots/prefix failed");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p(9,x.packet);const auto original=world(x.scene.world);
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);
        need(r.reason==s::Reason::packet_count&&r.capture==s::CaptureState::none&&!r.elapsed_accepted&&r.attempts==0&&q.snapshot().sequence==0&&world(x.scene.world)==original,"Hard count9 admitted/captured/mutated");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,4,17),load(x,-4,18)};p[1].loads.resize(9);
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);
        need(r.reason==s::Reason::packet_load_count&&r.capture==s::CaptureState::none&&!r.elapsed_accepted&&r.attempts==0,"Unbounded unused packet load capture");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,0,17)};const auto original=world(x.scene.world);
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,-1,p);
        need(r.reason==s::Reason::elapsed&&!r.elapsed_accepted&&r.capture==s::CaptureState::complete&&r.original&&r.boundary_count==1&&world(x.scene.world)==original,"Invalid elapsed changed state or fabricated admission");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p;
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,1,p);envelope(r);need(q.snapshot().backlog==1,"Initial backlog1 failed");
        r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,1.0/16,p);
        need(r.reason==s::Reason::backlog_limit&&!r.elapsed_accepted&&q.snapshot().backlog==1&&q.snapshot().sequence==1,"Backlog overflow admitted/dropped prior credit");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});std::vector<c::TickLoadPacket> p{load(x,0,17)};const auto old=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Cannot set rounding test");
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);need(std::fesetround(old)==0,"Cannot restore rounding");
        need(r.reason==s::Reason::environment&&r.capture==s::CaptureState::none&&!r.elapsed_accepted&&r.attempts==0,"Environment was not first numerical gate");++groups;
    }
    {
        auto x=f::base_case();s::Scheduler q({1.0/16,8});const auto nan=std::bit_cast<double>(0x7ff8000000001234ULL);std::vector<c::TickLoadPacket> p{load(x,0,17)};p[0].loads[0].force_newtons.x=nan;
        auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0,p);envelope(r);
        need(r.attempts==0&&bits(r.original->packets[0].loads[0].force_newtons.x)==bits(nan),"Unused raw nonfinite packet changed/applied");
        r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,1.0/16,p);envelope(r);
        need(r.status==s::Status::tick_rejected&&r.tick_reports[0]->report.reason==c::Reason::packet_load&&r.committed_ticks==0&&x.progress.ticks==17&&x.scene.world.find_body(101)->force.x==3,"Actual nonfinite packet was repaired/applied");++groups;
    }
    for(const s::Settings invalid:std::vector<s::Settings>{{0,1},{.2,1},{s::clock::minimum_step/2,1},{.0625,0},{.0625,9},{std::numeric_limits<double>::quiet_NaN(),1}}) {
        bool rejected=false;try {s::Scheduler q(invalid);(void)q;}catch(const std::invalid_argument&) {rejected=true;}need(rejected,"Invalid immutable settings accepted");++groups;
    }
    return groups;
}
void unsupported() {
    auto x=f::base_case();s::Scheduler q({.0625,8});std::vector<c::TickLoadPacket> p{load(x,4,17)};const auto original=world(x.scene.world);
    need(!s::current_binding().configured,"Expected genuine default-refusal build");auto r=q.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,.125,p);
    need(r.reason==s::Reason::binding_unsupported&&r.capture==s::CaptureState::none&&r.attempts==0&&!r.elapsed_accepted&&world(x.scene.world)==original&&q.snapshot().sequence==0,"Default profile changed input or clock");
}
}
int main(int argc,char** argv) {
    try {
        const std::string_view mode=argc==2?argv[1]:"--run";
        if(mode=="--unsupported-profile") {unsupported();std::cout<<"Controlled scheduler default profile refusal PASS.\n";return 0;}
        need(mode=="--run"&&s::current_binding().configured,"Configured isolated Native test required");
        const auto groups=directed();std::cout<<"Controlled scheduler: "<<groups<<" directed groups PASS; isolated MSVC assertions only, full owned fixture/independent reference/GNU/SDK pending.\n";
        return 0;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
