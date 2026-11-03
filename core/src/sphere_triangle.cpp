#include "pikapika/sphere_triangle.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <stdexcept>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Sphere triangle certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle {
namespace {
using I=interval::Interval;
struct Stop {Status status;Reason reason;const char* message;};
void need(bool condition,Status status,Reason reason,const char* message){if(!condition)throw Stop{status,reason,message};}
void fail(Result& out,Status status,Reason reason,const char* message) noexcept {
    out.geometry.reset();out.status=status;out.reason=reason;
    try{out.message=message;}catch(...){out.message.clear();}
}
I p(double x){return I::point(x);}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
I checked(I x){need(finite(x),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite interval intermediate");return x;}
bool zero(I x){return x.lower()==0&&x.upper()==0;}
I difference(double a,double b){return a==b?p(0):checked(p(a)-p(b));}
Bounds3 point(Vec3 a){return {p(a.x),p(a.y),p(a.z)};}
Bounds3 sub(Vec3 a,Vec3 b){return {difference(a.x,b.x),difference(a.y,b.y),difference(a.z,b.z)};}
Bounds3 sub(const Bounds3&a,const Bounds3&b){return {checked(a[0]-b[0]),checked(a[1]-b[1]),checked(a[2]-b[2])};}
Bounds3 add(const Bounds3&a,const Bounds3&b){return {checked(a[0]+b[0]),checked(a[1]+b[1]),checked(a[2]+b[2])};}
Bounds3 mul(const Bounds3&a,I s){return {checked(a[0]*s),checked(a[1]*s),checked(a[2]*s)};}
I dot(const Bounds3&a,const Bounds3&b){return checked(a[0]*b[0]+a[1]*b[1]+a[2]*b[2]);}
I squared(const Bounds3&a){return checked(interval::square(a[0])+interval::square(a[1])+interval::square(a[2]));}
Bounds3 cross(const Bounds3&a,const Bounds3&b){return {checked(a[1]*b[2]-a[2]*b[1]),checked(a[2]*b[0]-a[0]*b[2]),checked(a[0]*b[1]-a[1]*b[0])};}
Bounds3 hull(const Bounds3&a,const Bounds3&b){return {interval::hull(a[0],b[0]),interval::hull(a[1],b[1]),interval::hull(a[2],b[2])};}
bool bounded(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=coordinate_limit;}
bool width_ok(const Bounds3& v,double limit){
    for(const auto& x:v){
        if(!finite(x))return false;
        // The endpoints are exact binary64 reals. A scalar RN subtraction can
        // round their real width inward (including a lost subnormal addend).
        const I width=difference(x.upper(),x.lower());
        if(!finite(width)||width.upper()>limit)return false;
    }
    return true;
}
Bounds3 barycentric(I s,I t){return {checked(p(1)-s-t),s,t};}
bool feasible(const Bounds3& b){return std::all_of(b.begin(),b.end(),[](I x){return x.upper()>=0&&x.lower()<=1;});}
Bounds3 clipped(Bounds3 b){for(auto& x:b){const auto overlap=interval::intersection(x,I(0,1));need(overlap.has_value(),Status::numerical_failure,Reason::no_candidate,"Inconsistent simplex enclosure");x=*overlap;}return b;}
}

Result query_sphere_triangle(Sphere sphere,const StaticTriangle& triangle,const Settings& s){
    Result out;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(s.max_candidates>=1&&s.max_candidates<=7&&s.sqrt_refinements>=1&&s.sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=1024&&
             std::isfinite(s.maximum_local_width)&&s.maximum_local_width>0&&s.maximum_local_width<=1e6&&std::isfinite(s.maximum_normal_width)&&s.maximum_normal_width>0&&s.maximum_normal_width<=2&&
             std::isfinite(s.minimum_sine_squared)&&s.minimum_sine_squared>0&&s.minimum_sine_squared<=1,Status::invalid_input,Reason::settings,"Invalid sphere triangle numerical profile");
        need(triangle.id>0&&triangle.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid stable surface ID");
        need(bounded(sphere.center)&&std::isfinite(sphere.radius)&&sphere.radius>0&&sphere.radius<=coordinate_limit&&std::all_of(triangle.vertices.begin(),triangle.vertices.end(),bounded),Status::invalid_input,Reason::input_domain,"Sphere triangle input outside finite domain");
        // Every difference starts from source binary64 points. World q is never
        // subtracted back from world x to manufacture a locally precise delta.
        const auto e0=sub(triangle.vertices[1],triangle.vertices[0]),e1=sub(triangle.vertices[2],triangle.vertices[0]),w=sub(sphere.center,triangle.vertices[0]);
        const auto normal_cross=cross(e0,e1);const I determinant=squared(normal_cross);out.squared_cross=determinant;
        need(!std::all_of(normal_cross.begin(),normal_cross.end(),zero),Status::degenerate,Reason::zero_cross,"Triangle cross is provably zero");
        need(determinant.strictly_positive(),Status::quality_unresolved,Reason::cross_uncertain,"Triangle nondegeneracy could not be certified");
        const I a=squared(e0),b=dot(e0,e1),c=squared(e1);
        need(a.strictly_positive()&&c.strictly_positive(),Status::quality_unresolved,Reason::cross_uncertain,"Triangle edge norm unresolved");
        auto sine=interval::intersection(checked(determinant/checked(a*c)),I(0,1));
        need(sine.has_value(),Status::numerical_failure,Reason::nonfinite_intermediate,"Inconsistent geometric sine enclosure");out.sine_squared=*sine;
        need(sine->upper()>=s.minimum_sine_squared,Status::ill_conditioned,Reason::conditioning_rejected,"Triangle below explicit sine squared conditioning threshold");
        need(sine->lower()>=s.minimum_sine_squared,Status::quality_unresolved,Reason::conditioning_uncertain,"Triangle conditioning straddles threshold");
        const I u=dot(w,e0),v=dot(w,e1);
        out.candidates.reserve(7);
        Geometry geometry;geometry.surface_id=triangle.id;bool have=false;I candidate_distance=p(0);
        const std::array<Bounds3,3> vertices{point({}),e0,e1};
        const auto examine=[&](Feature feature,Bounds3 bary,unsigned kkt_count,const std::array<I,2>& kkt){
            need(out.candidates_examined<s.max_candidates,Status::budget_exceeded,Reason::candidate_budget,"All seven candidates must be examined");
            ++out.candidates_examined;CandidateAudit audit;audit.feature=feature;audit.barycentric=bary;audit.kkt_count=kkt_count;audit.kkt=kkt;
            if(!feasible(bary)){audit.disposition=Disposition::outside_simplex;out.candidates.push_back(std::move(audit));return;}
            for(unsigned i=0;i<kkt_count;++i)if(kkt[i].strictly_positive()){audit.disposition=Disposition::kkt_violated;out.candidates.push_back(std::move(audit));return;}
            // A residual containing zero is NOT evidence of a valid minimizer.
            // It is only a reason this candidate cannot safely be discarded.
            bary=clipped(bary);const auto local=add(mul(e0,bary[1]),mul(e1,bary[2])),delta=sub(w,local);const auto ds=squared(delta);
            geometry.surviving_features|=std::uint32_t(1)<<static_cast<unsigned>(feature);
            if(!have){geometry.barycentric=bary;geometry.closest_local=local;geometry.delta=delta;candidate_distance=ds;have=true;}
            else{geometry.barycentric=hull(geometry.barycentric,bary);geometry.closest_local=hull(geometry.closest_local,local);geometry.delta=hull(geometry.delta,delta);candidate_distance=interval::hull(candidate_distance,ds);}
            out.candidates.push_back(std::move(audit));
        };
        // Interior stationary point. These algebraic formulas satisfy the two
        // exact stationarity identities; interval feasibility alone filters it.
        const I face_s=checked(checked(c*u-b*v)/determinant),face_t=checked(checked(a*v-b*u)/determinant);
        examine(Feature::face,barycentric(face_s,face_t),0,{p(0),p(0)});
        // Edges retain endpoints too. Their remaining KKT inequality is against
        // the opposite vertex. No uncertain sign is rounded to a known region.
        for(unsigned edge=0;edge<3;++edge){
            const unsigned first=edge,last=(edge+1)%3,opposite=(edge+2)%3;
            const auto direction=sub(vertices[last],vertices[first]),offset=sub(w,vertices[first]);const I length_squared=squared(direction);
            need(length_squared.strictly_positive(),Status::quality_unresolved,Reason::cross_uncertain,"Edge length could not be certified");
            const I parameter=checked(dot(offset,direction)/length_squared);
            Bounds3 bary{p(0),p(0),p(0)};bary[first]=checked(p(1)-parameter);bary[last]=parameter;
            const auto delta=sub(offset,mul(direction,parameter));
            examine(static_cast<Feature>(static_cast<unsigned>(Feature::edge_ab)+edge),bary,1,{dot(delta,sub(vertices[opposite],vertices[first])),p(0)});
        }
        for(unsigned vertex=0;vertex<3;++vertex){
            Bounds3 bary{p(0),p(0),p(0)};bary[vertex]=p(1);const auto delta=sub(w,vertices[vertex]);
            examine(static_cast<Feature>(static_cast<unsigned>(Feature::vertex_a)+vertex),bary,2,
                    {dot(delta,sub(vertices[(vertex+1)%3],vertices[vertex])),dot(delta,sub(vertices[(vertex+2)%3],vertices[vertex]))});
        }
        need(have,Status::quality_unresolved,Reason::no_candidate,"No KKT candidate remained");
        need(width_ok(geometry.closest_local,s.maximum_local_width)&&width_ok(geometry.delta,s.maximum_local_width),Status::quality_unresolved,Reason::local_width,"Retained candidate local hull exceeds width budget");
        // Both enclosures contain the true closest distance. Intersect, without
        // selecting whichever nominal candidate happens to look smallest.
        auto ds=interval::intersection(candidate_distance,squared(geometry.delta));
        need(ds.has_value(),Status::numerical_failure,Reason::nonfinite_intermediate,"Distance enclosures disagree");geometry.squared_distance=*ds;
        need(!zero(*ds),Status::quality_unresolved,Reason::zero_distance,"Closest point coincides with centre; normal undefined");
        need(ds->strictly_positive(),Status::quality_unresolved,Reason::distance_uncertain,"Distance includes zero; normal unresolved");
        const auto root=interval::sqrt_enclosure(*ds,s.sqrt_refinements);out.sqrt_refinements=root.refinements;out.sqrt_refinement_limited=root.refinement_limited;
        need(out.sqrt_refinements<=s.max_total_sqrt_refinements,Status::budget_exceeded,Reason::sqrt_budget,"Actual sqrt refinement budget exceeded");
        geometry.distance=checked(root.value);need(geometry.distance.strictly_positive(),Status::quality_unresolved,Reason::distance_uncertain,"Positive distance lower bound required");
        for(unsigned k=0;k<3;++k){
            // A unit vector component lies in [-1,1] as a geometric identity,
            // not because an arbitrary interval box is itself a unit vector.
            const auto n=interval::intersection(checked(geometry.delta[k]/geometry.distance),I(-1,1));
            need(n.has_value(),Status::numerical_failure,Reason::nonfinite_intermediate,"Inconsistent normal enclosure");geometry.normal[k]=*n;
        }
        need(width_ok(geometry.normal,s.maximum_normal_width),Status::quality_unresolved,Reason::normal_width,"Normal component enclosure exceeds width budget");
        geometry.closest=add(point(triangle.vertices[0]),geometry.closest_local);
        geometry.sphere_point=sub(point(sphere.center),mul(geometry.normal,p(sphere.radius)));
        geometry.gap=checked(geometry.distance-p(sphere.radius));
        geometry.relation=geometry.gap.strictly_positive()?Relation::separated:geometry.gap.strictly_negative()?Relation::penetrating:zero(geometry.gap)?Relation::touching:Relation::boundary_unresolved;
        out.geometry=std::move(geometry);out.status=Status::completed;out.reason=Reason::none;
    }catch(const Stop& e){fail(out,e.status,e.reason,e.message);}
    catch(const std::bad_alloc&){fail(out,Status::numerical_failure,Reason::allocation_failure,"Allocation failed");}
    catch(const std::exception& e){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
