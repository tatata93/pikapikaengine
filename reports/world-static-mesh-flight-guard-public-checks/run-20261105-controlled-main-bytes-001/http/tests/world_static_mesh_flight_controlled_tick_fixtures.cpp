#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <type_traits>

namespace controlled_tick_fixture {
namespace {
namespace d=pikapika::dynamics;
using pikapika::Vec3;
void need(bool ok,const char* text) {if(!ok) {throw std::runtime_error(text);}}
void number(std::ostream& out,double x) {
    need(std::isfinite(x),"Nonfinite controlled fixture number: unit-only input cannot be emitted");
    if(x==0&&std::signbit(x)) {out<<"-0";}else {out<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x;}
}
void vec(std::ostream& out,Vec3 v) {out<<'[';number(out,v.x);out<<',';number(out,v.y);out<<',';number(out,v.z);out<<']';}
template<class E,std::size_t N> const char* name(E e,const char* const (&names)[N]) {
    const auto i=static_cast<std::underlying_type_t<E>>(e);need(i<N,"Unknown controlled result enum");return names[i];
}
const char* status(c::Status s) {constexpr const char* n[]={"committed","not_certified","invalid_input","unsupported_environment","numerical_failure"};return name(s,n);}
const char* reason(c::Reason s) {constexpr const char* n[]={"none","environment","binding_unsupported","body_count","plane_count","mesh_count","face_count","packet_count","original_body","packet_mode","expected_tick","packet_id","packet_duplicate","packet_load","static_load","private_copy","child_failed","child_inconsistent","origin_mismatch","candidate_mismatch","destination_mismatch","allocation_failure","unexpected_exception"};return name(s,n);}
const char* stage(c::Stage s) {constexpr const char* n[]={"environment","binding","counts","capture","original_validation","packet","staging","child","post_child","commit_preparation"};return name(s,n);}
const char* capture(c::CaptureState s) {constexpr const char* n[]={"none","partial","complete"};return name(s,n);}
void flag(std::ostream& out,bool x) {out<<(x?"true":"false");}
template<class T> void index(std::ostream& out,const std::optional<T>& x) {if(x) {out<<*x;}else {out<<"null";}}
void progress(std::ostream& out,c::advance::Progress p) {out<<"{\"time\":";number(out,p.time);out<<",\"ticks\":"<<p.ticks<<'}';}
void binding(std::ostream& out,const c::Binding& b) {
    need(b.build_id[64]=='\0'&&b.upstream_build_id[64]=='\0',"Binding unterminated");
    out<<"{\"profile\":"<<b.profile<<",\"configured\":";flag(out,b.configured);
    out<<",\"buildId\":";world_advance_fixture::string_json(out,b.build_id.data());
    out<<",\"upstreamBuildId\":";world_advance_fixture::string_json(out,b.upstream_build_id.data());out<<'}';
}
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
void work(std::ostream& out,const c::Work& w) {
    out<<'{';bool first=true;
#define FIELD(key,field) if(!first) {out<<',';}first=false;out<<'"'<<key<<"\":"<<w.field;
    FIELD("originalBodiesCopied",original_bodies_copied) FIELD("originalPlanesCopied",original_planes_copied)
    FIELD("originalMeshesCopied",original_meshes_copied) FIELD("originalFacesCopied",original_faces_copied) FIELD("packetRowsCopied",packet_rows_copied)
    FIELD("originalValidationsAttempted",original_validations_attempted) FIELD("originalValidationsReturned",original_validations_returned)
    FIELD("packetRowsChecked",packet_rows_checked) FIELD("packetValidationsAttempted",packet_validations_attempted) FIELD("packetValidationsReturned",packet_validations_returned)
    FIELD("privateCopiesAttempted",private_copies_attempted) FIELD("privateCopiesReturned",private_copies_returned)
    FIELD("stagedBodiesCopied",staged_bodies_copied) FIELD("stagedPlanesCopied",staged_planes_copied)
    FIELD("privateAfterBodiesCopied",private_after_bodies_copied) FIELD("privateAfterPlanesCopied",private_after_planes_copied)
    FIELD("childAttempts",child_attempts) FIELD("childReturns",child_returns) FIELD("candidateBodiesChecked",candidate_bodies_checked)
    FIELD("candidateValidationsAttempted",candidate_validations_attempted) FIELD("candidateValidationsReturned",candidate_validations_returned)
    FIELD("originBodiesChecked",origin_bodies_checked) FIELD("originPlanesChecked",origin_planes_checked) FIELD("originMeshesChecked",origin_meshes_checked)
    FIELD("originFacesChecked",origin_faces_checked) FIELD("originPacketRowsChecked",origin_packet_rows_checked)
    FIELD("destinationLookups",destination_lookups) FIELD("destinationsResolved",destinations_resolved)
    FIELD("bodyAssignments",body_assignments) FIELD("progressAssignments",progress_assignments)
#undef FIELD
    out<<'}';
}
void storage(std::ostream& out,const c::Storage& s) {
    out<<"{\"candidateSlots\":"<<s.candidate_slots<<",\"destinationSlots\":"<<s.destination_slots
       <<",\"candidateSizeofBytes\":"<<s.candidate_sizeof_bytes<<",\"destinationSizeofBytes\":"<<s.destination_sizeof_bytes<<'}';
}
std::string world_text(const d::World& w) {std::ostringstream out;out.imbue(std::locale::classic());world_guard_fixture::world_json(out,w);return out.str();}
template<class T,class Writer> std::string encoded(const T& value,Writer writer) {std::ostringstream out;out.imbue(std::locale::classic());writer(out,value);return out.str();}
void input(std::ostream& out,const Case& x) {out<<"{\"scene\":";world_guard_fixture::input_json(out,x.scene);out<<",\"progress\":";progress(out,x.progress);out<<",\"packet\":";packet_json(out,x.packet);out<<'}';}
c::TickLoadPacket rows(const d::World& world,std::uint64_t tick) {
    std::vector<c::BodyLoad> values;
    for(const auto& b:world.bodies()) {values.push_back({b.id,b.is_static?Vec3{-0.,0.,-0.}:b.force,b.is_static?Vec3{0.,-0.,0.}:b.torque});}
    return {c::LoadMode::replace_total_world_loads,tick,std::move(values)};
}
void directed(std::vector<Case>& out,Case x,const char* n,c::Status s,c::Reason r=c::Reason::none) {x.name=n;x.expected=s;x.reason=r;out.push_back(std::move(x));}
void sizes(std::ostream& out) {
    out<<"{\"BodyLoad\":"<<sizeof(c::BodyLoad)<<",\"TickLoadPacket\":"<<sizeof(c::TickLoadPacket)<<",\"Binding\":"<<sizeof(c::Binding)
       <<",\"WorldState\":"<<sizeof(c::WorldState)<<",\"OriginalSnapshot\":"<<sizeof(c::OriginalSnapshot)<<",\"Mapping\":"<<sizeof(c::Mapping)
       <<",\"Work\":"<<sizeof(c::Work)<<",\"Storage\":"<<sizeof(c::Storage)<<",\"ControlledReport\":"<<sizeof(c::ControlledReport)<<'}';
}
}

void packet_json(std::ostream& out,const c::TickLoadPacket& p) {
    out<<"{\"mode\":"<<static_cast<unsigned>(p.mode)<<",\"expectedTick\":"<<p.expected_tick<<",\"loads\":[";
    for(std::size_t i=0;i<p.loads.size();++i) {if(i) {out<<',';}const auto& row=p.loads[i];out<<"{\"bodyId\":"<<row.body_id<<",\"force\":";vec(out,row.force_newtons);out<<",\"torque\":";vec(out,row.torque_newton_meters);out<<'}';}out<<"]}";
}
void world_state_json(std::ostream& out,const c::WorldState& s) {
    out<<"{\"gravity\":";vec(out,s.gravity);out<<",\"bodies\":[";
    for(std::size_t i=0;i<s.bodies.size();++i) {if(i) {out<<',';}world_guard_fixture::body_json(out,s.bodies[i]);}
    out<<"],\"planes\":[";
    for(std::size_t i=0;i<s.planes.size();++i) {
        if(i) {out<<',';}const auto& p=s.planes[i];out<<"{\"id\":"<<p.id<<",\"normal\":";vec(out,p.normal);out<<",\"offset\":";number(out,p.offset);
        out<<",\"material\":{\"restitution\":";number(out,p.material.restitution);out<<",\"friction\":";number(out,p.material.friction);out<<"}}";
    }
    out<<"]}";
}
void report_json(std::ostream& out,const c::ControlledReport& r) {
    out<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"committed\":";flag(out,r.committed);
    out<<",\"requestedDt\":";number(out,r.requested_dt);out<<",\"advancedDt\":";number(out,r.advanced_dt);out<<",\"originalProgress\":";progress(out,r.original_progress);
    out<<",\"requestedMode\":"<<static_cast<unsigned>(r.requested_mode)<<",\"requestedTick\":"<<r.requested_tick<<",\"binding\":";binding(out,r.binding);
    out<<",\"failure\":";
    if(r.failure) {out<<"{\"stage\":\""<<stage(r.failure->stage)<<"\",\"bodyOrdinal\":";index(out,r.failure->body_ordinal);out<<",\"packetOrdinal\":";index(out,r.failure->packet_ordinal);out<<",\"meshOrdinal\":";index(out,r.failure->mesh_ordinal);out<<'}';}else {out<<"null";}
    out<<",\"capture\":\""<<capture(r.capture)<<"\",\"stagedCapture\":\""<<capture(r.staged_capture)<<"\",\"privateAfterCapture\":\""<<capture(r.private_after_capture)<<"\",\"originalBodiesValidated\":";flag(out,r.original_bodies_validated);
    out<<",\"original\":";
    if(r.original) {const auto& s=*r.original;out<<"{\"horizon\":";number(out,s.horizon);out<<",\"settings\":";world_guard_fixture::settings_json(out,s.settings);out<<",\"progress\":";progress(out,s.progress);out<<",\"world\":";world_state_json(out,s.world);out<<",\"meshes\":";meshes(out,s.meshes);out<<",\"packet\":";packet_json(out,s.packet);out<<'}';}else {out<<"null";}
    out<<",\"mappings\":[";
    for(std::size_t i=0;i<r.mappings.size();++i) {if(i) {out<<',';}if(r.mappings[i]) {const auto& m=*r.mappings[i];out<<"{\"packetOrdinal\":"<<m.packet_ordinal<<",\"bodyOrdinal\":"<<m.body_ordinal<<",\"bodyId\":"<<m.body_id<<'}';}else {out<<"null";}}out<<']';
    out<<",\"stagedBefore\":";if(r.staged_before) {world_state_json(out,*r.staged_before);}else {out<<"null";}
    out<<",\"privateAfter\":";if(r.private_after) {world_state_json(out,*r.private_after);}else {out<<"null";}
    out<<",\"privateProgressAfter\":";if(r.private_progress_after) {progress(out,*r.private_progress_after);}else {out<<"null";}
    out<<",\"child\":";if(r.child) {world_advance_fixture::report_json(out,*r.child);}else {out<<"null";}
    out<<",\"work\":";work(out,r.work);out<<",\"storage\":";storage(out,r.storage);out<<",\"message\":";world_advance_fixture::string_json(out,r.message);out<<'}';
}
Case base_case() {
    Case x;x.scene.world.gravity={-0.,0.,-0.};auto b=d::make_sphere(101,.25,2,{0.,4.,-0.});b.force={3.,-0.,0.};b.torque={-0.,0.,-0.};x.scene.world.add_body(b);
    x.scene.world.add_plane({201,{-0.,1.,-0.},-0.,{}});
    c::StaticMeshSource source;source.id=301;source.revision=1;
    source.triangles.push_back({11,{Vec3{-64.,-4.,-64.},Vec3{128.,-4.,-64.},Vec3{-64.,-4.,128.}}});
    x.scene.meshes.push_back(std::move(source));
    x.scene.horizon=.0625;x.scene.settings.contact_margin=0.;x.packet=rows(x.scene.world,17);return x;
}
std::vector<Case> cases() {
    std::vector<Case> out;
    for(auto source:world_guard_fixture::cases()) {Case x;x.name="guard-"+source.name;x.scene=std::move(source);x.packet=rows(x.scene.world,17);out.push_back(std::move(x));}
    using S=c::Status;using R=c::Reason;auto x=base_case();
    x.packet.loads[0].force_newtons={0.,-0.,0.};directed(out,x,"zero-total-load",S::committed);
    x=base_case();x.packet.loads[0].force_newtons={5.,-0.,0.};directed(out,x,"replace-original-three-by-five",S::committed);
    x=base_case();x.packet.expected_tick=16;directed(out,x,"stale-tick",S::invalid_input,R::expected_tick);
    x=base_case();x.packet.expected_tick=18;directed(out,x,"future-tick",S::invalid_input,R::expected_tick);
    x=base_case();x.packet.expected_tick=std::numeric_limits<std::uint64_t>::max();directed(out,x,"uint64-maximum-packet-tick",S::invalid_input,R::expected_tick);
    x=base_case();x.packet.mode=static_cast<c::LoadMode>(42);directed(out,x,"unknown-mode",S::invalid_input,R::packet_mode);
    x=base_case();x.packet.loads.clear();directed(out,x,"missing-row",S::invalid_input,R::packet_count);
    x=base_case();x.packet.loads[0].body_id=999;directed(out,x,"unknown-body",S::invalid_input,R::packet_id);
    x=base_case();x.packet.loads[0].body_id=0;directed(out,x,"zero-body-id",S::invalid_input,R::packet_id);
    x=base_case();x.packet.loads[0].body_id=9007199254740992ULL;directed(out,x,"unsafe-body-id",S::invalid_input,R::packet_id);
    x=base_case();x.packet.loads[0].force_newtons.x=0x1p100;directed(out,x,"replacement-force-out-of-domain",S::invalid_input,R::packet_load);
    x=base_case();x.packet.loads[0].torque_newton_meters.z=0x1p100;directed(out,x,"replacement-torque-out-of-domain",S::invalid_input,R::packet_load);
    x=base_case();x.scene.world.find_body(101)->force.x=0x1p100;x.packet.loads[0].force_newtons={0,0,0};directed(out,x,"original-force-cannot-be-repaired",S::invalid_input,R::original_body);
    x=base_case();x.scene.world.find_body(101)->mass=-1;directed(out,x,"original-mass-invalid",S::invalid_input,R::original_body);
    x=base_case();x.scene.horizon=0;directed(out,x,"zero-horizon-private-clock-refusal",S::invalid_input,R::child_failed);
    x=base_case();x.scene.horizon=.125;directed(out,x,"horizon-too-long",S::invalid_input,R::child_failed);
    x=base_case();x.progress.time=-1;directed(out,x,"negative-progress-time",S::invalid_input,R::child_failed);
    x=base_case();x.progress.ticks=c::advance::maximum_ticks;x.packet.expected_tick=x.progress.ticks;directed(out,x,"progress-tick-exhausted",S::invalid_input,R::child_failed);
    x=base_case();x.packet.loads[0].force_newtons={0,-4096,0};directed(out,x,"loads-enter-plane-refusal",S::not_certified,R::child_failed);
    x=base_case();for(auto& v:x.scene.meshes[0].triangles[0].vertices) {v={0.,-4.,0.};}directed(out,x,"degenerate-private-mesh-refusal",S::not_certified,R::child_failed);
    x=base_case();x.scene.world.find_body(101)->is_static=true;x.packet=rows(x.scene.world,17);directed(out,x,"static-exact-signed-zero",S::committed);
    x.packet.loads[0].force_newtons.x=.125;directed(out,x,"static-nonzero-force",S::invalid_input,R::static_load);
    x=base_case();x.scene.world.find_body(101)->is_static=true;x.packet=rows(x.scene.world,17);x.packet.loads[0].torque_newton_meters.z=.125;directed(out,x,"static-nonzero-torque",S::invalid_input,R::static_load);
    x=base_case();x.scene.world.add_body(d::make_sphere(102,.25,2,{8,4,0}));x.packet=rows(x.scene.world,17);x.packet.loads[1].body_id=101;directed(out,x,"duplicate-packet-body",S::invalid_input,R::packet_duplicate);
    x=base_case();x.scene.world.add_body(d::make_sphere(102,.25,2,{8,4,0}));x.packet=rows(x.scene.world,17);std::reverse(x.packet.loads.begin(),x.packet.loads.end());directed(out,x,"packet-order-maps-to-original-ordinals",S::committed);
    x=base_case();x.scene.world=d::World{};x.scene.world.gravity={-0.,0.,-0.};x.packet=rows(x.scene.world,17);directed(out,x,"empty-world-empty-packet",S::committed);
    x=base_case();x.scene.meshes.clear();directed(out,x,"no-mesh-hard-reject",S::invalid_input,R::mesh_count);
    x=base_case();while(x.scene.meshes.size()<5) {x.scene.meshes.push_back(x.scene.meshes.front());}directed(out,x,"five-mesh-hard-reject",S::invalid_input,R::mesh_count);
    x=base_case();while(x.scene.meshes[0].triangles.size()<65) {x.scene.meshes[0].triangles.push_back(x.scene.meshes[0].triangles.front());}directed(out,x,"65-faces-hard-reject",S::invalid_input,R::face_count);
    x=base_case();while(x.packet.loads.size()<9) {x.packet.loads.push_back(x.packet.loads.front());}directed(out,x,"nine-packet-rows-hard-reject",S::invalid_input,R::packet_count);
    x=base_case();for(std::uint64_t i=0;i<8;++i) {x.scene.world.add_body(d::make_sphere(102+i,.25,2,{double(i)*8+8,4,0}));}x.packet=rows(x.scene.world,17);directed(out,x,"nine-bodies-hard-reject",S::invalid_input,R::body_count);
    x=base_case();for(std::uint64_t i=0;i<16;++i) {x.scene.world.add_plane({202+i,{0,1,0},-double(i)-1,{}});}directed(out,x,"17-planes-hard-reject",S::invalid_input,R::plane_count);
    return out;
}

void emit_fixtures(std::ostream& output) {
    std::ostringstream out;out.imbue(std::locale::classic());
    out<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-controlled-tick-fixtures\",\"scope\":\"Actual external before/after and actual private snapshots/child; no fabricated intermediate state, no transaction/GNU/machine proof beyond reported finite runs.\",\"layoutSizes\":";
    world_guard_fixture::layout_sizes_json(out);
    out<<",\"advanceLayoutSizes\":{\"AdvanceReport\":"<<sizeof(c::advance::AdvanceReport)<<",\"Progress\":"<<sizeof(c::advance::Progress)<<",\"ClockAudit\":"<<sizeof(c::advance::ClockAudit)<<",\"CommitWork\":"<<sizeof(c::advance::CommitWork)<<",\"CommitStorage\":"<<sizeof(c::advance::CommitStorage)<<"},\"controlledLayoutSizes\":";sizes(out);
    out<<",\"maximumDocumentBytes\":67108864,\"fixtures\":[";std::size_t emitted=0;
    const auto emit=[&](Case& x,std::string_view scenario,std::size_t frame) {
        const auto world_before=world_text(x.scene.world);const auto progress_before=x.progress;
        const auto packet_before=encoded(x.packet,packet_json),meshes_before=encoded(x.scene.meshes,meshes),settings_before=encoded(x.scene.settings,world_guard_fixture::settings_json);
        const auto horizon_before=std::bit_cast<std::uint64_t>(x.scene.horizon);
        const auto gravity_before=std::array{std::bit_cast<std::uint64_t>(x.scene.world.gravity.x),std::bit_cast<std::uint64_t>(x.scene.world.gravity.y),std::bit_cast<std::uint64_t>(x.scene.world.gravity.z)};
        const c::WorldState plane_state_before{{}, {},x.scene.world.planes()};
        const auto planes_before=encoded(plane_state_before,world_state_json);
        std::ostringstream input_before;input_before.imbue(std::locale::classic());input(input_before,x);
        std::vector<const d::RigidBody*> pointers,lookups;std::vector<std::uint64_t> ids;
        for(const auto& b:x.scene.world.bodies()) {pointers.push_back(&b);lookups.push_back(x.scene.world.find_body(b.id));ids.push_back(b.id);}
        const auto* body_data=x.scene.world.bodies().data();const auto* plane_data=x.scene.world.planes().data();const auto* mesh_data=x.scene.meshes.data();
        std::vector<const pikapika::sphere_triangle::StaticTriangle*> face_data;for(const auto& m:x.scene.meshes) {face_data.push_back(m.triangles.data());}
        auto report=c::advance_with_loads(x.scene.world,x.scene.meshes,x.scene.horizon,x.scene.settings,x.progress,x.packet);
        if(x.expected) {need(report.status==*x.expected,"Unexpected controlled fixture status");}
        if(x.reason) {need(report.reason==*x.reason,"Unexpected controlled fixture reason");}
        const auto world_after=world_text(x.scene.world);
        need(report.work.child_attempts<=1&&report.work.child_returns<=report.work.child_attempts,"More than one actual child");
        if(!report.committed) {need(world_before==world_after&&std::bit_cast<std::uint64_t>(progress_before.time)==std::bit_cast<std::uint64_t>(x.progress.time)&&progress_before.ticks==x.progress.ticks,"Failed controlled tick changed original");}
        if(emitted++) {out<<',';}out<<"{\"name\":";world_advance_fixture::string_json(out,x.name);out<<",\"scenario\":";world_advance_fixture::string_json(out,scenario);out<<",\"frameOrdinal\":"<<frame<<",\"input\":"<<input_before.str()<<",\"inputAfter\":";input(out,x);
        out<<",\"worldBefore\":"<<world_before<<",\"worldAfter\":"<<world_after<<",\"progressBefore\":";progress(out,progress_before);out<<",\"progressAfter\":";progress(out,x.progress);out<<",\"report\":";report_json(out,report);
        out<<",\"observations\":{\"captureComplete\":true,\"controlledCalls\":1,\"worldUnchanged\":";flag(out,world_before==world_after);
        out<<",\"progressUnchanged\":";flag(out,std::bit_cast<std::uint64_t>(progress_before.time)==std::bit_cast<std::uint64_t>(x.progress.time)&&progress_before.ticks==x.progress.ticks);
        out<<",\"packetUnchanged\":";flag(out,packet_before==encoded(x.packet,packet_json));
        out<<",\"meshesUnchanged\":";flag(out,meshes_before==encoded(x.scene.meshes,meshes));
        out<<",\"settingsUnchanged\":";flag(out,settings_before==encoded(x.scene.settings,world_guard_fixture::settings_json));
        out<<",\"horizonUnchanged\":";flag(out,horizon_before==std::bit_cast<std::uint64_t>(x.scene.horizon));
        const c::WorldState plane_state_after{{},{},x.scene.world.planes()};
        out<<",\"planesUnchanged\":";flag(out,planes_before==encoded(plane_state_after,world_state_json));
        out<<",\"gravityUnchanged\":";flag(out,gravity_before==std::array{std::bit_cast<std::uint64_t>(x.scene.world.gravity.x),std::bit_cast<std::uint64_t>(x.scene.world.gravity.y),std::bit_cast<std::uint64_t>(x.scene.world.gravity.z)});
        out<<",\"pointerStability\":{\"bodyCountUnchanged\":";flag(out,pointers.size()==x.scene.world.bodies().size());
        out<<",\"bodyStorageStable\":";flag(out,body_data==x.scene.world.bodies().data());out<<",\"planeStorageStable\":";flag(out,plane_data==x.scene.world.planes().data());out<<",\"meshStorageStable\":";flag(out,mesh_data==x.scene.meshes.data());out<<",\"bodies\":[";
        for(std::size_t i=0;i<pointers.size();++i) {if(i) {out<<',';}const auto* found=x.scene.world.find_body(ids[i]);out<<"{\"ordinal\":"<<i<<",\"originalId\":"<<ids[i]<<",\"sameOrdinalAddress\":";flag(out,i<x.scene.world.bodies().size()&&pointers[i]==&x.scene.world.bodies()[i]);out<<",\"sameLookupResult\":";flag(out,found==lookups[i]);out<<",\"lookupBeforeMatchesOrdinal\":";flag(out,lookups[i]==pointers[i]);out<<",\"lookupAfterMatchesOrdinal\":";flag(out,i<x.scene.world.bodies().size()&&found==&x.scene.world.bodies()[i]);out<<'}';}
        out<<"],\"meshFaceStorageStable\":[";for(std::size_t i=0;i<face_data.size();++i) {if(i) {out<<',';}flag(out,face_data[i]==x.scene.meshes[i].triangles.data());}out<<"]}}}";
    };
    auto all=cases();for(auto& x:all) {emit(x,x.name,0);}
    auto seq=base_case();seq.packet.loads[0].force_newtons={4,0,0};seq.name="analytic-first-positive";seq.expected=c::Status::committed;seq.reason=c::Reason::none;emit(seq,"two-tick-opposite-loads",0);
    need(seq.scene.world.find_body(101)->position.x==1.0/256&&seq.scene.world.find_body(101)->velocity.x==1.0/8,"First dyadic analytic mismatch");
    seq.packet.expected_tick=seq.progress.ticks;seq.packet.loads[0].force_newtons={-4,0,0};seq.name="analytic-second-negative";emit(seq,"two-tick-opposite-loads",1);
    need(seq.scene.world.find_body(101)->position.x==1.0/128&&seq.scene.world.find_body(101)->velocity.x==0,"Second dyadic analytic mismatch");
    seq.name="analytic-replay-is-stale";seq.expected=c::Status::invalid_input;seq.reason=c::Reason::expected_tick;emit(seq,"two-tick-opposite-loads",2);
    seq=base_case();seq.packet.loads[0].force_newtons={0,-4096,0};seq.name="refused-packet-retains-origin";seq.expected=c::Status::not_certified;seq.reason=c::Reason::child_failed;emit(seq,"refusal-then-safe-retry",0);
    seq.packet.loads[0].force_newtons={0,-0.,0};seq.name="retry-same-tick-zero-load";seq.expected=c::Status::committed;seq.reason=c::Reason::none;emit(seq,"refusal-then-safe-retry",1);
    out<<"]}\n";const auto document=out.str();need(document.size()<=67108864,"Controlled full document budget");world_advance_fixture::validate_document(document);output<<document;
}
}
