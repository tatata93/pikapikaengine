#include "pikapika/continuous.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace pikapika::continuous {
namespace {
constexpr double bound=1e12;
constexpr double eps=std::numeric_limits<double>::epsilon();
Vec3 add(Vec3 a,Vec3 b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
Vec3 sub(Vec3 a,Vec3 b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
Vec3 mul(Vec3 a,double s) { return {a.x*s,a.y*s,a.z*s}; }
Vec3 div(Vec3 a,double s) { return {a.x/s,a.y/s,a.z/s}; }
double dot(Vec3 a,Vec3 b) { return std::fma(a.x,b.x,std::fma(a.y,b.y,a.z*b.z)); }
Vec3 cross(Vec3 a,Vec3 b) {
    return {std::fma(a.y,b.z,-a.z*b.y),std::fma(a.z,b.x,-a.x*b.z),std::fma(a.x,b.y,-a.y*b.x)};
}
double norm(Vec3 a) { return std::hypot(a.x,a.y,a.z); }
Vec3 unit(Vec3 a) {
    const double scale=std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)});
    if(scale==0)return {};
    const Vec3 scaled=div(a,scale);
    return div(scaled,norm(scaled));
}
bool subnormal(double value) { return std::fpclassify(value)==FP_SUBNORMAL; }
void scalar(double value,const char* message) {
    if(!std::isfinite(value)||std::abs(value)>bound)throw std::invalid_argument(message);
}
void vector(Vec3 value,const char* message) { scalar(value.x,message);scalar(value.y,message);scalar(value.z,message); }
void sphere_valid(const MovingSphere& s) {
    vector(s.center,"sphere coordinate outside finite +/-1e12 m domain");
    vector(s.velocity,"sphere velocity outside finite +/-1e12 m/s domain");
    scalar(s.radius,"sphere radius outside finite 1e12 m domain");
    if(s.radius<=0)throw std::invalid_argument("sphere radius must be positive");
}
void horizon_valid(double h) {
    if(!std::isfinite(h)||h<0||h>1e6)throw std::invalid_argument("horizon must be finite and in [0,1e6] seconds");
}
Motion motion(double speed,double normal_speed) {
    if(speed==0)return Motion::stationary;
    if(normal_speed<0)return Motion::approaching;
    if(normal_speed>0)return Motion::separating;
    return Motion::tangential;
}
bool initial(ToiResult& out,double horizon) {
    if(out.initial_gap>0)return false;
    out.kind=out.initial_gap<0?ContactKind::initial_overlap:ContactKind::initial_touch;
    out.time=0;
    out.at_horizon=horizon==0;
    return true;
}
// Do not turn a root just outside the interval into a certified impact.
// This is a diagnostic ulp-scale envelope, not an outward-rounded bound.
bool event_time(ToiResult& out,double travel,double speed,double horizon) {
    const double available=speed*horizon;
    const double guard=32*eps*std::max(travel,available);
    if(travel>available) {
        if(travel-available>guard)return false;
        out.kind=ContactKind::uncertain;
        out.roundoff_sensitive=true;
        out.time=horizon;
    } else {
        const double time=travel==available?horizon:travel/speed;
        if(!(time>0)||!std::isfinite(time))throw std::domain_error("positive contact time is not representable");
        out.time=std::min(time,horizon);
        if(available-travel<=guard)out.roundoff_sensitive=true;
    }
    out.at_horizon=*out.time==horizon;
    return true;
}
void set_normal(ToiResult& out,Vec3 direction,Vec3 velocity) {
    const double length=norm(direction);
    out.normal_valid=length>0;
    out.normal=out.normal_valid?unit(direction):Vec3{};
    out.normal_speed=out.normal_valid?dot(velocity,out.normal):0;
}
}

ToiResult sphere_plane(const MovingSphere& sphere,const MovingPlane& plane,double horizon) {
    sphere_valid(sphere);horizon_valid(horizon);
    vector(plane.normal,"plane normal must be finite");
    vector(plane.velocity,"plane velocity outside finite +/-1e12 m/s domain");
    scalar(plane.offset,"plane offset outside finite +/-1e12 m domain");
    const double nlength=norm(plane.normal);
    if(std::abs(nlength-1)>1e-12)throw std::invalid_argument("plane normal must be unit length within 1e-12");
    const Vec3 n=div(plane.normal,nlength);
    const double offset=plane.offset/nlength;
    const Vec3 relative=sub(sphere.velocity,plane.velocity);
    const double projection=dot(n,sphere.center);
    ToiResult out;
    out.initial_gap=(projection-offset)-sphere.radius;
    out.normal=n;out.normal_valid=true;
    out.initial_normal_speed=dot(n,relative);out.normal_speed=out.initial_normal_speed;
    out.initial_motion=motion(norm(relative),out.initial_normal_speed);
    const double gap_guard=16*eps*(std::abs(n.x*sphere.center.x)+std::abs(n.y*sphere.center.y)+std::abs(n.z*sphere.center.z)+std::abs(offset)+sphere.radius);
    out.roundoff_sensitive=std::abs(out.initial_gap)<=gap_guard||subnormal(out.initial_gap)||subnormal(out.initial_normal_speed);
    if(initial(out,horizon)||horizon==0||out.initial_normal_speed>=0)return out;
    out.kind=ContactKind::impact;
    if(!event_time(out,out.initial_gap,-out.initial_normal_speed,horizon)) {
        out.kind=ContactKind::none;out.time.reset();
    }
    return out;
}

ToiResult sphere_sphere(const MovingSphere& a,const MovingSphere& b,double horizon) {
    sphere_valid(a);sphere_valid(b);horizon_valid(horizon);
    const Vec3 r=sub(b.center,a.center),v=sub(b.velocity,a.velocity);
    const double radius=a.radius+b.radius,distance=norm(r),speed=norm(v);
    ToiResult out;
    out.initial_gap=distance-radius;
    set_normal(out,r,v);
    // At coincident centres the right derivative of separation is |v|, but
    // there is no unique contact normal (do not invent an arbitrary axis).
    out.initial_normal_speed=out.normal_valid?out.normal_speed:speed;
    out.initial_motion=motion(speed,out.initial_normal_speed);
    out.roundoff_sensitive=std::abs(out.initial_gap)<=16*eps*(distance+radius)||subnormal(distance)||subnormal(speed)||subnormal(radius);
    if(initial(out,horizon)||horizon==0||speed==0||out.initial_normal_speed>=0)return out;

    const double scale=std::max({std::abs(r.x),std::abs(r.y),std::abs(r.z),radius});
    const Vec3 p=div(r,scale),u=unit(v);
    const double q=radius/scale;
    if(q==0||q*q==0)throw std::domain_error("radius/relative-distance squared underflows; rescale or partition the query");
    const double bcoef=dot(p,u);
    const double c=(out.initial_gap/scale)*(distance/scale+q);
    if(!(c>0)||!std::isfinite(c))throw std::domain_error("separated sphere coefficient is not representable");
    const Vec3 perpendicular=cross(cross(u,p),u);
    const Vec3 crosspu=cross(p,u);
    const double crossnorm=norm(crosspu),cross2=crossnorm*crossnorm;
    const double discriminant=(q-crossnorm)*(q+crossnorm);
    // Error sensitivity estimate includes cross-product cancellation. It is
    // deliberately reported, not advertised as a formal interval enclosure.
    const double pnorm=norm(p);
    const double guard=64*eps*(q*q+cross2+crossnorm*pnorm)+128*eps*eps*pnorm*pnorm;
    if(discriminant< -guard)return out;
    out.roundoff_sensitive=out.roundoff_sensitive||std::abs(discriminant)<=guard;
    double root=0,travel_scaled=0;
    if(discriminant<0) {
        out.kind=ContactKind::uncertain;
        travel_scaled=-bcoef; // closest approach, not a certified contact
    } else {
        root=std::sqrt(discriminant);
        out.kind=discriminant==0?ContactKind::grazing:ContactKind::impact;
        const double denominator=-bcoef+root;
        if(!(denominator>0))throw std::domain_error("entry-root denominator is not positive");
        travel_scaled=c/denominator;
    }
    const double travel=travel_scaled*scale;
    if(!(travel>0)||!std::isfinite(travel))throw std::domain_error("entry distance is not representable");
    if(!event_time(out,travel,speed,horizon)) {
        out.kind=ContactKind::none;out.time.reset();return out;
    }
    // A stable entry normal: closest-approach perpendicular minus chord along u.
    // No subtraction of large, separately advected absolute world positions.
    set_normal(out,add(perpendicular,mul(u,-root)),v);
    return out;
}
}
