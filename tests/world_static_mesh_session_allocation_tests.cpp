// Test-only executable replacement of scalar/array global new. No production
// allocator or owner code is changed. This is controlled bad_alloc injection,
// not OS-wide OOM, aligned/CRT allocation interception or whole-heap proof.
#include "pikapika/world_static_mesh_session.hpp"
#include "world_static_mesh_flight_controlled_scheduler_fixture_support.hpp"
#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <bit>
#include <cstdlib>
#include <iostream>
#include <locale>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>

namespace allocation_probe {
struct State {bool active{};long long remaining=-1;std::size_t seen{};void (*callback)() noexcept=nullptr;};
constinit thread_local State state;
void begin(long long fail_after=-1,void (*callback)() noexcept=nullptr) noexcept {state={true,fail_after,0,callback};}
std::size_t end() noexcept {state.active=false;state.callback=nullptr;return state.seen;}
void* allocate(std::size_t size) {
    if(state.active) {
        ++state.seen;
        const auto callback=state.callback;state.callback=nullptr;
        if(callback) {callback();}
        if(state.remaining==0) {throw std::bad_alloc();}
        if(state.remaining>0) {--state.remaining;}
    }
    if(void* pointer=std::malloc(size==0?1:size)) {return pointer;}
    throw std::bad_alloc();
}
}
void* operator new(std::size_t n) {return allocation_probe::allocate(n);}
void* operator new[](std::size_t n) {return allocation_probe::allocate(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}

namespace {
namespace s=pikapika::world_static_mesh_session;
namespace q=s::flight;
namespace f=controlled_tick_fixture;
namespace codec=controlled_scheduler_fixture;
void need(bool ok,const char* message) {if(!ok) {throw std::runtime_error(message);}}
void flag(std::ostream& o,bool b) {o<<(b?"true":"false");}
std::string actual_read(const s::Read& value) {
    need(value.status==s::Status::ok&&value.snapshot.has_value(),"Actual public read failed outside injection");const auto& x=*value.snapshot;
    std::ostringstream o;o.imbue(std::locale::classic());o<<"{\"slot\":"<<x.token.slot<<",\"generation\":"<<x.token.generation<<",\"world\":";
    q::controlled::WorldState observed;observed.gravity=x.world.gravity;observed.bodies=x.world.bodies();observed.planes=x.world.planes();f::world_state_json(o,observed);
    o<<",\"meshes\":";codec::meshes_json(o,x.meshes);o<<",\"guard\":";world_guard_fixture::settings_json(o,x.guard);
    o<<",\"progressTimeBits\":"<<std::bit_cast<std::uint64_t>(x.progress.time)<<",\"ticks\":"<<x.progress.ticks<<",\"clock\":";codec::snapshot_json(o,x.scheduler);o<<'}';return o.str();
}
s::Token live(s::Registry& registry,const f::Case& source) {
    const auto made=registry.create(source.scene.world,source.scene.meshes,source.scene.settings,source.progress,{.0625,8});need(made.status==s::Status::ok,"Actual setup create failed");
    auto packet=source.packet;packet.loads[0].force_newtons={4,-0.,0.};std::vector<q::TickLoadPacket> packets{packet};
    const auto p=registry.pump(made.token,{made.token,.125,packets});need(p.status==s::Status::ok&&p.report&&p.report->committed_ticks==1&&p.report->status==q::Status::awaiting_input,"Nontrivial actual setup pump failed");
    auto state=registry.read(made.token);need(state.status==s::Status::ok&&state.snapshot&&state.snapshot->scheduler.backlog==.0625&&state.snapshot->scheduler.sequence==1&&state.snapshot->progress.ticks==18,"Actual setup credit/clock not retained");return made.token;
}
f::Case maximum_source() {
    auto x=f::base_case();
    for(std::uint64_t i=0;i<7;++i) {auto body=x.scene.world.bodies()[0];body.id=102+i;body.position.x=static_cast<double>(8*(i+1));x.scene.world.add_body(body);}
    for(std::uint64_t i=0;i<15;++i) {auto plane=x.scene.world.planes()[0];plane.id=202+i;x.scene.world.add_plane(plane);}
    while(x.scene.meshes.size()<4) {auto mesh=x.scene.meshes[0];mesh.id+=x.scene.meshes.size();x.scene.meshes.push_back(std::move(mesh));}
    for(auto& mesh:x.scene.meshes) {while(mesh.triangles.size()<16) {auto face=mesh.triangles[0];face.id+=mesh.triangles.size();mesh.triangles.push_back(face);}}
    x.scene.world.find_body(101)->position.x=10;x.progress={.5,100};return x;
}
enum class Operation {create,reset,read};
const char* operation_name(Operation value) {switch(value) {case Operation::create:return "create";case Operation::reset:return "reset";case Operation::read:return "read";}return "unknown";}
s::Token prepare(Operation operation,s::Registry& registry,const f::Case& base,const f::Case& maximum) {
    auto token=live(registry,base);
    if(operation==Operation::read) {
        const auto reset=registry.reset(token,maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});need(reset.status==s::Status::ok,"Actual maximum read setup reset failed");token=reset.token;
        auto waiting=registry.pump(token,{token,.03125,{}});need(waiting.status==s::Status::ok&&waiting.report&&waiting.report->elapsed_accepted&&waiting.report->attempts==0&&waiting.report->after.backlog==.03125,"Actual maximum read setup credit failed");
    }
    return token;
}
std::size_t measure(Operation operation,const f::Case& base,const f::Case& maximum) {
    s::Registry registry;const auto token=prepare(operation,registry,base,maximum);s::Created made;s::Read read;
    allocation_probe::begin();
    if(operation==Operation::create) {made=registry.create(maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});}
    if(operation==Operation::reset) {made=registry.reset(token,maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});}
    if(operation==Operation::read) {read=registry.read(token);}
    const auto count=allocation_probe::end();
    need(count>0&&count<=32,"Actual allocation count outside finite test budget");
    need(operation==Operation::read?read.status==s::Status::ok:made.status==s::Status::ok,"Baseline allocation path failed");return count;
}
struct Row {Operation operation;std::size_t fail_after{},attempts{};bool retained{},past_retained{},next_valid{};};
Row inject(Operation operation,std::size_t position,const f::Case& base,const f::Case& maximum) {
    s::Registry registry;const auto token=prepare(operation,registry,base,maximum);const auto before=registry.read(token);const auto original=actual_read(before);s::Created made;s::Read failed_read;
    allocation_probe::begin(static_cast<long long>(position));
    if(operation==Operation::create) {made=registry.create(maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});}
    if(operation==Operation::reset) {made=registry.reset(token,maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});}
    if(operation==Operation::read) {failed_read=registry.read(token);}
    const auto attempts=allocation_probe::end();
    need(attempts==position+1,"Actual selected allocation was not reached exactly once");
    if(operation==Operation::read) {need(failed_read.status==s::Status::allocation_failure&&!failed_read.snapshot,"Allocation-failed read published partial snapshot");}
    else {need(made.status==s::Status::allocation_failure&&made.token==s::Token{},"Allocation-failed create/reset published token or wrong status");}
    const auto after=registry.read(token);const bool retained=actual_read(after)==original,past_retained=actual_read(before)==original;need(retained&&past_retained,"Injected failure changed active world/source/generation/credit or past snapshot");
    bool next_valid=false;
    if(operation==Operation::create) {
        const auto next=registry.create(maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});next_valid=next.status==s::Status::ok&&next.token.slot==1&&next.token.generation==1;
    }else if(operation==Operation::reset) {
        const auto next=registry.reset(token,maximum.scene.world,maximum.scene.meshes,maximum.scene.settings,maximum.progress,{.0625,8});
        if(next.status==s::Status::ok) {auto state=registry.read(next.token);next_valid=next.token.slot==token.slot&&next.token.generation==token.generation+1&&state.status==s::Status::ok&&state.snapshot&&state.snapshot->progress.ticks==100&&state.snapshot->scheduler.backlog==0&&state.snapshot->scheduler.sequence==0;}
    }else {next_valid=actual_read(registry.read(token))==original;}
    need(next_valid,"Failed staging consumed slot/generation or left Registry busy");return {operation,position,attempts,retained,past_retained,next_valid};
}
enum class Reentry {read,create,reset,destroy,pump};
const char* reentry_name(Reentry value) {switch(value) {case Reentry::read:return "read";case Reentry::create:return "create";case Reentry::reset:return "reset";case Reentry::destroy:return "destroy";case Reentry::pump:return "pump";}return "unknown";}
struct Hook {s::Registry* registry{};const f::Case* source{};s::Token token;Reentry operation{};s::Status status=s::Status::unexpected_exception;bool no_output{};std::size_t calls{};};
thread_local Hook* hook_context=nullptr;
void reenter() noexcept {
    auto& h=*hook_context;++h.calls;
    switch(h.operation) {
        case Reentry::read: {auto r=h.registry->read(h.token);h.status=r.status;h.no_output=!r.snapshot;break;}
        case Reentry::create: {auto r=h.registry->create(h.source->scene.world,h.source->scene.meshes,h.source->scene.settings,h.source->progress,{.0625,8});h.status=r.status;h.no_output=r.token==s::Token{};break;}
        case Reentry::reset: {auto r=h.registry->reset(h.token,h.source->scene.world,h.source->scene.meshes,h.source->scene.settings,h.source->progress,{.0625,8});h.status=r.status;h.no_output=r.token==s::Token{};break;}
        case Reentry::destroy: {h.status=h.registry->destroy(h.token);h.no_output=true;break;}
        case Reentry::pump: {auto r=h.registry->pump(h.token,{h.token,0.,{}});h.status=r.status;h.no_output=r.scheduler_calls==0&&!r.report;break;}
    }
}
struct BusyRow {Reentry operation;std::size_t allocations{},callbacks{};bool busy{},no_output{},unchanged{};};
BusyRow busy_check(Reentry operation,const f::Case& base) {
    s::Registry registry;const auto token=live(registry,base);const auto before=registry.read(token);const auto original=actual_read(before);Hook hook{&registry,&base,token,operation};hook_context=&hook;
    allocation_probe::begin(-1,reenter);auto outer=registry.read(token);const auto allocations=allocation_probe::end();hook_context=nullptr;
    const bool blocked=hook.status==s::Status::busy;const bool unchanged=actual_read(outer)==original&&actual_read(registry.read(token))==original&&actual_read(before)==original;
    need(allocations>0&&hook.calls==1&&blocked&&hook.no_output&&unchanged,"Actual allocator reentry did not refuse without output/state change");
    return {operation,allocations,hook.calls,blocked,hook.no_output,unchanged};
}
void emit() {
    need(q::current_binding().configured,"Actual accepted parent binding required");auto base=f::base_case();auto maximum=maximum_source();std::vector<Row> rows;std::array<std::size_t,3> counts;
    for(std::size_t i=0;i<3;++i) {const auto operation=static_cast<Operation>(i);counts[i]=measure(operation,base,maximum);for(std::size_t n=0;n<counts[i];++n) {rows.push_back(inject(operation,n,base,maximum));}}
    std::vector<BusyRow> busy;for(std::size_t i=0;i<5;++i) {busy.push_back(busy_check(static_cast<Reentry>(i),base));}
    std::cout<<"{\"schema\":1,\"status\":\"PASS\",\"kind\":\"actual-owned-session-allocation-injection\",\"scope\":\"Controlled global scalar/array new bad_alloc and allocation-hook reentry in one MSVC Release test executable. Actual create/reset/read only; no OS OOM, aligned/CRT allocation interception, thread race, post-child physics fault, GNU or whole-heap/deadline proof.\",\"baselineAllocationAttempts\":{\"create\":"<<counts[0]<<",\"reset\":"<<counts[1]<<",\"read\":"<<counts[2]<<"},\"failures\":[";
    for(std::size_t i=0;i<rows.size();++i) {
        if(i) {std::cout<<',';}const auto& r=rows[i];std::cout<<"{\"operation\":\""<<operation_name(r.operation)<<"\",\"failAfter\":"<<r.fail_after<<",\"actualAttempts\":"<<r.attempts<<",\"activeStateRetained\":";flag(std::cout,r.retained);std::cout<<",\"pastSnapshotRetained\":";flag(std::cout,r.past_retained);std::cout<<",\"nextOperationValid\":";flag(std::cout,r.next_valid);std::cout<<'}';
    }
    std::cout<<"],\"busyReentry\":[";
    for(std::size_t i=0;i<busy.size();++i) {
        if(i) {std::cout<<',';}const auto& r=busy[i];std::cout<<"{\"operation\":\""<<reentry_name(r.operation)<<"\",\"outerReadAllocations\":"<<r.allocations<<",\"actualCallbacks\":"<<r.callbacks<<",\"busyRefused\":";flag(std::cout,r.busy);std::cout<<",\"noOutputOrModelCall\":";flag(std::cout,r.no_output);std::cout<<",\"stateUnchanged\":";flag(std::cout,r.unchanged);std::cout<<'}';
    }
    std::cout<<"],\"actualAllocationFailures\":"<<rows.size()<<",\"actualBusyChecks\":"<<busy.size()<<"}\n";
}
}
int main() {
    try {emit();return 0;}
    catch(const std::exception& e) {allocation_probe::end();std::cerr<<e.what()<<'\n';return 1;}
}
