#include "pikapika/accelerated_sphere_box_coverage.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <new>
#include <stdexcept>
#include <numeric>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Accelerated sphere box coverage requires strict floating point.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::accelerated_sphere_box_coverage {
namespace {
using I=interval::Interval;
static_assert(std::is_nothrow_copy_constructible_v<Snapshot>);
static_assert(std::is_nothrow_copy_constructible_v<Evaluation>);
static_assert(std::is_nothrow_copy_constructible_v<Audit>);
static_assert(std::is_nothrow_copy_assignable_v<PartitionLeaf>);
static_assert(std::is_nothrow_copy_constructible_v<Cell>);
static_assert(std::is_nothrow_move_constructible_v<Result>);

bool same_interval_bits(const I& a,const I& b) noexcept {
    return std::bit_cast<std::uint64_t>(a.lower())==std::bit_cast<std::uint64_t>(b.lower())&&
        std::bit_cast<std::uint64_t>(a.upper())==std::bit_cast<std::uint64_t>(b.upper());
}

void fail(Result& result,Status status,Reason reason,const char* message) noexcept {
    result.status=status;
    result.reason=reason;
    try {result.message=message;}catch(...) {result.message.clear();}
}
bool scalar_valid(double x) noexcept {
    return std::isfinite(x)&&std::abs(x)<=1e12;
}
bool vector_valid(Vec3 v) noexcept {
    return scalar_valid(v.x)&&scalar_valid(v.y)&&scalar_valid(v.z);
}
bool sphere_valid(const accelerated::Sphere& sphere) noexcept {
    return vector_valid(sphere.center)&&vector_valid(sphere.velocity)&&
        vector_valid(sphere.acceleration)&&scalar_valid(sphere.radius)&&sphere.radius>0;
}
bool settings_valid(const Settings& settings) noexcept {
    return std::isfinite(settings.time_tolerance)&&settings.time_tolerance>0&&
        settings.time_tolerance<=.1&&settings.max_evaluations>=1&&
        settings.max_evaluations<=maximum_evaluations&&settings.max_leaves>=1&&
        settings.max_leaves<=maximum_leaves&&settings.max_depth<=maximum_depth&&
        settings.sqrt_refinements>=1&&settings.sqrt_refinements<=maximum_sqrt_refinements;
}
bool same_cell(const Cell& a,const Cell& b) noexcept {
    return a.time_bounds==b.time_bounds&&a.depth==b.depth&&a.parent_audit==b.parent_audit;
}
// No Interval arithmetic or allocation: this verifies our own metadata, not a
// second geometry solver. Every record was produced from the owned snapshot.
bool consistent(const Result& result) noexcept {
    if(!result.snapshot||!result.snapshot_validated||!result.partition_complete||result.partition.empty()) {return false;}
    const auto& settings=result.snapshot->settings;
    if(result.partition.size()>settings.max_leaves||result.audits.size()>settings.max_evaluations||
       result.partition.front().cell.time_bounds[0]!=0||
       result.partition.back().cell.time_bounds[1]!=result.snapshot->horizon) {return false;}
    std::size_t attempted=0,returned=0,current_count=0,root_work=0,limited=0;
    for(std::size_t index=0;index<result.audits.size();++index) {
        const Audit& audit=result.audits[index];
        if(audit.call_attempted) {++attempted;}
        if(audit.evaluation) {
            ++returned;
            const Evaluation& evaluation=*audit.evaluation;
            const auto& root=evaluation.root;
            if(!same_interval_bits(root.value,evaluation.distance)||
               root.refinements>2*settings.sqrt_refinements||
               !std::isfinite(root.value.lower())||!std::isfinite(root.value.upper())||
               root.value.lower()<0||evaluation.raw_squared_distance.upper()<0||
               evaluation.nonnegative_squared_distance.lower()!=std::max(0.0,evaluation.raw_squared_distance.lower())||
               evaluation.nonnegative_squared_distance.upper()!=evaluation.raw_squared_distance.upper()) {return false;}
            root_work+=root.refinements;
            if(root.refinement_limited) {++limited;}
        }
        if(audit.evaluation&&!audit.call_attempted) {return false;}
        if(audit.outcome==Outcome::pending) {return false;}
        if(audit.outcome==Outcome::positive) {
            if(!audit.evaluation||!audit.evaluation->gap.strictly_positive()||audit.blocked_reason!=Reason::none||audit.split_time) {return false;}
        }else if(audit.outcome==Outcome::split) {
            if(!audit.evaluation||audit.evaluation->gap.strictly_positive()||audit.evaluation->gap.upper()<=0||
               audit.blocked_reason!=Reason::none||!audit.split_time||
               !(*audit.split_time>audit.cell.time_bounds[0]&&*audit.split_time<audit.cell.time_bounds[1])) {return false;}
        }else if(audit.blocked_reason==Reason::none||audit.split_time) {return false;}
        if(audit.cell.parent_audit) {
            const auto parent=*audit.cell.parent_audit;
            if(parent>=index) {return false;}
            const Audit& p=result.audits[parent];
            if(p.outcome!=Outcome::split||!p.split_time||audit.cell.depth!=p.cell.depth+1) {return false;}
            const auto bounds=audit.cell.time_bounds;
            if(!((bounds[0]==p.cell.time_bounds[0]&&bounds[1]==*p.split_time)||
                 (bounds[0]==*p.split_time&&bounds[1]==p.cell.time_bounds[1]))) {return false;}
        }else if(audit.cell.depth!=0||audit.cell.time_bounds!=std::array<double,2>{0,result.snapshot->horizon}) {return false;}
    }
    for(std::size_t index=0;index<result.partition.size();++index) {
        const PartitionLeaf& leaf=result.partition[index];
        if(!(leaf.cell.time_bounds[0]<leaf.cell.time_bounds[1])||leaf.cell.depth>settings.max_depth||
           (index>0&&result.partition[index-1].cell.time_bounds[1]!=leaf.cell.time_bounds[0])) {return false;}
        if(leaf.audit_index) {
            if(*leaf.audit_index>=result.audits.size()||!same_cell(leaf.cell,result.audits[*leaf.audit_index].cell)) {return false;}
        }
        if(leaf.state==LeafState::certified) {
            if(!leaf.audit_index||result.audits[*leaf.audit_index].outcome!=Outcome::positive||leaf.blocked_reason!=Reason::none) {return false;}
        }else if(leaf.state==LeafState::blocked) {
            if(!leaf.audit_index||result.audits[*leaf.audit_index].outcome!=Outcome::blocked||
               leaf.blocked_reason==Reason::none||leaf.blocked_reason!=result.audits[*leaf.audit_index].blocked_reason) {return false;}
        }else if(leaf.state==LeafState::unqueried) {
            if(leaf.audit_index||leaf.blocked_reason!=Reason::none) {return false;}
        }else {
            ++current_count;
            if(!result.current||!same_cell(*result.current,leaf.cell)||leaf.blocked_reason==Reason::none) {return false;}
        }
    }
    if(returned>attempted) {return false;}
    const std::size_t unknown_calls=attempted-returned;
    const std::size_t root_upper=root_work+unknown_calls*2*settings.sqrt_refinements;
    return current_count==(result.current?1U:0U)&&attempted==result.work.value_calls_attempted&&
        returned==result.work.value_calls_returned&&returned<=attempted&&unknown_calls<=1&&
        result.work.sqrt_results_returned==returned&&result.work.sqrt_refinements_returned==root_work&&
        result.work.sqrt_limited_returns==limited&&result.work.sqrt_refinements_upper==root_upper&&
        result.work.exact==(unknown_calls==0)&&root_upper<=maximum_sqrt_refinement_work;
}
void finish(Result& result) noexcept {
    // All three vectors were reserved BEFORE the root was installed. This copy
    // performs no allocation and never reclassifies the halted current as tail.
    result.frontier.clear();
    for(const PartitionLeaf& leaf:result.partition) {
        if(leaf.state==LeafState::unqueried) {result.frontier.push_back(leaf.cell);}
    }
}
void halt(Result& result,Reason reason,const char* message) noexcept {
    fail(result,Status::not_certified,reason,message);
    for(PartitionLeaf& leaf:result.partition) {
        if(leaf.state!=LeafState::current) {continue;}
        leaf.blocked_reason=reason;
        if(leaf.audit_index) {
            Audit& audit=result.audits[*leaf.audit_index];
            if(audit.outcome==Outcome::pending) {
                audit.outcome=Outcome::blocked;
                audit.blocked_reason=reason;
            }
        }
    }
}
void block(Result& result,std::size_t leaf_index,Reason reason) noexcept {
    auto& leaf=result.partition[leaf_index];
    leaf.state=LeafState::blocked;
    leaf.blocked_reason=reason;
    Audit& audit=result.audits[*leaf.audit_index];
    audit.outcome=Outcome::blocked;
    audit.blocked_reason=reason;
    result.current.reset();
}
std::optional<std::size_t> next_leaf(const Result& result) noexcept {
    std::optional<std::size_t> selected;
    // Partition is ordered by time; preserving the first equal-depth cell gives
    // minimum depth, then leftmost, even when some earlier cells are blocked.
    for(std::size_t index=0;index<result.partition.size();++index) {
        const auto& leaf=result.partition[index];
        if(leaf.state==LeafState::unqueried&&(!selected||leaf.cell.depth<result.partition[*selected].cell.depth)) {selected=index;}
    }
    return selected;
}
struct InputFailure {
    Reason reason;
    std::size_t ordinal;
    const char* message;
};
std::optional<InputFailure> input_failure(const Input& input) noexcept {
    if(!sphere_valid(input.first)) {
        return InputFailure{Reason::input_domain,0,"First sphere is outside the point input domain"};
    }
    if(!sphere_valid(input.second)) {
        return InputFailure{Reason::input_domain,1,"Second sphere is outside the point input domain"};
    }
    if(!std::isfinite(input.first_position_error)||input.first_position_error<0||input.first_position_error>1e12) {
        return InputFailure{Reason::position_error,2,"First declared position error must be finite in [0,1e12]"};
    }
    if(!std::isfinite(input.second_position_error)||input.second_position_error<0||input.second_position_error>1e12) {
        return InputFailure{Reason::position_error,3,"Second declared position error must be finite in [0,1e12]"};
    }
    if(!std::isfinite(input.contact_margin)||input.contact_margin<0||input.contact_margin>.1) {
        return InputFailure{Reason::contact_margin,4,"Explicit contact margin must be finite in [0,.1]"};
    }
    return std::nullopt;
}
I coordinate(double position,double velocity,double acceleration,const I& time,
             const I& squared_time,const I& error) {
    // Preserve this outward Interval AST. In particular aNom/2 is NOT first
    // rounded to a scalar, and B is not a derived physical/World bound here.
    const I linear=I::point(position)+I::point(velocity)*time;
    const I half_acceleration=I::point(acceleration)*I::point(.5);
    return (linear+half_acceleration*squared_time)+error;
}
}

Evaluation value(const Input& input,const I& time,unsigned sqrt_refinements) {
    interval::require_environment();
    if(const auto failure=input_failure(input)) {
        throw std::invalid_argument(failure->message);
    }
    if(sqrt_refinements<1||sqrt_refinements>maximum_sqrt_refinements) {
        throw std::invalid_argument("Sphere box square root refinement limit must be in [1,256]");
    }
    if(!std::isfinite(time.lower())||!std::isfinite(time.upper())||time.lower()<0||time.upper()>.1) {
        throw std::invalid_argument("Sphere box evaluation time must be finite in [0,.1] seconds");
    }
    const I squared_time=interval::square(time);
    const auto coordinates=[&](const accelerated::Sphere& sphere,double bound) {
        const I error{-bound,bound};
        return std::array<I,3>{
            coordinate(sphere.center.x,sphere.velocity.x,sphere.acceleration.x,time,squared_time,error),
            coordinate(sphere.center.y,sphere.velocity.y,sphere.acceleration.y,time,squared_time,error),
            coordinate(sphere.center.z,sphere.velocity.z,sphere.acceleration.z,time,squared_time,error)};
    };
    const auto first=coordinates(input.first,input.first_position_error);
    const auto second=coordinates(input.second,input.second_position_error);
    const std::array<I,3> delta{second[0]-first[0],second[1]-first[1],second[2]-first[2]};
    // The exact association follows Vec3::dot. Do not intersect this family with
    // a nominal quartic/Horner result: that could remove rounded predicate values.
    const I raw_squared=(interval::square(delta[0])+interval::square(delta[1]))+interval::square(delta[2]);
    if(!std::isfinite(raw_squared.lower())||!std::isfinite(raw_squared.upper())||raw_squared.upper()<0) {
        throw std::logic_error("Sphere box squared distance is not a finite nonnegative range");
    }
    // Each product and sum in the exact-or-RN family is nonnegative. Only the
    // outward lower endpoint can be negative; a negative upper is never clamped.
    const I squared{std::max(0.0,raw_squared.lower()),raw_squared.upper()};
    const auto root=interval::sqrt_enclosure(squared,sqrt_refinements); // EXACTLY one call.
    // Binary64 endpoints contain both exact sqrt and its monotone RN image.
    // This does not establish the external std::sqrt supported-target binding.
    const I distance=root.value;
    const I threshold=(I::point(input.first.radius)+I::point(input.second.radius))+I::point(input.contact_margin);
    const I gap=distance-threshold;
    return Evaluation{first,second,delta,raw_squared,squared,root,distance,threshold,gap};
}

Result query(const Input& input,double horizon_seconds,const Settings& settings) noexcept {
    Result result;
    if(const char* issue=interval::environment_issue()) {
        fail(result,Status::unsupported_environment,Reason::environment,issue);
        return result;
    }
    // Fixed-size, nothrow copy precedes all validation in supported environments.
    // Invalid captured originals are retained, not promoted to a valid tube.
    result.snapshot.emplace(Snapshot{input,horizon_seconds,settings});
    const Snapshot& snapshot=*result.snapshot;
    const auto& profile=snapshot.settings;
    const Input& captured=snapshot.input;
    if(!settings_valid(profile)) {
        fail(result,Status::invalid_input,Reason::settings,"Invalid sphere box coverage precision or budget");
        return result;
    }
    if(!std::isfinite(snapshot.horizon)||snapshot.horizon<=0||snapshot.horizon>.1) {
        fail(result,Status::invalid_input,Reason::horizon,"Coverage horizon must be finite in (0,.1] seconds");
        return result;
    }
    if(const auto failure=input_failure(captured)) {
        result.failed_input=failure->ordinal;
        fail(result,Status::invalid_input,failure->reason,failure->message);
        return result;
    }
    result.snapshot_validated=true;
    try {
        result.audits.reserve(profile.max_evaluations);
        result.partition.reserve(profile.max_leaves);
        result.frontier.reserve(profile.max_leaves);
        result.partition.push_back(PartitionLeaf{Cell{{0,snapshot.horizon},0,{}},LeafState::unqueried,{},Reason::none});
        result.partition_complete=true;
        while(const auto selected=next_leaf(result)) {
            const auto index=*selected;
            auto& leaf=result.partition[index];
            leaf.state=LeafState::current;
            result.current=leaf.cell;
            if(result.work.value_calls_attempted==profile.max_evaluations) {
                halt(result,Reason::evaluation_budget,"Sphere box coverage evaluation budget exhausted");
                finish(result);
                return result;
            }
            const auto audit_index=result.audits.size();
            result.audits.push_back(Audit{leaf.cell,false,{},Outcome::pending,Reason::none,{}});
            leaf.audit_index=audit_index;
            Audit& audit=result.audits[audit_index];
            const I time{leaf.cell.time_bounds[0],leaf.cell.time_bounds[1]};
            // Reserve the whole possible root block BEFORE the throwing public
            // call. All counts fit the fixed 255*2*256 hard bound.
            const std::size_t root_reservation=2*static_cast<std::size_t>(profile.sqrt_refinements);
            result.work.sqrt_refinements_upper=result.work.sqrt_refinements_returned+root_reservation;
            audit.call_attempted=true;
            ++result.work.value_calls_attempted;
            try {
                const Evaluation evaluated=value(captured,time,profile.sqrt_refinements);
                // Commit complete-return observations immediately, before the
                // fixed-size nothrow copy into the optional audit record.
                ++result.work.value_calls_returned;
                ++result.work.sqrt_results_returned;
                result.work.sqrt_refinements_returned+=evaluated.root.refinements;
                if(evaluated.root.refinement_limited) {++result.work.sqrt_limited_returns;}
                result.work.sqrt_refinements_upper=result.work.sqrt_refinements_returned;
                audit.evaluation.emplace(evaluated);
            }catch(...) {
                // A private sqrt may or may not have run before value threw.
                // Its actual attempts/refinements are not observable here.
                result.work.exact=false;
                result.work.sqrt_refinements_upper=result.work.sqrt_refinements_returned+root_reservation;
                halt(result,Reason::value_exception,"Public sphere box value call did not return");
                finish(result);
                return result;
            }
            if(audit.evaluation->gap.strictly_positive()) {
                leaf.state=LeafState::certified;
                audit.outcome=Outcome::positive;
                result.current.reset();
                continue;
            }
            if(audit.evaluation->gap.upper()<=0) {
                block(result,index,Reason::nonpositive_value);
                continue;
            }
            const I width=I::point(leaf.cell.time_bounds[1])-I::point(leaf.cell.time_bounds[0]);
            if(width.upper()<=profile.time_tolerance) {
                block(result,index,Reason::width_limit);
                continue;
            }
            if(leaf.cell.depth==profile.max_depth) {
                block(result,index,Reason::depth_budget);
                continue;
            }
            const double midpoint=std::midpoint(leaf.cell.time_bounds[0],leaf.cell.time_bounds[1]);
            if(!(midpoint>leaf.cell.time_bounds[0]&&midpoint<leaf.cell.time_bounds[1])) {
                block(result,index,Reason::time_resolution);
                continue;
            }
            if(result.partition.size()==profile.max_leaves) {
                block(result,index,Reason::leaf_budget);
                continue;
            }
            const Cell parent=leaf.cell;
            audit.outcome=Outcome::split;
            audit.split_time=midpoint;
            // No reallocation; both children share the identical original-global
            // seconds endpoint. All unqueried, blocked and certified tail stays.
            result.partition.push_back(result.partition.back());
            for(std::size_t move=result.partition.size()-1;move>index+1;--move) {
                result.partition[move]=result.partition[move-1];
            }
            result.partition[index]=PartitionLeaf{Cell{{parent.time_bounds[0],midpoint},parent.depth+1,audit_index},LeafState::unqueried,{},Reason::none};
            result.partition[index+1]=PartitionLeaf{Cell{{midpoint,parent.time_bounds[1]},parent.depth+1,audit_index},LeafState::unqueried,{},Reason::none};
            result.current.reset();
        }
        if(!consistent(result)) {
            halt(result,Reason::coverage_inconsistent,"Sphere box coverage metadata is inconsistent");
        }else {
            Reason blocked=Reason::none;
            for(const auto& leaf:result.partition) {
                if(leaf.state!=LeafState::certified) {blocked=leaf.blocked_reason;break;}
            }
            if(blocked==Reason::none) {
                result.status=Status::certified;
                result.reason=Reason::none;
            }else {
                fail(result,Status::not_certified,blocked,"At least one closed sphere box cell remains unproven");
            }
        }
    }catch(const std::bad_alloc&) {
        halt(result,Reason::allocation_failure,"Sphere box coverage storage allocation failed");
    }catch(...) {
        halt(result,Reason::coverage_inconsistent,"Sphere box coverage processing did not complete");
    }
    finish(result);
    return result;
}
}

#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
