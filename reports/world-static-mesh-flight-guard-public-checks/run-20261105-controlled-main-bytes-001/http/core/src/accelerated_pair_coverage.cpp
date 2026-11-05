#include "pikapika/accelerated_pair_coverage.hpp"
#include <cmath>
#include <new>
#include <numeric>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Accelerated pair coverage requires strict floating point.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::accelerated_pair_coverage {
namespace {
using I=interval::Interval;
static_assert(std::is_nothrow_copy_constructible_v<Snapshot>);
static_assert(std::is_nothrow_copy_constructible_v<Audit>);
static_assert(std::is_nothrow_copy_assignable_v<PartitionLeaf>);
static_assert(std::is_nothrow_copy_constructible_v<Cell>);
static_assert(std::is_nothrow_move_constructible_v<Result>);

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
        settings.max_leaves<=maximum_leaves&&settings.max_depth<=maximum_depth;
}
bool same_cell(const Cell& a,const Cell& b) noexcept {
    return a.time_bounds==b.time_bounds&&a.depth==b.depth&&a.parent_audit==b.parent_audit;
}
// No Interval arithmetic or allocation: this verifies our own metadata, not a
// second geometry solver. Every record was produced from the owned snapshot.
bool consistent(const Result& result,bool plane) noexcept {
    if(!result.snapshot||!result.snapshot_validated||!result.partition_complete||result.partition.empty()) {return false;}
    const auto& settings=result.snapshot->settings;
    if(result.partition.size()>settings.max_leaves||result.audits.size()>settings.max_evaluations||
       result.partition.front().cell.time_bounds[0]!=0||
       result.partition.back().cell.time_bounds[1]!=result.snapshot->horizon) {return false;}
    std::size_t attempted=0,returned=0,current_count=0;
    for(std::size_t index=0;index<result.audits.size();++index) {
        const Audit& audit=result.audits[index];
        if(audit.call_attempted) {++attempted;}
        if(audit.value) {++returned;}
        if(audit.value&&!audit.call_attempted) {return false;}
        if(audit.outcome==Outcome::pending) {return false;}
        if(audit.outcome==Outcome::positive) {
            if(!audit.value||!audit.value->strictly_positive()||audit.blocked_reason!=Reason::none||audit.split_time) {return false;}
        }else if(audit.outcome==Outcome::split) {
            if(!audit.value||audit.value->strictly_positive()||audit.value->upper()<=0||
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
    return current_count==(result.current?1U:0U)&&attempted==result.work.value_calls_attempted&&
        returned==result.work.value_calls_returned&&returned<=attempted&&
        result.work.plane_norm_calls_upper==(plane?attempted:0)&&
        result.work.plane_norm_loop_iterations_upper==(plane?64*attempted:0);
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
template<class Second>
Result query(const accelerated::Sphere& first,const Second& second,double horizon,const Settings& settings) noexcept {
    constexpr bool plane=std::is_same_v<Second,accelerated::StaticPlane>;
    Result result;
    if(const char* issue=interval::environment_issue()) {
        fail(result,Status::unsupported_environment,Reason::environment,issue);
        return result;
    }
    // The snapshot contains only fixed-size, nothrow-copyable values; invalid
    // source is retained without constructing any Interval or owning allocation.
    if constexpr(plane) {result.snapshot.emplace(Snapshot{SpherePlane{first,second},horizon,settings});}
    else {result.snapshot.emplace(Snapshot{SpherePair{first,second},horizon,settings});}
    const Snapshot& snapshot=*result.snapshot;
    const auto& profile=snapshot.settings;
    const accelerated::Sphere& a=[&]() -> const accelerated::Sphere& {
        if constexpr(plane) {return std::get<SpherePlane>(snapshot.input).sphere;}
        else {return std::get<SpherePair>(snapshot.input).first;}
    }();
    const Second& b=[&]() -> const Second& {
        if constexpr(plane) {return std::get<SpherePlane>(snapshot.input).plane;}
        else {return std::get<SpherePair>(snapshot.input).second;}
    }();
    if(!settings_valid(profile)) {
        fail(result,Status::invalid_input,Reason::settings,"Invalid coverage precision or budget");
        return result;
    }
    if(!std::isfinite(snapshot.horizon)||snapshot.horizon<=0||snapshot.horizon>.1) {
        fail(result,Status::invalid_input,Reason::horizon,"Coverage horizon must be finite in (0,.1] seconds");
        return result;
    }
    if(!sphere_valid(a)) {
        result.failed_input=0;
        fail(result,Status::invalid_input,Reason::input_domain,"First sphere is outside the point input domain");
        return result;
    }
    if constexpr(plane) {
        if(!vector_valid(b.normal)||!scalar_valid(b.offset)) {
            result.failed_input=1;
            fail(result,Status::invalid_input,Reason::input_domain,"Plane is outside the point input domain");
            return result;
        }
        if(b.normal.x==0&&b.normal.y==0&&b.normal.z==0) {
            result.failed_input=1;
            fail(result,Status::invalid_input,Reason::zero_normal,"Plane normal must be nonzero");
            return result;
        }
    }else {
        if(!sphere_valid(b)) {
            result.failed_input=1;
            fail(result,Status::invalid_input,Reason::input_domain,"Second sphere is outside the point input domain");
            return result;
        }
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
                halt(result,Reason::evaluation_budget,"Coverage evaluation budget exhausted");
                finish(result);
                return result;
            }
            const auto audit_index=result.audits.size();
            result.audits.push_back(Audit{leaf.cell,false,{},Outcome::pending,Reason::none,{}});
            leaf.audit_index=audit_index;
            Audit& audit=result.audits[audit_index];
            const I time{leaf.cell.time_bounds[0],leaf.cell.time_bounds[1]};
            audit.call_attempted=true;
            ++result.work.value_calls_attempted;
            if constexpr(plane) {
                ++result.work.plane_norm_calls_upper;
                result.work.plane_norm_loop_iterations_upper+=64;
            }
            try {
                const I value=[&]() {
                    if constexpr(plane) {return accelerated::sphere_plane_value(a,b,time);}
                    else {return accelerated::sphere_sphere_value(a,b,time);}
                }();
                ++result.work.value_calls_returned;
                audit.value=value;
            }catch(...) {
                halt(result,Reason::value_exception,"Public accelerated value call did not return");
                finish(result);
                return result;
            }
            if(audit.value->strictly_positive()) {
                leaf.state=LeafState::certified;
                audit.outcome=Outcome::positive;
                result.current.reset();
                continue;
            }
            if(audit.value->upper()<=0) {
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
            // All storage is already reserved. Install exactly the two closed
            // children, retaining the identical shared binary64 endpoint.
            result.partition.push_back(result.partition.back());
            for(std::size_t move=result.partition.size()-1;move>index+1;--move) {
                result.partition[move]=result.partition[move-1];
            }
            result.partition[index]=PartitionLeaf{Cell{{parent.time_bounds[0],midpoint},parent.depth+1,audit_index},LeafState::unqueried,{},Reason::none};
            result.partition[index+1]=PartitionLeaf{Cell{{midpoint,parent.time_bounds[1]},parent.depth+1,audit_index},LeafState::unqueried,{},Reason::none};
            result.current.reset();
        }
        if(!consistent(result,plane)) {
            halt(result,Reason::coverage_inconsistent,"Coverage metadata is inconsistent");
        }else {
            Reason blocked=Reason::none;
            for(const auto& leaf:result.partition) {
                if(leaf.state!=LeafState::certified) {blocked=leaf.blocked_reason;break;}
            }
            if(blocked==Reason::none) {
                result.status=Status::certified;
                result.reason=Reason::none;
            }else {
                fail(result,Status::not_certified,blocked,"At least one closed cell remains unproven");
            }
        }
    }catch(const std::bad_alloc&) {
        halt(result,Reason::allocation_failure,"Coverage storage allocation failed");
    }catch(...) {
        halt(result,Reason::coverage_inconsistent,"Coverage processing did not complete");
    }
    finish(result);
    return result;
}
}

Result sphere_sphere(const accelerated::Sphere& first,const accelerated::Sphere& second,
                     double horizon_seconds,const Settings& settings) noexcept {
    return query(first,second,horizon_seconds,settings);
}
Result sphere_plane(const accelerated::Sphere& sphere,const accelerated::StaticPlane& plane,
                    double horizon_seconds,const Settings& settings) noexcept {
    return query(sphere,plane,horizon_seconds,settings);
}
}

#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
