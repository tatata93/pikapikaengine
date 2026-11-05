// Test-only complete finite transcript. Never queries a guard or rebuilds an
// observed World through add_body; fixed boundary prefixes are copied as values.
#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <bit>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {
namespace s=pikapika::world_static_mesh_flight_controlled_scheduler;
namespace c=s::controlled;
namespace f=controlled_tick_fixture;
namespace g=world_guard_fixture;
namespace d=pikapika::dynamics;
using pikapika::Vec3;
constexpr std::size_t document_limit=64U*1024U*1024U;
void need(bool ok,std::string_view text) {if(!ok) {throw std::runtime_error(std::string(text));}}
void text(std::ostream& out,std::string_view value) {world_advance_fixture::string_json(out,value);}
void flag(std::ostream& out,bool value) {out<<(value?"true":"false");}
void number(std::ostream& out,double value) {
    need(std::isfinite(value),"Finite controlled scheduler transcript cannot emit nonfinite input/result");
    if(value==0&&std::signbit(value)) {out<<"-0";}else {out<<std::setprecision(std::numeric_limits<double>::max_digits10)<<value;}
}
void vec(std::ostream& out,Vec3 v) {out<<'[';number(out,v.x);out<<',';number(out,v.y);out<<',';number(out,v.z);out<<']';}
void interval_json(std::ostream& out,pikapika::interval::Interval value) {out<<'[';number(out,value.lower());out<<',';number(out,value.upper());out<<']';}
void progress(std::ostream& out,s::Progress value) {out<<"{\"time\":";number(out,value.time);out<<",\"ticks\":"<<value.ticks<<'}';}
template<class E,std::size_t N> const char* enum_name(E value,const char* const (&names)[N]) {
    const auto ordinal=static_cast<std::underlying_type_t<E>>(value);need(ordinal<N,"Unknown controlled scheduler result enum");return names[ordinal];
}
const char* status(s::Status x) {constexpr const char* n[]={"waiting","step_budget","awaiting_input","tick_rejected","invalid_input","unsupported_environment","numerical_failure","reentrant"};return enum_name(x,n);}
const char* reason(s::Reason x) {constexpr const char* n[]={"none","busy","environment","binding_unsupported","body_count","plane_count","mesh_count","face_count","packet_count","packet_load_count","elapsed","backlog_limit","sequence_limit","queue_arithmetic","cost_overflow","allocation_failure","unexpected_exception","packet_unavailable","controlled_rejected"};return enum_name(x,n);}
const char* capture_name(s::CaptureState x) {constexpr const char* n[]={"none","partial","complete"};return enum_name(x,n);}
void clock_settings(std::ostream& out,s::Settings x) {out<<"{\"step\":";number(out,x.step_seconds);out<<",\"maxAttempts\":"<<x.max_attempts_per_pump<<'}';}
void snapshot(std::ostream& out,const s::Snapshot& x) {out<<"{\"settings\":";clock_settings(out,x.settings);out<<",\"backlog\":";number(out,x.backlog);out<<",\"sequence\":"<<x.sequence<<",\"busy\":";flag(out,x.busy);out<<'}';}
void binding(std::ostream& out,const s::Binding& x) {
    out<<"{\"profile\":"<<x.profile<<",\"configured\":";flag(out,x.configured);
    for(const auto& entry:std::array<std::pair<const char*,const std::array<char,65>*>,4>{{{"buildId",&x.build_id},{"controlledBuildId",&x.controlled_build_id},{"schedulerBuildId",&x.scheduler_build_id},{"upstreamBuildId",&x.upstream_build_id}}}) {
        need((*entry.second)[64]=='\0',"Unterminated binding");out<<',';text(out,entry.first);out<<':';text(out,entry.second->data());
    }
    out<<'}';
}
void packets(std::ostream& out,const std::vector<c::TickLoadPacket>& x) {out<<'[';for(std::size_t i=0;i<x.size();++i) {if(i) {out<<',';}f::packet_json(out,x[i]);}out<<']';}
void meshes(std::ostream& out,const std::vector<c::StaticMeshSource>& source) {
    out<<'[';
    for(std::size_t i=0;i<source.size();++i) {
        if(i) {out<<',';}const auto& m=source[i];out<<"{\"id\":"<<m.id<<",\"revision\":"<<m.revision<<",\"triangles\":[";
        for(std::size_t j=0;j<m.triangles.size();++j) {
            if(j) {out<<',';}const auto& t=m.triangles[j];out<<"{\"id\":"<<t.id<<",\"vertices\":[";
            for(std::size_t k=0;k<3;++k) {if(k) {out<<',';}vec(out,t.vertices[k]);}out<<"]}";
        }
        out<<"]}";
    }
    out<<']';
}
void boundary(std::ostream& out,const s::Boundary& x) {
    need(x.world.body_count<=x.world.bodies.size()&&x.world.plane_count<=x.world.planes.size(),"Actual fixed boundary prefix exceeds storage");
    c::WorldState observed;observed.gravity=x.world.gravity;
    observed.bodies.assign(x.world.bodies.begin(),x.world.bodies.begin()+x.world.body_count);
    observed.planes.assign(x.world.planes.begin(),x.world.planes.begin()+x.world.plane_count);
    out<<"{\"world\":";f::world_state_json(out,observed);out<<",\"progress\":";progress(out,x.progress);
    out<<",\"originalBodyAddressSame\":[";
    for(std::size_t i=0;i<x.world.body_count;++i) {if(i) {out<<',';}flag(out,x.original_body_address_same[i]);}out<<"]}";
}
void work_grant(std::ostream& out,const pikapika::world_static_mesh_flight_guard::WorkGrant& w) {
    out<<"{\"meshQueries\":"<<w.mesh_queries<<",\"primitiveQueries\":"<<w.primitive_queries<<",\"candidatesExamined\":"<<w.candidates_examined
       <<",\"sqrtRefinements\":"<<w.sqrt_refinements<<",\"propagations\":"<<w.propagations<<",\"planeMetricValues\":"<<w.plane_metric_values
       <<",\"boxValues\":"<<w.box_values<<",\"planeNormLoopIterationsUpper\":"<<w.plane_norm_loop_iterations_upper<<",\"bridgeCallsUpper\":"<<w.bridge_calls_upper<<'}';
}
void report(std::ostream& out,const s::PumpReport& r) {
    out<<"{\"status\":";text(out,status(r.status));out<<",\"reason\":";text(out,reason(r.reason));
    out<<",\"binding\":";binding(out,r.binding);out<<",\"before\":";snapshot(out,r.before);out<<",\"after\":";snapshot(out,r.after);
    out<<",\"requestedElapsed\":";number(out,r.requested_elapsed);out<<",\"elapsedAccepted\":";flag(out,r.elapsed_accepted);
    out<<",\"admittedCredit\":";if(r.admitted_credit) {number(out,*r.admitted_credit);}else {out<<"null";}
    out<<",\"admissionRoundingError\":";if(r.admission_rounding_error) {interval_json(out,*r.admission_rounding_error);}else {out<<"null";}
    out<<",\"progressBefore\":";progress(out,r.progress_before);out<<",\"progressAfter\":";progress(out,r.progress_after);
    out<<",\"capture\":";text(out,capture_name(r.capture));out<<",\"original\":";
    if(r.original) {out<<"{\"settings\":";g::settings_json(out,r.original->settings);out<<",\"meshes\":";meshes(out,r.original->meshes);out<<",\"packets\":";packets(out,r.original->packets);out<<'}';}else {out<<"null";}
    out<<",\"boundaries\":[";
    for(std::size_t i=0;i<r.boundaries.size();++i) {if(i) {out<<',';}if(r.boundaries[i]) {boundary(out,*r.boundaries[i]);}else {out<<"null";}}out<<']';
    out<<",\"queuePlan\":[";
    for(std::size_t i=0;i<r.queue_plan.size();++i) {
        if(i) {out<<',';}if(r.queue_plan[i]) {const auto& q=*r.queue_plan[i];out<<"{\"creditBefore\":";number(out,q.credit_before);out<<",\"proposedAfter\":";number(out,q.proposed_after);out<<",\"roundingError\":";interval_json(out,q.rounding_error);out<<'}';}else {out<<"null";}
    }
    out<<"],\"tickReports\":[";
    for(std::size_t i=0;i<r.tick_reports.size();++i) {
        if(i) {out<<',';}if(r.tick_reports[i]) {const auto& t=*r.tick_reports[i];out<<"{\"queueIndex\":"<<t.queue_index<<",\"packetOrdinal\":"<<t.packet_ordinal<<",\"creditConsumed\":";flag(out,t.credit_consumed);out<<",\"packetConsumed\":";flag(out,t.packet_consumed);out<<",\"report\":";f::report_json(out,t.report);out<<'}';}else {out<<"null";}
    }
    out<<"],\"boundaryCount\":"<<r.boundary_count<<",\"plannedAttempts\":"<<r.planned_attempts<<",\"attempts\":"<<r.attempts<<",\"committedTicks\":"<<r.committed_ticks<<",\"packetsConsumed\":"<<r.packets_consumed;
    out<<",\"upperBudget\":{\"attempts\":"<<r.upper_budget.attempts<<",\"guardWork\":";work_grant(out,r.upper_budget.guard_work);out<<",\"guardLogicalPayloadBytes\":"<<r.upper_budget.guard_logical_payload_bytes<<'}';
    const auto& w=r.work;out<<",\"work\":{\"boundaryCaptures\":"<<w.boundary_captures<<",\"bodyObservations\":"<<w.body_observations<<",\"planeObservations\":"<<w.plane_observations<<",\"meshCopies\":"<<w.mesh_copies<<",\"faceCopies\":"<<w.face_copies<<",\"packetCopies\":"<<w.packet_copies<<",\"loadCopies\":"<<w.load_copies<<'}';
    const auto& b=r.storage;out<<",\"storage\":{\"boundarySlots\":"<<b.boundary_slots<<",\"boundarySizeofBytes\":"<<b.boundary_sizeof_bytes<<",\"addressSlots\":"<<b.address_slots<<",\"addressSizeofBytes\":"<<b.address_sizeof_bytes<<'}';
    out<<",\"droppedSeconds\":";number(out,r.dropped_seconds);out<<",\"hasWholeTickBacklog\":";flag(out,r.has_whole_tick_backlog);out<<'}';
}
class Buffer final:public std::streambuf {
    std::string bytes_;
    void append(const char* p,std::size_t count) {need(count<=document_limit-bytes_.size(),"Complete packet-scheduler document exceeds fixed64MiB budget");bytes_.append(p,count);}
protected:
    std::streamsize xsputn(const char* p,std::streamsize count) override {need(count>=0,"Negative write size");append(p,static_cast<std::size_t>(count));return count;}
    int_type overflow(int_type ch) override {if(traits_type::eq_int_type(ch,traits_type::eof())) {return traits_type::not_eof(ch);}const char value=traits_type::to_char_type(ch);append(&value,1);return ch;}
public:
    const std::string& bytes() const noexcept {return bytes_;}
};
template<class Writer> std::string encoded(Writer writer) {
    Buffer buffer;std::ostream out(&buffer);out.imbue(std::locale::classic());out.exceptions(std::ios::badbit|std::ios::failbit);writer(out);return buffer.bytes();
}
void source(std::ostream& out,const g::Case& scene,s::Progress p,const std::vector<c::TickLoadPacket>& loads) {
    out<<"{\"scene\":";g::input_json(out,scene);out<<",\"progress\":";progress(out,p);out<<",\"packets\":";packets(out,loads);out<<'}';
}
struct Pointers {
    const d::RigidBody* body_data;
    const d::Plane* plane_data;
    const c::StaticMeshSource* mesh_data;
    std::vector<const d::RigidBody*> body,lookup;
    std::vector<std::uint64_t> ids;
    std::vector<const pikapika::sphere_triangle::StaticTriangle*> faces;
    explicit Pointers(const g::Case& x):body_data(x.world.bodies().data()),plane_data(x.world.planes().data()),mesh_data(x.meshes.data()) {
        for(const auto& b:x.world.bodies()) {body.push_back(&b);lookup.push_back(x.world.find_body(b.id));ids.push_back(b.id);}
        for(const auto& m:x.meshes) {faces.push_back(m.triangles.data());}
    }
    void json(std::ostream& out,const g::Case& x) const {
        out<<"{\"bodyCountUnchanged\":";flag(out,body.size()==x.world.bodies().size());out<<",\"bodyStorageStable\":";flag(out,body_data==x.world.bodies().data());
        out<<",\"planeStorageStable\":";flag(out,plane_data==x.world.planes().data());out<<",\"meshStorageStable\":";flag(out,mesh_data==x.meshes.data());out<<",\"bodies\":[";
        for(std::size_t i=0;i<body.size();++i) {
            if(i) {out<<',';}const auto* current=x.world.find_body(ids[i]);out<<"{\"ordinal\":"<<i<<",\"originalId\":"<<ids[i]<<",\"sameOrdinalAddress\":";flag(out,i<x.world.bodies().size()&&body[i]==&x.world.bodies()[i]);
            out<<",\"sameLookupResult\":";flag(out,current==lookup[i]);out<<",\"lookupBeforeMatchesOrdinal\":";flag(out,lookup[i]==body[i]);out<<",\"lookupAfterMatchesOrdinal\":";flag(out,i<x.world.bodies().size()&&current==&x.world.bodies()[i]);out<<'}';
        }
        out<<"],\"meshFaceStorageStable\":[";for(std::size_t i=0;i<faces.size();++i) {if(i) {out<<',';}flag(out,i<x.meshes.size()&&faces[i]==x.meshes[i].triangles.data());}out<<"]}";
    }
};
c::TickLoadPacket load(const g::Case& x,std::uint64_t tick,double force=0) {
    std::vector<c::BodyLoad> rows;
    for(const auto& b:x.world.bodies()) {rows.push_back({b.id,b.is_static?Vec3{-0.,0,-0.}:Vec3{force,-0.,0},Vec3{-0.,0,-0.}});}
    return {c::LoadMode::replace_total_world_loads,tick,std::move(rows)};
}
struct Frame {std::string label;double elapsed;std::vector<c::TickLoadPacket> packets;std::optional<s::Reason> hard_count_reason{};};
struct Scenario {std::string label;g::Case scene;s::Settings settings{.0625,8};s::Progress progress{.125,17};std::vector<Frame> frames;};
std::vector<Scenario> scenarios() {
    std::vector<Scenario> all;const auto base=f::base_case();const double h=.0625;
    Scenario x;x.scene=base.scene;x.label="two-opposite-loads";x.frames={{"both",2*h,{load(x.scene,17,4),load(x.scene,18,-4)}}};all.push_back(x);
    x.label="input-shortage-retry";x.frames={{"first-only",2*h,{load(x.scene,17,4)}},{"remaining-only",0,{load(x.scene,18,-4)}}};all.push_back(x);
    auto bad=load(x.scene,18);bad.loads[0].force_newtons={0,-4096,0};
    x.label="guard-refusal-retry";x.frames={{"one-success-one-rejection",2*h,{load(x.scene,17,4),bad}},{"safe-retry0",0,{load(x.scene,18,-4)}}};all.push_back(x);
    x.label="stale-then-corrected";x.frames={{"first",2*h,{load(x.scene,17,4)}},{"stale",0,{load(x.scene,17,4)}},{"correct",0,{load(x.scene,18,-4)}}};all.push_back(x);
    bad=load(x.scene,18);bad.mode=static_cast<c::LoadMode>(99);x.label="invalid-second-mode";x.frames={{"prefix-and-mode-refusal",2*h,{load(x.scene,17,4),bad}}};all.push_back(x);
    x.label="unused-future-tail";x.frames={{"due0",0,{bad}},{"one-due-extra-invalid",h,{load(x.scene,17,4),bad}}};all.push_back(x);
    x.label="max-attempts1";x.settings.max_attempts_per_pump=1;x.frames={{"two-inputs-one-budget",2*h,{load(x.scene,17,4),load(x.scene,18,-4)}},{"suffix",0,{load(x.scene,18,-4)}}};all.push_back(x);
    x.settings.max_attempts_per_pump=8;x.label="empty-then-provided";x.frames={{"await",2*h,{}},{"provided",0,{load(x.scene,17,4),load(x.scene,18,-4)}}};all.push_back(x);
    x.label="eight-ticks";x.frames={{"eight",.5,{}}};for(std::uint64_t i=0;i<8;++i) {x.frames[0].packets.push_back(load(x.scene,17+i));}all.push_back(x);
    x.label="hard-packets9";x.frames={{"count9",h,std::vector<c::TickLoadPacket>(9,load(x.scene,17))}};all.push_back(x);
    bad=load(x.scene,18);bad.loads.resize(9);x.label="hard-future-loads9";x.frames={{"unused-but-unbounded",0,{load(x.scene,17,4),bad}}};all.push_back(x);
    x.label="invalid-elapsed";x.frames={{"negative",-1,{load(x.scene,17)}},{"too-large",2,{load(x.scene,17)}}};all.push_back(x);
    x.label="backlog-limit";x.frames={{"fill",1,{}},{"overflow",h,{}},{"retry0-no-input",0,{}}};all.push_back(x);
    x.label="fractional-credit";const double below=std::nextafter(h,0.);x.frames={{"below",below,{}},{"zero-still-below",0,{}},{"complement",h-below,{load(x.scene,17)}}};all.push_back(x);
    Scenario hz120;hz120.scene=base.scene;hz120.label="default120Hz-rounded-credit";hz120.settings=s::Settings{};
    hz120.frames={{"cap4",.05,{}},{"drain0",0,{}},{"fractional",.001,{}}};
    for(std::uint64_t i=0;i<8;++i) {hz120.frames[0].packets.push_back(load(hz120.scene,17+i));hz120.frames[1].packets.push_back(load(hz120.scene,21+i));}
    all.push_back(std::move(hz120));
    Scenario hard;hard.scene=base.scene;hard.label="body-count9";
    for(std::uint64_t i=0;i<8;++i) {hard.scene.world.add_body(d::make_sphere(1000+i,.25,2,{20.0*static_cast<double>(i+1),4,8}));}
    hard.frames={{"before-fixed-capture",h,{load(hard.scene,17)},s::Reason::body_count}};all.push_back(std::move(hard));
    hard=Scenario{};hard.scene=base.scene;hard.label="plane-count17";
    for(std::uint64_t i=0;i<16;++i) {hard.scene.world.add_plane({2000+i,{0,1,0},-static_cast<double>(i+1),{}});}
    hard.frames={{"before-fixed-capture",h,{load(hard.scene,17)},s::Reason::plane_count}};all.push_back(std::move(hard));
    hard=Scenario{};hard.scene=base.scene;hard.label="mesh-count5";
    for(std::uint64_t i=0;i<4;++i) {auto m=base.scene.meshes[0];m.id=3000+i;hard.scene.meshes.push_back(std::move(m));}
    hard.frames={{"before-owned-capture",h,{load(hard.scene,17)},s::Reason::mesh_count}};all.push_back(std::move(hard));
    hard=Scenario{};hard.scene=base.scene;hard.label="face-count65";
    const auto original_triangle=hard.scene.meshes[0].triangles[0];
    for(std::uint64_t i=0;i<64;++i) {auto triangle=original_triangle;triangle.id=20+i;hard.scene.meshes[0].triangles.push_back(triangle);}
    hard.frames={{"before-owned-capture",h,{load(hard.scene,17)},s::Reason::face_count}};all.push_back(std::move(hard));
    // Reuse static scene/body/settings originals at the explicit scheduler step.
    // Original guard fixture H is NOT claimed rerun unchanged in this corpus.
    for(auto scene:g::cases()) {
        Scenario inherited;inherited.label="scene-"+scene.name;inherited.scene=std::move(scene);inherited.scene.horizon=h;
        inherited.frames={{"one-due",h,{load(inherited.scene,17)}}};all.push_back(std::move(inherited));
    }
    return all;
}
void emit(std::ostream& final) {
    need(s::current_binding().configured,"Configured Native packet scheduler library required");
    Buffer buffer;std::ostream out(&buffer);out.imbue(std::locale::classic());out.exceptions(std::ios::badbit|std::ios::failbit);
    out<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-controlled-scheduler-fixtures\",\"scope\":\"Actual finite input before/after, actual fixed boundaries and actual returned controlled reports. No guard requery, candidate-built World, child pointer-row fabrication, nonfinite full codec, allocator fault injection, independent-reference or GNU acceptance claim.\",\"maximumDocumentBytes\":"<<document_limit;
    out<<",\"layoutSizes\":";g::layout_sizes_json(out);out<<",\"controlledSchedulerLayoutSizes\":{\"PumpReport\":"<<sizeof(s::PumpReport)<<",\"WorldState\":"<<sizeof(s::WorldState)<<",\"Boundary\":"<<sizeof(s::Boundary)<<",\"OptionalBoundary\":"<<sizeof(std::optional<s::Boundary>)<<",\"Original\":"<<sizeof(s::Original)<<",\"Attempt\":"<<sizeof(s::Attempt)<<",\"OptionalAttempt\":"<<sizeof(std::optional<s::Attempt>)<<",\"Storage\":"<<sizeof(s::Storage)<<"},\"fixtures\":[";
    bool first=true;std::size_t hard_assertions=0;
    for(auto scenario:scenarios()) {
        scenario.scene.horizon=scenario.settings.step_seconds;s::Scheduler scheduler(scenario.settings);
        for(std::size_t i=0;i<scenario.frames.size();++i) {
            const auto& frame=scenario.frames[i];const auto before=encoded([&](std::ostream& o){source(o,scenario.scene,scenario.progress,frame.packets);});
            const auto source_before=encoded([&](std::ostream& o){o<<"{\"settings\":";g::settings_json(o,scenario.scene.settings);o<<",\"meshes\":";meshes(o,scenario.scene.meshes);o<<",\"packets\":";packets(o,frame.packets);o<<'}';});
            const Pointers pointers(scenario.scene);
            auto actual=scheduler.pump(scenario.scene.world,scenario.scene.meshes,scenario.scene.settings,scenario.progress,frame.elapsed,frame.packets);
            if(frame.hard_count_reason) {
                need(actual.status==s::Status::invalid_input&&actual.reason==*frame.hard_count_reason&&actual.capture==s::CaptureState::none&&!actual.original&&
                     !actual.elapsed_accepted&&actual.attempts==0&&actual.boundary_count==0&&actual.after.sequence==actual.before.sequence&&actual.after.backlog==actual.before.backlog,
                     "Hard count failed to refuse before bounded capture/admission");++hard_assertions;
            }
            const auto after=encoded([&](std::ostream& o){source(o,scenario.scene,scenario.progress,frame.packets);});
            const auto source_after=encoded([&](std::ostream& o){o<<"{\"settings\":";g::settings_json(o,scenario.scene.settings);o<<",\"meshes\":";meshes(o,scenario.scene.meshes);o<<",\"packets\":";packets(o,frame.packets);o<<'}';});
            need(source_before==source_after,"Caller source/settings/packet changed across real pump");
            if(!first) {out<<',';}first=false;
            out<<"{\"name\":";text(out,scenario.label+"/"+frame.label);out<<",\"scenario\":";text(out,scenario.label);out<<",\"frameOrdinal\":"<<i<<",\"requestedElapsed\":";number(out,frame.elapsed);
            out<<",\"input\":"<<before<<",\"inputAfter\":"<<after<<",\"report\":";report(out,actual);
            out<<",\"observations\":{\"pumpCalls\":1,\"sourceSettingsPacketsUnchanged\":";flag(out,source_before==source_after);out<<",\"pointerStability\":";pointers.json(out,scenario.scene);out<<"}}";
        }
    }
    need(hard_assertions==4,"All four fixed/source hard-count boundary cases must execute");
    out<<"],\"directedHardCountAssertions\":"<<hard_assertions<<"}\n";const auto& bytes=buffer.bytes();world_advance_fixture::validate_document(bytes);final.write(bytes.data(),static_cast<std::streamsize>(bytes.size()));need(static_cast<bool>(final),"Final complete transcript write failed");
}
}
int main(int argc,char** argv) {
    try {need(argc==2&&std::string_view(argv[1])=="--fixtures","Use --fixtures for the complete finite transcript");emit(std::cout);return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
