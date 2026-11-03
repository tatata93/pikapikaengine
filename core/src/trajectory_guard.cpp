#include "pikapika/trajectory_guard.hpp"
#include "pikapika/interval.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <unordered_set>
#include <vector>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Trajectory guard requires strict floating point without contraction.
#endif

namespace pikapika::trajectory_guard {
namespace {
using I=interval::Interval;
using V=std::array<I,3>;
struct Stop {Failure failure;const char* message;};
void need(bool b,Failure f,const char* m){if(!b)throw Stop{f,m};}
I point(double x){return I::point(x);}
V points(Vec3 x){return {point(x.x),point(x.y),point(x.z)};}
V sub(const V& a,const V& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
I dot(const V& a,const V& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
I squared(const V& a){return interval::square(a[0])+interval::square(a[1])+interval::square(a[2]);}
bool bounded(double x){return std::isfinite(x)&&std::abs(x)<=1e12;}
bool bounded(Vec3 x){return bounded(x.x)&&bounded(x.y)&&bounded(x.z);}
bool same(Vec3 a,Vec3 b){return a.x==b.x&&a.y==b.y&&a.z==b.z;}
bool zero(Vec3 x){return x.x==0&&x.y==0&&x.z==0;}
struct Polynomial {
    V start,end,linear,quadratic;
    Polynomial(V a,V z,V b):start(a),end(z),linear(b),quadratic{sub(sub(z,a),b)}{}
    V at(I s) const {
        // Endpoint identities avoid unnecessary coefficient dependency there.
        if(s.lower()==0&&s.upper()==0)return start;
        if(s.lower()==1&&s.upper()==1)return end;
        V value=start;
        for(unsigned k=0;k<3;++k)value[k]=(quadratic[k]*s+linear[k])*s+start[k];
        return value;
    }
};
Polynomial path(const dynamics::RigidBody& a,const dynamics::RigidBody& z,double dt){
    V b=points(a.velocity);for(auto& x:b)x=x*point(dt);
    return {points(a.position),points(z.position),b};
}
Polynomial relative_path(const dynamics::RigidBody& a,const dynamics::RigidBody& az,
                         const dynamics::RigidBody& b,const dynamics::RigidBody& bz,double dt){
    // Subtract original positions and velocities BEFORE propagation, so common
    // translation/velocity does not inflate an interval of each absolute path.
    V linear=sub(points(b.velocity),points(a.velocity));for(auto& x:linear)x=x*point(dt);
    return {sub(points(b.position),points(a.position)),sub(points(bz.position),points(az.position)),linear};
}
struct Test {
    bool safe{};
    Predicate predicate{};
    I value;
};
std::array<I,5> sphere_polynomial(const Polynomial& q,I threshold){
    // |a+b*s+c*s^2|^2-R^2, with ALL coefficient construction enclosed.
    // Keeping cancellation between coordinates here is crucial for curved
    // support: its true residual can be O(h^4) while coordinate boxes lose O(h^2).
    return {squared(q.quadratic),point(2)*dot(q.linear,q.quadratic),
        squared(q.linear)+point(2)*dot(q.start,q.quadratic),
        point(2)*dot(q.start,q.linear),squared(q.start)-threshold};
}
std::array<I,5> plane_polynomial(const Polynomial& q,const V& n,I offset){
    return {point(0),point(0),dot(n,q.quadratic),dot(n,q.linear),dot(n,q.start)-offset};
}
I intersect(I a,I b){
    const auto common=interval::intersection(a,b);
    if(!common)throw std::runtime_error("independent trajectory enclosures do not intersect");
    return *common;
}
struct Pair {
    Polynomial curve;
    bool plane{};
    V normal;
    I threshold_squared;
    I offset;
    std::array<I,5> coefficients;
    Pair(Polynomial p,I radius_squared):curve(p),normal(points({})),threshold_squared(radius_squared),offset(point(0)),
        coefficients(sphere_polynomial(curve,threshold_squared)){}
    Pair(Polynomial p,const dynamics::Plane& f,I radius_squared):curve(p),plane(true),normal(points(f.normal)),
        threshold_squared(radius_squared*squared(normal)),offset(point(f.offset)),coefficients(plane_polynomial(curve,normal,offset)){}
    Test evaluate(I s) const {
        const V q=curve.at(s);
        const I polynomial=interval::polynomial(coefficients,s);
        if(!plane){const I value=intersect(squared(q)-threshold_squared,polynomial);return {value.lower()>=0,Predicate::sphere_squared_clearance,value};}
        const I side=intersect(dot(normal,q)-offset,polynomial);
        // A positive radius makes the signed-side test essential before squaring.
        const I value=interval::square(side)-threshold_squared;
        if(side.lower()<0){
            // Squared distance below threshold proves penetration on EITHER
            // side, even when the signed offset straddles zero through rounding.
            if(side.upper()>=0&&value.upper()<0)return {false,Predicate::plane_squared_clearance,value};
            return {false,Predicate::plane_signed_offset,side};
        }
        return {value.lower()>=0,Predicate::plane_squared_clearance,value};
    }
};
struct Cell {double lower,upper;unsigned depth;};
void inspect(const Pair& pair,const Settings& settings,Result& result){
    const auto evaluate=[&](I s){
        result.parameter_bounds={s.lower(),s.upper()};
        need(result.evaluations<settings.max_evaluations,Failure::evaluation_budget,"trajectory evaluation budget exhausted");
        ++result.evaluations;const auto test=pair.evaluate(s);
        result.predicate=test.predicate;result.predicate_bounds={test.value.lower(),test.value.upper()};return test;
    };
    const auto witness=[&](double s){const auto test=evaluate(point(s));
        if(test.value.upper()<0){result.has_point_witness=true;result.witness_parameter=s;
            throw Stop{Failure::penetration_witness,"exact normalized parameter has a strictly forbidden penetration enclosure"};}
    };
    // Witness probes cannot make an interval pass. Only a full cell enclosure
    // with nonnegative lower endpoint can certify any part of [0,1].
    witness(0);witness(1);
    std::vector<Cell> pending{{0,1,0}};
    while(!pending.empty()){
        const auto cell=pending.back();pending.pop_back();result.maximum_depth=std::max(result.maximum_depth,cell.depth);
        const auto test=evaluate(I(cell.lower,cell.upper));
        if(test.safe){++result.certified_intervals;continue;}
        const double mid=std::midpoint(cell.lower,cell.upper);
        witness(mid);
        result.parameter_bounds={cell.lower,cell.upper};result.predicate=test.predicate;
        result.predicate_bounds={test.value.lower(),test.value.upper()};
        need(cell.depth<settings.max_depth,Failure::depth_budget,"trajectory cell remains unresolved at maximum subdivision depth");
        need(mid>cell.lower&&mid<cell.upper,Failure::numerical_uncertainty,"normalized parameter cannot be subdivided further");
        pending.push_back({mid,cell.upper,cell.depth+1});pending.push_back({cell.lower,mid,cell.depth+1});
    }
}
}

Result audit(std::span<const dynamics::RigidBody> initial,std::span<const dynamics::RigidBody> final,
             std::span<const dynamics::Plane> planes,double dt,const Settings& settings){
    Result result;
    try{
        interval::require_environment();
        need(std::isfinite(dt)&&dt>0&&dt<=.1,Failure::invalid_input,"dt must be finite in (0,0.1] seconds");
        need(std::isfinite(settings.spatial_tolerance)&&settings.spatial_tolerance>=0&&settings.spatial_tolerance<=1e6&&
            settings.max_pair_queries>0&&settings.max_pair_queries<=10000000&&settings.max_evaluations>0&&settings.max_evaluations<=100000000&&
            settings.max_depth<=52,Failure::invalid_input,"invalid trajectory tolerances or bounded budgets");
        need(initial.size()==final.size()&&initial.size()<=4096&&planes.size()<=4096,Failure::invalid_input,"invalid trajectory array sizes");
        std::unordered_set<std::uint64_t> ids;
        for(std::size_t k=0;k<initial.size();++k){const auto& a=initial[k];const auto& z=final[k];
            need(a.id!=0&&ids.insert(a.id).second&&z.id==a.id,Failure::invalid_input,"trajectory IDs must be nonzero, unique and retain final array order");
            need(bounded(a.radius)&&a.radius>settings.spatial_tolerance&&z.radius==a.radius&&a.is_static==z.is_static&&
                bounded(a.position)&&bounded(z.position)&&bounded(a.velocity)&&bounded(z.velocity),Failure::invalid_input,"invalid or inconsistent trajectory geometry/velocity");
            need(!a.is_static||(same(a.position,z.position)&&zero(a.velocity)&&zero(z.velocity)),Failure::invalid_input,"static body moved or has nonzero trajectory velocity");
        }
        for(const auto& p:planes){
            need(p.id!=0&&ids.insert(p.id).second&&bounded(p.normal)&&!zero(p.normal)&&bounded(p.offset),Failure::invalid_input,"invalid or duplicate static plane");
            need(squared(points(p.normal)).lower()>0,Failure::numerical_uncertainty,"plane normal norm cannot be proven positive");
        }
        const auto begin_pair=[&](std::uint64_t first,std::uint64_t second){
            result.first_id=first;result.second_id=second;result.parameter_bounds={0,1};result.predicate=Predicate::none;result.predicate_bounds={0,0};
            need(result.pair_queries<settings.max_pair_queries,Failure::pair_budget,"trajectory pair budget exhausted; no unchecked pair is dropped");++result.pair_queries;
        };
        for(const auto& p:planes)for(std::size_t k=0;k<initial.size();++k){
            if(!settings.include_static_pairs&&initial[k].is_static){++result.skipped_static_pairs;continue;}
            begin_pair(p.id,initial[k].id);
            const I radius=point(initial[k].radius)-point(settings.spatial_tolerance);
            inspect(Pair(path(initial[k],final[k],dt),p,interval::square(radius)),settings,result);
        }
        for(std::size_t a=0;a<initial.size();++a)for(std::size_t b=a+1;b<initial.size();++b){
            if(!settings.include_static_pairs&&initial[a].is_static&&initial[b].is_static){++result.skipped_static_pairs;continue;}
            begin_pair(initial[a].id,initial[b].id);
            const I radius=(point(initial[a].radius)+point(initial[b].radius))-point(settings.spatial_tolerance);
            inspect(Pair(relative_path(initial[a],final[a],initial[b],final[b],dt),interval::square(radius)),settings,result);
        }
        result.success=true;result.first_id=0;result.second_id=0;result.parameter_bounds={0,0};result.predicate=Predicate::none;result.predicate_bounds={0,0};
        result.message="all pairs and the complete defined normalized trajectory are within the penetration band";
    }catch(const Stop& stop){result.failure=stop.failure;result.message=stop.message;
    }catch(const std::exception& e){result.failure=Failure::numerical_failure;result.message=e.what();}
    return result;
}
}
