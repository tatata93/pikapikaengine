#include "pikapika/sphere_triangle_mesh_trajectory.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <numeric>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Trajectory certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle_mesh_trajectory {
namespace {
using I=interval::Interval;
namespace mesh=sphere_triangle_mesh;
namespace tri=sphere_triangle;
struct Stop {Status status;Reason reason;const char* text;};
void need(bool b,Status status,Reason reason,const char* text){if(!b)throw Stop{status,reason,text};}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
I checked(I x){need(finite(x),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite guard interval");return x;}
bool bounded(Vec3 v,double cap=coordinate_limit){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=cap;}
std::array<double,3> xyz(Vec3 v){return {v.x,v.y,v.z};}
Bounds3 point(Vec3 v){return {I::point(v.x),I::point(v.y),I::point(v.z)};}
Bounds3 path(const Bounds3& origin,const Bounds3& delta,I s){return {checked(origin[0]+s*delta[0]),checked(origin[1]+s*delta[1]),checked(origin[2]+s*delta[2])};}
I norm_squared(const Bounds3& b,Vec3 c){I sum=I::point(0);const auto a=xyz(c);for(unsigned j=0;j<3;++j)sum=checked(sum+interval::square(checked(b[j]-I::point(a[j]))));return sum;}
bool profile(const Settings& s){const auto& p=s.mesh.primitive;return s.mesh.max_surfaces>=1&&s.mesh.max_surfaces<=64&&p.max_candidates>=1&&p.max_candidates<=7&&p.sqrt_refinements>=1&&p.sqrt_refinements<=256&&p.max_total_sqrt_refinements>=1&&p.max_total_sqrt_refinements<=1024&&std::isfinite(p.maximum_local_width)&&p.maximum_local_width>0&&p.maximum_local_width<=1e6&&std::isfinite(p.maximum_normal_width)&&p.maximum_normal_width>0&&p.maximum_normal_width<=2&&std::isfinite(p.minimum_sine_squared)&&p.minimum_sine_squared>0&&p.minimum_sine_squared<=1&&s.max_evaluations>=1&&s.max_evaluations<=1024&&s.max_leaves>=1&&s.max_leaves<=128&&s.max_depth<=32&&s.enclosure_sqrt_refinements>=1&&s.enclosure_sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=16777216;}
void fail(Result& out,Status status,Reason reason,const char* text) noexcept {
    out.status=status;out.reason=reason;if(status!=Status::penetration_witness)out.witness.reset();
    if(out.current&&!out.audits.empty()&&out.audits.back().cell.parameter==out.current->parameter&&out.audits.back().outcome==Outcome::pending)out.audits.back().outcome=Outcome::not_certified;
    try{out.message=text;}catch(...){out.message.clear();}
}
bool ambiguous_work(const mesh::Result& r){
    if(r.status==mesh::Status::numerical_failure)return true;
    for(const auto& row:r.rows)if(!row.query||row.query->status==tri::Status::numerical_failure)return true;
    return false;
}
struct InFlight {std::size_t global_before{},cell_before{},reserved{},audit_index{};};
void uncertain(Result& out,const InFlight& f) noexcept {
    out.work.exact=false;out.work.sqrt_refinements_upper=f.global_before+f.reserved;
    auto& w=out.audits[f.audit_index].work;w.exact=false;w.sqrt_refinements_upper=f.cell_before+f.reserved;
}
void sync(Work& w){w.sqrt_refinements=w.primitive_sqrt_refinements+w.enclosure_sqrt_refinements;if(w.exact)w.sqrt_refinements_upper=w.sqrt_refinements;}
}

Result audit(Vec3 start,Vec3 end,double radius,std::span<const tri::StaticTriangle> triangles,const Settings& s){
    Result out;std::optional<InFlight> in_flight;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(profile(s),Status::invalid_input,Reason::settings,"Invalid trajectory guard profile");
        need(!triangles.empty()&&triangles.size()<=64,Status::invalid_input,Reason::surface_count,"Trajectory guard requires 1..64 surfaces");
        need(bounded(start)&&bounded(end)&&std::isfinite(radius)&&radius>0&&radius<=coordinate_limit,Status::invalid_input,Reason::input_domain,"Trajectory endpoints/radius outside finite domain");
        for(std::size_t j=0;j<triangles.size();++j){out.failed_index=j;const auto& t=triangles[j];
            need(t.id>=1&&t.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid trajectory surface ID");
            for(std::size_t k=0;k<j;++k)need(t.id!=triangles[k].id,Status::invalid_input,Reason::duplicate_id,"Duplicate trajectory surface ID");
            need(std::all_of(t.vertices.begin(),t.vertices.end(),[](Vec3 v){return bounded(v);}),Status::invalid_input,Reason::input_domain,"Trajectory source vertex outside finite domain");
        }
        out.failed_index.reset();
        Snapshot snapshot{start,end,radius,{triangles.begin(),triangles.end()},s};out.snapshot=std::move(snapshot);
        out.frontier.reserve(33);out.frontier.push_back(Cell{});out.partition_leaves=1;
        need(triangles.size()<=s.mesh.max_surfaces,Status::not_certified,Reason::surface_budget,"Source exceeds caller mesh budget");
        out.certified_leaves.reserve(s.max_leaves);out.audits.reserve(s.max_evaluations);
        const auto origin=point(start),finish=point(end);
        const Bounds3 delta{checked(finish[0]-origin[0]),checked(finish[1]-origin[1]),checked(finish[2]-origin[2])};
        while(!out.frontier.empty()){
            out.current=out.frontier.front();out.frontier.erase(out.frontier.begin());const auto cell=*out.current;
            out.maximum_depth=std::max(out.maximum_depth,cell.depth);
            need(out.work.mesh_queries<s.max_evaluations,Status::not_certified,Reason::evaluation_budget,"No remaining mesh evaluation budget");
            out.audits.emplace_back();const std::size_t index=out.audits.size()-1;auto& a=out.audits.back();a.cell=cell;
            a.midpoint=std::midpoint(cell.parameter[0],cell.parameter[1]);
            need(cell.parameter[0]<a.midpoint&&a.midpoint<cell.parameter[1],Status::not_certified,Reason::parameter_resolution,"No representable interior midpoint");
            a.path_bounds=path(origin,delta,I(cell.parameter[0],cell.parameter[1]));a.point_bounds=path(origin,delta,I::point(a.midpoint));
            const auto& pm=*a.point_bounds;const Vec3 c{pm[0].lower()/2+pm[0].upper()/2,pm[1].lower()/2+pm[1].upper()/2,pm[2].lower()/2+pm[2].upper()/2};a.anchor=c;
            need(bounded(c,tri::coordinate_limit),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite/out-of-domain derived anchor");
            const auto reserve=[&](std::size_t worst){need(out.work.sqrt_refinements_upper<=s.max_total_sqrt_refinements&&worst<=s.max_total_sqrt_refinements-out.work.sqrt_refinements_upper,Status::not_certified,Reason::sqrt_budget,"Insufficient worst-block sqrt reservation");in_flight=InFlight{out.work.sqrt_refinements,a.work.sqrt_refinements,worst,index};};
            reserve(triangles.size()*512);
            a.mesh_queried=true;++a.work.mesh_queries;++out.work.mesh_queries;
            auto m=mesh::query({c,radius},out.snapshot->triangles,s.mesh);
            a.mesh_status=m.status;a.mesh_reason=m.reason;
            need(m.queries<=triangles.size()&&m.candidates_examined<=triangles.size()*7&&m.sqrt_refinements<=triangles.size()*512,Status::numerical_failure,Reason::coverage_inconsistent,"Invalid underlying mesh work bound");
            a.work.primitive_queries=m.queries;a.work.candidates_examined=m.candidates_examined;a.work.primitive_sqrt_refinements=m.sqrt_refinements;a.work.mesh_sqrt_limited_rows=m.sqrt_limited_rows;
            out.work.primitive_queries+=m.queries;out.work.candidates_examined+=m.candidates_examined;out.work.primitive_sqrt_refinements+=m.sqrt_refinements;out.work.mesh_sqrt_limited_rows+=m.sqrt_limited_rows;sync(a.work);sync(out.work);
            const bool ambiguous=ambiguous_work(m);
            if(ambiguous)uncertain(out,*in_flight);
            in_flight.reset();
            static_assert(std::is_nothrow_move_assignable_v<std::optional<mesh::Result>>);
            out.last_mesh=std::move(m);out.last_mesh_audit_index=index;const auto& last=*out.last_mesh;
            need(last.status==mesh::Status::completed&&last.nearest.has_value()&&!ambiguous,Status::not_certified,Reason::mesh_query_failed,"Underlying triangle mesh query did not complete");
            a.distance=last.nearest->distance;
            a.displacement_squared_bound=norm_squared(*a.path_bounds,c);a.error_squared_bound=norm_squared(*a.point_bounds,c);
            const auto root=[&](I squared){
                need(finite(squared)&&squared.upper()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid norm squared upper bound");
                reserve(512);++a.work.enclosure_sqrt_calls;++out.work.enclosure_sqrt_calls;
                const auto result=interval::sqrt_enclosure(I::point(squared.upper()),s.enclosure_sqrt_refinements);
                need(result.refinements<=512,Status::numerical_failure,Reason::coverage_inconsistent,"Enclosure sqrt violated hard work bound");
                a.work.enclosure_sqrt_refinements+=result.refinements;out.work.enclosure_sqrt_refinements+=result.refinements;
                a.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;out.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;sync(a.work);sync(out.work);in_flight.reset();
                need(finite(result.value)&&result.value.lower()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid finite norm root enclosure");return result.value;
            };
            a.displacement_root=root(*a.displacement_squared_bound);a.error_root=root(*a.error_squared_bound);
            a.clearance_certificate=checked(I::point(a.distance->lower())-I::point(a.displacement_root->upper())-I::point(radius));
            a.penetration_certificate=checked(I::point(a.distance->upper())+I::point(a.error_root->upper())-I::point(radius));
            if(a.clearance_certificate->strictly_positive()){
                a.outcome=Outcome::separated;out.certified_leaves.push_back({cell,*a.clearance_certificate,index});
                const double previous=out.safe_prefix?(*out.safe_prefix)[1]:0;
                need(previous==cell.parameter[0],Status::numerical_failure,Reason::coverage_inconsistent,"Certified leaves do not extend contiguous prefix");
                out.safe_prefix=std::array<double,2>{0,cell.parameter[1]};out.current.reset();continue;
            }
            if(a.penetration_certificate->strictly_negative()){
                a.outcome=Outcome::penetration_witness;out.witness=Witness{cell,a.midpoint,*a.point_bounds,c,a.error_root->upper(),*a.penetration_certificate,index};out.status=Status::penetration_witness;out.reason=Reason::none;return out;
            }
            need(cell.depth<s.max_depth,Status::not_certified,Reason::depth_budget,"Unresolved cell reached depth budget");
            need(out.partition_leaves<s.max_leaves,Status::not_certified,Reason::leaf_budget,"Unresolved split exceeds full partition budget");
            const Cell left{{cell.parameter[0],a.midpoint},cell.depth+1},right{{a.midpoint,cell.parameter[1]},cell.depth+1};
            out.frontier.insert(out.frontier.begin(),{left,right});++out.partition_leaves;a.outcome=Outcome::split;out.current.reset();
        }
        need(out.work.exact&&out.safe_prefix&&(*out.safe_prefix)[0]==0&&(*out.safe_prefix)[1]==1&&out.certified_leaves.size()==out.partition_leaves,Status::numerical_failure,Reason::coverage_inconsistent,"Incomplete whole-path certificate");
        double previous=0;for(const auto& leaf:out.certified_leaves){need(leaf.cell.parameter[0]==previous&&leaf.cell.parameter[1]>previous&&leaf.lower_gap_certificate.strictly_positive(),Status::numerical_failure,Reason::coverage_inconsistent,"Invalid closed certificate cover");previous=leaf.cell.parameter[1];}
        need(previous==1,Status::numerical_failure,Reason::coverage_inconsistent,"Certified cover ended before one");out.status=Status::separated;out.reason=Reason::none;
    }catch(const Stop& e){if(in_flight)uncertain(out,*in_flight);fail(out,e.status,e.reason,e.text);}
    catch(const std::bad_alloc&){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::allocation_failure,"Trajectory diagnostic allocation failed");}
    catch(const std::exception& e){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    catch(...){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown trajectory exception");}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
