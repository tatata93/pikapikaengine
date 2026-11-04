#include "world_static_mesh_flight_scheduler_fixture_support.hpp"
#include "world_static_mesh_flight_advance_fixture_support.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <ostream>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace world_scheduler_fixture {
namespace {
namespace s=pikapika::world_static_mesh_flight_scheduler;
namespace a=pikapika::world_static_mesh_flight_advance;
namespace g=pikapika::world_static_mesh_flight_guard;
namespace d=pikapika::dynamics;
using Case=world_guard_fixture::Case;
using Bits=std::vector<std::uint64_t>;
void need(bool condition,std::string_view message) {if(!condition) {throw std::runtime_error(std::string(message));}}
void flag(std::ostream& out,bool value) {out<<(value?"true":"false");}
void text(std::ostream& out,std::string_view value) {world_advance_fixture::string_json(out,value);}
std::uint64_t bits(double value) noexcept {return std::bit_cast<std::uint64_t>(value);}
void bits_json(std::ostream& out,double value) {
    constexpr char hex[]="0123456789abcdef";const auto raw=bits(value);out<<'"';
    for(unsigned j=0;j<16;++j) {out<<hex[(raw>>((15U-j)*4U))&15U];}out<<'"';
}
void number(std::ostream& out,double value) {
    need(std::isfinite(value),"Nonfinite full scheduler fixture number");
    if(value==0&&std::signbit(value)) {out<<"-0";}else {out<<std::setprecision(std::numeric_limits<double>::max_digits10)<<value;}
}
void interval_json(std::ostream& out,pikapika::interval::Interval value) {out<<'[';number(out,value.lower());out<<',';number(out,value.upper());out<<']';}
template<class E,std::size_t N> const char* enum_name(E value,const char* const (&names)[N]) {
    const auto n=static_cast<std::underlying_type_t<E>>(value);need(n<N,"Unknown scheduler fixture enum");return names[n];
}
const char* status(s::Status value) {constexpr const char* names[]={"waiting","step_budget","tick_rejected","invalid_input","unsupported_environment","numerical_failure","reentrant"};return enum_name(value,names);}
const char* reason(s::Reason value) {constexpr const char* names[]={"none","environment","binding_unsupported","elapsed","backlog_limit","sequence_limit","queue_arithmetic","cost_overflow","allocation_failure","unexpected_exception","busy","advance_rejected"};return enum_name(value,names);}
void settings_json(std::ostream& out,s::Settings value) {out<<"{\"stepSeconds\":";number(out,value.step_seconds);out<<",\"maxAttemptsPerPump\":"<<value.max_attempts_per_pump<<'}';}
void snapshot_json(std::ostream& out,s::Snapshot value) {out<<"{\"settings\":";settings_json(out,value.settings);out<<",\"backlog\":";number(out,value.backlog);out<<",\"sequence\":"<<value.sequence<<",\"busy\":";flag(out,value.busy);out<<'}';}
void progress_json(std::ostream& out,a::Progress value) {need(value.ticks<=a::maximum_ticks,"Progress tick domain");out<<"{\"time\":";number(out,value.time);out<<",\"ticks\":"<<value.ticks<<'}';}
void binding_json(std::ostream& out,const s::Binding& value) {
    need(value.profile<=1,"Unknown scheduler profile");out<<"{\"profile\":"<<value.profile<<",\"configured\":";flag(out,value.configured);out<<",\"buildId\":\"";
    bool ended=false;std::size_t count=0;
    for(char ch:value.build_id) {
        if(ch=='\0') {ended=true;continue;}
        need(!ended&&((ch>='a'&&ch<='f')||(ch>='0'&&ch<='9')),"Invalid scheduler identity");out<<ch;++count;
    }
    need(ended&&(!value.configured||count==64),"Incomplete scheduler identity");out<<"\"}";
}
void work_json(std::ostream& out,const g::WorkGrant& w) {
    out<<"{\"meshQueries\":"<<w.mesh_queries<<",\"primitiveQueries\":"<<w.primitive_queries<<",\"candidatesExamined\":"<<w.candidates_examined;
    out<<",\"sqrtRefinements\":"<<w.sqrt_refinements<<",\"propagations\":"<<w.propagations<<",\"planeMetricValues\":"<<w.plane_metric_values;
    out<<",\"boxValues\":"<<w.box_values<<",\"planeNormLoopIterationsUpper\":"<<w.plane_norm_loop_iterations_upper<<",\"bridgeCallsUpper\":"<<w.bridge_calls_upper<<'}';
}
class Buffer final:public std::streambuf {
    std::string raw_;
    void append(const char* source,std::size_t count) {need(count<=maximum_document_bytes-raw_.size(),"Full scheduler JSON byte budget exceeded");raw_.append(source,count);}
protected:
    std::streamsize xsputn(const char* source,std::streamsize count) override {need(count>=0,"Negative write size");append(source,static_cast<std::size_t>(count));return count;}
    int_type overflow(int_type ch) override {
        if(traits_type::eq_int_type(ch,traits_type::eof())) {return traits_type::not_eof(ch);}
        const char raw=traits_type::to_char_type(ch);append(&raw,1);return ch;
    }
public:
    const std::string& str() const noexcept {return raw_;}
};
class CoutFormat {
    std::ios::fmtflags flags_=std::cout.flags();std::streamsize precision_=std::cout.precision();std::locale locale_=std::cout.getloc();
public:
    CoutFormat() {std::cout.imbue(std::locale::classic());std::cout.flags(std::ios::dec);std::cout.precision(std::numeric_limits<double>::max_digits10);}
    ~CoutFormat() noexcept {try {std::cout.flags(flags_);std::cout.precision(precision_);std::cout.imbue(locale_);}catch(...) {}}
    CoutFormat(const CoutFormat&)=delete;CoutFormat& operator=(const CoutFormat&)=delete;
};
template<class Writer> std::string capture(Writer writer) {
    Buffer buffer;std::ostream out(&buffer);out.imbue(std::locale::classic());out.exceptions(std::ios::badbit|std::ios::failbit);
    writer(out);need(static_cast<bool>(out),"Private fixture stream failed");return buffer.str();
}
void vector_bits(Bits& out,pikapika::Vec3 value) {out.push_back(bits(value.x));out.push_back(bits(value.y));out.push_back(bits(value.z));}
Bits source_bits(const Case& input) {
    Bits out{static_cast<std::uint64_t>(input.meshes.size())};
    for(const auto& m:input.meshes) {out.push_back(m.id);out.push_back(m.revision);out.push_back(static_cast<std::uint64_t>(m.triangles.size()));for(const auto& t:m.triangles) {out.push_back(t.id);for(auto v:t.vertices) {vector_bits(out,v);}}}
    return out;
}
Bits plane_bits(const Case& input) {
    Bits out{static_cast<std::uint64_t>(input.world.planes().size())};
    for(const auto& p:input.world.planes()) {out.push_back(p.id);vector_bits(out,p.normal);out.push_back(bits(p.offset));out.push_back(bits(p.material.restitution));out.push_back(bits(p.material.friction));}return out;
}
Bits gravity_bits(const Case& input) {Bits out;vector_bits(out,input.world.gravity);return out;}
struct Pointers {
    const d::RigidBody* body_data;const d::Plane* plane_data;const g::StaticMeshSource* mesh_data;
    std::vector<const d::RigidBody*> bodies,lookups;std::vector<std::uint64_t> ids;std::vector<const pikapika::sphere_triangle::StaticTriangle*> faces;
    explicit Pointers(const Case& input):body_data(input.world.bodies().data()),plane_data(input.world.planes().data()),mesh_data(input.meshes.data()) {
        for(const auto& b:input.world.bodies()) {bodies.push_back(&b);ids.push_back(b.id);lookups.push_back(input.world.find_body(b.id));}
        for(const auto& m:input.meshes) {faces.push_back(m.triangles.data());}
    }
    void json(std::ostream& out,const Case& after) const {
        out<<"{\"bodyCountUnchanged\":";flag(out,bodies.size()==after.world.bodies().size());out<<",\"bodyStorageStable\":";flag(out,body_data==after.world.bodies().data());
        out<<",\"planeStorageStable\":";flag(out,plane_data==after.world.planes().data());out<<",\"meshStorageStable\":";flag(out,mesh_data==after.meshes.data());out<<",\"bodies\":[";
        for(std::size_t i=0;i<bodies.size();++i) {
            if(i) {out<<',';}const auto* lookup=after.world.find_body(ids[i]);out<<"{\"ordinal\":"<<i<<",\"originalId\":"<<ids[i]<<",\"sameOrdinalAddress\":";
            flag(out,i<after.world.bodies().size()&&bodies[i]==&after.world.bodies()[i]);out<<",\"sameLookupResult\":";flag(out,lookup==lookups[i]);
            out<<",\"lookupBeforeMatchesOrdinal\":";flag(out,lookups[i]==bodies[i]);out<<",\"lookupAfterMatchesOrdinal\":";flag(out,i<after.world.bodies().size()&&lookup==&after.world.bodies()[i]);out<<'}';
        }
        out<<"],\"meshFaceStorageStable\":[";for(std::size_t i=0;i<faces.size();++i) {if(i) {out<<',';}flag(out,i<after.meshes.size()&&faces[i]==after.meshes[i].triangles.data());}out<<"]}";
    }
};
enum class Edit {none,raise_body};
struct Frame {std::string name;double elapsed;Edit edit=Edit::none;};
struct Scenario {std::string name;Case input;s::Settings scheduler;a::Progress progress{.125,17};std::vector<Frame> frames;};
Case empty() {
    Case input;input.world.gravity={-0.,0,-0.};input.settings=g::GuardSettings{0.};
    input.meshes={{301,7,{{11,{{{-32,-4,-32},{64,-4,-32},{-32,-4,64}}}}}}};return input;
}
Case moving(double y=2.) {
    auto input=empty();auto b=d::make_sphere(101,.25,2,{1,y,1});b.inertia_diagonal={1,1,1};b.force={-0.,0,-0.};b.torque={0,-0.,0};b.material={-0.,.5};
    input.world.add_body(b);input.world.add_plane({201,{-0.,1,-0.},-0.,{-0.,.5}});return input;
}
std::vector<Scenario> scenarios() {
    std::vector<Scenario> out;const double h=.0625,below=std::nextafter(h,0.);
    out.push_back({"boundary",empty(),{h,4},{.125,17},{{"below-step",below},{"retry-zero",0.},{"complete-step",h-below},{"three-ticks",.1875}}});
    out.push_back({"cap4",empty(),{h,4},{.125,17},{{"retained",.5},{"drain-zero",0.}}});
    out.push_back({"cap8",empty(),{h,8},{.125,17},{{"retained",1.},{"drain-zero",0.}}});
    out.push_back({"guard-retry",moving(.25),{h,4},{.125,17},{{"first-reject",h},{"retry-zero-reject",0.},{"fixed-retry-zero",0.,Edit::raise_body}}});
    auto plane=moving(.375);plane.world.find_body(101)->velocity={0,-1,0};
    out.push_back({"success-prefix",std::move(plane),{h,4},{.125,17},{{"one-commit-then-plane-reject",.1875},{"retry-zero-reject",0.}}});
    auto loads=moving();loads.world.find_body(101)->velocity={1,0,0};loads.world.find_body(101)->force={8,-0.,0};loads.world.find_body(101)->torque={0,0,.125};
    out.push_back({"loads",std::move(loads),{h,4},{.125,17},{{"two-ticks-first-force-only",.125},{"zero-no-tick",0.}}});
    out.push_back({"admission-cap",empty(),{h,1},{.125,17},{{"fill",1.},{"elapsed-rejected",.125},{"drain-zero",0.},{"resubmit-unaccepted-elapsed",.125}}});
    out.push_back({"tick-limit",moving(),{h,4},{.125,a::maximum_ticks},{{"refused",h}}});
    out.push_back({"time-limit",moving(),{h,4},{a::maximum_time,17},{{"refused",h}}});
    out.push_back({"default-step",empty(),{},{.125,17},{{"two-default-ticks",2*(1.0/120.0)}}});
    out.push_back({"elapsed-bits",empty(),{h,4},{.125,17},{{"negative-zero",-0.},{"subnormal",std::numeric_limits<double>::denorm_min()},
        {"negative",-.125},{"over-cap",std::nextafter(1.,2.)},{"infinity",std::numeric_limits<double>::infinity()},
        {"nan",std::bit_cast<double>(std::uint64_t{0x7ff8000000001234ULL})}}});
    return out;
}
void frame_json(std::ostream& out,Scenario& scenario,s::Scheduler& scheduler,std::size_t ordinal,const Frame& frame) {
    if(frame.edit==Edit::raise_body) {auto* b=scenario.input.world.find_body(101);need(b!=nullptr,"Edit body missing");b->position.y=2.;}
    auto& input=scenario.input;input.horizon=scenario.scheduler.step_seconds;
    const auto before_input=capture([&](auto& o){world_guard_fixture::input_json(o,input);});
    const auto before_world=capture([&](auto& o){world_guard_fixture::world_json(o,input.world);});
    const auto before_settings=capture([&](auto& o){world_guard_fixture::settings_json(o,input.settings);});
    const auto before_source=source_bits(input),before_planes=plane_bits(input),before_gravity=gravity_bits(input);const auto before_horizon=bits(input.horizon);
    const auto before_progress=scenario.progress;const auto before_scheduler=scheduler.snapshot();const Pointers pointers(input);
    const auto report=scheduler.pump(input.world,input.meshes,input.settings,scenario.progress,frame.elapsed); // ONE actual pump, no other query.
    const auto after_input=capture([&](auto& o){world_guard_fixture::input_json(o,input);});
    const auto after_world=capture([&](auto& o){world_guard_fixture::world_json(o,input.world);});
    const auto after_settings=capture([&](auto& o){world_guard_fixture::settings_json(o,input.settings);});
    out<<"{\"name\":";text(out,scenario.name+"/"+frame.name);out<<",\"scenario\":";text(out,scenario.name);out<<",\"frameOrdinal\":"<<ordinal<<",\"externalEdit\":";
    if(frame.edit==Edit::none) {out<<"null";}else {text(out,"body-position-y-to-2");}
    out<<",\"input\":"<<before_input<<",\"inputAfter\":"<<after_input<<",\"worldBefore\":"<<before_world<<",\"worldAfter\":"<<after_world;
    out<<",\"progressBefore\":";progress_json(out,before_progress);out<<",\"progressAfter\":";progress_json(out,scenario.progress);
    out<<",\"schedulerBefore\":";snapshot_json(out,before_scheduler);out<<",\"schedulerAfter\":";snapshot_json(out,scheduler.snapshot());
    out<<",\"elapsedBits\":";bits_json(out,frame.elapsed);out<<",\"report\":";report_json(out,report);
    out<<",\"observations\":{\"captureComplete\":true,\"pumpCalls\":1,\"sourceUnchanged\":";flag(out,before_source==source_bits(input));
    out<<",\"settingsUnchanged\":";flag(out,before_settings==after_settings);out<<",\"horizonUnchanged\":";flag(out,before_horizon==bits(input.horizon));
    out<<",\"planesUnchanged\":";flag(out,before_planes==plane_bits(input));out<<",\"gravityUnchanged\":";flag(out,before_gravity==gravity_bits(input));
    out<<",\"worldUnchanged\":";flag(out,before_world==after_world);out<<",\"progressUnchanged\":";flag(out,bits(before_progress.time)==bits(scenario.progress.time)&&before_progress.ticks==scenario.progress.ticks);
    out<<",\"pointerStability\":";pointers.json(out,input);out<<"}}";
}
}

void report_json(std::ostream& out,const s::PumpReport& report) {
    out<<"{\"status\":";text(out,status(report.status));out<<",\"reason\":";text(out,reason(report.reason));out<<",\"binding\":";binding_json(out,report.binding);
    out<<",\"before\":";snapshot_json(out,report.before);out<<",\"after\":";snapshot_json(out,report.after);
    out<<",\"requestedElapsedBits\":";bits_json(out,report.requested_elapsed);out<<",\"elapsedAccepted\":";flag(out,report.elapsed_accepted);
    out<<",\"admittedCredit\":";if(report.admitted_credit) {number(out,*report.admitted_credit);}else {out<<"null";}
    out<<",\"admissionRoundingError\":";if(report.admission_rounding_error) {interval_json(out,*report.admission_rounding_error);}else {out<<"null";}
    out<<",\"progressBefore\":";progress_json(out,report.progress_before);out<<",\"progressAfter\":";progress_json(out,report.progress_after);
    out<<",\"queuePlan\":[";
    for(std::size_t i=0;i<s::hard_max_attempts;++i) {
        if(i) {out<<',';}if(!report.queue_plan[i]) {out<<"null";continue;}const auto& q=*report.queue_plan[i];
        out<<"{\"creditBefore\":";number(out,q.credit_before);out<<",\"proposedAfter\":";number(out,q.proposed_after);out<<",\"roundingError\":";interval_json(out,q.rounding_error);out<<'}';
    }
    out<<"],\"plannedAttempts\":"<<report.planned_attempts<<",\"attempts\":"<<report.attempts<<",\"committedTicks\":"<<report.committed_ticks<<",\"tickReports\":[";
    for(std::size_t i=0;i<s::hard_max_attempts;++i) {
        if(i) {out<<',';}if(!report.tick_reports[i]) {out<<"null";continue;}const auto& tick=*report.tick_reports[i];
        out<<"{\"queueIndex\":"<<tick.queue_index<<",\"creditConsumed\":";flag(out,tick.credit_consumed);out<<",\"report\":";world_advance_fixture::report_json(out,tick.report);out<<'}';
    }
    out<<"],\"upperBudget\":{\"attempts\":"<<report.upper_budget.attempts<<",\"guardWork\":";work_json(out,report.upper_budget.guard_work);
    out<<",\"guardLogicalPayloadBytes\":"<<report.upper_budget.guard_logical_payload_bytes<<"},\"droppedSeconds\":";number(out,report.dropped_seconds);
    out<<",\"hasWholeTickBacklog\":";flag(out,report.has_whole_tick_backlog);out<<'}';
}

void emit_fixtures(std::ostream& output) {
    const CoutFormat format;need(s::current_binding().configured,"Full scheduler corpus requires existing configured scheduler identity");
    auto corpus=scenarios();
    const auto document=capture([&](auto& out) {
        out<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-scheduler-fixtures\",\"scope\":";
        text(out,"Actual outer pump observations and full actual reports. Intermediate candidate chains are not independent external World/pointer observations. No independent checker or full machine proof is asserted by this writer.");
        out<<",\"layoutSizes\":";world_guard_fixture::layout_sizes_json(out);
        out<<",\"advanceLayoutSizes\":{\"AdvanceReport\":"<<sizeof(a::AdvanceReport)<<",\"Progress\":"<<sizeof(a::Progress)<<",\"ClockAudit\":"<<sizeof(a::ClockAudit)<<",\"CommitWork\":"<<sizeof(a::CommitWork)<<",\"CommitStorage\":"<<sizeof(a::CommitStorage)<<'}';
        out<<",\"schedulerLayoutSizes\":{\"Settings\":"<<sizeof(s::Settings)<<",\"Snapshot\":"<<sizeof(s::Snapshot)<<",\"Binding\":"<<sizeof(s::Binding)<<",\"QueueStep\":"<<sizeof(s::QueueStep)<<",\"Attempt\":"<<sizeof(s::Attempt)<<",\"UpperBudget\":"<<sizeof(s::UpperBudget)<<",\"PumpReport\":"<<sizeof(s::PumpReport)<<",\"Scheduler\":"<<sizeof(s::Scheduler)<<'}';
        out<<",\"maximumDocumentBytes\":"<<maximum_document_bytes<<",\"fixtures\":[";bool first=true;
        for(auto& scenario:corpus) {
            s::Scheduler scheduler(scenario.scheduler);
            for(std::size_t i=0;i<scenario.frames.size();++i) {if(!first) {out<<',';}first=false;frame_json(out,scenario,scheduler,i,scenario.frames[i]);}
        }
        out<<"]}\n";
    });
    world_advance_fixture::validate_document(document);
    output.write(document.data(),static_cast<std::streamsize>(document.size()));need(static_cast<bool>(output),"Full scheduler output write failure");
}
}

int main(int argc,char** argv) {
    try {
        if(argc!=2||std::string_view(argv[1])!="--fixtures") {std::cerr<<"Usage: scheduler_fixtures --fixtures\n";return 2;}
        world_scheduler_fixture::emit_fixtures(std::cout);return 0;
    }catch(const std::exception& error) {std::cerr<<"Full scheduler fixture failed: "<<error.what()<<'\n';return 1;}
    catch(...) {std::cerr<<"Full scheduler fixture failed: unknown exception\n";return 1;}
}
