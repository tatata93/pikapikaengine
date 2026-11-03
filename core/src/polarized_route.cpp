#include "pikapika/polarized_route.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <type_traits>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Polarized route requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::polarized_route {
namespace {
using I=Interval;using Z=ComplexBounds;using V=Bounds3;
using M=std::array<std::array<Z,3>,3>;
I p(double x){return I::point(x);}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
bool zero(I x){return x.lower()==0&&x.upper()==0;}
bool singleton(I x){return x.lower()==x.upper();}
I meet(I x,I domain){const auto y=interval::intersection(x,domain);if(!y||!finite(*y))throw std::domain_error("Inconsistent physical enclosure");return *y;}
Z add(Z a,Z b){return {a.real+b.real,a.imag+b.imag};}
Z mul(Z a,Z b){return {a.real*b.real-a.imag*b.imag,a.real*b.imag+a.imag*b.real};}
Z scale(Z a,I b){return {a.real*b,a.imag*b};}
Z conj(Z a){return {a.real,-a.imag};}
I dot(const V&a,const V&b){I x=p(0);for(unsigned k=0;k<3;++k)x=x+a[k]*b[k];return x;}
I norm2(const V&a){I x=p(0);for(I k:a)x=x+interval::square(k);return x;}
V cross(const V&a,const V&b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
bool zero(const V&v){return zero(v[0])&&zero(v[1])&&zero(v[2]);}
struct Unresolved {PowerFailure failure;};
struct Budget {};
struct Work {
    Result& out;const Settings& settings;
    void audit(){if(out.geometry_sqrt_refinements+out.power_sqrt_refinements>settings.max_total_sqrt_refinements)throw Budget{};}
    I root(I x){const auto r=interval::sqrt_enclosure(x,settings.max_sqrt_refinements);out.power_sqrt_refinements+=r.refinements;out.refinement_limited=out.refinement_limited||r.refinement_limited;audit();return r.value;}
    V unit(const V&v,PowerFailure failure){
        const I q=norm2(v);if(!q.strictly_positive())throw Unresolved{failure};
        const I length=root(q);if(!length.strictly_positive())throw Unresolved{failure};
        V result{p(0),p(0),p(0)};for(unsigned k=0;k<3;++k)result[k]=meet(v[k]/length,I(-1,1));return result;
    }
};
void vector_valid(const V&v){for(I x:v)if(!finite(x)||x.lower()<-1e6||x.upper()>1e6)throw std::invalid_argument("Polarized vector outside finite +/-1e6 domain");}
void position_valid(Vec3 v){vector_valid(optical_bounds::enclose(v));}
void axis_valid(Vec3 v){position_valid(v);if(std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<1e-6)throw std::invalid_argument("Shape axis max component below 1e-6");}
void radius_valid(double x){if(!std::isfinite(x)||x<1e-6||x>1e6)throw std::invalid_argument("Shape radius outside [1e-6,1e6]");}
void domain_valid(double a,double b){if(!std::isfinite(a)||!std::isfinite(b)||a<0||a>b||b>1e9)throw std::invalid_argument("Ray closed parameter domain outside [0,1e9]");}
void index_valid(I x){if(!finite(x)||x.lower()<1e-6||x.upper()>1e6)throw std::invalid_argument("Index endpoints outside [1e-6,1e6]");}
void surface_valid(const optical_route::Surface& surface){
    if(surface.valueless_by_exception())throw std::invalid_argument("Valueless surface");
    std::visit([](const auto&s){using T=std::decay_t<decltype(s)>;
        if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>){position_valid(s.center);axis_valid(s.normal);radius_valid(s.aperture_radius);}
        else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){position_valid(s.center);radius_valid(s.radius);}
        else{position_valid(s.vertex);axis_valid(s.axis);radius_valid(std::abs(s.signed_radius));radius_valid(s.aperture_radius);if(s.aperture_radius>std::abs(s.signed_radius))throw std::invalid_argument("Cap aperture exceeds radius");}
    },surface);
}
bool physical(const Stokes&s){
    for(double x:{s.i,s.q,s.u,s.v})if(!std::isfinite(x)||std::abs(x)>1e12)throw std::invalid_argument("Stokes outside finite +/-1e12 domain");
    if(s.i<0||(s.i==0&&(s.q!=0||s.u!=0||s.v!=0)))throw std::invalid_argument("Nonphysical Stokes");
    const unsigned nonzero=unsigned(s.q!=0)+unsigned(s.u!=0)+unsigned(s.v!=0);
    if(nonzero==0||(nonzero==1&&(std::abs(s.q)==s.i||std::abs(s.u)==s.i||std::abs(s.v)==s.i)))return true;
    const I delta=interval::square(p(s.i))-interval::square(p(s.q))-interval::square(p(s.u))-interval::square(p(s.v));
    if(delta.upper()<0)throw std::invalid_argument("Stokes is outside exact physical cone");
    return delta.lower()>=0;
}
M matrix(const Coherency&c){M m{};for(unsigned k=0;k<3;++k)m[k][k].real=c.diagonal[k];m[0][1]=c.upper[0];m[0][2]=c.upper[1];m[1][2]=c.upper[2];m[1][0]=conj(m[0][1]);m[2][0]=conj(m[0][2]);m[2][1]=conj(m[1][2]);return m;}
State state(const M&m,double source,I cap){
    State s;for(unsigned k=0;k<3;++k)s.coherency.diagonal[k]=meet(m[k][k].real,I(0,source));
    const double half=(p(source)/p(2)).upper();const I off(-half,half);unsigned ix=0;
    for(unsigned j=0;j<3;++j)for(unsigned k=j+1;k<3;++k)s.coherency.upper[ix++]={meet(m[j][k].real,off),meet(m[j][k].imag,off)};
    I trace=p(0);for(I d:s.coherency.diagonal)trace=trace+d;
    s.power=meet(meet(trace,I(0,source)),cap);return s;
}
State initial(const Frame&f,const Stokes&s){
    const I a=(p(s.i)+p(s.q))/p(2),b=(p(s.i)-p(s.q))/p(2);const Z c{p(s.u)/p(2),p(s.v)/p(2)};
    M m{};for(unsigned j=0;j<3;++j)for(unsigned k=0;k<3;++k){
        m[j][k].real=a*f.first[j]*f.first[k]+b*f.second[j]*f.second[k]+c.real*(f.first[j]*f.second[k]+f.second[j]*f.first[k]);
        m[j][k].imag=c.imag*(f.first[j]*f.second[k]-f.second[j]*f.first[k]);
    }
    return state(m,s.i,p(s.i));
}
State scalar(const State&s,I factor,double source){auto m=matrix(s.coherency);for(auto&row:m)for(auto&x:row)x=scale(x,factor);return state(m,source,meet(s.power*factor,I(0,s.power.upper())));}
State transport(const State&s,const M&j,double source,bool conserve){
    const auto c=matrix(s.coherency);M temp{},out{};
    for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b)for(unsigned k=0;k<3;++k)temp[a][b]=add(temp[a][b],mul(j[a][k],c[k][b]));
    for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b)for(unsigned k=0;k<3;++k)out[a][b]=add(out[a][b],mul(temp[a][k],conj(j[b][k])));
    return state(out,source,conserve?s.power:I(0,s.power.upper()));
}
Z phase(I a,I b){const I aa=interval::square(a),bb=interval::square(b),den=aa+bb;if(!den.strictly_positive())throw Unresolved{PowerFailure::amplitude_uncertain};return {meet((aa-bb)/den,I(-1,1)),meet(-p(2)*a*b/den,I(-1,1))};}
void amplitudes(const optical_route::Segment&g,Segment&segment,Work&w){
    const auto&f=*g.interface;const I ni=g.incident_index,nt=g.other_index,ci=*f.cosine_incident;
    if(f.kind==optical_bounds::InterfaceKind::total_internal_reflection){
        if(!f.discriminant||!f.discriminant->strictly_negative())throw Unresolved{PowerFailure::amplitude_uncertain};
        const I denom=interval::square(nt)*norm2(g.incoming.direction)*norm2(g.geometry.nearest->incident_normal);
        if(!denom.strictly_positive())throw Unresolved{PowerFailure::amplitude_uncertain};
        I k2=-*f.discriminant/denom;if(!k2.strictly_positive())throw Unresolved{PowerFailure::amplitude_uncertain};const I k=w.root(k2);
        segment.s=phase(ni*ci,nt*k);segment.p=phase(nt*ci,ni*k);return;
    }
    if(g.branch==optical_route::Branch::transmitted){segment.s=Z{meet(w.root(f.power->transmittance_s),I(0,1)),p(0)};segment.p=Z{meet(w.root(f.power->transmittance_p),I(0,1)),p(0)};return;}
    const I ct=*f.cosine_transmitted,ds=ni*ci+nt*ct,dp=nt*ci+ni*ct;
    if(!ds.strictly_positive()||!dp.strictly_positive())throw Unresolved{PowerFailure::amplitude_uncertain};
    segment.s=Z{meet((ni*ci-nt*ct)/ds,I(-1,1)),p(0)};segment.p=Z{meet((nt*ci-ni*ct)/dp,I(-1,1)),p(0)};
}
}

Result trace_route(const Input&input,const Settings&settings){
    Result out;bool checked=false;
    try{
        interval::require_environment();const auto& ps=settings.route.primitive;
        if(settings.route.maximum_steps<1||settings.route.maximum_steps>64||ps.max_sqrt_refinements<1||ps.max_sqrt_refinements>256||!std::isfinite(ps.maximum_parameter_width)||ps.maximum_parameter_width<=0||ps.maximum_parameter_width>1e6||settings.max_sqrt_refinements<1||settings.max_sqrt_refinements>256||settings.max_total_sqrt_refinements<1||settings.max_total_sqrt_refinements>4000000)throw std::invalid_argument("Invalid polarized route budget/settings");
        const auto&in=input.route;vector_valid(in.ray.origin);vector_valid(in.ray.direction);domain_valid(in.ray.minimum_parameter,in.ray.maximum_parameter);index_valid(in.index);position_valid(input.transverse_reference);
        if(!std::isfinite(in.vacuum_wavelength_m)||in.vacuum_wavelength_m<=0)throw std::invalid_argument("Wavelength must be positive finite");
        for(const auto&step:in.steps){surface_valid(step.surface);index_valid(step.next_index);domain_valid(step.minimum_parameter,step.maximum_parameter);if(step.branch!=optical_route::Branch::reflected&&step.branch!=optical_route::Branch::transmitted)throw std::invalid_argument("Invalid branch");}
        const bool cone=physical(input.initial);checked=true;
        if(in.steps.size()>settings.route.maximum_steps){out.status=Status::budget_exceeded;out.message="Step count exceeds budget before work";return out;}
        out.geometry=optical_route::trace_route(in,settings.route);const auto& geometry=*out.geometry;
        out.geometry_queries=unsigned(geometry.segments.size());
        for(const auto&s:geometry.segments){out.geometry_sqrt_refinements+=s.geometry.sqrt_refinements;out.refinement_limited=out.refinement_limited||s.geometry.refinement_limited;if(s.interface){++out.interface_queries;out.geometry_sqrt_refinements+=s.interface->sqrt_refinements;out.refinement_limited=out.refinement_limited||s.interface->refinement_limited;}}
        if(geometry.status==optical_route::Status::invalid_input||geometry.status==optical_route::Status::numerical_failure){out.status=Status::numerical_failure;out.message="Preflighted geometry failed numerically; partial sqrt work may be unreported";return out;}
        Work work{out,settings};work.audit();if(!cone)throw Unresolved{PowerFailure::initial_state_uncertain};
        Frame frame{{p(0),p(0),p(0)},{p(0),p(0),p(0)},{p(0),p(0),p(0)}};frame.direction=work.unit(in.ray.direction,PowerFailure::initial_frame_uncertain);frame.second=work.unit(cross(frame.direction,optical_bounds::enclose(input.transverse_reference)),PowerFailure::initial_frame_uncertain);frame.first=cross(frame.second,frame.direction);
        out.initial_frame=frame;State current=initial(frame,input.initial);out.initial_state=current;out.segments.reserve(geometry.completed_steps);
        for(unsigned i=0;i<geometry.completed_steps;++i){
            out.failed_power_step=i;const auto&g=geometry.segments[i];out.segments.push_back({i,g.branch});auto& segment=out.segments.back();
            const auto&f=*g.interface;
            if(singleton(g.incident_index)&&singleton(g.other_index)&&g.incident_index.lower()==g.other_index.lower()){
                segment.homogeneous=true;segment.s=Z{p(g.branch==optical_route::Branch::transmitted?1:0),p(0)};segment.p=segment.s;
                if(g.branch==optical_route::Branch::reflected)current=scalar(current,p(0),input.initial.i);
            }else if(zero(cross(g.incoming.direction,g.geometry.nearest->incident_normal))){
                segment.exact_normal=true;const I sum=g.incident_index+g.other_index;
                I factor=p(0);if(g.branch==optical_route::Branch::reflected){const I r=(g.incident_index-g.other_index)/sum;segment.s=Z{r,p(0)};segment.p=Z{-r,p(0)};factor=interval::square(r);}
                else{factor=meet(p(4)*g.incident_index*g.other_index/interval::square(sum),I(0,1));const I amplitude=work.root(factor);segment.s=Z{amplitude,p(0)};segment.p=segment.s;}
                current=scalar(current,meet(factor,I(0,1)),input.initial.i);
            }else{
                const V s=work.unit(cross(*f.normal_unit,*f.incident_unit),PowerFailure::incidence_frame_uncertain);
                const V pi=cross(*f.incident_unit,s);const auto& outgoing=g.branch==optical_route::Branch::reflected?*f.reflected:*f.transmitted;const V po=cross(outgoing,s);
                amplitudes(g,segment,work);M j{};for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b)j[a][b]=add(scale(*segment.s,s[a]*s[b]),scale(*segment.p,po[a]*pi[b]));
                current=transport(current,j,input.initial.i,f.kind==optical_bounds::InterfaceKind::total_internal_reflection);
            }
            segment.outgoing=current;++out.completed_power_steps;
        }
        out.failed_power_step=out.completed_power_steps;
        if(geometry.status!=optical_route::Status::completed){out.status=geometry.status==optical_route::Status::budget_exceeded?Status::budget_exceeded:Status::geometry_failed;out.message="Geometry did not complete; power prefix is diagnostic only";return out;}
        out.completion=Completion{current,geometry.completion->ray,geometry.completion->index};out.status=Status::completed;return out;
    }catch(const Budget&){out.status=Status::budget_exceeded;out.message="Actual reported sqrt work exceeds total budget";}
    catch(const Unresolved&u){out.status=Status::power_unresolved;out.power_failure=u.failure;out.message="Full-family polarization frame/state/amplitude not certified";}
    catch(const std::invalid_argument&e){out.status=checked?Status::numerical_failure:Status::invalid_input;out.power_failure=checked?PowerFailure::numerical_domain:PowerFailure::none;out.message=e.what();}
    catch(const std::exception&e){out.status=Status::numerical_failure;out.power_failure=PowerFailure::numerical_domain;out.message=e.what();}
    out.completion.reset();return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif

