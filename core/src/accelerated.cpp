#include "pikapika/accelerated.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Accelerated enclosure queries require strict floating point.
#endif
namespace pikapika::accelerated {
namespace {
using I=interval::Interval;
I point(double x) { return I::point(x); }
struct IV { I x,y,z; };
IV vector(Vec3 v) { return {point(v.x),point(v.y),point(v.z)}; }
IV sub(IV a,IV b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
IV add(IV a,IV b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
IV mul(IV a,I s) { return {a.x*s,a.y*s,a.z*s}; }
I dot(IV a,IV b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
I square_norm(IV a) { return interval::square(a.x)+interval::square(a.y)+interval::square(a.z); }
void scalar_valid(double x,const char* message) { if(!std::isfinite(x)||std::abs(x)>1e12)throw std::invalid_argument(message); }
void vector_valid(Vec3 x) {scalar_valid(x.x,"vector component outside finite +/-1e12 domain");scalar_valid(x.y,"vector component outside finite +/-1e12 domain");scalar_valid(x.z,"vector component outside finite +/-1e12 domain");}
void valid(const Sphere& s) {
    vector_valid(s.center);vector_valid(s.velocity);vector_valid(s.acceleration);scalar_valid(s.radius,"radius outside finite 1e12 domain");
    if(s.radius<=0)throw std::invalid_argument("sphere radius must be positive");
}
void time_valid(double h) {if(!std::isfinite(h)||h<0||h>1e6)throw std::invalid_argument("time must be finite and in [0,1e6] seconds");}
void settings_valid(const Settings& s) {
    if(!std::isfinite(s.time_tolerance)||s.time_tolerance<=0||s.time_tolerance>1e6||s.max_evaluations<1||s.max_evaluations>1000000||
       s.max_frontier<1||s.max_frontier>65536||s.max_depth>128)throw std::invalid_argument("invalid accelerated-query precision or budget");
}
I intersect(I a,I b) {
    const auto result=interval::intersection(a,b);
    if(!result)throw std::logic_error("inconsistent geometric/polynomial enclosures");
    return *result;
}
// Bounded norm enclosure without assuming libm sqrt/hypot rounding. Initially
// max|n_i| <= |n| <= sum|n_i|. Every refinement is proved using interval square.
I normal_magnitude(Vec3 n) {
    const std::array<double,3> values{std::abs(n.x),std::abs(n.y),std::abs(n.z)};
    double lo=std::max({values[0],values[1],values[2]});
    if(lo==0)throw std::invalid_argument("plane normal must be nonzero");
    unsigned nonzero=0;for(double x:values)if(x!=0)++nonzero;
    if(nonzero==1)return point(lo);
    const I n2=square_norm(vector(n));
    double hi=(point(values[0])+point(values[1])+point(values[2])).upper();
    for(unsigned i=0;i<64;++i) {
        const double mid=std::midpoint(lo,hi);
        if(mid==lo||mid==hi)break;
        const I mid2=interval::square(point(mid));
        if(mid2.upper()<n2.lower())lo=mid;
        else if(mid2.lower()>n2.upper())hi=mid;
        else {
            // |sqrt(N)-m|=|N-m²|/(sqrt(N)+m), denominator >= lo+m.
            // This also handles an exactly representable norm at the midpoint.
            const I delta=n2-mid2;
            const double difference=std::max(std::abs(delta.lower()),std::abs(delta.upper()));
            const I denominator=point(lo)+point(mid);
            if(denominator.strictly_positive()) {
                const double error=(I{0,difference}/denominator).upper();
                if(std::isfinite(error))return intersect(I{lo,hi},point(mid)+I{-error,error});
            }
            break;
        }
    }
    return {lo,hi};
}
struct PairEquation {
    IV r,v,half_a;
    I radius_squared;
    std::array<I,5> coefficients;
    PairEquation(const Sphere& a,const Sphere& b):
        r(sub(vector(b.center),vector(a.center))),v(sub(vector(b.velocity),vector(a.velocity))),
        half_a(mul(sub(vector(b.acceleration),vector(a.acceleration)),point(0.5))),
        radius_squared(interval::square(point(a.radius)+point(b.radius))),
        coefficients{dot(half_a,half_a),point(2)*dot(v,half_a),dot(v,v)+point(2)*dot(r,half_a),point(2)*dot(r,v),square_norm(r)-radius_squared} {}
    I operator()(I t) const {
        const IV position=add(add(r,mul(v,t)),mul(half_a,interval::square(t)));
        return intersect(square_norm(position)-radius_squared,interval::polynomial(coefficients,t));
    }
};
struct PlaneEquation {
    IV n,p,v,half_a;
    I d,support;
    std::array<I,3> coefficients;
    PlaneEquation(const Sphere& sphere,const StaticPlane& plane):n(vector(plane.normal)),p(vector(sphere.center)),v(vector(sphere.velocity)),
        half_a(mul(vector(sphere.acceleration),point(0.5))),d(point(plane.offset)),support(point(sphere.radius)*normal_magnitude(plane.normal)),
        coefficients{dot(n,half_a),dot(n,v),dot(n,p)-d-support} {}
    I operator()(I t) const {
        const IV position=add(add(p,mul(v,t)),mul(half_a,interval::square(t)));
        return intersect(dot(n,position)-d-support,interval::polynomial(coefficients,t));
    }
};
struct Node {double lo,hi;};
template<class Equation> Result search(const Equation& equation,double horizon,const Settings& settings) {
    Result result;
    const auto evaluate=[&](I time)->std::optional<I> {
        if(result.evaluations==settings.max_evaluations)return std::nullopt;
        ++result.evaluations;return equation(time);
    };
    const auto unresolved=[&](Reason reason) {result.kind=Kind::unresolved;result.reason=reason;return result;};
    const auto initial=evaluate(point(0));result.initial_value=initial;
    if(!initial->strictly_positive())return unresolved(initial->strictly_negative()?Reason::initial_overlap:Reason::initial_boundary);
    result.initial_separation_proven=true;result.value_at_safe=initial;
    if(horizon==0){result.kind=Kind::none;return result;}
    const auto witness=[&](double time,I value) {
        if(value.strictly_negative()&&(!result.negative_witness||time<*result.negative_witness)) {
            result.negative_witness=time;result.negative_value=value;
        }
    };
    const auto isolated=[&]() {
        if(!result.negative_witness||*result.negative_witness<=result.safe_until)return false;
        const I width=point(*result.negative_witness)-point(result.safe_until);
        if(width.upper()>settings.time_tolerance)return false;
        result.kind=Kind::entry_bracket;result.reason=Reason::none;
        result.bracket=I{result.safe_until,*result.negative_witness};return true;
    };
    std::vector<Node> frontier{{0,horizon}},next;
    for(unsigned depth=0;;++depth) {
        result.depth_reached=depth;next.clear();bool pending=false;Reason blocked=Reason::none;
        for(const Node original:frontier) {
            if(result.negative_witness&&original.lo>=*result.negative_witness)break;
            const Node node{original.lo,result.negative_witness?std::min(original.hi,*result.negative_witness):original.hi};
            const auto range=evaluate(I{node.lo,node.hi});
            if(!range)return unresolved(Reason::evaluation_budget);
            if(range->strictly_positive()) {
                ++result.excluded_intervals;
                if(!pending){result.safe_until=node.hi;result.value_at_safe=range;if(isolated())return result;}
                continue;
            }
            if(!pending) {
                const auto left=evaluate(point(node.lo));
                if(!left)return unresolved(Reason::evaluation_budget);
                if(!left->strictly_positive())return unresolved(Reason::numerical_uncertainty);
                result.safe_until=node.lo;result.value_at_safe=left;pending=true;
            }
            const double mid=std::midpoint(node.lo,node.hi);
            if(range->strictly_negative())witness(node.lo,*range);
            else {
                for(double t:std::array<double,2>{mid,node.hi}) {
                    if(result.negative_witness&&t>=*result.negative_witness)continue;
                    const auto sample=evaluate(point(t));if(!sample)return unresolved(Reason::evaluation_budget);
                    witness(t,*sample);
                }
            }
            if(isolated())return result;
            if(depth==settings.max_depth) {blocked=Reason::depth_limit;continue;}
            const double right=result.negative_witness?std::min(node.hi,*result.negative_witness):node.hi;
            if(right<=node.lo)continue;
            const double split=std::midpoint(node.lo,right);
            if(split==node.lo||split==right){blocked=Reason::time_resolution;continue;}
            if(next.size()+2>settings.max_frontier)return unresolved(Reason::frontier_budget);
            next.push_back({node.lo,split});next.push_back({split,right});
        }
        if(!pending) {
            // All remaining intervals were strictly positive; previously removed
            // gaps were also proved positive. A negative witness would contradict this.
            if(result.negative_witness)return unresolved(Reason::numerical_uncertainty);
            result.kind=Kind::none;result.reason=Reason::none;result.safe_until=horizon;return result;
        }
        if(blocked!=Reason::none)return unresolved(blocked);
        if(next.empty())return unresolved(Reason::numerical_uncertainty);
        frontier.swap(next);
    }
}
void plane_valid(const StaticPlane& plane) {vector_valid(plane.normal);scalar_valid(plane.offset,"plane offset outside finite +/-1e12 domain");}
void interval_time_valid(I time) {time_valid(time.lower());time_valid(time.upper());}
}
Result sphere_sphere(const Sphere& a,const Sphere& b,double horizon,const Settings& settings) {
    interval::require_environment();valid(a);valid(b);time_valid(horizon);settings_valid(settings);
    return search(PairEquation{a,b},horizon,settings);
}
Result sphere_plane(const Sphere& sphere,const StaticPlane& plane,double horizon,const Settings& settings) {
    interval::require_environment();valid(sphere);plane_valid(plane);time_valid(horizon);settings_valid(settings);
    return search(PlaneEquation{sphere,plane},horizon,settings);
}
I sphere_sphere_value(const Sphere& a,const Sphere& b,const I& time) {
    interval::require_environment();valid(a);valid(b);interval_time_valid(time);return PairEquation{a,b}(time);
}
I sphere_plane_value(const Sphere& sphere,const StaticPlane& plane,const I& time) {
    interval::require_environment();valid(sphere);plane_valid(plane);interval_time_valid(time);return PlaneEquation{sphere,plane}(time);
}
}
