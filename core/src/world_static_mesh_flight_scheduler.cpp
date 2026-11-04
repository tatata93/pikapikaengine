#include "pikapika/world_static_mesh_flight_scheduler.hpp"
#include <cfloat>
#include <cmath>
#include <limits>
#include <new>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Scheduler requires strict binary64 evaluation.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#endif

namespace pikapika::world_static_mesh_flight_scheduler {
namespace {
namespace guard=world_static_mesh_flight_guard;
using I=interval::Interval;
static_assert(sizeof(double)==8&&std::numeric_limits<double>::digits==53&&std::numeric_limits<double>::is_iec559&&FLT_EVAL_METHOD==0);
static_assert(std::is_nothrow_move_constructible_v<advance::AdvanceReport>);
static_assert(std::is_nothrow_move_constructible_v<Attempt>);
static_assert(std::is_nothrow_move_constructible_v<PumpReport>);
static_assert(std::is_nothrow_destructible_v<PumpReport>);
static_assert(std::is_nothrow_copy_constructible_v<QueueStep>);

struct Stop {Reason reason;};
void need(bool condition,Reason reason) {if(!condition) {throw Stop{reason};}}
bool finite(I value) noexcept {return std::isfinite(value.lower())&&std::isfinite(value.upper());}
std::size_t multiply(std::size_t a,std::size_t b) {
    need(a==0||b<=std::numeric_limits<std::size_t>::max()/a,Reason::cost_overflow);return a*b;
}
UpperBudget budget(std::size_t count) {
    UpperBudget out;out.attempts=count;
    auto& w=out.guard_work;
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
#if defined(PIKAPIKA_FLIGHT_SCHEDULER_PROFILE) && PIKAPIKA_FLIGHT_SCHEDULER_PROFILE == 1 && defined(PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID) && defined(NDEBUG) && !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && _MSC_VER == 1951 && defined(_M_X64)) || (defined(__GNUC__) && __GNUC__ == 13 && defined(__x86_64__) && defined(__SSE2__)))
    constexpr char id[]=PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID;
    if(sizeof(id)!=65) {return out;}
    for(std::size_t i=0;i<64;++i) {
        const char c=id[i];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))) {return out;}
    }
    for(std::size_t i=0;i<65;++i) {out.build_id[i]=id[i];}
    out.profile=1;out.configured=true;
#endif
    return out;
}

Scheduler::Scheduler(Settings settings):settings_(settings) {
    if(!std::isfinite(settings.step_seconds)||settings.step_seconds<minimum_step||settings.step_seconds>maximum_step||
       settings.max_attempts_per_pump==0||settings.max_attempts_per_pump>hard_max_attempts) {
        throw std::invalid_argument("Scheduler settings outside fixed finite domain");
    }
}
Snapshot Scheduler::snapshot() const noexcept {return {settings_,backlog_,sequence_,busy_};}

PumpReport Scheduler::pump(dynamics::World& world,std::span<const StaticMeshSource> meshes,
                          const GuardSettings& settings,advance::Progress& progress,double elapsed) noexcept {
    PumpReport out;out.before=snapshot();out.after=out.before;out.requested_elapsed=elapsed;
    out.progress_before=progress;out.progress_after=progress;
    out.has_whole_tick_backlog=backlog_>=settings_.step_seconds;
    if(busy_) {out.status=Status::reentrant;out.reason=Reason::busy;return out;}
    if(interval::environment_issue()) {out.status=Status::unsupported_environment;out.reason=Reason::environment;return out;}
    out.binding=current_binding();
    if(!out.binding.configured) {out.status=Status::unsupported_environment;out.reason=Reason::binding_unsupported;return out;}
    const Busy busy(busy_);
    // EVERYTHING potentially throwing in the outer scheduler is confined to
    // this pre-admission block. No catch can hide a later successful prefix.
    try {
        need(std::isfinite(elapsed)&&elapsed>=0&&elapsed<=maximum_elapsed,Reason::elapsed);
        need(sequence_<std::numeric_limits<std::uint64_t>::max(),Reason::sequence_limit);
        const double credit=backlog_+elapsed;
        need(std::isfinite(credit)&&credit>=0&&credit<=maximum_backlog,Reason::backlog_limit);
        const auto error=I::point(credit)-(I::point(backlog_)+I::point(elapsed));
        need(finite(error),Reason::queue_arithmetic);
        out.admitted_credit=credit;out.admission_rounding_error=error;
        double planned=credit;
        while(planned>=settings_.step_seconds&&out.planned_attempts<settings_.max_attempts_per_pump) {
            const double next=planned-settings_.step_seconds;
            need(std::isfinite(next)&&next>=0&&next<planned,Reason::queue_arithmetic);
            const auto delta=I::point(next)-(I::point(planned)-I::point(settings_.step_seconds));
            need(finite(delta),Reason::queue_arithmetic);
            out.queue_plan[out.planned_attempts].emplace(QueueStep{planned,next,delta});
            ++out.planned_attempts;planned=next;
        }
        out.upper_budget=budget(out.planned_attempts);
    } catch(const Stop& stop) {
        out.status=stop.reason==Reason::queue_arithmetic?Status::numerical_failure:Status::invalid_input;
        out.reason=stop.reason;return out;
    } catch(const std::bad_alloc&) {
        out.status=Status::numerical_failure;out.reason=Reason::allocation_failure;return out;
    } catch(...) {
        out.status=Status::numerical_failure;out.reason=Reason::unexpected_exception;return out;
    }
    // Scalar admission is separate from tick commit. Failure below keeps this
    // accepted credit; callers retry with zero, not the original elapsed.
    backlog_=*out.admitted_credit;++sequence_;out.elapsed_accepted=true;
    for(std::size_t i=0;i<out.planned_attempts;++i) {
        ++out.attempts;
        auto result=advance::advance(world,meshes,settings_.step_seconds,settings,progress);
        const bool committed=result.committed;
        out.tick_reports[i].emplace(Attempt{i,committed,std::move(result)});
        if(!committed) {
            out.status=Status::tick_rejected;out.reason=Reason::advance_rejected;break;
        }
        // Only nonthrowing scalar stores follow the returned commit. All queue
        // arithmetic and report slots were prepared BEFORE the first advance.
        backlog_=out.queue_plan[i]->proposed_after;++out.committed_ticks;
    }
    if(out.status!=Status::tick_rejected) {
        out.status=backlog_>=settings_.step_seconds?Status::step_budget:Status::waiting;out.reason=Reason::none;
    }
    out.after={settings_,backlog_,sequence_,false};out.progress_after=progress;
    out.has_whole_tick_backlog=backlog_>=settings_.step_seconds;return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
