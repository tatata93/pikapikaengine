#include "pikapika/world_static_mesh_flight_controlled_tick.hpp"
#include <bit>
#include <cfloat>
#include <cmath>
#include <limits>
#include <new>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Controlled tick requires strict binary64 evaluation.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#endif

namespace pikapika::world_static_mesh_flight_controlled_tick {
namespace {
namespace g=world_static_mesh_flight_guard;
using Body=dynamics::RigidBody;
using Buffer=std::array<Body,hard_max_bodies>;
using Destinations=std::array<Body*,hard_max_bodies>;
static_assert(sizeof(double)==8&&std::numeric_limits<double>::digits==53&&std::numeric_limits<double>::is_iec559&&FLT_EVAL_METHOD==0);
static_assert(std::is_copy_constructible_v<dynamics::World>);
static_assert(std::is_nothrow_copy_assignable_v<Body>&&std::is_nothrow_copy_constructible_v<Body>);
static_assert(std::is_nothrow_copy_assignable_v<advance::Progress>);
static_assert(std::is_nothrow_copy_constructible_v<GuardSettings>);
static_assert(std::is_nothrow_move_constructible_v<advance::AdvanceReport>);
static_assert(std::is_nothrow_move_constructible_v<ControlledReport>&&std::is_nothrow_destructible_v<ControlledReport>);
struct Stop {Status status;Reason reason;Stage stage;const char* message;std::optional<std::size_t> body,row,mesh;};
[[noreturn]] void stop(Status s,Reason r,Stage stage,const char* message,
    std::optional<std::size_t> body={},std::optional<std::size_t> row={},std::optional<std::size_t> mesh={}) {
    throw Stop{s,r,stage,message,body,row,mesh};
}
void require(bool ok,Reason reason,Stage stage,const char* message,std::optional<std::size_t> body={}) {
    if(!ok) {stop(Status::numerical_failure,reason,stage,message,body);}
}
void fail(ControlledReport& out,const Stop& s) noexcept {
    out.status=s.status;out.reason=s.reason;out.committed=false;out.advanced_dt=0.0;
    out.work.body_assignments=0;out.work.progress_assignments=0;
    out.failure=Failure{s.stage,s.body,s.row,s.mesh};
    try {out.message=s.message;}catch(...) {out.message.clear();}
}
bool bits(double a,double b) noexcept {return std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b);}
bool same(Vec3 a,Vec3 b) noexcept {return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z);}
bool same(Quaternion a,Quaternion b) noexcept {return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z)&&bits(a.w,b.w);}
bool same(dynamics::Material a,dynamics::Material b) noexcept {return bits(a.restitution,b.restitution)&&bits(a.friction,b.friction);}
bool same(const Body& a,const Body& b) noexcept {
    return a.id==b.id&&a.is_static==b.is_static&&bits(a.mass,b.mass)&&bits(a.radius,b.radius)&&same(a.inertia_diagonal,b.inertia_diagonal)&&
        same(a.position,b.position)&&same(a.orientation,b.orientation)&&same(a.velocity,b.velocity)&&same(a.angular_momentum,b.angular_momentum)&&
        same(a.force,b.force)&&same(a.torque,b.torque)&&same(a.material,b.material);
}
bool same(const dynamics::Plane& a,const dynamics::Plane& b) noexcept {return a.id==b.id&&same(a.normal,b.normal)&&bits(a.offset,b.offset)&&same(a.material,b.material);}
bool same(const sphere_triangle::StaticTriangle& a,const sphere_triangle::StaticTriangle& b) noexcept {
    if(a.id!=b.id) {return false;}
    for(std::size_t i=0;i<3;++i) {if(!same(a.vertices[i],b.vertices[i])) {return false;}}
    return true;
}
bool same(advance::Progress a,advance::Progress b) noexcept {return bits(a.time,b.time)&&a.ticks==b.ticks;}
bool same(const WorldState& a,const dynamics::World& b) noexcept {
    if(!same(a.gravity,b.gravity)||a.bodies.size()!=b.bodies().size()||a.planes.size()!=b.planes().size()) {return false;}
    for(std::size_t i=0;i<a.bodies.size();++i) {if(!same(a.bodies[i],b.bodies()[i])) {return false;}}
    for(std::size_t i=0;i<a.planes.size();++i) {if(!same(a.planes[i],b.planes()[i])) {return false;}}
    return true;
}
bool zero(Vec3 a) noexcept {return a.x==0&&a.y==0&&a.z==0;}
bool finite(Vec3 a) noexcept {return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
[[maybe_unused]] bool identity(const std::array<char,65>& a) noexcept {
    if(a[64]!='\0') {return false;}
    for(std::size_t i=0;i<64;++i) {if(!((a[i]>='0'&&a[i]<='9')||(a[i]>='a'&&a[i]<='f'))) {return false;}}
    return true;
}
Status child_status(advance::Status s) noexcept {
    switch(s) {
    case advance::Status::not_certified:return Status::not_certified;
    case advance::Status::invalid_input:return Status::invalid_input;
    case advance::Status::unsupported_environment:return Status::unsupported_environment;
    case advance::Status::numerical_failure:return Status::numerical_failure;
    case advance::Status::committed:return Status::numerical_failure;
    }
    return Status::numerical_failure;
}
void counts(const dynamics::World& world,std::span<const StaticMeshSource> meshes,const TickLoadPacket& packet) {
    if(world.bodies().size()>hard_max_bodies) {stop(Status::invalid_input,Reason::body_count,Stage::counts,"Body hard count");}
    if(world.planes().size()>hard_max_planes) {stop(Status::invalid_input,Reason::plane_count,Stage::counts,"Plane hard count");}
    if(meshes.empty()||meshes.size()>hard_max_meshes) {stop(Status::invalid_input,Reason::mesh_count,Stage::counts,"Mesh hard count");}
    std::size_t remaining=hard_max_faces;
    for(std::size_t i=0;i<meshes.size();++i) {
        if(meshes[i].triangles.size()>remaining) {stop(Status::invalid_input,Reason::face_count,Stage::counts,"Face hard total",{},{},i);}
        remaining-=meshes[i].triangles.size();
    }
    if(packet.loads.size()>hard_max_bodies) {stop(Status::invalid_input,Reason::packet_count,Stage::counts,"Packet hard count");}
}
void capture(ControlledReport& out,const dynamics::World& world,std::span<const StaticMeshSource> meshes,
    double h,const GuardSettings& settings,advance::Progress progress,const TickLoadPacket& packet) {
    out.capture=CaptureState::partial;
    out.original.emplace(h,settings,progress,packet.mode,packet.expected_tick);
    auto& s=*out.original;s.world.gravity=world.gravity;
    s.world.bodies.reserve(world.bodies().size());s.world.planes.reserve(world.planes().size());
    s.meshes.reserve(meshes.size());s.packet.loads.reserve(packet.loads.size());
    for(const auto& body:world.bodies()) {s.world.bodies.push_back(body);++out.work.original_bodies_copied;}
    for(const auto& plane:world.planes()) {s.world.planes.push_back(plane);++out.work.original_planes_copied;}
    for(const auto& mesh:meshes) {
        s.meshes.push_back({mesh.id,mesh.revision,{}});++out.work.original_meshes_copied;
        auto& row=s.meshes.back();row.triangles.reserve(mesh.triangles.size());
        for(const auto& face:mesh.triangles) {row.triangles.push_back(face);++out.work.original_faces_copied;}
    }
    for(const auto& row:packet.loads) {s.packet.loads.push_back(row);++out.work.packet_rows_copied;}
    out.capture=CaptureState::complete;
}
void world_capture(std::optional<WorldState>& snapshot,CaptureState& state,const dynamics::World& world,
    std::size_t& bodies,std::size_t& planes) {
    state=CaptureState::partial;snapshot.emplace();auto& out=*snapshot;out.gravity=world.gravity;
    out.bodies.reserve(world.bodies().size());out.planes.reserve(world.planes().size());
    for(const auto& b:world.bodies()) {out.bodies.push_back(b);++bodies;}
    for(const auto& p:world.planes()) {out.planes.push_back(p);++planes;}
    state=CaptureState::complete;
}
void original_validation(ControlledReport& out) {
    const auto& bodies=out.original->world.bodies;
    for(std::size_t i=0;i<bodies.size();++i) {
        ++out.work.original_validations_attempted;
        try {bodies[i].validate();}catch(const std::bad_alloc&) {throw;}
        catch(...) {stop(Status::invalid_input,Reason::original_body,Stage::original_validation,"Original body is invalid",i);}
        ++out.work.original_validations_returned;
    }
    out.original_bodies_validated=true;
}
void packet_validation(ControlledReport& out) {
    const auto& s=*out.original;const auto& p=s.packet;
    if(p.mode!=LoadMode::replace_total_world_loads) {stop(Status::invalid_input,Reason::packet_mode,Stage::packet,"Explicit replacement mode required");}
    if(p.expected_tick>advance::maximum_ticks||p.expected_tick!=s.progress.ticks) {stop(Status::invalid_input,Reason::expected_tick,Stage::packet,"Packet tick stale or outside domain");}
    if(p.loads.size()!=s.world.bodies.size()) {stop(Status::invalid_input,Reason::packet_count,Stage::packet,"Every original body needs one row");}
    std::array<bool,hard_max_bodies> seen{};
    for(std::size_t row=0;row<p.loads.size();++row) {
        const auto& load=p.loads[row];++out.work.packet_rows_checked;
        std::size_t ordinal=s.world.bodies.size();
        if(load.body_id>0&&load.body_id<=advance::maximum_ticks) {
            for(std::size_t i=0;i<s.world.bodies.size();++i) {if(s.world.bodies[i].id==load.body_id) {ordinal=i;break;}}
        }
        if(ordinal==s.world.bodies.size()) {stop(Status::invalid_input,Reason::packet_id,Stage::packet,"Unknown packet body",{},row);}
        if(seen[ordinal]) {stop(Status::invalid_input,Reason::packet_duplicate,Stage::packet,"Duplicate packet body",ordinal,row);}
        seen[ordinal]=true;out.mappings[row]=Mapping{row,ordinal,load.body_id};
        if(!finite(load.force_newtons)||!finite(load.torque_newton_meters)) {stop(Status::invalid_input,Reason::packet_load,Stage::packet,"Nonfinite load",ordinal,row);}
        auto candidate=s.world.bodies[ordinal];candidate.force=load.force_newtons;candidate.torque=load.torque_newton_meters;
        if(candidate.is_static&&(!zero(candidate.force)||!zero(candidate.torque))) {stop(Status::invalid_input,Reason::static_load,Stage::packet,"Static loads must be exact zero",ordinal,row);}
        ++out.work.packet_validations_attempted;
        try {candidate.validate();}catch(const std::bad_alloc&) {throw;}
        catch(...) {stop(Status::invalid_input,Reason::packet_load,Stage::packet,"Replacement load violates body domain",ordinal,row);}
        ++out.work.packet_validations_returned;
    }
}
void origin_check(ControlledReport& out,dynamics::World& world,std::span<const StaticMeshSource> meshes,
    advance::Progress progress,const TickLoadPacket& packet) {
    const auto& s=*out.original;
    require(same(s.world.gravity,world.gravity)&&same(s.progress,progress)&&world.bodies().size()==s.world.bodies.size()&&
        world.planes().size()==s.world.planes.size()&&meshes.size()==s.meshes.size(),Reason::origin_mismatch,Stage::commit_preparation,"External origin dimensions or progress differ");
    for(std::size_t i=0;i<s.world.bodies.size();++i) {++out.work.origin_bodies_checked;require(same(s.world.bodies[i],world.bodies()[i]),Reason::origin_mismatch,Stage::commit_preparation,"External body changed",i);}
    for(std::size_t i=0;i<s.world.planes.size();++i) {++out.work.origin_planes_checked;require(same(s.world.planes[i],world.planes()[i]),Reason::origin_mismatch,Stage::commit_preparation,"External plane changed");}
    for(std::size_t i=0;i<s.meshes.size();++i) {
        ++out.work.origin_meshes_checked;const auto& a=s.meshes[i];const auto& b=meshes[i];
        require(a.id==b.id&&a.revision==b.revision&&a.triangles.size()==b.triangles.size(),Reason::origin_mismatch,Stage::commit_preparation,"External mesh changed");
        for(std::size_t j=0;j<a.triangles.size();++j) {++out.work.origin_faces_checked;require(same(a.triangles[j],b.triangles[j]),Reason::origin_mismatch,Stage::commit_preparation,"External face changed");}
    }
    require(packet.mode==s.packet.mode&&packet.expected_tick==s.packet.expected_tick&&packet.loads.size()==s.packet.loads.size(),Reason::origin_mismatch,Stage::commit_preparation,"External packet metadata changed");
    for(std::size_t i=0;i<packet.loads.size();++i) {++out.work.origin_packet_rows_checked;const auto& a=packet.loads[i];const auto& b=s.packet.loads[i];require(a.body_id==b.body_id&&same(a.force_newtons,b.force_newtons)&&same(a.torque_newton_meters,b.torque_newton_meters),Reason::origin_mismatch,Stage::commit_preparation,"External packet row changed");}
}
void candidates(ControlledReport& out,const dynamics::World& working,advance::Progress progress,Buffer& buffer) {
    const auto& child=*out.child;const auto& before=*out.staged_before;
    require(child.status==advance::Status::committed&&child.reason==advance::Reason::none&&child.committed&&bits(child.advanced_dt,out.requested_dt)&&
        same(child.original_progress,out.original_progress)&&child.proposed_progress&&same(*child.proposed_progress,progress)&&child.guard&&
        child.guard->status==g::Status::certified_separated&&child.guard->candidate_bodies&&child.guard->preparation&&child.guard->preparation->snapshot,
        Reason::child_inconsistent,Stage::post_child,"Private success metadata incomplete");
    const auto& original=*child.guard->preparation->snapshot;const auto& expected=*child.guard->candidate_bodies;
    require(original.bodies.size()==before.bodies.size()&&original.planes.size()==before.planes.size()&&expected.size()==before.bodies.size()&&
        working.bodies().size()==before.bodies.size()&&working.planes().size()==before.planes.size()&&same(original.gravity,before.gravity)&&same(working.gravity,before.gravity)&&
        bits(original.horizon,out.requested_dt)&&original.meshes.size()==out.original->meshes.size(),Reason::child_inconsistent,Stage::post_child,"Private source dimensions differ");
    for(std::size_t i=0;i<before.planes.size();++i) {require(same(original.planes[i],before.planes[i])&&same(working.planes()[i],before.planes[i]),Reason::child_inconsistent,Stage::post_child,"Private raw plane changed");}
    for(std::size_t i=0;i<original.meshes.size();++i) {
        const auto& a=original.meshes[i];const auto& b=out.original->meshes[i];
        require(a.id==b.id&&a.revision==b.revision&&a.triangles.size()==b.triangles.size(),Reason::child_inconsistent,Stage::post_child,"Private mesh link differs");
        for(std::size_t j=0;j<a.triangles.size();++j) {require(same(a.triangles[j],b.triangles[j]),Reason::child_inconsistent,Stage::post_child,"Private face link differs");}
    }
    for(std::size_t i=0;i<expected.size();++i) {
        ++out.work.candidate_bodies_checked;
        require(same(original.bodies[i],before.bodies[i]),Reason::child_inconsistent,Stage::post_child,"Child guard origin is not staged origin",i);
        Body cleared=expected[i];cleared.force={0.,0.,0.};cleared.torque={0.,0.,0.};
        require(same(cleared,working.bodies()[i]),Reason::candidate_mismatch,Stage::post_child,"Actual private result differs from child candidate",i);
        ++out.work.candidate_validations_attempted;
        try {cleared.validate();}catch(const std::bad_alloc&) {throw;}
        catch(...) {stop(Status::numerical_failure,Reason::candidate_mismatch,Stage::post_child,"Private candidate invalid",i);}
        ++out.work.candidate_validations_returned;buffer[i]=cleared;
    }
}
void commit(const Buffer& buffer,const Destinations& destinations,std::size_t count,advance::Progress& progress,advance::Progress value) noexcept {
    for(std::size_t i=0;i<count;++i) {*destinations[i]=buffer[i];}
    progress=value;
}
}

Binding current_binding() noexcept {
    Binding out;
#if defined(PIKAPIKA_CONTROLLED_TICK_PROFILE) && PIKAPIKA_CONTROLLED_TICK_PROFILE == 1 && defined(PIKAPIKA_CONTROLLED_TICK_BUILD_ID) && defined(PIKAPIKA_CONTROLLED_TICK_UPSTREAM_ID) && defined(NDEBUG) && !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && _MSC_VER==1951 && defined(_M_X64)) || (defined(__GNUC__) && __GNUC__==13 && defined(__x86_64__) && defined(__SSE2__)))
    constexpr char id[]=PIKAPIKA_CONTROLLED_TICK_BUILD_ID,upstream[]=PIKAPIKA_CONTROLLED_TICK_UPSTREAM_ID;
    if(sizeof(id)!=65||sizeof(upstream)!=65) {return out;}
    for(std::size_t i=0;i<65;++i) {out.build_id[i]=id[i];out.upstream_build_id[i]=upstream[i];}
    if(!identity(out.build_id)||!identity(out.upstream_build_id)) {return Binding{};}
    const auto actual=g::current_binding();
    if(!actual.checked||actual.profile!=1||actual.state!=g::BindingState::ready||actual.build_id!=out.upstream_build_id) {return Binding{};}
    out.profile=1;out.configured=true;
#endif
    return out;
}

ControlledReport advance_with_loads(dynamics::World& world,std::span<const StaticMeshSource> meshes,
    double horizon,const GuardSettings& settings,advance::Progress& progress,const TickLoadPacket& packet) noexcept {
    ControlledReport out;out.requested_dt=horizon;out.original_progress=progress;out.requested_mode=packet.mode;out.requested_tick=packet.expected_tick;
    Buffer buffer{};Destinations destinations{};std::optional<dynamics::World> working;
    advance::Progress private_progress=progress;Stage stage=Stage::environment;std::size_t count=0;
    out.storage={hard_max_bodies,hard_max_bodies,sizeof(buffer),sizeof(destinations)};
    try {
        if(const char* issue=interval::environment_issue()) {stop(Status::unsupported_environment,Reason::environment,stage,issue);}
        stage=Stage::binding;out.binding=current_binding();
        if(!out.binding.configured) {stop(Status::unsupported_environment,Reason::binding_unsupported,stage,"Independent controlled-tick binding unavailable");}
        stage=Stage::counts;counts(world,meshes,packet);
        stage=Stage::capture;capture(out,world,meshes,horizon,settings,progress,packet);
        stage=Stage::original_validation;original_validation(out);
        stage=Stage::packet;packet_validation(out);
        stage=Stage::staging;++out.work.private_copies_attempted;working.emplace(world);++out.work.private_copies_returned;
        require(same(out.original->world,*working),Reason::origin_mismatch,stage,"Private copy differs from owned original");
        for(std::size_t row=0;row<out.original->packet.loads.size();++row) {
            const auto& mapping=*out.mappings[row];auto* body=working->find_body(mapping.body_id);
            require(body&&body==&working->bodies()[mapping.body_ordinal],Reason::private_copy,stage,"Private destination lookup differs");
            body->force=out.original->packet.loads[row].force_newtons;body->torque=out.original->packet.loads[row].torque_newton_meters;
        }
        world_capture(out.staged_before,out.staged_capture,*working,out.work.staged_bodies_copied,out.work.staged_planes_copied);
        stage=Stage::child;++out.work.child_attempts;
        auto actual=advance::advance(*working,out.original->meshes,horizon,out.original->settings,private_progress);
        ++out.work.child_returns;out.child.emplace(std::move(actual));out.private_progress_after=private_progress;
        stage=Stage::post_child;
        world_capture(out.private_after,out.private_after_capture,*working,out.work.private_after_bodies_copied,out.work.private_after_planes_copied);
        if(!out.child->committed) {stop(child_status(out.child->status),Reason::child_failed,Stage::child,"Actual private advance refused");}
        candidates(out,*working,private_progress,buffer);
        stage=Stage::commit_preparation;origin_check(out,world,meshes,progress,packet);
        count=out.original->world.bodies.size();
        for(std::size_t i=0;i<count;++i) {
            ++out.work.destination_lookups;destinations[i]=world.find_body(out.original->world.bodies[i].id);
            require(destinations[i]&&destinations[i]==&world.bodies()[i],Reason::destination_mismatch,stage,"Original destination not stable",i);
            ++out.work.destinations_resolved;
        }
        out.status=Status::committed;out.reason=Reason::none;out.committed=true;out.advanced_dt=horizon;out.failure.reset();out.message.clear();
        out.work.body_assignments=count;out.work.progress_assignments=1;
    }catch(const Stop& s) {fail(out,s);return out;}
    catch(const std::bad_alloc&) {fail(out,{Status::numerical_failure,Reason::allocation_failure,stage,"Controlled tick preparation allocation failed",{},{},{}});return out;}
    catch(...) {fail(out,{Status::numerical_failure,Reason::unexpected_exception,stage,"Controlled tick preparation failed",{},{},{}});return out;}
    // All throwing work has finished. These are the ONLY external stores.
    commit(buffer,destinations,count,progress,private_progress);return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
