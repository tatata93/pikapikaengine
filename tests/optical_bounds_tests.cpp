#include "pikapika/optical_bounds.hpp"
#include "pikapika/optics.hpp"
#include "pikapika/dispersion.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace pikapika;
namespace b=pikapika::optical_bounds;
namespace g=pikapika::optical_geometry;
namespace o=pikapika::optics;
using I=pikapika::interval::Interval;
namespace {
unsigned groups=0,samples=0,index_samples=0;
I p(double v){return I::point(v);}
void check(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void test(const char* name,const std::function<void()>& fn){fn();++groups;std::cout<<"PASS "<<name<<'\n';}
const b::Hit& hit(const b::Result& r){check(r.status==b::Status::hit&&r.nearest.has_value(),"family hit certified");return *r.nearest;}
void contains(I a,double v){check(a.contains(v),"known value inside enclosure");}
void vec(const b::Bounds3& a,Vec3 v){contains(a[0],v.x);contains(a[1],v.y);contains(a[2],v.z);}
void transmission(const b::InterfaceResult& r){check(r.kind==b::InterfaceKind::transmission&&r.reflected&&r.transmitted&&r.power,"family transmission certified");}
template<class F>void rejects(F fn){bool threw=false;try{fn();}catch(const std::invalid_argument&){threw=true;}check(threw,"invalid input rejected");}
void emit(I a){std::cout<<','<<std::hex<<std::bit_cast<std::uint64_t>(a.lower())<<','<<std::bit_cast<std::uint64_t>(a.upper())<<std::dec;}
void oracle(){
    // Exact rational reference families: axial origin/direction boxes intersect
    // z=plane, then same-axis ni=1 -> nt=1.5 has Rs=Rp=1/25, Ts=Tp=24/25.
    std::cout<<"kind,k,originLo,originHi,directionLo,directionHi,plane,tLo,tHi,dLo,dHi,xLo,xHi,yLo,yHi,zLo,zHi\n";
    for(int k=1;k<=120;++k){
        const double lo=-double(k+8)/8,hi=lo+1.0/32,dl=double(k%7+4)/8,dh=dl+1.0/64,z=double(k%3)/4;
        b::BoundedRay ray{{p(0),p(0),I(lo,hi)},{p(0),p(0),I(dl,dh)},0,100};
        const auto r=b::intersect(ray,g::PlaneDisk{{0,0,z},{0,0,-2},2});const auto& h=hit(r);
        std::cout<<"P,"<<k<<','<<std::hex<<std::bit_cast<std::uint64_t>(lo)<<','<<std::bit_cast<std::uint64_t>(hi)<<','<<std::bit_cast<std::uint64_t>(dl)<<','<<std::bit_cast<std::uint64_t>(dh)<<','<<std::bit_cast<std::uint64_t>(z)<<std::dec;
        emit(h.parameter);emit(h.physical_distance);for(auto a:h.position)emit(a);std::cout<<'\n';
    }
    for(int k=1;k<=120;++k){
        const double radius=double(k%4+1)/4,lo=-double(k+16)/8,hi=lo+1.0/65536,dl=double(k%7+4)/8,dh=dl+1.0/65536;
        b::BoundedRay ray{{p(0),p(0),I(lo,hi)},{p(0),p(0),I(dl,dh)},0,100};
        const auto r=b::intersect(ray,g::FullSphere{{},radius});const auto& h=hit(r);
        std::cout<<"Q,"<<k<<','<<std::hex<<std::bit_cast<std::uint64_t>(lo)<<','<<std::bit_cast<std::uint64_t>(hi)<<','<<std::bit_cast<std::uint64_t>(dl)<<','<<std::bit_cast<std::uint64_t>(dh)<<','<<std::bit_cast<std::uint64_t>(radius)<<std::dec;
        emit(h.parameter);emit(h.physical_distance);for(auto a:h.position)emit(a);for(const auto& c:r.candidates)emit(c.parameter);std::cout<<'\n';
    }
    for(int k=1;k<=60;++k){
        const double lo=double(k+40)/8,hi=lo+1.0/65536,dl=-double(k%7+4)/8-1.0/65536,dh=dl+1.0/65536;
        b::BoundedRay ray{{p(0),p(0),I(lo,hi)},{p(0),p(0),I(dl,dh)},0,100};
        const auto r=b::intersect(ray,g::SphericalCap{{},{0,0,1},2,1});const auto& h=hit(r);
        check(r.candidates[0].state==b::CandidateState::rejected_cap&&r.candidates[1].state==b::CandidateState::accepted,"oracle cap root ordering");
        std::cout<<"C,"<<k<<','<<std::hex<<std::bit_cast<std::uint64_t>(lo)<<','<<std::bit_cast<std::uint64_t>(hi)<<','<<std::bit_cast<std::uint64_t>(dl)<<','<<std::bit_cast<std::uint64_t>(dh)<<','<<std::bit_cast<std::uint64_t>(2.0)<<std::dec;
        emit(h.parameter);emit(h.physical_distance);for(auto a:h.position)emit(a);for(const auto& c:r.candidates)emit(c.parameter);std::cout<<'\n';
    }
    // Exact 3-4-5 direction, Brewster ni=4 -> nt=3: transmitted (4/5,-3/5),
    // reflected (3/5,4/5), Rs=49/625, Rp=0, Ts=576/625, Tp=1.
    b::InterfaceInput in;in.incident=b::enclose({3,-4,0});in.normal=b::enclose({0,1,0});in.index_incident=4;in.index_transmitted=3;
    const auto r=b::dielectric_interface(in);transmission(r);
    std::cout<<"B,0,0,0,0,0,0";for(auto a:*r.transmitted)emit(a);for(auto a:*r.reflected)emit(a);
    emit(r.power->reflectance_s);emit(r.power->transmittance_s);emit(r.power->reflectance_p);emit(r.power->transmittance_p);std::cout<<'\n';
    b::InterfaceInput normal;normal.incident={p(0),I(-4,-2),p(0)};normal.normal={p(0),I(2,3),p(0)};
    const auto n=b::dielectric_interface(normal);transmission(n);
    std::cout<<"N,0,0,0,0,0,0";for(auto a:*n.transmitted)emit(a);for(auto a:*n.reflected)emit(a);
    emit(n.power->reflectance_s);emit(n.power->transmittance_s);emit(n.power->reflectance_p);emit(n.power->transmittance_p);std::cout<<'\n';
}
void index_row(char tag,unsigned k,const b::IndexBoundsInterfaceInput& in){
    const auto r=b::dielectric_interface_bounds(in);transmission(r);
    std::cout<<tag<<','<<k;emit(in.index_incident);emit(in.index_transmitted);
    std::cout<<','<<std::hex<<std::bit_cast<std::uint64_t>(in.vacuum_wavelength_m)<<std::dec;
    for(auto a:*r.transmitted)emit(a);for(auto a:*r.reflected)emit(a);
    emit(r.power->reflectance_s);emit(r.power->transmittance_s);emit(r.power->reflectance_p);emit(r.power->transmittance_p);std::cout<<'\n';
}
void index_oracle(){
    std::cout<<"kind,k,niLo,niHi,ntLo,ntHi,wavelength,transmitted6,reflected6,Rs2,Ts2,Rp2,Tp2\n";
    for(unsigned k=0;k<100;++k){
        b::IndexBoundsInterfaceInput in;
        const double ni=1+double(k%4)/16,nt=1.5+double(k%5)/16;
        in.index_incident=I(ni,ni+1.0/128);in.index_transmitted=I(nt,nt+1.0/128);
        index_row('N',k,in);
    }
    for(unsigned k=0;k<10;++k){
        b::IndexBoundsInterfaceInput in;in.incident=b::enclose({3,-4,0});
        const double ni=1+double(k%4)/32,nt=1.5+double(k%5)/32;
        in.index_incident=I(ni,ni+1.0/128);in.index_transmitted=I(nt,nt+1.0/128);
        index_row('S',k,in);
    }
    namespace d=pikapika::optics::dispersion;
    const double wavelength=0x1p-20;
    const auto phase=d::evaluate(d::Cauchy{1.5,0x1p-44,0x1p-88,{0x1p-21,0x1p-19}},{wavelength,wavelength});
    check(phase.status==d::Status::resolved&&phase.values->within_interface_domain,"dispersion phase resolved");
    b::IndexBoundsInterfaceInput in;in.incident=b::enclose({3,-4,0});in.index_transmitted=phase.values->phase;in.vacuum_wavelength_m=wavelength;
    check(in.index_transmitted.lower()<in.index_transmitted.upper(),"point wavelength arithmetic still has a nonpoint phase enclosure");
    index_row('F',0,in);
}
void compare_member(const b::InterfaceResult& family,Vec3 iv,Vec3 nv,double ni_value,double nt_value){
    const long double il=std::sqrt((long double)iv.x*iv.x+(long double)iv.y*iv.y+(long double)iv.z*iv.z);
    const long double nl=std::sqrt((long double)nv.x*nv.x+(long double)nv.y*nv.y+(long double)nv.z*nv.z);
    const long double ix=iv.x/il,iy=iv.y/il,iz=iv.z/il,nx=nv.x/nl,ny=nv.y/nl,nz=nv.z/nl;
    const long double ni=ni_value,nt=nt_value,eta=ni/nt,ci=-(ix*nx+iy*ny+iz*nz),ct=std::sqrt(1-eta*eta*(1-ci*ci));
    const long double ds=ni*ci+nt*ct,dp=nt*ci+ni*ct,rs=(ni*ci-nt*ct)/ds,rp=(nt*ci-ni*ct)/dp;
    // Independent electric transmission amplitudes and normal Poynting flux.
    const long double es=2*ni*ci/ds,ep=2*ni*ci/dp,flux=nt*ct/(ni*ci);
    vec(*family.transmitted,{double(eta*ix+(eta*ci-ct)*nx),double(eta*iy+(eta*ci-ct)*ny),double(eta*iz+(eta*ci-ct)*nz)});
    vec(*family.reflected,{double(ix+2*ci*nx),double(iy+2*ci*ny),double(iz+2*ci*nz)});
    contains(family.power->reflectance_s,double(rs*rs));contains(family.power->reflectance_p,double(rp*rp));
    contains(family.power->transmittance_s,double(flux*es*es));contains(family.power->transmittance_p,double(flux*ep*ep));++index_samples;
}
void tests(){
    test("axial plane family has a common first root and encloses exact rational extrema",[]{
        b::BoundedRay ray{{p(0),p(0),I(-4,-3)},{p(0),p(0),I(1,2)},0,10};
        const auto r=b::intersect(ray,g::PlaneDisk{{0,0,0},{0,0,-1},1});const auto& h=hit(r);
        contains(h.parameter,1.5);contains(h.parameter,4);contains(h.physical_distance,3);contains(h.physical_distance,4);
        vec(h.position,{0,0,0});vec(h.incident_normal,{0,0,-1});check(h.front_face,"front facing all rays");
    });
    test("plane parameter aperture and parallel mixtures are unresolved not guessed",[]{
        b::BoundedRay ray{{p(0),p(0),I(-4,-3)},{p(0),p(0),I(1,2)},2,10};
        auto r=b::intersect(ray,g::PlaneDisk{});check(r.status==b::Status::unresolved&&r.reason==b::Reason::parameter_boundary,"mixed t domain");
        ray={{I(.9,1.1),p(0),p(-2)},b::enclose({0,0,1}),0,10};
        r=b::intersect(ray,g::PlaneDisk{});check(r.status==b::Status::unresolved&&r.reason==b::Reason::aperture_boundary,"mixed aperture");
        ray.direction={p(1),p(0),I(-.1,.1)};
        r=b::intersect(ray,g::PlaneDisk{});check(r.status==b::Status::unresolved&&r.reason==b::Reason::parallel_or_coplanar,"mixed denominator");
        ray.direction=b::enclose({1,0,0});r=b::intersect(ray,g::PlaneDisk{});check(r.status==b::Status::miss,"all parallel disjoint");
    });
    test("uncertainty expansion does not turn ambiguous aperture or incident side into success",[]{
        b::BoundedRay ray{{I(.9,1.1),p(0),p(-2)},b::enclose({0,0,1}),0,10};
        check(b::intersect(ray,g::PlaneDisk{}).status==b::Status::unresolved,"small ambiguous aperture");
        ray.origin[0]=I(.5,1.5);check(b::intersect(ray,g::PlaneDisk{}).status==b::Status::unresolved,"wider ambiguous aperture");
        b::InterfaceInput in;in.incident={p(1),I(-.01,.01),p(0)};
        check(b::dielectric_interface(in).reason==b::Reason::incident_side,"small side ambiguity");
        in.incident[1]=I(-1,1);check(b::dielectric_interface(in).reason==b::Reason::incident_side,"wider side ambiguity");
    });
    test("sphere family proves real ordered roots without midpoint collapse",[]{
        b::BoundedRay ray{{I(-.01,.01),p(0),I(-3.01,-2.99)},{I(-.001,.001),p(0),I(.99,1.01)},0,10};
        const auto r=b::intersect(ray,g::FullSphere{{0,0,0},1});const auto& h=hit(r);
        check(r.root_count==2&&r.candidates[0].state==b::CandidateState::accepted&&r.candidates[1].state==b::CandidateState::not_examined,"ordered first root");
        contains(h.parameter,2);vec(h.position,{0,0,-1});vec(h.geometric_normal,{0,0,-1});
        for(int k=0;k<=20;++k){
            const double f=k/20.0,x=std::lerp(ray.origin[0].lower(),ray.origin[0].upper(),f),z=std::lerp(ray.origin[2].lower(),ray.origin[2].upper(),f),dx=std::lerp(ray.direction[0].lower(),ray.direction[0].upper(),f),dz=std::lerp(ray.direction[2].lower(),ray.direction[2].upper(),f);
            const long double A=(long double)dx*dx+(long double)dz*dz,H=(long double)x*dx+(long double)z*dz,C=(long double)x*x+(long double)z*z-1;
            const long double root=C/(-H+std::sqrt(H*H-A*C));
            contains(h.parameter,double(root));vec(h.position,{double(x+root*dx),0,double(z+root*dz)});++samples;
        }
    });
    test("sphere tangency family and zero direction return unresolved without false existence",[]{
        b::BoundedRay ray{{I(.99,1.01),p(0),p(-2)},b::enclose({0,0,1}),0,10};
        auto r=b::intersect(ray,g::FullSphere{});check(r.status==b::Status::unresolved&&r.reason==b::Reason::tangent_or_discriminant,"some members miss tangent");
        ray.direction={I(-1,1),I(-1,1),I(-1,1)};r=b::intersect(ray,g::FullSphere{});check(r.reason==b::Reason::zero_direction,"zero member");
        ray.origin=b::enclose({2,0,-2});ray.direction=b::enclose({0,0,1});check(b::intersect(ray,g::FullSphere{}).status==b::Status::miss,"all roots absent");
    });
    test("cap uniform hemisphere exclusion selects second root and aperture ambiguity blocks it",[]{
        b::BoundedRay ray{{I(-.001,.001),p(0),I(4.99,5.01)},{p(0),p(0),I(-1.01,-.99)},0,10};
        const auto r=b::intersect(ray,g::SphericalCap{{0,0,0},{0,0,1},2,1});const auto& h=hit(r);
        check(r.candidates[0].state==b::CandidateState::rejected_cap&&r.candidates[1].state==b::CandidateState::accepted,"same second root across family");contains(h.parameter,5);check(!h.front_face,"all back side");
        ray={{I(.99,1.01),p(0),p(-2)},b::enclose({0,0,1}),0,10};
        const auto mixed=b::intersect(ray,g::SphericalCap{{0,0,0},{0,0,1},2,1});
        check(mixed.status==b::Status::unresolved&&mixed.nearest==std::nullopt,"mixed aperture not success");
    });
    test("tilted cap uses original real axis normalization and signed radius",[]{
        const auto ray=b::enclose_ray(g::Ray{{-3,0,-4},{3,0,4},0,10});
        const auto r=b::intersect(ray,g::SphericalCap{{},{3,0,4},5,2});const auto& h=hit(r);
        contains(h.parameter,1);contains(h.physical_distance,5);vec(h.position,{});vec(h.geometric_normal,{-.6,0,-.8});
        const auto reverse=b::intersect(b::enclose_ray(g::Ray{{3,0,4},{-3,0,-4},0,10}),g::SphericalCap{{},{3,0,4},-5,2});
        contains(hit(reverse).parameter,1);vec(hit(reverse).geometric_normal,{.6,0,.8});
    });
    test("normal family and exact Brewster enclose independent rational flux and directions",[]{
        b::InterfaceInput in;in.incident={p(0),I(-4,-2),p(0)};in.normal={p(0),I(2,3),p(0)};
        const auto normal=b::dielectric_interface(in);transmission(normal);vec(*normal.transmitted,{0,-1,0});vec(*normal.reflected,{0,1,0});
        contains(normal.power->reflectance_s,1.0/25);contains(normal.power->transmittance_p,24.0/25);
        in.incident=b::enclose({3,-4,0});in.normal=b::enclose({0,1,0});in.index_incident=4;in.index_transmitted=3;
        const auto brewster=b::dielectric_interface(in);transmission(brewster);vec(*brewster.transmitted,{.8,-.6,0});vec(*brewster.reflected,{.6,.8,0});
        contains(brewster.power->reflectance_s,49.0/625);contains(brewster.power->transmittance_s,576.0/625);contains(brewster.power->reflectance_p,0);contains(brewster.power->transmittance_p,1);
    });
    test("TIR equal media critical family and invalid normal remain distinct",[]{
        b::InterfaceInput in;in.incident={I(.799,.801),I(-.601,-.599),p(0)};in.index_incident=1.5;in.index_transmitted=1;
        auto r=b::dielectric_interface(in);check(r.kind==b::InterfaceKind::total_internal_reflection&&r.reflected&&!r.transmitted&&r.power,"all TIR");contains(r.power->reflectance_s,1);
        in.incident=b::enclose({3,-4,0});in.index_incident=5;in.index_transmitted=3;r=b::dielectric_interface(in);check(r.kind==b::InterfaceKind::unresolved&&r.reason==b::Reason::critical_angle&&!r.power&&!r.reflected&&!r.transmitted,"critical raw interval");
        in.index_transmitted=5;r=b::dielectric_interface(in);transmission(r);vec(*r.transmitted,{.6,-.8,0});contains(r.power->reflectance_s,0);
        in.normal={I(-1,1),I(-1,1),I(-1,1)};r=b::dielectric_interface(in);check(r.reason==b::Reason::zero_normal,"zero normal family");
        in.normal=b::enclose({0,-1,0});rejects([&]{b::dielectric_interface(in);});
    });
    test("exact grazing is a stated one-sided limit and equal media do not bypass side uncertainty",[]{
        b::InterfaceInput in;in.incident=b::enclose({1,0,0});
        auto r=b::dielectric_interface(in);transmission(r);check(r.exact_grazing,"all rays exactly grazing");contains(r.power->reflectance_s,1);contains(r.power->transmittance_s,0);
        in.index_incident=1.5;in.index_transmitted=1;r=b::dielectric_interface(in);
        check(r.kind==b::InterfaceKind::total_internal_reflection&&r.exact_grazing,"grazing TIR side");
        in.index_transmitted=1.5;in.incident[0]=I(1,2);r=b::dielectric_interface(in);transmission(r);vec(*r.transmitted,{1,0,0});contains(r.power->transmittance_p,1);
        in.incident[1]=I(-.001,.001);r=b::dielectric_interface(in);
        check(r.kind==b::InterfaceKind::unresolved&&r.reason==b::Reason::incident_side&&!r.transmitted,"equal indices after orientation proof only");
    });
    test("bounded Snell tube contains independently evaluated members",[]{
        b::InterfaceInput in;in.incident={I(.29,.31),I(-1.01,-.99),I(-.002,.002)};in.normal={I(-.001,.001),p(1),I(-.001,.001)};
        const auto r=b::dielectric_interface(in);transmission(r);
        for(unsigned k=0;k<=100;++k){
            const double f=k/100.0;const auto member=[&](I x,bool reverse=false){return std::lerp(x.lower(),x.upper(),reverse?1-f:f);};
            long double ix=member(in.incident[0]),iy=member(in.incident[1]),iz=member(in.incident[2]),nx=member(in.normal[0]),ny=1,nz=member(in.normal[2],true);
            const long double il=std::sqrt(ix*ix+iy*iy+iz*iz),nl=std::sqrt(nx*nx+ny*ny+nz*nz);
            ix/=il;iy/=il;iz/=il;nx/=nl;ny/=nl;nz/=nl;
            const long double ci=-(ix*nx+iy*ny+iz*nz),eta=2.0L/3,ct=std::sqrt(1-eta*eta*(1-ci*ci));
            vec(*r.transmitted,{double(eta*ix+(eta*ci-ct)*nx),double(eta*iy+(eta*ci-ct)*ny),double(eta*iz+(eta*ci-ct)*nz)});++samples;
        }
    });
    test("plane refraction plane continuation preserves whole boxes and self hit is not skipped",[]{
        b::BoundedRay ray{{I(-.01,.01),p(0),I(-2.01,-1.99)},{I(-.001,.001),p(0),I(.99,1.01)},0,10};
        const auto first=b::intersect(ray,g::PlaneDisk{{0,0,0},{0,0,-1},2});const auto& h=hit(first);
        b::InterfaceInput in;in.incident=ray.direction;in.normal=h.incident_normal;const auto boundary=b::dielectric_interface(in);transmission(boundary);
        const auto continuation=b::spawn_ray(h,*boundary.transmitted,0,10);
        for(unsigned k=0;k<3;++k){check(continuation.origin[k].lower()==h.position[k].lower()&&continuation.origin[k].upper()==h.position[k].upper(),"copy origin box");check(continuation.direction[k].contains((*boundary.transmitted)[k]),"copy direction box");}
        const auto second=b::intersect(continuation,g::PlaneDisk{{0,0,1},{0,0,-1},2});const auto& next=hit(second);contains(next.position[2],1);
        const auto self=b::intersect(continuation,g::PlaneDisk{{0,0,0},{0,0,-1},2});check(self.status==b::Status::hit,"source-plane exact zero remains a hit");contains(hit(self).parameter,0);
    });
    test("point sphere hit retains its rounding enclosure through Snell into next sphere",[]{
        const auto incoming=b::enclose_ray(g::Ray{{0,0,-3},{0,0,1},0,10});
        const auto first=b::intersect(incoming,g::FullSphere{});const auto& h=hit(first);
        b::InterfaceInput in;in.incident=incoming.direction;in.normal=h.incident_normal;
        const auto boundary=b::dielectric_interface(in);transmission(boundary);
        const auto forward=b::spawn_ray(h,*boundary.transmitted,0,10);
        const auto second=b::intersect(forward,g::FullSphere{{0,0,3},1});const auto& next=hit(second);
        contains(next.parameter,3);vec(next.position,{0,0,2});
        const auto backward=b::spawn_ray(h,*boundary.reflected,0,10);
        const auto reflected=b::intersect(backward,g::PlaneDisk{{0,0,-2},{0,0,1},1});contains(hit(reflected).parameter,1);
        const auto source=b::intersect(forward,g::FullSphere{});
        check(source.status==b::Status::unresolved&&source.reason==b::Reason::parameter_boundary,"same sphere source ambiguity not skipped");
    });
    test("point-degenerate families agree with existing classification and include known outputs",[]{
        for(unsigned k=0;k<40;++k){
            g::Ray ray{{double(k%4)/10,0,-3},{0,0,1},0,10};
            const auto point=g::intersect(ray,g::FullSphere{{0,0,0},1});const auto bounded=b::intersect(b::enclose_ray(ray),g::FullSphere{{0,0,0},1});
            check(point.status==g::Status::hit&&bounded.status==b::Status::hit,"point sphere status");vec(hit(bounded).position,point.nearest->position_estimate);
            o::InterfaceInput old{{double(k)/100,-1,0},{0,1,0},1,1.5,550e-9};
            b::InterfaceInput in;in.incident=b::enclose(old.incident);in.normal=b::enclose(old.normal);
            const auto po=o::dielectric_interface(old);const auto bo=b::dielectric_interface(in);transmission(bo);check(po.kind==o::InterfaceKind::transmission,"point interface status");
            vec(*bo.transmitted,*po.transmitted);contains(bo.power->reflectance_s,po.power->reflectance_s);++samples;
        }
    });
    test("width and refinement budgets never create unproved success and invalid domains reject",[]{
        auto ray=b::enclose_ray(g::Ray{{0,0,-3},{0,0,1},0,10});b::Settings s;s.maximum_parameter_width=1e-30;
        auto r=b::intersect(ray,g::FullSphere{},s);check(r.status==b::Status::unresolved,"width floor");
        s={};s.maximum_parameter_width=1e-8;s.max_sqrt_refinements=1;r=b::intersect(ray,g::FullSphere{},s);check(r.status==b::Status::unresolved&&r.refinement_limited,"budget not guessed");
        rejects([&]{auto bad=ray;bad.minimum_parameter=11;b::intersect(bad,g::FullSphere{});});
        rejects([&]{b::intersect(ray,g::SphericalCap{{},{0,0,1},1,2});});
        rejects([&]{b::Settings bad;bad.max_sqrt_refinements=0;b::intersect(ray,g::FullSphere{},bad);});
        rejects([&]{b::InterfaceInput bad;bad.index_incident=0;b::dielectric_interface(bad);});
    });
    test("independent index families enclose analytic normal reflection extrema without collapsing indices",[]{
        b::IndexBoundsInterfaceInput in;in.index_incident=I(1,1.25);in.index_transmitted=I(1.5,2);
        const auto r=b::dielectric_interface_bounds(in);transmission(r);
        vec(*r.transmitted,{0,-1,0});vec(*r.reflected,{0,1,0});
        contains(r.power->reflectance_s,1.0/121);contains(r.power->reflectance_s,1.0/9);
        contains(r.power->transmittance_p,8.0/9);contains(r.power->transmittance_p,120.0/121);
        in.index_incident=I(1,2);in.index_transmitted=I(1,2);
        const auto independent=b::dielectric_interface_bounds(in);transmission(independent);
        contains(independent.power->reflectance_s,1.0/9);check(independent.power->reflectance_s.upper()>0,"same nonpoint index ranges are not homogeneous");
        in.index_incident=p(1.5);in.index_transmitted=p(1.5);const auto same=b::dielectric_interface_bounds(in);transmission(same);
        check(same.power->reflectance_s.lower()==0&&same.power->reflectance_s.upper()==0,"equal singleton analytical branch");
    });
    test("mixed critical indices and identical broad independent intervals stay unresolved",[]{
        b::IndexBoundsInterfaceInput in;in.incident=b::enclose({3,-4,0});in.index_incident=I(4.9,5.1);in.index_transmitted=p(3);
        auto r=b::dielectric_interface_bounds(in);
        check(r.kind==b::InterfaceKind::unresolved&&r.reason==b::Reason::critical_angle&&!r.reflected&&!r.transmitted&&!r.power,"index family straddles physical critical angle");
        in.incident=b::enclose({4,-3,0});in.index_incident=in.index_transmitted=I(1,2);
        r=b::dielectric_interface_bounds(in);check(r.kind==b::InterfaceKind::unresolved&&!r.transmitted,"same interval not identical medium");
        in.index_incident=I(1.5,1.6);in.index_transmitted=I(1,1.1);
        r=b::dielectric_interface_bounds(in);check(r.kind==b::InterfaceKind::total_internal_reflection&&r.reflected&&!r.transmitted,"whole index family TIR");
        in.index_incident=I(.9,1.2);in.index_transmitted=I(1.4,1.7);
        r=b::dielectric_interface_bounds(in);transmission(r);
        in.normal={I(-1,1),I(-1,1),I(-1,1)};
        check(b::dielectric_interface_bounds(in).reason==b::Reason::zero_normal,"zero normal family remains guarded");
    });
    test("index and geometric family corner and interior members match independent flux calculation",[]{
        b::IndexBoundsInterfaceInput in;in.incident={I(.29,.31),I(-1.01,-.99),I(-.002,.002)};in.normal={I(-.001,.001),p(1),I(-.001,.001)};
        in.index_incident=I(1,1.25);in.index_transmitted=I(1.5,1.75);
        const auto r=b::dielectric_interface_bounds(in);transmission(r);
        const auto endpoint=[](I a,unsigned side){return side?a.upper():a.lower();};
        for(unsigned mask=0;mask<128;++mask){
            Vec3 i{endpoint(in.incident[0],mask&1),endpoint(in.incident[1],mask&2),endpoint(in.incident[2],mask&4)};
            Vec3 n{endpoint(in.normal[0],mask&8),1,endpoint(in.normal[2],mask&16)};
            compare_member(r,i,n,endpoint(in.index_incident,mask&32),endpoint(in.index_transmitted,mask&64));
        }
        for(unsigned j=1;j<20;++j){
            const double f=j/20.0;const auto member=[&](I a,bool reverse=false){return std::lerp(a.lower(),a.upper(),reverse?1-f:f);};
            compare_member(r,{member(in.incident[0]),member(in.incident[1],true),member(in.incident[2])},{member(in.normal[0],true),1,member(in.normal[2])},member(in.index_incident),member(in.index_transmitted,true));
        }
    });
    test("point wavelength dispersion phase enclosure connects intact to bounded interface and next plane",[]{
        namespace d=pikapika::optics::dispersion;const double wavelength=0x1p-20;
        const auto phase=d::evaluate(d::Cauchy{1.5,0x1p-44,0x1p-88,{0x1p-21,0x1p-19}},{wavelength,wavelength});
        check(phase.status==d::Status::resolved&&phase.values->within_interface_domain,"phase is within optical domain");
        const I full_phase=phase.values->phase;contains(full_phase,401.0/256);check(full_phase.lower()<full_phase.upper(),"retain nonpoint phase output");
        b::IndexBoundsInterfaceInput in;in.incident=b::enclose({3,-4,0});in.index_transmitted=full_phase;in.vacuum_wavelength_m=wavelength;
        const auto r=b::dielectric_interface_bounds(in);transmission(r);
        check(in.index_transmitted.lower()==full_phase.lower()&&in.index_transmitted.upper()==full_phase.upper(),"whole phase box retained");
        contains((*r.transmitted)[0],768.0/2005);check(r.vacuum_wavelength_m==wavelength,"wavelength provenance");
        compare_member(r,{3,-4,0},{0,1,0},1,full_phase.lower());compare_member(r,{3,-4,0},{0,1,0},1,full_phase.upper());
        b::Hit source;source.position=b::enclose({0,0,0});
        const auto next=b::intersect(b::spawn_ray(source,*r.transmitted,0,10),g::PlaneDisk{{0,-1,0},{0,1,0},2});const auto& h=hit(next);
        contains(h.position[1],-1);
        // A second, square-root model supplies its phase bounds with no rounding
        // into a selected point refractive index before the interface.
        d::Sellmeier sellmeier;sellmeier.count=1;sellmeier.terms[0]={2.25,0x1p-42};sellmeier.valid_band={0x1p-21,0x1p-19};
        const auto sell=d::evaluate(sellmeier,{wavelength,wavelength});check(sell.status==d::Status::resolved&&sell.values->within_interface_domain,"Sellmeier phase");
        in.index_transmitted=sell.values->phase;transmission(b::dielectric_interface_bounds(in));contains(in.index_transmitted,2);
    });
    test("point wrapper agrees bitwise with singleton index API and invalid index endpoints reject",[]{
        b::InterfaceInput old;old.incident=b::enclose({3,-4,0});old.index_incident=4;old.index_transmitted=3;
        const auto a=b::dielectric_interface(old),c=b::dielectric_interface_bounds({old.incident,old.normal,p(4),p(3),old.vacuum_wavelength_m});transmission(a);transmission(c);
        check(a.sqrt_refinements==c.sqrt_refinements&&a.kind==c.kind,"same point classification");
        for(unsigned k=0;k<3;++k)check((*a.transmitted)[k].lower()==(*c.transmitted)[k].lower()&&(*a.transmitted)[k].upper()==(*c.transmitted)[k].upper(),"wrapper direction bits");
        rejects([]{b::IndexBoundsInterfaceInput in;in.index_incident=I(0,1);b::dielectric_interface_bounds(in);});
        rejects([]{b::IndexBoundsInterfaceInput in;in.index_transmitted=I(1,1e7);b::dielectric_interface_bounds(in);});
        rejects([]{b::IndexBoundsInterfaceInput in;in.index_incident=I::whole();b::dielectric_interface_bounds(in);});
    });
    std::cout<<"Bounded optics: "<<groups<<" groups, "<<samples<<" geometric and "<<index_samples<<" index sampled consistency cases (sampling is NOT a family proof)\n";
}
}
int main(int argc,char** argv){try{if(argc==2&&std::string(argv[1])=="--oracle")oracle();else if(argc==2&&std::string(argv[1])=="--index-oracle")index_oracle();else tests();return 0;}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
