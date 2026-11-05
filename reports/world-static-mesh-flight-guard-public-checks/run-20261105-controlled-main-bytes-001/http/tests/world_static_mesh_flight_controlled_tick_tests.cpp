#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <array>
#include <bit>
#include <cfenv>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace {
namespace c=pikapika::world_static_mesh_flight_controlled_tick;
namespace f=controlled_tick_fixture;
namespace d=pikapika::dynamics;
using Bits=std::vector<std::uint64_t>;
void need(bool condition,const char* text) {if(!condition) {throw std::runtime_error(text);}}
std::uint64_t bits(double x) noexcept {return std::bit_cast<std::uint64_t>(x);}
Bits raw_world(const d::World& w) {
    Bits out{bits(w.gravity.x),bits(w.gravity.y),bits(w.gravity.z)};
    for(const auto& b:w.bodies()) {
        out.push_back(b.id);out.push_back(b.is_static?1ULL:0ULL);
        const std::array<double,26> fields{b.mass,b.radius,b.inertia_diagonal.x,b.inertia_diagonal.y,b.inertia_diagonal.z,
            b.position.x,b.position.y,b.position.z,b.orientation.x,b.orientation.y,b.orientation.z,b.orientation.w,
            b.velocity.x,b.velocity.y,b.velocity.z,b.angular_momentum.x,b.angular_momentum.y,b.angular_momentum.z,
            b.force.x,b.force.y,b.force.z,b.torque.x,b.torque.y,b.torque.z,b.material.restitution,b.material.friction};
        for(auto x:fields) {out.push_back(bits(x));}
    }
    for(const auto& p:w.planes()) {out.push_back(p.id);for(auto x:std::array{p.normal.x,p.normal.y,p.normal.z,p.offset,p.material.restitution,p.material.friction}) {out.push_back(bits(x));}}
    return out;
}
std::string report_text(const c::ControlledReport& r) {std::ostringstream out;out.imbue(std::locale::classic());f::report_json(out,r);return out.str();}
void exact_failure(const f::Case& x,const Bits& before,c::advance::Progress progress,const c::ControlledReport& r) {
    need(raw_world(x.scene.world)==before&&bits(x.progress.time)==bits(progress.time)&&x.progress.ticks==progress.ticks,"Failure changed original World/Progress bits");
    need(!r.committed&&bits(r.advanced_dt)==0&&r.work.body_assignments==0&&r.work.progress_assignments==0,"Failure falsely published external assignments");
}
unsigned test_cases() {
    unsigned groups=0;
    for(auto x:f::cases()) {
        const auto before=raw_world(x.scene.world);const auto p=x.progress;
        std::vector<const d::RigidBody*> addresses;for(const auto& b:x.scene.world.bodies()) {addresses.push_back(&b);}
        auto r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
        if(x.expected&&r.status!=*x.expected) {throw std::runtime_error("Status mismatch: "+x.name);}
        if(x.reason&&r.reason!=*x.reason) {throw std::runtime_error("Reason mismatch: "+x.name);}
        need(r.work.child_attempts<=1&&r.work.child_returns<=r.work.child_attempts,"Child called repeatedly");
        need(addresses.size()==x.scene.world.bodies().size(),"Body count changed");
        for(std::size_t i=0;i<addresses.size();++i) {need(addresses[i]==&x.scene.world.bodies()[i],"Original body address moved");}
        if(!r.committed) {exact_failure(x,before,p,r);}
        else {
            need(r.status==c::Status::committed&&r.reason==c::Reason::none&&r.child&&r.child->committed&&r.private_after&&r.work.child_attempts==1&&r.work.child_returns==1,"Incomplete controlled success");
            need(r.work.body_assignments==x.scene.world.bodies().size()&&r.work.progress_assignments==1&&x.progress.ticks==p.ticks+1,"Commit count/progress");
            for(const auto& b:x.scene.world.bodies()) {need(bits(b.force.x)==0&&bits(b.force.y)==0&&bits(b.force.z)==0&&bits(b.torque.x)==0&&bits(b.torque.y)==0&&bits(b.torque.z)==0,"Successful loads not positive zero");}
        }
        const auto document=report_text(r);world_advance_fixture::validate_document(document);++groups;
    }
    return groups;
}
unsigned test_directed() {
    auto x=f::base_case();x.packet.loads[0].force_newtons={4,0,0};
    auto r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.committed&&x.scene.world.find_body(101)->position.x==1.0/256&&x.scene.world.find_body(101)->velocity.x==1.0/8,"Analytic first held-load tick");
    x.packet.expected_tick=x.progress.ticks;x.packet.loads[0].force_newtons={-4,0,0};
    r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.committed&&x.scene.world.find_body(101)->position.x==1.0/128&&x.scene.world.find_body(101)->velocity.x==0,"Analytic second opposite load");
    const auto now=raw_world(x.scene.world);const auto p=x.progress;
    r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.reason==c::Reason::expected_tick&&r.work.child_attempts==0,"Successful packet replay not rejected");exact_failure(x,now,p,r);
    x=f::base_case();x.packet.loads[0].force_newtons={0,-4096,0};
    r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(!r.committed&&r.status==c::Status::not_certified&&x.progress.ticks==17,"Directed initial guard refusal");
    x.packet.loads[0].force_newtons={0,-0.,0};
    r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.committed&&x.progress.ticks==18,"Refused packet retry at same tick failed");
    x=f::base_case();x.packet.loads[0].force_newtons={5,-0.,0};
    r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.committed&&r.original&&r.staged_before&&r.child&&r.child->guard&&r.child->guard->preparation&&r.child->guard->preparation->snapshot,"Replacement origin unavailable");
    need(r.original->world.bodies[0].force.x==3&&r.staged_before->bodies[0].force.x==5&&r.child->guard->preparation->snapshot->bodies[0].force.x==5,"Replacement added/inherited original load or relabeled guard");
    const auto frozen=report_text(r);
    x.packet.loads[0].force_newtons={99,1,2};x.scene.world.find_body(101)->position.x=100;x.scene.meshes[0].triangles[0].vertices[0].x=200;x.scene.settings.contact_margin=.1;
    need(report_text(r)==frozen,"Returned Report aliases caller input/World/source/settings");
    auto altered=f::base_case();auto invalid_report=c::advance_with_loads(altered.scene.world,altered.scene.meshes,altered.scene.horizon,altered.scene.settings,altered.progress,altered.packet);
    invalid_report.status=static_cast<c::Status>(42);bool refused=false;
    try {const auto unused=report_text(invalid_report);(void)unused;}catch(const std::runtime_error&) {refused=true;}
    need(refused,"Unknown result enum writer accepted");
    return 6;
}
void hex(std::ostream& out,std::uint64_t x) {out<<'"'<<std::hex<<std::setw(16)<<std::setfill('0')<<x<<std::dec<<'"';}
void words(std::ostream& out,const Bits& b) {out<<'[';for(std::size_t i=0;i<b.size();++i) {if(i) {out<<',';}hex(out,b[i]);}out<<']';}
unsigned unit_raw(std::ostream* output) {
    const auto nan=std::bit_cast<double>(0x7ff8000000001234ULL);std::ostringstream out;out.imbue(std::locale::classic());out<<"{\"schema\":1,\"kind\":\"controlled-tick-unit-raw-observations\",\"scope\":\"Nonfinite raw inputs are unit-only. No fabricated finite child JSON; old finite writer refusal measured. No allocation/nonreturn/post-child fault injection.\",\"cases\":[";
    for(unsigned i=0;i<4;++i) {
        auto x=f::base_case();
        if(i==0) {x.scene.world.find_body(101)->force.x=nan;x.packet.loads[0].force_newtons={0,0,0};}
        if(i==1) {x.packet.loads[0].force_newtons.x=nan;}
        if(i==2) {x.scene.horizon=nan;}
        if(i==3) {x.progress.time=nan;}
        const auto before=raw_world(x.scene.world);const auto p=x.progress;
        const auto original_force=bits(x.scene.world.find_body(101)->force.x),packet_force=bits(x.packet.loads[0].force_newtons.x);
        auto r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
        exact_failure(x,before,p,r);
        need(r.capture==c::CaptureState::complete&&r.original,"Nonfinite raw source not captured");
        if(i==0) {need(r.reason==c::Reason::original_body&&!r.child&&bits(r.original->world.bodies[0].force.x)==original_force,"Original NaN repaired/lost");}
        if(i==1) {need(r.reason==c::Reason::packet_load&&!r.child&&bits(r.original->packet.loads[0].force_newtons.x)==packet_force,"Packet NaN lost/queried");}
        bool child_writer_refused=false;
        if(i>=2) {
            need(r.reason==c::Reason::child_failed&&r.child&&r.work.child_returns==1,"Nonfinite clock did not retain actual child");
            need(i==2?bits(r.child->requested_dt)==bits(nan):bits(r.child->original_progress.time)==bits(nan),"Actual child raw clock input changed");
            try {std::ostringstream text;world_advance_fixture::report_json(text,*r.child);}catch(const std::runtime_error&) {child_writer_refused=true;}
            need(child_writer_refused,"Old finite child writer accepted nonfinite clock");
        }
        if(i) {out<<',';}out<<"{\"ordinal\":"<<i<<",\"reason\":"<<static_cast<unsigned>(r.reason)<<",\"capture\":"<<static_cast<unsigned>(r.capture)<<",\"childPresent\":"<<(r.child?"true":"false")<<",\"oldChildWriterRefused\":"<<(child_writer_refused?"true":"false")<<",\"horizonBits\":";hex(out,bits(x.scene.horizon));out<<",\"progressTimeBits\":";hex(out,bits(p.time));out<<",\"originalForceXBits\":";hex(out,original_force);out<<",\"packetForceXBits\":";hex(out,packet_force);out<<",\"worldBeforeWords\":";words(out,before);out<<",\"worldAfterWords\":";words(out,raw_world(x.scene.world));out<<'}';
    }
    out<<"]}\n";if(output) {*output<<out.str();}return 4;
}
unsigned environment_test() {
    auto x=f::base_case();const auto before=raw_world(x.scene.world);const auto p=x.progress;
    const auto old=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Cannot set directed rounding test");
    auto r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(std::fesetround(old)==0,"Cannot restore rounding");
    need(r.status==c::Status::unsupported_environment&&r.reason==c::Reason::environment&&r.capture==c::CaptureState::none&&r.work.child_attempts==0,"Environment was not first");exact_failure(x,before,p,r);return 1;
}
void unsupported() {
    auto x=f::base_case();const auto before=raw_world(x.scene.world);const auto p=x.progress;
    need(!c::current_binding().configured,"This executable is configured, not refusal profile");
    auto r=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
    need(r.reason==c::Reason::binding_unsupported&&r.capture==c::CaptureState::none&&r.work.child_attempts==0,"Default profile did not refuse before capture/query");exact_failure(x,before,p,r);
}
}
int main(int argc,char** argv) {
    try {
        const std::string_view mode=argc==2?argv[1]:"--run";
        if(mode=="--unsupported-profile") {unsupported();std::cout<<"Controlled tick default profile refusal PASS; no new transaction acceptance.\n";return 0;}
        need(c::current_binding().configured,"Configured Native prototype required");
        if(mode=="--fixtures") {f::emit_fixtures(std::cout);return std::cout?0:1;}
        if(mode=="--unit-observations") {(void)unit_raw(&std::cout);return std::cout?0:1;}
        need(mode=="--run","Unknown controlled tick test mode");
        unsigned groups=test_cases();groups+=test_directed();groups+=unit_raw(nullptr);groups+=environment_test();
        std::cout<<"Controlled tick: "<<groups<<" directed groups PASS. Finite isolated Native prototype; no GNU, scheduler, SDK, whole clock/commit proof or natural fault injection.\n";return 0;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
