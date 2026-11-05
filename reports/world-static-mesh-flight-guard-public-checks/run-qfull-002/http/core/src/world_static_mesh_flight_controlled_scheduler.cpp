#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include <cfloat>
#include <cmath>
#include <limits>
#include <new>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Controlled scheduler requires strict binary64 evaluation.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#endif

namespace pikapika::world_static_mesh_flight_controlled_scheduler {
namespace {
namespace guard=world_static_mesh_flight_guard;
using I=interval::Interval;
static_assert(sizeof(double)==8&&std::numeric_limits<double>::digits==53&&std::numeric_limits<double>::is_iec559&&FLT_EVAL_METHOD==0);
static_assert(std::is_nothrow_copy_assignable_v<WorldState>);
static_assert(std::is_nothrow_copy_constructible_v<Boundary>);
static_assert(std::is_nothrow_move_constructible_v<Attempt>);
static_assert(std::is_nothrow_move_constructible_v<PumpReport>);
static_assert(std::is_nothrow_destructible_v<PumpReport>);
static_assert(std::is_nothrow_copy_constructible_v<QueueStep>);
struct Stop {Reason reason;};
void need(bool ok,Reason reason) {if(!ok) {throw Stop{reason};}}
bool finite(I value) noexcept {return std::isfinite(value.lower())&&std::isfinite(value.upper());}
[[maybe_unused]] bool identity(const std::array<char,65>& value) noexcept {
    if(value[64]!='\0') {return false;}
    for(std::size_t i=0;i<64;++i) {const char c=value[i];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))) {return false;}}
    return true;
}
std::size_t multiply(std::size_t a,std::size_t b) {
    need(a==0||b<=std::numeric_limits<std::size_t>::max()/a,Reason::cost_overflow);return a*b;
}
UpperBudget budget(std::size_t count) {
    UpperBudget out;out.attempts=count;auto& w=out.guard_work;
    w.mesh_queries=multiply(count,guard::hard_max_mesh_queries);
    w.primitive_queries=multiply(count,guard::hard_max_primitive_queries);
    w.candidates_examined=multiply(count,guard::hard_max_candidates_examined);
    w.sqrt_refinements=multiply(count,guard::hard_max_sqrt_refinements);
    w.propagations=multiply(count,guard::hard_max_propagations);
    w.plane_metric_values=multiply(count,guard::hard_max_value_attempts);
    w.box_values=multiply(count,guard::hard_max_value_attempts);
    w.plane_norm_loop_iterations_upper=multiply(w.plane_metric_values,64);
    w.bridge_calls_upper=multiply(count,32);
    out.guard_logical_payload_bytes=multiply(count,guard::hard_max_logical_payload);return out;
}
using Addresses=std::array<const dynamics::RigidBody*,controlled::hard_max_bodies>;
Boundary boundary(const dynamics::World& world,Progress progress,const Addresses& addresses) noexcept {
    Boundary out;out.world.gravity=world.gravity;out.progress=progress;
    out.world.body_count=world.bodies().size();out.world.plane_count=world.planes().size();
    // Counts are bounded before the first call. Children preserve structure;
    // concurrent structural changes violate the explicit caller precondition.
    for(std::size_t i=0;i<out.world.body_count;++i) {
        out.world.bodies[i]=world.bodies()[i];out.original_body_address_same[i]=addresses[i]==&world.bodies()[i];
    }
    for(std::size_t i=0;i<out.world.plane_count;++i) {out.world.planes[i]=world.planes()[i];}
    return out;
}
void capture_boundary(PumpReport& out,const dynamics::World& world,Progress progress,const Addresses& addresses) noexcept {
    out.boundaries[out.boundary_count].emplace(boundary(world,progress,addresses));++out.boundary_count;
    ++out.work.boundary_captures;out.work.body_observations+=world.bodies().size();out.work.plane_observations+=world.planes().size();
}
struct Busy {
    bool& flag;
    explicit Busy(bool& value) noexcept:flag(value) {flag=true;}
    ~Busy() noexcept {flag=false;}
    Busy(const Busy&)=delete;
    Busy& operator=(const Busy&)=delete;
};
}

Binding current_binding() noexcept {
    Binding out;
#if defined(PIKAPIKA_CONTROLLED_SCHEDULER_PROFILE) && PIKAPIKA_CONTROLLED_SCHEDULER_PROFILE == 1 && defined(PIKAPIKA_CONTROLLED_SCHEDULER_BUILD_ID) && defined(PIKAPIKA_CONTROLLED_SCHEDULER_CONTROLLED_ID) && defined(PIKAPIKA_CONTROLLED_SCHEDULER_CLOCK_ID) && defined(NDEBUG) && !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && _MSC_VER==1951 && defined(_M_X64)) || (defined(__GNUC__) && __GNUC__==13 && defined(__x86_64__) && defined(__SSE2__)))
    constexpr char id[]=PIKAPIKA_CONTROLLED_SCHEDULER_BUILD_ID,controlled_id[]=PIKAPIKA_CONTROLLED_SCHEDULER_CONTROLLED_ID,clock_id[]=PIKAPIKA_CONTROLLED_SCHEDULER_CLOCK_ID;
    if(sizeof(id)!=65||sizeof(controlled_id)!=65||sizeof(clock_id)!=65) {return out;}
    for(std::size_t i=0;i<65;++i) {out.build_id[i]=id[i];out.controlled_build_id[i]=controlled_id[i];out.scheduler_build_id[i]=clock_id[i];}
    if(!identity(out.build_id)||!identity(out.controlled_build_id)||!identity(out.scheduler_build_id)) {return Binding{};}
    const auto actual=controlled::current_binding();const auto actual_clock=clock::current_binding();
    if(!actual.configured||actual.build_id!=out.controlled_build_id||!actual_clock.configured||actual_clock.build_id!=out.scheduler_build_id) {return Binding{};}
    out.upstream_build_id=actual.upstream_build_id;if(!identity(out.upstream_build_id)) {return Binding{};}
    out.profile=1;out.configured=true;
#endif
    return out;
}
Scheduler::Scheduler(Settings settings):settings_(settings) {
    if(!std::isfinite(settings.step_seconds)||settings.step_seconds<clock::minimum_step||settings.step_seconds>clock::maximum_step||
       settings.max_attempts_per_pump==0||settings.max_attempts_per_pump>hard_max_attempts) {
        throw std::invalid_argument("Controlled scheduler settings outside fixed finite domain");
    }
}
Snapshot Scheduler::snapshot() const noexcept {return {settings_,backlog_,sequence_,busy_};}
PumpReport Scheduler::pump(dynamics::World& world,std::span<const StaticMeshSource> meshes,const GuardSettings& settings,
                          Progress& progress,double elapsed,std::span<const TickLoadPacket> packets) noexcept {
    PumpReport out;out.before=snapshot();out.after=out.before;out.requested_elapsed=elapsed;
    out.progress_before=progress;out.progress_after=progress;out.has_whole_tick_backlog=backlog_>=settings_.step_seconds;
    if(busy_) {out.status=Status::reentrant;out.reason=Reason::busy;return out;}
    if(interval::environment_issue()) {out.status=Status::unsupported_environment;out.reason=Reason::environment;return out;}
    out.binding=current_binding();if(!out.binding.configured) {out.status=Status::unsupported_environment;out.reason=Reason::binding_unsupported;return out;}
    const Busy busy(busy_);Addresses addresses{};
    // Every potentially throwing OUTER operation is pre-admission. No catch
    // surrounds later children: it cannot erase an already committed prefix.
    try {
        need(world.bodies().size()<=controlled::hard_max_bodies,Reason::body_count);
        need(world.planes().size()<=controlled::hard_max_planes,Reason::plane_count);
        need(meshes.size()<=controlled::hard_max_meshes,Reason::mesh_count);
        std::size_t faces=0;
        for(const auto& mesh:meshes) {need(mesh.triangles.size()<=controlled::hard_max_faces-faces,Reason::face_count);faces+=mesh.triangles.size();}
        need(packets.size()<=hard_max_packets,Reason::packet_count);
        for(const auto& packet:packets) {need(packet.loads.size()<=controlled::hard_max_bodies,Reason::packet_load_count);}
        for(std::size_t i=0;i<world.bodies().size();++i) {addresses[i]=&world.bodies()[i];}
        out.storage={hard_max_attempts+1,sizeof(out.boundaries),addresses.size(),sizeof(addresses)};
        out.capture=CaptureState::partial;out.original.emplace(settings);
        capture_boundary(out,world,progress,addresses);
        out.original->meshes.reserve(meshes.size());
        for(const auto& mesh:meshes) {out.original->meshes.push_back(mesh);++out.work.mesh_copies;out.work.face_copies+=mesh.triangles.size();}
        out.original->packets.reserve(packets.size());
        for(const auto& packet:packets) {out.original->packets.push_back(packet);++out.work.packet_copies;out.work.load_copies+=packet.loads.size();}
        out.capture=CaptureState::complete;
        need(std::isfinite(elapsed)&&elapsed>=0&&elapsed<=clock::maximum_elapsed,Reason::elapsed);
        need(sequence_<std::numeric_limits<std::uint64_t>::max(),Reason::sequence_limit);
        const double credit=backlog_+elapsed;
        need(std::isfinite(credit)&&credit>=0&&credit<=clock::maximum_backlog,Reason::backlog_limit);
        const auto error=I::point(credit)-(I::point(backlog_)+I::point(elapsed));need(finite(error),Reason::queue_arithmetic);
        out.admitted_credit=credit;out.admission_rounding_error=error;
        double planned=credit;
        while(planned>=settings_.step_seconds&&out.planned_attempts<settings_.max_attempts_per_pump) {
            const double next=planned-settings_.step_seconds;need(std::isfinite(next)&&next>=0&&next<planned,Reason::queue_arithmetic);
            const auto delta=I::point(next)-(I::point(planned)-I::point(settings_.step_seconds));need(finite(delta),Reason::queue_arithmetic);
            out.queue_plan[out.planned_attempts].emplace(QueueStep{planned,next,delta});++out.planned_attempts;planned=next;
        }
        out.upper_budget=budget(out.planned_attempts);
    }catch(const Stop& stop) {
        out.status=stop.reason==Reason::queue_arithmetic?Status::numerical_failure:Status::invalid_input;out.reason=stop.reason;return out;
    }catch(const std::bad_alloc&) {out.status=Status::numerical_failure;out.reason=Reason::allocation_failure;return out;
    }catch(...) {out.status=Status::numerical_failure;out.reason=Reason::unexpected_exception;return out;}
    backlog_=*out.admitted_credit;++sequence_;out.elapsed_accepted=true;
    for(std::size_t i=0;i<out.planned_attempts;++i) {
        if(i>=out.original->packets.size()) {out.status=Status::awaiting_input;out.reason=Reason::packet_unavailable;break;}
        ++out.attempts;
        auto result=controlled::advance_with_loads(world,out.original->meshes,settings_.step_seconds,out.original->settings,progress,out.original->packets[i]);
        const bool committed=result.committed;
        out.tick_reports[i].emplace(Attempt{i,i,committed,committed,std::move(result)});
        capture_boundary(out,world,progress,addresses);
        if(!committed) {out.status=Status::tick_rejected;out.reason=Reason::controlled_rejected;break;}
        backlog_=out.queue_plan[i]->proposed_after;++out.committed_ticks;++out.packets_consumed;
    }
    if(out.status!=Status::tick_rejected&&out.status!=Status::awaiting_input) {
        out.status=backlog_>=settings_.step_seconds?Status::step_budget:Status::waiting;out.reason=Reason::none;
    }
    out.after={settings_,backlog_,sequence_,false};out.progress_after=progress;
    out.has_whole_tick_backlog=backlog_>=settings_.step_seconds;return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
