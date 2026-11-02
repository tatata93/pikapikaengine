#include "pikapika/portable.h"
#if !defined(__clang__)
#include <cmath>
#endif
namespace {
double square_root(double x) {
#if defined(__clang__)
    return __builtin_sqrt(x);
#else
    return std::sqrt(x);
#endif
}
}
extern "C" double pp_sweep_fraction(double mx,double my,double mz,double dx,double dy,double dz,double radius) {
    const double c=mx*mx+my*my+mz*mz-radius*radius;
    if(c<=0) return 0;
    const double a=dx*dx+dy*dy+dz*dz,b=mx*dx+my*dy+mz*dz;
    if(a<1e-24||b>=0) return -1;
    const double discriminant=b*b-a*c;
    if(discriminant<0) return -1;
    const double t=c/(-b+square_root(discriminant));
    return t>=0&&t<=1?t:-1;
}
extern "C" double pp_direct_delay(double distance,double speed) { return distance/speed; }
extern "C" double pp_direct_pressure_gain(double distance,double reference) {
    return reference/(distance>reference?distance:reference);
}
extern "C" double pp_integrate_velocity(double position,double velocity,double dt) { return position+velocity*dt; }
