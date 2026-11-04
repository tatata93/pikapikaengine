#include "pikapika/world_static_mesh_flight_scheduler.hpp"
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {
namespace s=pikapika::world_static_mesh_flight_scheduler;
namespace a=pikapika::world_static_mesh_flight_advance;
namespace g=pikapika::world_static_mesh_flight_guard;
namespace d=pikapika::dynamics;
using Bits=std::vector<std::uint64_t>;
using I=pikapika::interval::Interval;
void need(bool condition,std::string_view message) {if(!condition) {throw std::runtime_error(std::string(message));}}
std::uint64_t bits(double value) noexcept {return std::bit_cast<std::uint64_t>(value);}
void vector(Bits& out,pikapika::Vec3 v) {out.push_back(bits(v.x));out.push_back(bits(v.y));out.push_back(bits(v.z));}
Bits body_bits(const d::RigidBody& b) {
    Bits out{b.id,b.is_static?1ULL:0ULL,bits(b.mass)};vector(out,b.inertia_diagonal);out.push_back(bits(b.radius));
    vector(out,b.position);vector(out,b.velocity);vector(out,b.angular_momentum);
    for(double n:{b.orientation.x,b.orientation.y,b.orientation.z,b.orientation.w}) {out.push_back(bits(n));}
    vector(out,b.force);vector(out,b.torque);out.push_back(bits(b.material.restitution));out.push_back(bits(b.material.friction));return out;
}
struct Input {d::World world;std::vector<s::StaticMeshSource> meshes;g::GuardSettings settings{0.};};
Input empty() {
    Input x;x.world.gravity={-0.,0,-0.};
    x.meshes={{301,7,{{11,{{{-32,-4,-32},{64,-4,-32},{-32,-4,64}}}}}}};return x;
}
Input moving(double y=2.) {
    auto x=empty();auto b=d::make_sphere(101,.25,2,{1,y,1});b.inertia_diagonal={1,1,1};
    b.force={-0.,0,-0.};b.torque={0,-0.,0};b.material={-0.,.5};x.world.add_body(b);
    x.world.add_plane({201,{-0.,1,-0.},-0.,{-0.,.5}});return x;
}
Bits world_bits(const Input& x) {
    Bits out{static_cast<std::uint64_t>(x.world.bodies().size())};
    for(const auto& b:x.world.bodies()) {const auto v=body_bits(b);out.insert(out.end(),v.begin(),v.end());}
    out.push_back(static_cast<std::uint64_t>(x.world.planes().size()));
    for(const auto& p:x.world.planes()) {out.push_back(p.id);vector(out,p.normal);out.push_back(bits(p.offset));out.push_back(bits(p.material.restitution));out.push_back(bits(p.material.friction));}
    vector(out,x.world.gravity);return out;
}
Bits source_bits(const Input& x) {
    Bits out{static_cast<std::uint64_t>(x.meshes.size())};
    for(const auto& m:x.meshes) {
        out.push_back(m.id);out.push_back(m.revision);out.push_back(static_cast<std::uint64_t>(m.triangles.size()));
        for(const auto& t:m.triangles) {out.push_back(t.id);for(auto v:t.vertices) {vector(out,v);}}
    }
    const auto& z=x.settings;const auto& h=z.mesh.held_load;const auto& p=h.mesh.primitive;
    for(auto n:{z.preparation.max_bodies,z.preparation.max_planes,z.preparation.max_meshes,z.preparation.max_total_faces,z.preparation.max_pairs,h.mesh.max_surfaces}) {out.push_back(n);}
    out.push_back(p.max_candidates);out.push_back(p.sqrt_refinements);out.push_back(p.max_total_sqrt_refinements);
    for(double n:{p.maximum_local_width,p.maximum_normal_width,p.minimum_sine_squared,h.time_tolerance,z.mesh.max_angular_increment,z.contact_margin}) {out.push_back(bits(n));}
    out.push_back(h.max_evaluations);out.push_back(h.max_leaves);out.push_back(h.max_depth);out.push_back(h.enclosure_sqrt_refinements);out.push_back(h.max_total_sqrt_refinements);
    const auto coverage=[&](const auto& c) {out.push_back(bits(c.time_tolerance));out.push_back(c.max_evaluations);out.push_back(c.max_leaves);out.push_back(c.max_depth);if constexpr(requires{c.sqrt_refinements;}) {out.push_back(c.sqrt_refinements);}};
    coverage(z.plane_metric);coverage(z.plane_box);coverage(z.sphere_box);
    const auto& l=z.limits;
    for(auto n:{l.body_records,l.pair_records,l.held_audits,l.held_certified_leaves,l.held_partition,l.held_frontier,l.primitive_audits,l.primitive_partition,l.primitive_frontier,l.last_mesh_rows,l.primitive_candidates,l.retained_faces,l.mesh_queries,l.primitive_queries,l.candidates_examined,l.sqrt_refinements,l.plane_metric_values,l.box_values,l.propagations,l.logical_payload_bytes}) {out.push_back(n);}
    return out;
}
bool same(s::Snapshot x,s::Snapshot y) {
    return bits(x.settings.step_seconds)==bits(y.settings.step_seconds)&&x.settings.max_attempts_per_pump==y.settings.max_attempts_per_pump&&
        bits(x.backlog)==bits(y.backlog)&&x.sequence==y.sequence&&x.busy==y.busy;
}
bool same(a::Progress x,a::Progress y) {return bits(x.time)==bits(y.time)&&x.ticks==y.ticks;}
struct Trace {std::string name;Bits before_world,after_world,before_source,after_source;a::Progress before_progress,after_progress;s::PumpReport report;};
std::vector<Trace> traces;
std::size_t pump(std::string name,s::Scheduler& scheduler,Input& input,a::Progress& progress,double elapsed) {
    const auto before_world=world_bits(input),source=source_bits(input);const auto before_progress=progress;const auto before_state=scheduler.snapshot();
    const auto* body_data=input.world.bodies().data();const auto* plane_data=input.world.planes().data();const auto* mesh_data=input.meshes.data();
    std::vector<const pikapika::sphere_triangle::StaticTriangle*> faces;
    for(const auto& m:input.meshes) {faces.push_back(m.triangles.data());}
    auto r=scheduler.pump(input.world,input.meshes,input.settings,progress,elapsed);
    need(same(r.before,before_state)&&same(r.after,scheduler.snapshot())&&!r.after.busy,"Actual private scheduler before/after state");
    need(same(r.progress_before,before_progress)&&same(r.progress_after,progress),"Actual Progress before/after report");
    need(source_bits(input)==source,"Source/settings ALL fields and signed zeros unchanged");
    need(body_data==input.world.bodies().data()&&plane_data==input.world.planes().data()&&mesh_data==input.meshes.data(),"Existing World/source addresses stable");
    for(std::size_t i=0;i<faces.size();++i) {need(faces[i]==input.meshes[i].triangles.data(),"Every face storage stable");}
    need(bits(r.requested_elapsed)==bits(elapsed)&&bits(r.dropped_seconds)==bits(0.),"Original elapsed signed zero and retain-only drop +0");
    need(r.attempts<=r.planned_attempts&&r.planned_attempts<=before_state.settings.max_attempts_per_pump&&r.attempts<=8,"Bounded planned/executed slots");
    need(r.upper_budget.attempts==r.planned_attempts,"Unexecuted tail reservation retained");
    need(r.upper_budget.guard_work.sqrt_refinements==r.planned_attempts*g::hard_max_sqrt_refinements&&
         r.upper_budget.guard_logical_payload_bytes==r.planned_attempts*g::hard_max_logical_payload,"Checked settled hard budget products");
    std::size_t committed=0;
    for(std::size_t i=0;i<8;++i) {
        need(r.queue_plan[i].has_value()==(i<r.planned_attempts)&&r.tick_reports[i].has_value()==(i<r.attempts),"Dense fixed slots and actual unexecuted tail");
        if(i<r.attempts) {
            const auto& t=*r.tick_reports[i];need(t.queue_index==i&&t.credit_consumed==t.report.committed,"Only actual returned commit consumes queue");
            need(bits(t.report.requested_dt)==bits(before_state.settings.step_seconds),"Identical step bits per call");
            if(t.report.committed) {++committed;} else {need(i+1==r.attempts&&r.status==s::Status::tick_rejected,"First rejected tick stops");}
        }
    }
    need(committed==r.committed_ticks,"Exact committed prefix count");
    if(!r.elapsed_accepted) {need(same(before_state,scheduler.snapshot())&&world_bits(input)==before_world&&same(before_progress,progress),"Pre-admission refusal ALL state unchanged");}
    if(r.committed_ticks==0) {need(world_bits(input)==before_world&&same(before_progress,progress),"No successful tick means ALL World/Progress fields unchanged");}
    traces.push_back({std::move(name),before_world,world_bits(input),source,source_bits(input),before_progress,progress,std::move(r)});return traces.size()-1;
}
const s::PumpReport& report(std::size_t i) {return traces.at(i).report;}
void committed_body(const Input& x,const s::PumpReport& r) {
    need(r.committed_ticks>0,"Expected an actual nonempty successful prefix");
    const auto& last=r.tick_reports[r.committed_ticks-1]->report;
    need(last.guard&&last.guard->candidate_bodies,"Actual candidate evidence exists");
    need(last.guard->candidate_bodies->size()==x.world.bodies().size(),"Whole candidate count");
    for(std::size_t i=0;i<x.world.bodies().size();++i) {
        auto expected=(*last.guard->candidate_bodies)[i];expected.force={};expected.torque={};
        need(body_bits(expected)==body_bits(x.world.bodies()[i]),"EVERY committed body field equals its actual candidate except +0 loads");
    }
}
void boundaries() {
    auto x=empty();a::Progress p{.125,17};s::Scheduler scheduler({.0625,4});
    const double lower=std::nextafter(.0625,0.);
    auto i=pump("empty-below-step",scheduler,x,p,lower);need(report(i).status==s::Status::waiting&&report(i).attempts==0,"No epsilon early tick");
    i=pump("empty-zero-retains-fraction",scheduler,x,p,0.);need(report(i).attempts==0,"Zero retry does not invent due work");
    i=pump("empty-exact-step-completion",scheduler,x,p,.0625-lower);need(report(i).committed_ticks==1&&scheduler.snapshot().backlog==0&&p.ticks==18,"One exact dyadic tick");
    i=pump("empty-three-ticks",scheduler,x,p,.1875);need(report(i).committed_ticks==3&&p.ticks==21&&p.time==.375,"Three actual clock commits");
}
void budget() {
    auto x=empty();a::Progress p{};s::Scheduler scheduler({.0625,4});
    auto i=pump("budget-four-keeps-backlog",scheduler,x,p,.5);need(report(i).status==s::Status::step_budget&&report(i).committed_ticks==4&&scheduler.snapshot().backlog==.25,"Retain backlog after cap");
    i=pump("budget-retry-zero",scheduler,x,p,0.);need(report(i).committed_ticks==4&&p.ticks==8&&scheduler.snapshot().backlog==0,"Retry credit once only");
    a::Progress p8{};s::Scheduler eight({.0625,8});
    i=pump("hard-eight-keeps-backlog",eight,x,p8,1.);need(report(i).committed_ticks==8&&eight.snapshot().backlog==.5,"Hard8 reservation");
    i=pump("hard-eight-drains-zero",eight,x,p8,0.);need(report(i).committed_ticks==8&&p8.ticks==16&&eight.snapshot().backlog==0,"Hard8 retry");
}
void cap() {
    auto x=empty();a::Progress p{};s::Scheduler scheduler({.0625,1});
    pump("cap-fill",scheduler,x,p,1.);
    const auto i=pump("cap-overflow-not-accepted",scheduler,x,p,.125);need(report(i).reason==s::Reason::backlog_limit&&!report(i).elapsed_accepted&&scheduler.snapshot().backlog==.9375,"Do not clamp or consume excessive elapsed");
    pump("cap-drain-zero",scheduler,x,p,0.);
    const auto retry=pump("cap-original-rejected-elapsed-now-accepted",scheduler,x,p,.125);
    need(report(retry).elapsed_accepted&&report(retry).committed_ticks==1&&scheduler.snapshot().backlog==.9375,
         "Previously unaccepted elapsed may be submitted after credit drains");
}
void rejected_retry() {
    auto x=moving(.25);a::Progress p{.125,17};s::Scheduler scheduler({.0625,4});
    const auto i=pump("first-guard-reject",scheduler,x,p,.0625);
    need(report(i).elapsed_accepted&&report(i).status==s::Status::tick_rejected&&report(i).attempts==1&&report(i).committed_ticks==0&&scheduler.snapshot().backlog==.0625,"Rejected tick consumes no credit");
    need(report(i).tick_reports[0]->report.guard&&report(i).tick_reports[0]->report.work.guard_queries_attempted==1,"Real owned failed guard");
    const auto old_body=body_bits(report(i).tick_reports[0]->report.guard->preparation->snapshot->bodies.front());
    pump("same-guard-retry-zero-reject",scheduler,x,p,0.);
    x.world.find_body(101)->position.y=2.;
    const auto next=pump("corrected-world-retry-zero",scheduler,x,p,0.);need(report(next).committed_ticks==1&&scheduler.snapshot().backlog==0&&p.ticks==18,"No new elapsed on corrected retry");
    committed_body(x,report(next));need(body_bits(report(i).tick_reports[0]->report.guard->preparation->snapshot->bodies.front())==old_body,"Old owned rejected snapshot survives world mutation and new tick");
}
void prefix() {
    auto x=moving(.375);x.world.find_body(101)->velocity={0,-1,0};a::Progress p{.125,17};s::Scheduler scheduler({.0625,4});
    const auto i=pump("one-success-then-plane-reject",scheduler,x,p,.1875);const auto& r=report(i);
    need(r.status==s::Status::tick_rejected&&r.attempts==2&&r.committed_ticks==1,"Meaningful nonempty successful prefix then contact-band refusal");
    need(p.time==.1875&&p.ticks==18&&scheduler.snapshot().backlog==.125&&x.world.find_body(101)->position.y==.3125,"Prefix stays; rejected tick retains two credits");
    committed_body(x,r);
    need(r.tick_reports[1]->report.guard->preparation->snapshot->bodies.front().position.y==.3125,"Second guard used current state, not cached evidence");
}
void loads() {
    auto x=moving();auto& body=*x.world.find_body(101);body.velocity={1,0,0};body.force={8,-0.,0};body.torque={0,0,.125};
    a::Progress p{};s::Scheduler scheduler({.0625,4});const auto i=pump("loads-first-tick-only",scheduler,x,p,.125);const auto& r=report(i);
    need(r.committed_ticks==2&&r.status==s::Status::waiting,"Two nonempty load ticks");
    need(body.position.x==1.1484375&&body.velocity.x==1.25,"Exact analytic dyadic first acceleration then free flight");
    const auto& first=r.tick_reports[0]->report;const auto& second=r.tick_reports[1]->report;
    need(first.guard->preparation->snapshot->bodies.front().force.x==8&&bits(second.guard->preparation->snapshot->bodies.front().force.x)==bits(0.),"Loads cleared once, not silently held across frame");
    need(bits(body.force.x)==bits(0.)&&bits(body.torque.z)==bits(0.),"Consumed final loads +0");committed_body(x,r);
}
void invalid_elapsed() {
    auto x=moving();a::Progress p{};s::Scheduler scheduler;
    for(double value:{-1.,std::nextafter(1.,2.),std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) {
        const auto i=pump("invalid-elapsed-bits",scheduler,x,p,value);need(report(i).reason==s::Reason::elapsed&&!report(i).elapsed_accepted,"Invalid elapsed is not admitted");
    }
    const auto i=pump("negative-zero-original",scheduler,x,p,-0.);need(bits(report(i).requested_elapsed)==bits(-0.)&&report(i).elapsed_accepted&&report(i).attempts==0,"Signed-zero original is retained");
}
void invalid_config() {
    std::size_t refused=0;
    for(auto config:{s::Settings{0.,4},s::Settings{std::nextafter(s::minimum_step,0.),4},s::Settings{std::nextafter(.1,1.),4},s::Settings{.0625,0},s::Settings{.0625,9},s::Settings{std::numeric_limits<double>::quiet_NaN(),4}}) {
        try {s::Scheduler scheduler(config);(void)scheduler;} catch(const std::invalid_argument&) {++refused;}
    }
    need(refused==6,"All invalid immutable configurations refused");
}
void clock_refusal() {
    auto x=moving();a::Progress p{.125,a::maximum_ticks};s::Scheduler scheduler({.0625,4});
    auto i=pump("tick-limit-keeps-credit",scheduler,x,p,.0625);need(report(i).tick_reports[0]->report.reason==a::Reason::tick_limit&&report(i).tick_reports[0]->report.work.guard_queries_attempted==0,"Actual clock rejection before guard");
    a::Progress limit{a::maximum_time,1};s::Scheduler time_limit({.0625,4});
    i=pump("time-limit-keeps-credit",time_limit,x,limit,.0625);need(report(i).tick_reports[0]->report.reason==a::Reason::time_limit,"Actual maximum represented time guard");
}
void environment() {
    auto x=moving();a::Progress p{};s::Scheduler scheduler({.0625,4});const int original=std::fegetround();
    need(std::fesetround(FE_DOWNWARD)==0,"Set temporary directed test environment");
    std::size_t i{};
    try {i=pump("unsupported-rounding",scheduler,x,p,.0625);} catch(...) {std::fesetround(original);throw;}
    need(std::fesetround(original)==0,"Restore original rounding environment");
    need(report(i).status==s::Status::unsupported_environment&&report(i).reason==s::Reason::environment&&!report(i).admission_rounding_error,"Env before Interval diagnostics/admission");
}
void default_step() {
    auto x=empty();a::Progress p{};s::Scheduler scheduler;
    const auto i=pump("default-120hz-two",scheduler,x,p,(1.0/120.0)*2);need(report(i).committed_ticks==2&&report(i).status==s::Status::waiting,"Default binary64 120Hz exact repeated step usage");
    need(bits(report(i).tick_reports[0]->report.requested_dt)==bits(1.0/120.0),"No alternate rational/chord step");
}
void minimal_step() {
    auto x=empty();a::Progress p{};s::Scheduler scheduler({s::minimum_step,4});
    auto i=pump("minimum-step-subnormal-elapsed",scheduler,x,p,std::numeric_limits<double>::denorm_min());need(report(i).attempts==0,"Subnormal elapsed retained");
    i=pump("minimum-step-admission-rounding",scheduler,x,p,s::minimum_step);need(report(i).committed_ticks==1&&scheduler.snapshot().backlog==0,"Explicit represented-credit RN absorption");
}
void represented_rates() {
    for(unsigned hz:{30U,60U,120U,144U,1000U}) {
        auto x=empty();a::Progress p{};s::Scheduler scheduler;
        for(unsigned frame=0;frame<hz;++frame) {pump("represented-rate-"+std::to_string(hz),scheduler,x,p,1.0/static_cast<double>(hz));}
        need(p.ticks==(hz==144?119U:120U),"Represented ledger rate expectation, no old epsilon tick replacement");
        if(hz==144) {need(bits(scheduler.snapshot().backlog)==0x3f811111111110f9ULL,"144Hz represented backlog matches independent integer reference candidate");}
    }
}
void unconfigured() {
    auto x=moving();a::Progress p{};s::Scheduler scheduler({.0625,4});
    const auto i=pump("unconfigured-refusal",scheduler,x,p,.0625);need(report(i).reason==s::Reason::binding_unsupported&&!report(i).elapsed_accepted&&report(i).attempts==0,"No caller unlock/default scheduler profile refusal");
}

std::string hex(std::uint64_t value) {std::ostringstream out;out<<std::hex<<std::setfill('0')<<std::setw(16)<<value;return out.str();}
void bit_array(const Bits& value) {
    std::cout<<'[';for(std::size_t i=0;i<value.size();++i) {if(i) {std::cout<<',';}std::cout<<'"'<<hex(value[i])<<'"';}std::cout<<']';
}
void progress_json(a::Progress p) {std::cout<<"{\"timeBits\":\""<<hex(bits(p.time))<<"\",\"ticks\":"<<p.ticks<<'}';}
void interval_json(I value) {std::cout<<"[\""<<hex(bits(value.lower()))<<"\",\""<<hex(bits(value.upper()))<<"\"]";}
void snapshot_json(s::Snapshot value) {
    std::cout<<"{\"stepBits\":\""<<hex(bits(value.settings.step_seconds))<<"\",\"maxAttempts\":"<<value.settings.max_attempts_per_pump
             <<",\"backlogBits\":\""<<hex(bits(value.backlog))<<"\",\"sequence\":"<<value.sequence<<",\"busy\":"<<(value.busy?"true":"false")<<'}';
}
void emit() {
    std::cout.imbue(std::locale::classic());std::cout<<"{\"schema\":1,\"kind\":\"world-flight-scheduler-prototype-observations\",\"scope\":\"Finite internal assertions and full World/source bit snapshots; selected report diagnostics, NOT full nested Report serialization or independent checker.\",\"traces\":[";
    for(std::size_t n=0;n<traces.size();++n) {
        if(n) {std::cout<<',';}const auto& t=traces[n];const auto& r=t.report;
        std::cout<<"{\"name\":\""<<t.name<<"\",\"worldBeforeBits\":";bit_array(t.before_world);std::cout<<",\"worldAfterBits\":";bit_array(t.after_world);
        std::cout<<",\"sourceBeforeBits\":";bit_array(t.before_source);std::cout<<",\"sourceAfterBits\":";bit_array(t.after_source);
        std::cout<<",\"progressBefore\":";progress_json(t.before_progress);std::cout<<",\"progressAfter\":";progress_json(t.after_progress);
        std::cout<<",\"report\":{\"status\":"<<static_cast<unsigned>(r.status)<<",\"reason\":"<<static_cast<unsigned>(r.reason)<<",\"elapsedBits\":\""<<hex(bits(r.requested_elapsed))<<"\",\"accepted\":"<<(r.elapsed_accepted?"true":"false")<<",\"before\":";snapshot_json(r.before);
        std::cout<<",\"after\":";snapshot_json(r.after);std::cout<<",\"dropBits\":\""<<hex(bits(r.dropped_seconds))<<"\",\"planned\":"<<r.planned_attempts<<",\"attempts\":"<<r.attempts<<",\"committed\":"<<r.committed_ticks<<",\"admittedCreditBits\":";
        if(r.admitted_credit) {std::cout<<'"'<<hex(bits(*r.admitted_credit))<<'"';} else {std::cout<<"null";}
        std::cout<<",\"admissionErrorBits\":";if(r.admission_rounding_error) {interval_json(*r.admission_rounding_error);} else {std::cout<<"null";}
        std::cout<<",\"queue\":[";
        for(std::size_t i=0;i<r.planned_attempts;++i) {if(i) {std::cout<<',';}const auto& q=*r.queue_plan[i];std::cout<<"{\"beforeBits\":\""<<hex(bits(q.credit_before))<<"\",\"proposedBits\":\""<<hex(bits(q.proposed_after))<<"\",\"errorBits\":";interval_json(q.rounding_error);std::cout<<'}';}
        std::cout<<"],\"ticks\":[";
        for(std::size_t i=0;i<r.attempts;++i) {if(i) {std::cout<<',';}const auto& tick=*r.tick_reports[i];std::cout<<"{\"queueIndex\":"<<tick.queue_index<<",\"consumed\":"<<(tick.credit_consumed?"true":"false")<<",\"status\":"<<static_cast<unsigned>(tick.report.status)<<",\"reason\":"<<static_cast<unsigned>(tick.report.reason)<<",\"guardPresent\":"<<(tick.report.guard?"true":"false")<<",\"guardAttempts\":"<<tick.report.work.guard_queries_attempted<<",\"guardReturns\":"<<tick.report.work.guard_queries_returned<<",\"bodyStores\":"<<tick.report.work.body_assignments<<",\"progressStores\":"<<tick.report.work.progress_assignments<<'}';}
        std::cout<<"]}}";
    }
    std::cout<<"]}\n";
}
}

int main(int argc,char** argv) {
    try {
        need(argc==2,"Expected --run, --observations, or --unsupported-profile");
        const std::string_view mode=argv[1];
        if(mode=="--unsupported-profile") {unconfigured();std::cout<<"Scheduler default profile refusal PASS\n";return 0;}
        need(mode=="--run"||mode=="--observations","Unknown prototype CLI");
        need(s::current_binding().configured,"Configured Release scheduler TU required; no fabricated profile");
        static_assert(!std::is_copy_constructible_v<s::Scheduler>&&!std::is_move_constructible_v<s::Scheduler>);
        boundaries();budget();cap();rejected_retry();prefix();loads();invalid_elapsed();invalid_config();clock_refusal();environment();default_step();minimal_step();represented_rates();
        if(mode=="--observations") {emit();}
        else {std::cout<<"Scheduler prototype: 13 directed groups PASS; "<<traces.size()<<" actual pump observations. No independent checker, cross-GNU, full nested fixture serialization, sanitizer or main integration claimed.\n";}
        return 0;
    } catch(const std::exception& error) {std::cerr<<"Scheduler prototype failed: "<<error.what()<<'\n';return 1;}
}
