#include "pikapika/constrained.hpp"
#include "pikapika/interval.hpp"
#include "dynamics_internal.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Constrained residual audits require strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::constrained {
namespace {
using I=interval::Interval;
using V=std::array<I,3>;
constexpr std::size_t absent=static_cast<std::size_t>(-1);
struct Stop {Failure failure;const char* message;};
void need(bool ok,Failure f,const char* text){if(!ok)throw Stop{f,text};}
double coord(Vec3 v,unsigned k){return k==0?v.x:k==1?v.y:v.z;}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
I p(double x){return I::point(x);}
V point(Vec3 v){return {p(v.x),p(v.y),p(v.z)};}
V sub(const V& a,const V& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
I dot(const V& a,const V& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
I squared(const V& v){return interval::square(v[0])+interval::square(v[1])+interval::square(v[2]);}
double magnitude(I x){return std::max(std::abs(x.lower()),std::abs(x.upper()));}
std::array<double,2> bounds(I x){return {x.lower(),x.upper()};}
I norm(const V& v,Vec3 approximate){
    const I s=squared(v);double lo=std::hypot(approximate.x,approximate.y,approximate.z),hi=lo;
    need(std::isfinite(lo)&&lo>0,Failure::numerical_failure,"undefined constraint distance/normal");
    for(unsigned j=0;j<256;++j){
        const bool lower=interval::square(p(lo)).upper()<=s.lower(),upper=interval::square(p(hi)).lower()>=s.upper();
        if(lower&&upper)return I(lo,hi);
        if(!lower)lo=std::nextafter(lo,0.0);
        if(!upper)hi=std::nextafter(hi,std::numeric_limits<double>::infinity());
    }
    throw Stop{Failure::numerical_failure,"constraint norm audit exhausted"};
}
V normalized(const V& v,I n){return {v[0]/n,v[1]/n,v[2]/n};}
struct Row {Pair pair;std::size_t a{absent},b{},plane{absent};};
struct Geometry {Vec3 normal{};V normal_bounds;I gap,vn;double nominal_gap{};};
double inverse_mass(const dynamics::RigidBody& b){return b.is_static?0:1/b.mass;}
void settings_valid(const Settings& s,double dt){
    const auto positive=[](double v,double max){return std::isfinite(v)&&v>0&&v<=max;};
    need(std::isfinite(dt)&&dt>=1e-12&&dt<=.1,Failure::invalid_input,"constrained dt outside [1e-12,0.1] s");
    need(positive(s.initial_gap_tolerance,1e-3)&&positive(s.initial_velocity_tolerance,1e-3)&&positive(s.position_tolerance,1e-3)&&
         positive(s.velocity_tolerance,1e-3)&&positive(s.position_equation_tolerance,1e-3)&&positive(s.velocity_equation_tolerance,1e-3)&&
         positive(s.minimum_scaled_pivot,1)&&s.minimum_scaled_pivot>=1e-14&&positive(s.maximum_normal_rotation,1)&&
         positive(s.maximum_impulse,1e24)&&positive(s.maximum_angular_increment,3.141592653589793),Failure::invalid_input,"invalid constrained numerical profile");
    need(s.max_newton_iterations>0&&s.max_newton_iterations<=64&&s.max_linear_solves>0&&s.max_linear_solves<=256&&
         s.max_line_search_steps>0&&s.max_line_search_steps<=32&&s.max_contacts>0&&s.max_contacts<=256,
         Failure::invalid_input,"invalid constrained bounded work profile");
}
std::vector<Row> rows(std::span<const dynamics::RigidBody> bodies,std::span<const dynamics::Plane> planes,std::span<const Pair> active){
    const auto body_index=[&](std::uint64_t id){for(std::size_t i=0;i<bodies.size();++i)if(bodies[i].id==id)return i;return absent;};
    std::vector<Row> result;result.reserve(active.size());
    for(const auto pair:active){
        need(pair.first_id!=pair.second_id,Failure::invalid_input,"constraint IDs must differ");
        for(const auto& r:result)need(r.pair!=pair,Failure::invalid_input,"duplicate active pair");
        Row row;row.pair=pair;row.b=body_index(pair.second_id);
        need(row.b!=absent,Failure::invalid_input,"second constraint ID must identify a sphere");
        for(std::size_t j=0;j<planes.size();++j)if(planes[j].id==pair.first_id)row.plane=j;
        if(row.plane==absent){row.a=body_index(pair.first_id);need(row.a!=absent&&pair.first_id<pair.second_id,Failure::invalid_input,"sphere pairs require canonical ascending IDs");}
        need(!bodies[row.b].is_static||(row.a!=absent&&!bodies[row.a].is_static),Failure::static_constraint,"active static-static constraint is indeterminate");
        result.push_back(row);
    }
    return result;
}
Geometry geometry(const Row& row,std::span<const dynamics::RigidBody> bodies,std::span<const dynamics::Plane> planes,Result& result){
    ++result.geometry_evaluations;const auto& b=bodies[row.b];
    if(row.a==absent){
        const auto& plane=planes[row.plane];const V raw=point(plane.normal);const I length=norm(raw,plane.normal);const V n=normalized(raw,length);
        const double nominal_length=std::hypot(plane.normal.x,plane.normal.y,plane.normal.z);
        const Vec3 normal=plane.normal*(1/nominal_length);
        const I gap=(dot(raw,point(b.position))-p(plane.offset))/length-p(b.radius);
        return {normal,n,gap,dot(n,point(b.velocity)),(plane.normal.dot(b.position)-plane.offset)/nominal_length-b.radius};
    }
    const auto& a=bodies[row.a];const Vec3 delta=b.position-a.position;const V exact_delta=sub(point(b.position),point(a.position));
    const I length=norm(exact_delta,delta);const V n=normalized(exact_delta,length);
    const double nominal_length=std::hypot(delta.x,delta.y,delta.z);
    return {delta*(1/nominal_length),n,length-p(a.radius)-p(b.radius),dot(n,sub(point(b.velocity),point(a.velocity))),nominal_length-a.radius-b.radius};
}
double coefficient(const Row& i,const Row& j,Vec3 ni,Vec3 nj,std::span<const dynamics::RigidBody> bodies){
    double mass=0;
    if(i.a!=absent&&i.a==j.a)mass+=inverse_mass(bodies[i.a]);
    if(i.a!=absent&&i.a==j.b)mass-=inverse_mass(bodies[i.a]);
    if(i.b==j.a)mass-=inverse_mass(bodies[i.b]);
    if(i.b==j.b)mass+=inverse_mass(bodies[i.b]);
    return ni.dot(nj)*mass;
}
// Row/column equilibration by sqrt(J0 M^-1 J0^T diagonal), then partial-pivot
// LU. Cross-endpoint position Jacobians are NOT assumed symmetric or positive.
std::vector<double> solve(std::vector<double> matrix,std::vector<double> rhs,const std::vector<double>& scale,const Settings& settings,Result& result){
    need(result.linear_solves<settings.max_linear_solves,Failure::linear_budget,"constrained linear-solve budget exhausted");++result.linear_solves;
    const std::size_t n=rhs.size();
    for(std::size_t i=0;i<n;++i){rhs[i]/=scale[i];for(std::size_t j=0;j<n;++j)matrix[i*n+j]/=scale[i]*scale[j];}
    for(std::size_t k=0;k<n;++k){
        std::size_t pivot=k;for(std::size_t i=k+1;i<n;++i)if(std::abs(matrix[i*n+k])>std::abs(matrix[pivot*n+k]))pivot=i;
        const double diagonal=std::abs(matrix[pivot*n+k]);
        result.residuals.minimum_scaled_pivot=std::min(result.residuals.minimum_scaled_pivot,diagonal);
        need(std::isfinite(diagonal)&&diagonal>=settings.minimum_scaled_pivot,Failure::ill_conditioned,"singular or ill-conditioned constrained Jacobian");
        if(pivot!=k){for(std::size_t j=k;j<n;++j)std::swap(matrix[k*n+j],matrix[pivot*n+j]);std::swap(rhs[k],rhs[pivot]);}
        for(std::size_t i=k+1;i<n;++i){const double factor=matrix[i*n+k]/matrix[k*n+k];for(std::size_t j=k+1;j<n;++j)matrix[i*n+j]-=factor*matrix[k*n+j];rhs[i]-=factor*rhs[k];}
    }
    std::vector<double> answer(n);
    for(std::size_t ii=n;ii>0;--ii){const std::size_t i=ii-1;double v=rhs[i];for(std::size_t j=i+1;j<n;++j)v-=matrix[i*n+j]*answer[j];answer[i]=v/matrix[i*n+i];need(std::isfinite(answer[i]),Failure::numerical_failure,"nonfinite constrained linear solution");}
    for(std::size_t i=0;i<n;++i)answer[i]/=scale[i];return answer;
}
void add_impulses(std::vector<Vec3>& velocity,const std::vector<Row>& rows,const std::vector<Geometry>& geometry,const std::vector<double>& impulse,std::span<const dynamics::RigidBody> bodies){
    for(std::size_t j=0;j<rows.size();++j){const auto& r=rows[j];const Vec3 force=geometry[j].normal*impulse[j];
        velocity[r.b]=velocity[r.b]+force*inverse_mass(bodies[r.b]);
        if(r.a!=absent)velocity[r.a]=velocity[r.a]-force*inverse_mass(bodies[r.a]);}
}
double gap_max(const std::vector<Geometry>& geo){double maximum=0;for(const auto& g:geo)maximum=std::max(maximum,magnitude(g.gap));return maximum;}
}

Result advance(std::span<const dynamics::RigidBody> bodies,std::span<const dynamics::Plane> planes,Vec3 gravity,double dt,std::span<const Pair> active,const Settings& settings){
    Result result;
    try{
        interval::require_environment();settings_valid(settings,dt);
        need(bodies.size()<=1024&&planes.size()<=64,Failure::invalid_input,"constrained body/plane domain exceeded");
        need(active.size()<=settings.max_contacts,Failure::contact_budget,"constrained active contact budget exceeded");
        need(finite(gravity)&&std::max({std::abs(gravity.x),std::abs(gravity.y),std::abs(gravity.z)})<=1e9,Failure::invalid_input,"invalid constrained gravity");
        std::uint64_t previous=0;for(const auto& b:bodies){try{b.validate();}catch(const std::exception&){throw Stop{Failure::invalid_input,"invalid constrained body"};}
            need(b.id>previous,Failure::invalid_input,"constrained bodies must have unique ascending IDs");previous=b.id;
            need(settings.initial_gap_tolerance<=b.radius*1e-3,Failure::invalid_input,"initial contact band exceeds 0.001 of a radius");}
        previous=0;for(const auto& plane:planes){need(plane.id>previous&&plane.id<=9007199254740991ULL&&finite(plane.normal)&&std::abs(plane.normal.dot(plane.normal)-1)<1e-8&&std::isfinite(plane.offset)&&std::abs(plane.offset)<=1e12&&
                std::isfinite(plane.material.restitution)&&plane.material.restitution>=0&&plane.material.restitution<=1&&std::isfinite(plane.material.friction)&&plane.material.friction>=0&&plane.material.friction<=10,
                Failure::invalid_input,"invalid constrained plane geometry/ID");previous=plane.id;for(const auto& b:bodies)need(b.id!=plane.id,Failure::invalid_input,"plane/body duplicate ID");}
        const auto row=rows(bodies,planes,active);const std::size_t n=row.size();
        std::vector<Geometry> initial;initial.reserve(n);std::vector<double> scale(n);
        for(std::size_t i=0;i<n;++i){initial.push_back(geometry(row[i],bodies,planes,result));const auto& g=initial.back();
            result.residuals.initial_gap=std::max(result.residuals.initial_gap,magnitude(g.gap));
            result.residuals.initial_normal_velocity=std::max(result.residuals.initial_normal_velocity,magnitude(g.vn));
            need(magnitude(g.gap)<=settings.initial_gap_tolerance,Failure::initial_geometry,"active initial gap exceeds explicit tolerance");
            need(magnitude(g.vn)<=settings.initial_velocity_tolerance,Failure::initial_velocity,"active initial normal velocity exceeds explicit tolerance");
            scale[i]=std::sqrt(coefficient(row[i],row[i],g.normal,g.normal,bodies));need(std::isfinite(scale[i])&&scale[i]>0,Failure::static_constraint,"active row has no dynamic response");}
        std::vector<Vec3> acceleration(bodies.size()),base_half(bodies.size());std::vector<V> exact_acceleration;exact_acceleration.reserve(bodies.size());
        for(std::size_t i=0;i<bodies.size();++i){const auto& b=bodies[i];V exact=point({});
            if(!b.is_static){acceleration[i]=gravity+b.force*inverse_mass(b);for(unsigned k=0;k<3;++k)exact[k]=p(coord(gravity,k))+p(coord(b.force,k))/p(b.mass);
                need(finite(acceleration[i])&&std::max({magnitude(exact[0]),magnitude(exact[1]),magnitude(exact[2])})<=1e12,Failure::numerical_failure,"constrained free acceleration exceeds numerical domain");}
            exact_acceleration.push_back(exact);base_half[i]=b.velocity+acceleration[i]*(dt*.5);}
        std::vector<double> position_impulse(n,0);std::vector<Vec3> half;
        const auto state=[&](const std::vector<double>& impulse,std::vector<Vec3>& out_half){
            out_half=base_half;add_impulses(out_half,row,initial,impulse,bodies);std::vector<dynamics::RigidBody> candidate(bodies.begin(),bodies.end());
            for(std::size_t i=0;i<candidate.size();++i)if(!candidate[i].is_static){candidate[i].position=bodies[i].position+out_half[i]*dt;candidate[i].velocity=out_half[i];
                need(finite(candidate[i].position)&&std::max({std::abs(candidate[i].position.x),std::abs(candidate[i].position.y),std::abs(candidate[i].position.z)})<=1e12,Failure::numerical_failure,"constrained candidate position exceeds numerical domain");}return candidate;
        };
        const double cosine_limit=std::cos(settings.maximum_normal_rotation);
        const auto geometries=[&](std::span<const dynamics::RigidBody> candidate){std::vector<Geometry> geo;geo.reserve(n);for(std::size_t j=0;j<n;++j){geo.push_back(geometry(row[j],candidate,planes,result));
                const double cosine=std::clamp(initial[j].normal.dot(geo.back().normal),-1.0,1.0);
                result.residuals.maximum_normal_rotation=std::max(result.residuals.maximum_normal_rotation,std::acos(cosine));
                need(cosine>=cosine_limit,Failure::normal_rotation,"constraint endpoint/trial normal rotates beyond budget");}return geo;};
        auto candidate=state(position_impulse,half);auto final=geometries(candidate);bool converged=n==0;
        result.residuals.final_gap=gap_max(final);
        for(unsigned iteration=0;iteration<settings.max_newton_iterations&&!converged;++iteration){
            std::vector<double> matrix(n*n),rhs(n);for(std::size_t i=0;i<n;++i){rhs[i]=-final[i].nominal_gap/dt;for(std::size_t j=0;j<n;++j)matrix[i*n+j]=coefficient(row[i],row[j],final[i].normal,initial[j].normal,bodies);}
            const auto delta=solve(std::move(matrix),std::move(rhs),scale,settings,result);++result.newton_iterations;
            const double old_gap=gap_max(final);bool accepted=false;double fraction=1;
            for(unsigned line=0;line<settings.max_line_search_steps;++line,fraction*=.5){++result.line_search_trials;auto trial_impulse=position_impulse;
                for(std::size_t j=0;j<n;++j){trial_impulse[j]+=fraction*delta[j];need(std::isfinite(trial_impulse[j])&&std::abs(trial_impulse[j])<=settings.maximum_impulse,Failure::numerical_failure,"position-stage impulse exceeds domain");}
                std::vector<Vec3> trial_half;auto trial=state(trial_impulse,trial_half);auto trial_geometry=geometries(trial);const double trial_gap=gap_max(trial_geometry);
                if(trial_gap<old_gap||trial_gap<=settings.position_tolerance){position_impulse=std::move(trial_impulse);candidate=std::move(trial);half=std::move(trial_half);final=std::move(trial_geometry);accepted=true;break;}
            }
            need(accepted,Failure::line_search,"position Newton line search cannot reduce audited gap");result.residuals.final_gap=gap_max(final);converged=result.residuals.final_gap<=settings.position_tolerance;
        }
        need(converged,Failure::newton_budget,"position Newton budget exhausted");
        std::vector<Vec3> velocity=half;for(std::size_t i=0;i<bodies.size();++i)if(!bodies[i].is_static)velocity[i]=velocity[i]+acceleration[i]*(dt*.5);
        std::vector<double> velocity_impulse(n),matrix(n*n),rhs(n);
        for(std::size_t i=0;i<n;++i){Vec3 relative=velocity[row[i].b];if(row[i].a!=absent)relative=relative-velocity[row[i].a];rhs[i]=-final[i].normal.dot(relative);
            for(std::size_t j=0;j<n;++j)matrix[i*n+j]=coefficient(row[i],row[j],final[i].normal,final[j].normal,bodies);}
        if(n)velocity_impulse=solve(std::move(matrix),std::move(rhs),scale,settings,result);
        for(double impulse:velocity_impulse)need(std::isfinite(impulse)&&std::abs(impulse)<=settings.maximum_impulse,Failure::numerical_failure,"velocity-stage impulse exceeds domain");
        add_impulses(velocity,row,final,velocity_impulse,bodies);
        // Residuals enclose the discrete equations using real input F/m and
        // interval geometric normal bounds, not just the rounded Newton matrix.
        std::vector<V> impulse0(bodies.size(),point({})),impulse1(bodies.size(),point({}));
        for(std::size_t j=0;j<n;++j){const auto& rr=row[j];for(unsigned k=0;k<3;++k){const I a=initial[j].normal_bounds[k]*p(position_impulse[j]),b=final[j].normal_bounds[k]*p(velocity_impulse[j]);
                impulse0[rr.b][k]=impulse0[rr.b][k]+a;impulse1[rr.b][k]=impulse1[rr.b][k]+b;
                if(rr.a!=absent){impulse0[rr.a][k]=impulse0[rr.a][k]-a;impulse1[rr.a][k]=impulse1[rr.a][k]-b;}}}
        for(std::size_t i=0;i<bodies.size();++i){
            const Vec3 position=candidate[i].position;
            if(!bodies[i].is_static)for(unsigned k=0;k<3;++k){
                const I inverse=p(1)/p(bodies[i].mass),v0=p(coord(bodies[i].velocity,k));
                const I expected_half=v0+exact_acceleration[i][k]*p(dt)*p(.5)+impulse0[i][k]*inverse;
                const I expected_position=p(coord(bodies[i].position,k))+expected_half*p(dt);
                const I expected_velocity=expected_half+exact_acceleration[i][k]*p(dt)*p(.5)+impulse1[i][k]*inverse;
                result.residuals.position_equation=std::max(result.residuals.position_equation,magnitude(p(coord(position,k))-expected_position));
                result.residuals.velocity_equation=std::max(result.residuals.velocity_equation,magnitude(p(coord(velocity[i],k))-expected_velocity));
            }
            // Same independent world-L/midpoint attitude propagator; its temporary
            // free q/v are replaced by RATTLE q/v before validating the candidate.
            candidate[i]=bodies[i];dynamics::detail::propagate_free(candidate[i],gravity,dt,settings.maximum_angular_increment);
            candidate[i].position=position;candidate[i].velocity=velocity[i];candidate[i].validate();
        }
        for(std::size_t j=0;j<n;++j){const auto g=geometry(row[j],candidate,planes,result);Constraint c;c.pair=row[j].pair;c.initial_normal=initial[j].normal;c.final_normal=g.normal;
            c.initial_gap=bounds(initial[j].gap);c.final_gap=bounds(g.gap);c.initial_normal_velocity=bounds(initial[j].vn);c.final_normal_velocity=bounds(g.vn);
            c.impulse_position=position_impulse[j];c.impulse_velocity=velocity_impulse[j];result.constraints.push_back(c);
            result.residuals.final_gap=std::max(result.residuals.final_gap,magnitude(g.gap));result.residuals.final_normal_velocity=std::max(result.residuals.final_normal_velocity,magnitude(g.vn));
            result.residuals.maximum_normal_rotation=std::max(result.residuals.maximum_normal_rotation,std::acos(std::clamp(initial[j].normal.dot(g.normal),-1.0,1.0)));
            if(position_impulse[j]<0||velocity_impulse[j]<0)result.release_pairs.push_back(row[j].pair);
        }
        need(result.release_pairs.empty(),Failure::release_required,"signed RATTLE stage impulse requires tension; driver must release/recompute");
        need(result.residuals.final_gap<=settings.position_tolerance&&result.residuals.final_normal_velocity<=settings.velocity_tolerance&&
             result.residuals.position_equation<=settings.position_equation_tolerance&&result.residuals.velocity_equation<=settings.velocity_equation_tolerance,
             Failure::residual,"constrained endpoint or original discrete-equation audit exceeds tolerance");
        result.success=true;result.candidate_bodies=std::move(candidate);
    }catch(const Stop& e){result.failure=e.failure;result.message=e.message;}
     catch(const std::exception& e){result.failure=Failure::numerical_failure;result.message=e.what();}
    return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
