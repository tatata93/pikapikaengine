#include "pikapika/support.hpp"
#include "pikapika/interval.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace pikapika::support {
namespace {
using I=interval::Interval;
using V=std::array<I,3>;
constexpr std::size_t absent=static_cast<std::size_t>(-1);
struct Stop {Failure failure;const char* message;};
void need(bool b,Failure f,const char* message){if(!b)throw Stop{f,message};}
I point(double x){return I::point(x);}
V points(Vec3 v){return {point(v.x),point(v.y),point(v.z)};}
double component(Vec3 v,unsigned k){return k==0?v.x:k==1?v.y:v.z;}
double magnitude(I x){return std::max(std::abs(x.lower()),std::abs(x.upper()));}
double midpoint(I x){return std::midpoint(x.lower(),x.upper());}
double width(I x){return (point(x.upper())-point(x.lower())).upper();}
V difference(const V& a,const V& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
I dot(const V& a,const V& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
I squared(const V& a){return interval::square(a[0])+interval::square(a[1])+interval::square(a[2]);}
std::array<double,2> bounds(I x){return {x.lower(),x.upper()};}
Vec3 lower(const V& v){return {v[0].lower(),v[1].lower(),v[2].lower()};}
Vec3 upper(const V& v){return {v[0].upper(),v[1].upper(),v[2].upper()};}
Vec3 middle(const V& v){return {midpoint(v[0]),midpoint(v[1]),midpoint(v[2])};}
bool bounded(Vec3 v,double m){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::abs(v.x)<=m&&std::abs(v.y)<=m&&std::abs(v.z)<=m;}
// Check, rather than assume, that squared adjacent endpoints enclose the exact
// squared norm. No promise about library sqrt/hypot accuracy is used as a proof.
I norm(const V& v,Vec3 estimate_vector){
    const I s=squared(v);double lo=std::hypot(estimate_vector.x,estimate_vector.y,estimate_vector.z),hi=lo;
    need(std::isfinite(lo)&&lo>0,Failure::geometry_uncertain,"undefined or unrepresentable support normal");
    for(unsigned step=0;step<256;++step){
        const bool a=interval::square(point(lo)).upper()<=s.lower(),b=interval::square(point(hi)).lower()>=s.upper();
        if(a&&b)return I(lo,hi);
        if(!a)lo=std::nextafter(lo,0.0);if(!b)hi=std::nextafter(hi,std::numeric_limits<double>::infinity());
    }
    throw Stop{Failure::geometry_uncertain,"support distance/normal enclosure exhausted"};
}
V normalized(const V& v,I length){return {v[0]/length,v[1]/length,v[2]/length};}
struct Row {std::size_t a{absent},b{},output{};V normal;I free;Row(std::size_t aa,std::size_t bb,std::size_t out,V n,I f):a(aa),b(bb),output(out),normal(n),free(f){}};
I inverse_mass(const dynamics::RigidBody& b){return b.is_static?point(0):point(1)/point(b.mass);}
V free_acceleration(const dynamics::RigidBody& b,Vec3 gravity){
    if(b.is_static)return points({});
    V a=points({});for(unsigned k=0;k<3;++k){a[k]=point(component(gravity,k))+point(component(b.force,k))/point(b.mass);
        need(magnitude(a[k])<=1e12,Failure::invalid_input,"support free acceleration exceeds 1e12 m/s^2");}return a;
}
void settings_valid(const Settings& s){
    const auto positive=[](double x,double maximum){return std::isfinite(x)&&x>0&&x<=maximum;};
    need(positive(s.gap_tolerance,1e-3)&&positive(s.velocity_interval_tolerance,1e-3)&&positive(s.acceleration_tolerance,1)&&
        positive(s.complementarity_tolerance,1)&&positive(s.projected_force_tolerance,1)&&positive(s.minimum_scaled_pivot,1)&&
        s.minimum_scaled_pivot>=1e-14&&positive(s.maximum_force,1e24),Failure::invalid_input,"invalid support finite-precision tolerances");
    need(s.max_iterations>0&&s.max_iterations<=100000&&s.max_contacts>0&&s.max_contacts<=256&&s.max_pair_queries>0&&s.max_pair_queries<=1000000,
        Failure::invalid_input,"invalid support bounded budgets");
}
I coefficient(const Row& a,const Row& b,const std::vector<dynamics::RigidBody>& bodies){
    const I d=dot(a.normal,b.normal);I sum=point(0);
    if(a.a!=absent&&a.a==b.a)sum=sum+inverse_mass(bodies[a.a]);
    if(a.a!=absent&&a.a==b.b)sum=sum-inverse_mass(bodies[a.a]);
    if(a.b==b.a)sum=sum-inverse_mass(bodies[a.b]);
    if(a.b==b.b)sum=sum+inverse_mass(bodies[a.b]);
    return d*sum;
}
}

Result solve(const dynamics::World& world,const Settings& settings){
    Result result;
    try{
        interval::require_environment();settings_valid(settings);
        need(bounded(world.gravity,1e9),Failure::invalid_input,"invalid support gravity");
        const auto& bodies=world.bodies();const auto& planes=world.planes();
        std::vector<V> free;free.reserve(bodies.size());std::uint64_t previous=0;
        for(const auto& b:bodies){try{b.validate();}catch(const std::exception&){throw Stop{Failure::invalid_input,"invalid support body state"};}
            need(b.id>previous,Failure::invalid_input,"support body IDs must retain insertion order/uniqueness");previous=b.id;
            for(const auto& p:planes)need(b.id!=p.id,Failure::invalid_input,"support body ID duplicates a plane");
            need(settings.gap_tolerance<=b.radius*1e-3,Failure::invalid_input,"support gap band exceeds 0.001 of a radius");free.push_back(free_acceleration(b,world.gravity));}
        std::vector<Row> rows;
        const auto candidate=[&](std::size_t a,std::size_t b,std::uint64_t first,V normal,I gap,I vn,I curve,bool exact_zero){
            result.first_id=first;result.second_id=bodies[b].id;
            need(result.pair_queries<settings.max_pair_queries,Failure::pair_budget,"support geometry pair budget exhausted");++result.pair_queries;
            if(gap.lower()>settings.gap_tolerance){++result.separated_pairs;return;}
            need(gap.upper()>=-settings.gap_tolerance,Failure::geometry_incompatible,"support pair is penetrated beyond the explicit contact band");
            need(gap.lower()>=-settings.gap_tolerance&&gap.upper()<=settings.gap_tolerance,Failure::geometry_uncertain,"support gap enclosure crosses the contact-band boundary");
            result.maximum_geometry_offset=std::max(result.maximum_geometry_offset,magnitude(gap));
            need(!bodies[b].is_static||(a!=absent&&!bodies[a].is_static),Failure::static_constraint,"static-static normal reaction is indeterminate in this support subset");
            need(!vn.strictly_negative(),Failure::impact_required,"provably closing contact requires an impact solve, irrespective of speed magnitude");
            if(exact_zero)vn=point(0);
            need(exact_zero||vn.strictly_positive(),Failure::velocity_uncertain,"nonstructural zero/uncertain normal velocity is not silently treated as support");
            result.maximum_velocity_interval_width=std::max(result.maximum_velocity_interval_width,width(vn));
            need(width(vn)<=settings.velocity_interval_tolerance,Failure::velocity_uncertain,"normal-velocity enclosure exceeds its uncertainty guard");
            need(result.constraints.size()<settings.max_contacts,Failure::contact_budget,"support contact budget exhausted");
            V relative=free[b];if(a!=absent)relative=difference(relative,free[a]);const I base=dot(normal,relative)+curve;
            need(std::isfinite(base.lower())&&std::isfinite(base.upper())&&std::isfinite(curve.lower())&&std::isfinite(curve.upper()),
                Failure::numerical_uncertainty,"support acceleration/curvature enclosure exceeds finite binary64 output");
            Constraint c;c.first_id=first;c.second_id=bodies[b].id;c.normal=middle(normal);c.normal_lower=lower(normal);c.normal_upper=upper(normal);
            c.gap=bounds(gap);c.normal_velocity=bounds(vn);c.curvature=bounds(curve);c.free_normal_acceleration=midpoint(base);
            c.phase=exact_zero?Phase::resting:Phase::separating;
            result.constraints.push_back(c);
            if(exact_zero){rows.emplace_back(a,b,result.constraints.size()-1,normal,base);++result.resting_constraints;}
            else ++result.separating_constraints;
        };
        for(std::size_t i=0;i<bodies.size();++i){
            const auto& b=bodies[i];
            for(const auto& p:planes){
                const V n=points(p.normal);const I length=norm(n,p.normal);const V unit=normalized(n,length);
                const I gap=(dot(n,points(b.position))-point(p.offset))/length-point(b.radius);
                bool zero=true;for(unsigned k=0;k<3;++k)zero=zero&&(component(p.normal,k)==0||component(b.velocity,k)==0);
                const I vn=zero?point(0):dot(unit,points(b.velocity));candidate(absent,i,p.id,unit,gap,vn,point(0),zero);
            }
            for(std::size_t j=i+1;j<bodies.size();++j){
                const auto& other=bodies[j];const V delta=difference(points(other.position),points(b.position));
                const Vec3 rounded=other.position-b.position;
                // Coincidence is invalid geometry, not an arbitrary {1,0,0} normal.
                const I length=norm(delta,rounded);const V n=normalized(delta,length);
                const I gap=length-point(b.radius)-point(other.radius);
                const V velocity=difference(points(other.velocity),points(b.velocity));
                bool zero=true;for(unsigned k=0;k<3;++k)zero=zero&&
                    (component(other.position,k)==component(b.position,k)||component(other.velocity,k)==component(b.velocity,k));
                const I vn=zero?point(0):dot(n,velocity);
                I tangential=squared(velocity)-interval::square(vn);
                need(tangential.upper()>=0,Failure::numerical_uncertainty,"relative tangent-speed enclosure is inconsistent");
                tangential=I(std::max(0.0,tangential.lower()),tangential.upper());
                candidate(i,j,b.id,n,gap,vn,tangential/length,zero);
            }
        }
        const std::size_t n=rows.size();std::vector<I> enclosure(n*n,point(0));std::vector<double> matrix(n*n),lambda(n,0),base(n),diagonal(n);
        for(std::size_t i=0;i<n;++i){base[i]=midpoint(rows[i].free);for(std::size_t j=0;j<=i;++j){const I a=coefficient(rows[i],rows[j],bodies);
            enclosure[i*n+j]=enclosure[j*n+i]=a;matrix[i*n+j]=matrix[j*n+i]=midpoint(a);}diagonal[i]=matrix[i*n+i];
            need(std::isfinite(diagonal[i])&&diagonal[i]>0,Failure::static_constraint,"normal support constraint has no dynamic effective mass");}
        // Deliberately reject singular/redundant systems, even if an iterative
        // method could produce one plausible force distribution. No diagonal
        // regularisation or hidden compliance is added to pass the test.
        std::vector<double> cholesky(n*n,0);
        for(std::size_t i=0;i<n;++i)for(std::size_t j=0;j<=i;++j){
            double value=matrix[i*n+j]/(std::sqrt(diagonal[i])*std::sqrt(diagonal[j]));
            for(std::size_t k=0;k<j;++k)value-=cholesky[i*n+k]*cholesky[j*n+k];
            if(i==j){result.minimum_scaled_pivot=std::min(result.minimum_scaled_pivot,value);
                need(std::isfinite(value)&&value>=settings.minimum_scaled_pivot,Failure::ill_conditioned,"singular/redundant or ill-conditioned normal constraint matrix");
                cholesky[i*n+j]=std::sqrt(value);
            }else cholesky[i*n+j]=value/cholesky[j*n+j];
        }
        const auto audit=[&]{
            result.residuals.negative_acceleration=0;result.residuals.complementarity=0;result.residuals.maximum_acceleration_interval_width=0;
            for(std::size_t i=0;i<n;++i){I a=rows[i].free;for(std::size_t j=0;j<n;++j)a=a+enclosure[i*n+j]*point(lambda[j]);
                auto& out=result.constraints[rows[i].output];out.lambda=lambda[i];out.normal_acceleration=midpoint(a);out.acceleration_bounds=bounds(a);
                result.residuals.negative_acceleration=std::max(result.residuals.negative_acceleration,std::max(0.0,-a.lower()));
                result.residuals.complementarity=std::max(result.residuals.complementarity,magnitude(point(lambda[i])*a));
                result.residuals.maximum_acceleration_interval_width=std::max(result.residuals.maximum_acceleration_interval_width,width(a));}
        };
        bool converged=n==0;
        for(unsigned iteration=0;iteration<settings.max_iterations&&!converged;++iteration){
            for(std::size_t i=0;i<n;++i){double acceleration=base[i];for(std::size_t j=0;j<n;++j)acceleration+=matrix[i*n+j]*lambda[j];
                const double candidate=lambda[i]-acceleration/diagonal[i];
                need(std::isfinite(acceleration)&&std::isfinite(candidate),Failure::numerical_failure,"nonfinite support iteration");
                lambda[i]=std::max(0.0,candidate);
                need(lambda[i]<=settings.maximum_force,Failure::numerical_failure,"support force exceeds configured numeric domain");}
            result.iterations=iteration+1;double negative=0,comp=0,projected=0;
            for(std::size_t i=0;i<n;++i){double a=base[i];for(std::size_t j=0;j<n;++j)a+=matrix[i*n+j]*lambda[j];
                negative=std::max(negative,std::max(0.0,-a));comp=std::max(comp,std::abs(lambda[i]*a));
                projected=std::max(projected,std::abs(lambda[i]-std::max(0.0,lambda[i]-a/diagonal[i])));}
            result.residuals.projected_force=projected;
            if(negative>settings.acceleration_tolerance/8||comp>settings.complementarity_tolerance/8||projected>settings.projected_force_tolerance/8)continue;
            audit();
            need(result.residuals.negative_acceleration<=settings.acceleration_tolerance&&result.residuals.complementarity<=settings.complementarity_tolerance&&
                projected<=settings.projected_force_tolerance,Failure::numerical_uncertainty,"nominal support converged but interval complementarity/acceleration audit failed");
            converged=true;
        }
        if(!converged)audit();
        need(converged,Failure::iteration_budget,"support iteration budget exhausted before verified complementarity");
        std::vector<V> forces(bodies.size(),points({}));
        for(std::size_t i=0;i<n;++i)for(unsigned k=0;k<3;++k){const I f=rows[i].normal[k]*point(lambda[i]);forces[rows[i].b][k]=forces[rows[i].b][k]+f;
            if(rows[i].a!=absent)forces[rows[i].a][k]=forces[rows[i].a][k]-f;}
        std::vector<V> accelerations=free;
        for(std::size_t i=0;i<bodies.size();++i){for(unsigned k=0;k<3;++k)accelerations[i][k]=accelerations[i][k]+forces[i][k]*inverse_mass(bodies[i]);
            BodyReaction b;b.id=bodies[i].id;b.force=middle(forces[i]);b.force_lower=lower(forces[i]);b.force_upper=upper(forces[i]);
            b.acceleration=middle(accelerations[i]);b.acceleration_lower=lower(accelerations[i]);b.acceleration_upper=upper(accelerations[i]);result.bodies.push_back(b);}
        // Separating contacts have lambda=0, and do not require a_n>=0: a positive
        // vn can coexist with inward acceleration. They are outside the rest LCP.
        for(auto& c:result.constraints)if(c.phase==Phase::separating){
            std::size_t b=absent,a=absent;for(std::size_t i=0;i<bodies.size();++i){if(bodies[i].id==c.second_id)b=i;if(bodies[i].id==c.first_id)a=i;}
            V relative=accelerations[b];if(a!=absent)relative=difference(relative,accelerations[a]);
            const V normal={I(c.normal_lower.x,c.normal_upper.x),I(c.normal_lower.y,c.normal_upper.y),I(c.normal_lower.z,c.normal_upper.z)};
            const I value=dot(normal,relative)+I(c.curvature[0],c.curvature[1]);c.normal_acceleration=midpoint(value);c.acceleration_bounds=bounds(value);}
        result.success=true;result.first_id=result.second_id=0;
    }catch(const Stop& stop){result.failure=stop.failure;result.message=stop.message;}
     catch(const std::exception& error){result.failure=Failure::numerical_failure;result.message=error.what();}
    return result;
}
}
