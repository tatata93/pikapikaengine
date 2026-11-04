#include "pikapika/sphere_triangle_mesh.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <stdexcept>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Finite triangle set certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle_mesh {
namespace {
using I=interval::Interval;
struct Stop {Status status;Reason reason;const char* text;};
void need(bool b,Status status,Reason reason,const char* text){if(!b)throw Stop{status,reason,text};}
void fail(Result& r,Status status,Reason reason,const char* text) noexcept {
    r.nearest.reset();r.status=status;r.reason=reason;
    try{r.message=text;}catch(...){r.message.clear();}
}
bool bounded(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=sphere_triangle::coordinate_limit;}
bool primitive_settings(const sphere_triangle::Settings& s){
    return s.max_candidates>=1&&s.max_candidates<=7&&s.sqrt_refinements>=1&&s.sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=1024&&
        std::isfinite(s.maximum_local_width)&&s.maximum_local_width>0&&s.maximum_local_width<=1e6&&
        std::isfinite(s.maximum_normal_width)&&s.maximum_normal_width>0&&s.maximum_normal_width<=2&&
        std::isfinite(s.minimum_sine_squared)&&s.minimum_sine_squared>0&&s.minimum_sine_squared<=1;
}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
I minimum_bounds(I a,I b){return I(std::min(a.lower(),b.lower()),std::min(a.upper(),b.upper()));}
}

Result query(Sphere sphere,std::span<const sphere_triangle::StaticTriangle> triangles,const Settings& s){
    Result out;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(s.max_surfaces>=1&&s.max_surfaces<=maximum_surfaces&&primitive_settings(s.primitive),Status::invalid_input,Reason::settings,"Invalid finite triangle set profile");
        need(!triangles.empty()&&triangles.size()<=maximum_surfaces,Status::invalid_input,Reason::surface_count,"Triangle set must contain 1..64 surfaces");
        need(triangles.size()<=s.max_surfaces,Status::budget_exceeded,Reason::surface_budget,"Triangle source exceeds configured surface budget");
        need(bounded(sphere.center)&&std::isfinite(sphere.radius)&&sphere.radius>0&&sphere.radius<=sphere_triangle::coordinate_limit,Status::invalid_input,Reason::input_domain,"Sphere input outside single-kernel domain");
        for(std::size_t i=0;i<triangles.size();++i){const auto& t=triangles[i];out.failed_index=i;
            need(t.id>0&&t.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid stable surface ID");
            for(std::size_t j=0;j<i;++j)need(t.id!=triangles[j].id,Status::invalid_input,Reason::duplicate_id,"Duplicate surface ID");
            need(std::all_of(t.vertices.begin(),t.vertices.end(),bounded),Status::invalid_input,Reason::input_domain,"Triangle source outside single-kernel finite domain");
        }
        out.failed_index.reset();
        // Preallocate then copy ALL sources before the first actual query. No
        // adjacency inference, reorder, quantization or borrowed output storage.
        out.rows.reserve(triangles.size());
        for(const auto& t:triangles)out.rows.push_back({t,std::nullopt});
        for(std::size_t i=0;i<out.rows.size();++i){auto& row=out.rows[i];
            row.query=sphere_triangle::query_sphere_triangle(sphere,row.triangle,s.primitive);++out.queries;
            const auto& r=*row.query;
            need(r.candidates_examined<=7&&r.sqrt_refinements<=512&&r.geometry.has_value()==(r.status==sphere_triangle::Status::completed),Status::numerical_failure,Reason::aggregate_inconsistent,"Single query violated work/completion invariant");
            out.candidates_examined+=r.candidates_examined;out.sqrt_refinements+=r.sqrt_refinements;out.sqrt_limited_rows+=r.sqrt_refinement_limited?1:0;
            if(r.status!=sphere_triangle::Status::completed){++out.failed_rows;if(!out.first_failed_row)out.first_failed_row=i;}
        }
        if(out.failed_rows){fail(out,Status::row_failure,Reason::row_failed,"At least one triangle query did not complete; all rows retained");return out;}
        const auto& first=*out.rows.front().query->geometry;
        Nearest nearest;nearest.squared_distance=first.squared_distance;nearest.distance=first.distance;nearest.gap=first.gap;
        for(const auto& row:out.rows){const auto& g=*row.query->geometry;
            need(finite(g.squared_distance)&&finite(g.distance)&&finite(g.gap)&&g.squared_distance.strictly_positive()&&g.distance.strictly_positive(),Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid completed row distance enclosure");
            nearest.squared_distance=minimum_bounds(nearest.squared_distance,g.squared_distance);
            nearest.distance=minimum_bounds(nearest.distance,g.distance);nearest.gap=minimum_bounds(nearest.gap,g.gap);
        }
        nearest.possible_surface_ids.reserve(out.rows.size());
        for(const auto& row:out.rows)if(row.query->geometry->squared_distance.lower()<=nearest.squared_distance.upper())nearest.possible_surface_ids.push_back(row.triangle.id);
        need(!nearest.possible_surface_ids.empty(),Status::numerical_failure,Reason::aggregate_inconsistent,"No possible nearest surface remained");
        std::sort(nearest.possible_surface_ids.begin(),nearest.possible_surface_ids.end());
        out.nearest=std::move(nearest);out.status=Status::completed;out.reason=Reason::none;
    }catch(const Stop& e){fail(out,e.status,e.reason,e.text);}
    catch(const std::bad_alloc&){fail(out,Status::numerical_failure,Reason::allocation_failure,"Allocation failed while owning triangle source/query snapshot");}
    catch(const std::exception& e){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
