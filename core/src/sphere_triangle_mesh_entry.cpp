#include "pikapika/sphere_triangle_mesh_entry.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <numeric>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Entry certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle_mesh_entry {
namespace {
using I=interval::Interval;
namespace mesh=sphere_triangle_mesh;
namespace tri=sphere_triangle;
struct Stop {Status status;Reason reason;const char* text;};
void need(bool b,Status status,Reason reason,const char* text){if(!b)throw Stop{status,reason,text};}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
I checked(I x){need(finite(x),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite entry interval");return x;}
bool bounded(Vec3 v,double cap=coordinate_limit){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=cap;}
Bounds3 point(Vec3 p){return {I::point(p.x),I::point(p.y),I::point(p.z)};}
Bounds3 path(const Bounds3& origin,const Bounds3& delta,I s){return {checked(origin[0]+s*delta[0]),checked(origin[1]+s*delta[1]),checked(origin[2]+s*delta[2])};}
I norm_squared(const Bounds3& b,Vec3 c){I sum=I::point(0);const std::array<double,3> a{c.x,c.y,c.z};
    for(unsigned j=0;j<3;++j){sum=checked(sum+interval::square(checked(b[j]-I::point(a[j]))));}return sum;}
bool profile(const Settings& s){const auto& p=s.mesh.primitive;
    return s.mesh.max_surfaces>=1&&s.mesh.max_surfaces<=64&&p.max_candidates>=1&&p.max_candidates<=7&&p.sqrt_refinements>=1&&p.sqrt_refinements<=256&&p.max_total_sqrt_refinements>=1&&p.max_total_sqrt_refinements<=1024&&
        std::isfinite(p.maximum_local_width)&&p.maximum_local_width>0&&p.maximum_local_width<=1e6&&std::isfinite(p.maximum_normal_width)&&p.maximum_normal_width>0&&p.maximum_normal_width<=2&&
        std::isfinite(p.minimum_sine_squared)&&p.minimum_sine_squared>0&&p.minimum_sine_squared<=1&&std::isfinite(s.parameter_tolerance)&&s.parameter_tolerance>0&&s.parameter_tolerance<=1&&
        s.max_evaluations>=1&&s.max_evaluations<=256&&s.max_leaves>=1&&s.max_leaves<=128&&s.max_depth<=32&&s.enclosure_sqrt_refinements>=1&&s.enclosure_sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=16777216;
}
bool same_cell(const Cell& a,const Cell& b){return a.depth==b.depth&&a.parameter==b.parameter;}
void fail(Result& out,Status status,Reason reason,const char* text) noexcept {
    out.status=status;out.reason=reason;out.window.reset();out.candidate_surface_ids.clear();
    if(out.current){
        if(!out.audits.empty()&&same_cell(out.audits.back().cell,*out.current)&&out.audits.back().outcome==Outcome::pending)out.audits.back().outcome=Outcome::unresolved;
        for(auto& leaf:out.partition)if(leaf.state==LeafState::current&&same_cell(leaf.cell,*out.current))leaf.blocked_reason=reason;
    }
    try{out.message=text;}catch(...){out.message.clear();}
}
void sync(Work& w){w.sqrt_refinements=w.primitive_sqrt_refinements+w.enclosure_sqrt_refinements;if(w.exact)w.sqrt_refinements_upper=w.sqrt_refinements;}
struct InFlight {std::size_t global_before{},audit_before{},reserved{},audit_index{};};
void uncertain(Result& out,const InFlight& f) noexcept {
    out.work.exact=false;out.work.sqrt_refinements_upper=f.global_before+f.reserved;
    auto& w=out.audits[f.audit_index].work;w.exact=false;w.sqrt_refinements_upper=f.audit_before+f.reserved;
}
bool unknown_work(const mesh::Result& m){
    if(m.status==mesh::Status::numerical_failure)return true;
    for(const auto& r:m.rows)if(!r.query||r.query->status==tri::Status::numerical_failure)return true;
    return false;
}
bool environment_failure(const mesh::Result& m){
    if(m.status==mesh::Status::unsupported_environment)return true;
    for(const auto& r:m.rows)if(r.query&&r.query->status==tri::Status::unsupported_environment)return true;
    return false;
}
bool recoverable_rows(const mesh::Result& m){
    if(m.status!=mesh::Status::row_failure||m.failed_rows==0)return false;
    for(const auto& row:m.rows){if(!row.query)return false;const auto status=row.query->status;
        if(status!=tri::Status::completed&&status!=tri::Status::degenerate&&status!=tri::Status::ill_conditioned&&status!=tri::Status::quality_unresolved&&status!=tri::Status::budget_exceeded)return false;
    }return true;
}
void update_prefix(Result& out){
    if(!out.initial_separation_proven)return;
    double end=0;
    for(const auto& leaf:out.partition){if(leaf.state!=LeafState::certified)break;
        need(leaf.cell.parameter[0]==end,Status::numerical_failure,Reason::coverage_inconsistent,"Gap in certified entry prefix");end=leaf.cell.parameter[1];}
    out.safe_prefix=std::array<double,2>{0,end};
}
bool accept_window(Result& out,const Settings& s){
    if(!out.initial_separation_proven||!out.safe_prefix||!out.best_witness||!out.work.exact)return false;
    const double l=(*out.safe_prefix)[1],u=out.best_witness->parameter;
    need(l<u,Status::numerical_failure,Reason::coverage_inconsistent,"Negative witness conflicts with strict certified prefix");
    const I width=checked(I::point(u)-I::point(l));
    if(width.upper()>s.parameter_tolerance)return false;
    for(const auto& triangle:out.snapshot->triangles)out.candidate_surface_ids.push_back(triangle.id);
    std::sort(out.candidate_surface_ids.begin(),out.candidate_surface_ids.end());
    out.window=EntryWindow{{l,u},width,out.best_witness->audit_index};out.status=Status::entry_window;out.reason=Reason::none;return true;
}
std::optional<std::size_t> next_leaf(const Result& out){
    std::optional<std::size_t> chosen;
    for(std::size_t i=0;i<out.partition.size();++i){const auto& l=out.partition[i];
        if(l.state!=LeafState::unqueried||(out.best_witness&&l.cell.parameter[0]>=out.best_witness->parameter))continue;
        if(!chosen||l.cell.depth<out.partition[*chosen].cell.depth||
            (l.cell.depth==out.partition[*chosen].cell.depth&&l.cell.parameter[0]<out.partition[*chosen].cell.parameter[0]))chosen=i;
    }return chosen;
}
// All capacities are reserved before a partition is installed. This final
// owned-view refresh uses only trivial Cell copies within existing capacity.
void finish(Result& out) noexcept {
    static_assert(std::is_nothrow_copy_constructible_v<Cell>);
    static_assert(std::is_nothrow_move_constructible_v<CertifiedLeaf>&&std::is_nothrow_move_assignable_v<CertifiedLeaf>);
    out.partition_leaves=out.partition.size();out.frontier.clear();
    for(const auto& l:out.partition)if(l.state==LeafState::unqueried)out.frontier.push_back(l.cell);
    // Bounded insertion sort, without allocating during an exception finalizer.
    for(std::size_t i=1;i<out.certified_leaves.size();++i){auto value=std::move(out.certified_leaves[i]);std::size_t j=i;
        while(j>0&&value.cell.parameter[0]<out.certified_leaves[j-1].cell.parameter[0]){out.certified_leaves[j]=std::move(out.certified_leaves[j-1]);--j;}
        out.certified_leaves[j]=std::move(value);
    }
}
}

Result query(Vec3 start,Vec3 end,double radius,std::span<const tri::StaticTriangle> triangles,const Settings& s){
    Result out;std::optional<InFlight> in_flight;std::optional<std::size_t> current_leaf;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(profile(s),Status::invalid_input,Reason::settings,"Invalid entry profile");
        need(!triangles.empty()&&triangles.size()<=64,Status::invalid_input,Reason::surface_count,"Entry requires 1..64 surfaces");
        need(bounded(start)&&bounded(end)&&std::isfinite(radius)&&radius>0&&radius<=coordinate_limit,Status::invalid_input,Reason::input_domain,"Entry path/radius outside finite domain");
        for(std::size_t i=0;i<triangles.size();++i){out.failed_index=i;const auto& t=triangles[i];
            need(t.id>0&&t.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid entry surface ID");
            for(std::size_t j=0;j<i;++j)need(t.id!=triangles[j].id,Status::invalid_input,Reason::duplicate_id,"Duplicate entry surface ID");
            need(std::all_of(t.vertices.begin(),t.vertices.end(),[](Vec3 p){return bounded(p);}),Status::invalid_input,Reason::input_domain,"Entry source outside finite domain");
        }
        out.failed_index.reset();out.snapshot=Snapshot{start,end,radius,{triangles.begin(),triangles.end()},s};
        out.frontier.reserve(s.max_leaves);out.partition.reserve(s.max_leaves);out.certified_leaves.reserve(s.max_leaves);out.audits.reserve(s.max_evaluations);out.candidate_surface_ids.reserve(triangles.size());
        out.partition.push_back({});out.partition_leaves=1;
        need(triangles.size()<=s.mesh.max_surfaces,Status::not_certified,Reason::surface_budget,"Entry source exceeds mesh budget");
        const auto origin=point(start),endpoints=point(end);
        const Bounds3 delta{checked(endpoints[0]-origin[0]),checked(endpoints[1]-origin[1]),checked(endpoints[2]-origin[2])};
        const auto evaluate=[&](AuditKind kind,const Cell& cell){
            out.current=cell;out.maximum_depth=std::max(out.maximum_depth,cell.depth);
            need(out.work.mesh_queries<s.max_evaluations,Status::not_certified,Reason::evaluation_budget,"Entry mesh evaluation budget exhausted");
            out.audits.emplace_back();const std::size_t index=out.audits.size()-1;auto& a=out.audits.back();a.kind=kind;a.cell=cell;
            if(current_leaf)out.partition[*current_leaf].audit_index=index;
            a.parameter=kind==AuditKind::initial_point?0:std::midpoint(cell.parameter[0],cell.parameter[1]);
            if(kind==AuditKind::cell)need(cell.parameter[0]<a.parameter&&a.parameter<cell.parameter[1],Status::not_certified,Reason::parameter_resolution,"Entry midpoint has no representable interior");
            a.path_bounds=kind==AuditKind::initial_point?origin:path(origin,delta,I(cell.parameter[0],cell.parameter[1]));
            a.point_bounds=kind==AuditKind::initial_point?origin:path(origin,delta,I::point(a.parameter));
            const auto& p=*a.point_bounds;const Vec3 c=kind==AuditKind::initial_point?start:Vec3{p[0].lower()/2+p[0].upper()/2,p[1].lower()/2+p[1].upper()/2,p[2].lower()/2+p[2].upper()/2};a.anchor=c;
            need(bounded(c,tri::coordinate_limit),Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid derived entry anchor");
            const auto reserve=[&](std::size_t worst){
                need(out.work.sqrt_refinements_upper<=s.max_total_sqrt_refinements&&worst<=s.max_total_sqrt_refinements-out.work.sqrt_refinements_upper,Status::not_certified,Reason::sqrt_budget,"Entry sqrt block reservation failed");
                in_flight=InFlight{out.work.sqrt_refinements,a.work.sqrt_refinements,worst,index};
            };
            reserve(triangles.size()*512);a.mesh_queried=true;++a.work.mesh_queries;++out.work.mesh_queries;
            auto m=mesh::query({c,radius},out.snapshot->triangles,s.mesh);a.mesh_status=m.status;a.mesh_reason=m.reason;
            need(m.queries<=triangles.size()&&m.candidates_examined<=triangles.size()*7&&m.sqrt_refinements<=triangles.size()*512,Status::numerical_failure,Reason::coverage_inconsistent,"Invalid returned entry mesh work");
            a.work.primitive_queries=m.queries;a.work.candidates_examined=m.candidates_examined;a.work.primitive_sqrt_refinements=m.sqrt_refinements;a.work.mesh_sqrt_limited_rows=m.sqrt_limited_rows;
            out.work.primitive_queries+=m.queries;out.work.candidates_examined+=m.candidates_examined;out.work.primitive_sqrt_refinements+=m.sqrt_refinements;out.work.mesh_sqrt_limited_rows+=m.sqrt_limited_rows;sync(a.work);sync(out.work);
            const bool unknown=unknown_work(m),environment=environment_failure(m),recoverable=recoverable_rows(m);
            if(unknown)uncertain(out,*in_flight);
            in_flight.reset();
            static_assert(std::is_nothrow_move_assignable_v<std::optional<mesh::Result>>);
            out.last_mesh=std::move(m);out.last_mesh_audit_index=index;const auto& last=*out.last_mesh;
            need(!environment,Status::unsupported_environment,Reason::environment,"Entry mesh environment rejected");
            need(!unknown,Status::not_certified,Reason::mesh_query_failed,"Entry mesh has unknown executed work");
            if(last.status!=mesh::Status::completed){
                need(recoverable,Status::numerical_failure,Reason::coverage_inconsistent,"Unexpected entry mesh failure classification");
                need(kind!=AuditKind::initial_point,Status::not_certified,Reason::mesh_query_failed,"Initial entry point has no certified distance");return index;
            }
            need(last.nearest.has_value(),Status::numerical_failure,Reason::coverage_inconsistent,"Completed entry mesh lacks nearest bounds");a.distance=last.nearest->distance;
            a.displacement_squared_bound=norm_squared(*a.path_bounds,c);a.error_squared_bound=norm_squared(*a.point_bounds,c);
            const auto root=[&](I squared){
                need(finite(squared)&&squared.upper()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid entry norm square");
                reserve(512);++a.work.enclosure_sqrt_calls;++out.work.enclosure_sqrt_calls;
                const auto result=interval::sqrt_enclosure(I::point(squared.upper()),s.enclosure_sqrt_refinements);
                need(result.refinements<=512,Status::numerical_failure,Reason::coverage_inconsistent,"Entry root exceeded block bound");
                a.work.enclosure_sqrt_refinements+=result.refinements;out.work.enclosure_sqrt_refinements+=result.refinements;
                a.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;out.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;sync(a.work);sync(out.work);in_flight.reset();
                need(finite(result.value)&&result.value.lower()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid entry norm root");return result.value;
            };
            a.displacement_root=root(*a.displacement_squared_bound);a.error_root=root(*a.error_squared_bound);
            a.clearance_certificate=checked(I::point(a.distance->lower())-I::point(a.displacement_root->upper())-I::point(radius));
            a.penetration_certificate=checked(I::point(a.distance->upper())+I::point(a.error_root->upper())-I::point(radius));return index;
        };
        const auto initial_index=evaluate(AuditKind::initial_point,Cell{{0,0},0});auto& initial=out.audits[initial_index];
        need(initial.clearance_certificate&&initial.penetration_certificate,Status::numerical_failure,Reason::coverage_inconsistent,"Initial entry proof missing bounds");
        out.initial=InitialProof{*initial.clearance_certificate,*initial.penetration_certificate,initial_index};out.current.reset();
        if(initial.clearance_certificate->strictly_positive()){initial.outcome=Outcome::initial_separated;out.initial_separation_proven=true;out.safe_prefix=std::array<double,2>{0,0};}
        else if(initial.penetration_certificate->strictly_negative()){initial.outcome=Outcome::initial_penetration;out.status=Status::initial_penetration;out.reason=Reason::none;finish(out);return out;}
        else{initial.outcome=Outcome::initial_uncertain;fail(out,Status::not_certified,Reason::initial_boundary,"Initial entry sign is not strict");finish(out);return out;}
        while(const auto chosen=next_leaf(out)){
            current_leaf=*chosen;auto& selected=out.partition[*chosen];selected.state=LeafState::current;const auto cell=selected.cell;
            const auto index=evaluate(AuditKind::cell,cell);auto& a=out.audits[index];
            if(a.penetration_certificate&&a.penetration_certificate->strictly_negative()&&(!out.best_witness||a.parameter<out.best_witness->parameter))
                out.best_witness=Witness{cell,a.parameter,*a.point_bounds,*a.anchor,a.error_root->upper(),*a.penetration_certificate,index};
            auto& leaf=out.partition[*chosen];
            if(a.clearance_certificate&&a.clearance_certificate->strictly_positive()){
                leaf.state=LeafState::certified;a.outcome=Outcome::separated;out.certified_leaves.push_back({cell,*a.clearance_certificate,index});out.current.reset();current_leaf.reset();update_prefix(out);
                if(accept_window(out,s)){finish(out);return out;}continue;
            }
            leaf.state=LeafState::unresolved;a.outcome=Outcome::unresolved;out.current.reset();current_leaf.reset();
            if(accept_window(out,s)){finish(out);return out;}
            if(cell.depth>=s.max_depth){leaf.blocked_reason=Reason::depth_budget;continue;}
            if(out.partition.size()>=s.max_leaves){leaf.blocked_reason=Reason::leaf_budget;continue;}
            const PartitionLeaf left{Cell{{cell.parameter[0],a.parameter},cell.depth+1},LeafState::unqueried,std::nullopt,Reason::none};
            const PartitionLeaf right{Cell{{a.parameter,cell.parameter[1]},cell.depth+1},LeafState::unqueried,std::nullopt,Reason::none};
            out.partition[*chosen]=left;out.partition.insert(out.partition.begin()+*chosen+1,right);out.partition_leaves=out.partition.size();a.outcome=Outcome::split;
        }
        update_prefix(out);
        if(accept_window(out,s)){finish(out);return out;}
        const bool all_separated=std::all_of(out.partition.begin(),out.partition.end(),[](const auto& leaf){return leaf.state==LeafState::certified;});
        if(all_separated){need(out.work.exact&&!out.best_witness&&out.safe_prefix&&(*out.safe_prefix)[1]==1,Status::numerical_failure,Reason::coverage_inconsistent,"Incomplete separated entry partition");out.status=Status::separated;out.reason=Reason::none;}
        else{
            Reason blocked=Reason::none;
            for(const auto& leaf:out.partition)if(leaf.state==LeafState::unresolved&&leaf.blocked_reason!=Reason::none){blocked=leaf.blocked_reason;break;}
            need(blocked!=Reason::none,Status::numerical_failure,Reason::coverage_inconsistent,"Entry has remaining cells without blocking reason");
            fail(out,Status::not_certified,blocked,"Unresolved entry partition exhausted eligible work");
        }
    }catch(const Stop& e){if(in_flight)uncertain(out,*in_flight);fail(out,e.status,e.reason,e.text);}
    catch(const std::bad_alloc&){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::allocation_failure,"Entry diagnostic allocation failed");}
    catch(const std::exception& e){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    catch(...){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown entry exception");}
    finish(out);return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
