#include "pikapika/dynamics.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace pikapika::dynamics {
namespace {
void require(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
bool finite(Vec3 v) { return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z); }
bool bounded(Vec3 v,double bound) { return finite(v)&&std::abs(v.x)<=bound&&std::abs(v.y)<=bound&&std::abs(v.z)<=bound; }
void material_valid(Material m) {
    require(std::isfinite(m.restitution)&&m.restitution>=0&&m.restitution<=1&&
            std::isfinite(m.friction)&&m.friction>=0&&m.friction<=10,"invalid dynamics material");
}
void id_valid(std::uint64_t id) { require(id>0&&id<=9007199254740991ULL,"invalid dynamics stable ID"); }
Quaternion multiply(Quaternion a,Quaternion b) {
    return {a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
            a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z};
}
Quaternion advance_orientation(Quaternion q,Vec3 omega,double dt,double max_angle) {
    const double speed=omega.length(),angle=speed*dt;
    require(std::isfinite(angle)&&angle<=max_angle,"rotation step too large; reduce dynamics timestep");
    if(speed<1e-15)return q;
    const double scale=std::sin(angle*0.5)/speed;
    return multiply({omega.x*scale,omega.y*scale,omega.z*scale,std::cos(angle*0.5)},q).normalized();
}
void integrate(RigidBody& body,Vec3 gravity,double dt,double max_angle) {
    if(body.is_static) { body.force={};body.torque={};return; }
    const auto acceleration=gravity+body.force*body.inverse_mass();
    body.position=body.position+body.velocity*dt+acceleration*(0.5*dt*dt);
    body.velocity=body.velocity+acceleration*dt;
    // World L, rather than omega, is advanced. Thus changing R changes omega even
    // at zero external torque; the anisotropic gyroscopic behaviour is retained.
    const auto midpoint=advance_orientation(body.orientation,body.angular_velocity(),dt*0.5,max_angle);
    auto midbody=body;midbody.orientation=midpoint;
    midbody.angular_momentum=body.angular_momentum+body.torque*(dt*0.5);
    body.orientation=advance_orientation(body.orientation,midbody.angular_velocity(),dt,max_angle);
    body.angular_momentum=body.angular_momentum+body.torque*dt;
    body.force={};body.torque={};body.validate();
}
constexpr std::size_t no_body=std::numeric_limits<std::size_t>::max();
struct Contact {
    std::size_t a{no_body},b{no_body};
    Vec3 point{},normal{},ra{},rb{},t1{},t2{};
    double penetration{},friction{},bounce{},normal_impulse{},tangent1{},tangent2{};
};
Vec3 point_velocity(const RigidBody* body,Vec3 r) {
    return body?body->velocity+body->angular_velocity().cross(r):Vec3{};
}
Vec3 relative_velocity(const Contact& c,const std::vector<RigidBody>& bodies) {
    return point_velocity(&bodies[c.b],c.rb)-point_velocity(c.a==no_body?nullptr:&bodies[c.a],c.ra);
}
Vec3 mass_response(const RigidBody* body,Vec3 r,Vec3 direction) {
    if(!body||body->is_static)return {};
    return direction*body->inverse_mass()+body->inverse_world_inertia(r.cross(direction)).cross(r);
}
Vec3 contact_mass_response(const Contact& c,const std::vector<RigidBody>& bodies,Vec3 direction) {
    return mass_response(c.a==no_body?nullptr:&bodies[c.a],c.ra,direction)+mass_response(&bodies[c.b],c.rb,direction);
}
void body_impulse(RigidBody& body,Vec3 impulse,Vec3 arm) {
    if(body.is_static)return;
    body.velocity=body.velocity+impulse*body.inverse_mass();
    body.angular_momentum=body.angular_momentum+arm.cross(impulse);
}
void contact_impulse(Contact& c,std::vector<RigidBody>& bodies,Vec3 impulse) {
    if(c.a!=no_body)body_impulse(bodies[c.a],impulse*(-1),c.ra);
    body_impulse(bodies[c.b],impulse,c.rb);
}
void prepare(Contact& c,const std::vector<RigidBody>& bodies,Material a,Material b,const SolverSettings& settings) {
    if(c.a!=no_body)c.ra=c.point-bodies[c.a].position;
    c.rb=c.point-bodies[c.b].position;
    c.friction=std::sqrt(a.friction*b.friction);
    const auto relative=relative_velocity(c,bodies);const double vn=relative.dot(c.normal);
    c.bounce=vn < -settings.restitution_velocity_threshold ? -std::max(a.restitution,b.restitution)*vn : 0;
    const auto tangent=relative-c.normal*vn;
    if(tangent.length()>1e-10)c.t1=tangent.normalized();
    else c.t1=c.normal.cross(std::abs(c.normal.x)<0.8?Vec3{1,0,0}:Vec3{0,1,0}).normalized();
    c.t2=c.normal.cross(c.t1);
}
void solve(Contact& c,std::vector<RigidBody>& bodies) {
    const double normal_mass=c.normal.dot(contact_mass_response(c,bodies,c.normal));
    require(std::isfinite(normal_mass)&&normal_mass>0,"invalid contact normal effective mass");
    const double vn=relative_velocity(c,bodies).dot(c.normal);
    const double previous=c.normal_impulse;
    c.normal_impulse=std::max(0.0,previous+(c.bounce-vn)/normal_mass);
    contact_impulse(c,bodies,c.normal*(c.normal_impulse-previous));
    if(c.friction==0)return;
    const auto k1=contact_mass_response(c,bodies,c.t1),k2=contact_mass_response(c,bodies,c.t2);
    const double k11=c.t1.dot(k1),k12=c.t1.dot(k2),k22=c.t2.dot(k2),scale=std::max(k11,k22);
    require(std::isfinite(scale)&&scale>0,"invalid tangent effective mass");
    const double a=k11/scale,b=k12/scale,d=k22/scale,det=a*d-b*b;
    require(std::isfinite(det)&&det>1e-14,"ill-conditioned contact tangent effective mass");
    const auto relative=relative_velocity(c,bodies);
    const double v1=relative.dot(c.t1)/scale,v2=relative.dot(c.t2)/scale;
    double candidate1=c.tangent1+(-d*v1+b*v2)/det,candidate2=c.tangent2+(b*v1-a*v2)/det;
    const double length=std::hypot(candidate1,candidate2),limit=c.friction*c.normal_impulse;
    if(length>limit) {
        if(limit==0) {candidate1=0;candidate2=0;}
        else {
            // Minimise the tangent kinetic-energy quadratic on the Coulomb disk.
            // A radial clamp would be incorrect for anisotropic effective mass.
            const double w1=v1-a*c.tangent1-b*c.tangent2,w2=v2-b*c.tangent1-d*c.tangent2;
            double low=0,high=std::max(1.0,std::hypot(w1,w2)/limit);
            require(std::isfinite(high),"contact friction scale outside numeric range");
            const auto constrained=[&](double eta) {
                const double s=std::max(a+eta,d+eta),aa=(a+eta)/s,bb=b/s,dd=(d+eta)/s;
                const double denominator=aa*dd-bb*bb,u=w1/s,v=w2/s;
                return std::array<double,2>{(-dd*u+bb*v)/denominator,(bb*u-aa*v)/denominator};
            };
            for(unsigned iteration=0;iteration<48;++iteration) {
                const double mid=(low+high)*0.5;const auto lambda=constrained(mid);
                if(std::hypot(lambda[0],lambda[1])>limit)low=mid;else high=mid;
            }
            const auto lambda=constrained(high);candidate1=lambda[0];candidate2=lambda[1];
        }
    }
    contact_impulse(c,bodies,c.t1*(candidate1-c.tangent1)+c.t2*(candidate2-c.tangent2));
    c.tangent1=candidate1;c.tangent2=candidate2;
}
void settings_valid(const SolverSettings& s) {
    require(s.velocity_iterations>0&&s.velocity_iterations<=128&&s.max_contacts>0&&s.max_contacts<=65536,"invalid bounded solver budget");
    require(std::isfinite(s.contact_margin)&&s.contact_margin>=0&&s.contact_margin<=0.1&&
        std::isfinite(s.penetration_slop)&&s.penetration_slop>=0&&s.penetration_slop<=0.1&&
        std::isfinite(s.position_correction)&&s.position_correction>=0&&s.position_correction<=1&&
        std::isfinite(s.max_position_correction)&&s.max_position_correction>=0&&s.max_position_correction<=10&&
        std::isfinite(s.restitution_velocity_threshold)&&s.restitution_velocity_threshold>=0&&
        std::isfinite(s.max_angular_increment)&&s.max_angular_increment>0&&s.max_angular_increment<=3.141592653589793,"invalid dynamics solver settings");
}
}
double RigidBody::inverse_mass() const { return is_static?0:1/mass; }
Vec3 RigidBody::inverse_world_inertia(Vec3 v) const {
    if(is_static)return {};
    const Quaternion inverse{-orientation.x,-orientation.y,-orientation.z,orientation.w};
    const auto local=inverse.rotate(v);
    return orientation.rotate({local.x/inertia_diagonal.x,local.y/inertia_diagonal.y,local.z/inertia_diagonal.z});
}
Vec3 RigidBody::angular_velocity() const { return inverse_world_inertia(angular_momentum); }
double RigidBody::kinetic_energy() const {
    return is_static?0:0.5*mass*velocity.dot(velocity)+0.5*angular_velocity().dot(angular_momentum);
}
void RigidBody::validate() const {
    id_valid(id);material_valid(material);
    require(std::isfinite(mass)&&mass>=1e-12&&mass<=1e18,"rigid body mass outside numerical domain");
    require(bounded(inertia_diagonal,1e18)&&inertia_diagonal.x>=1e-12&&inertia_diagonal.y>=1e-12&&inertia_diagonal.z>=1e-12,"invalid principal inertia");
    require(inertia_diagonal.x+inertia_diagonal.y>=inertia_diagonal.z&&inertia_diagonal.x+inertia_diagonal.z>=inertia_diagonal.y&&
            inertia_diagonal.y+inertia_diagonal.z>=inertia_diagonal.x,"principal inertia violates triangle inequality");
    require(std::isfinite(radius)&&radius>0&&radius<=1e9,"invalid sphere collision radius");
    require(bounded(position,1e12)&&bounded(velocity,1e9)&&bounded(angular_momentum,1e24)&&bounded(force,1e24)&&bounded(torque,1e24),"rigid body state outside numerical domain");
    const double q2=orientation.x*orientation.x+orientation.y*orientation.y+orientation.z*orientation.z+orientation.w*orientation.w;
    require(std::isfinite(q2)&&std::abs(q2-1)<1e-8,"dynamics quaternion must be normalized");
    require(!is_static||(velocity.dot(velocity)==0&&angular_momentum.dot(angular_momentum)==0),"static body cannot have velocity or angular momentum");
    require(std::isfinite(kinetic_energy()),"nonfinite rigid body kinetic energy");
}
RigidBody make_sphere(std::uint64_t id,double radius,double mass,Vec3 position,bool is_static) {
    RigidBody body;body.id=id;body.radius=radius;body.mass=mass;body.position=position;body.is_static=is_static;
    const double inertia=0.4*mass*radius*radius;body.inertia_diagonal={inertia,inertia,inertia};body.validate();return body;
}
bool World::contains_id(std::uint64_t id) const {
    for(const auto& body:bodies_)if(body.id==id)return true;
    for(const auto& plane:planes_)if(plane.id==id)return true;
    return false;
}
void World::add_body(RigidBody body) {
    body.validate();require(!contains_id(body.id),"duplicate dynamics stable ID");require(bodies_.size()<1024,"dynamics body budget exceeded");
    bodies_.push_back(body);std::sort(bodies_.begin(),bodies_.end(),[](const auto& a,const auto& b){return a.id<b.id;});
}
void World::add_plane(Plane plane) {
    id_valid(plane.id);material_valid(plane.material);require(!contains_id(plane.id),"duplicate dynamics stable ID");
    require(finite(plane.normal)&&std::abs(plane.normal.dot(plane.normal)-1)<1e-8&&std::isfinite(plane.offset)&&std::abs(plane.offset)<=1e12,"invalid unit plane");
    require(planes_.size()<64,"dynamics plane budget exceeded");planes_.push_back(plane);
    std::sort(planes_.begin(),planes_.end(),[](const auto& a,const auto& b){return a.id<b.id;});
}
RigidBody* World::find_body(std::uint64_t id) { for(auto& body:bodies_)if(body.id==id)return &body;return nullptr; }
const RigidBody* World::find_body(std::uint64_t id) const { for(const auto& body:bodies_)if(body.id==id)return &body;return nullptr; }
void World::apply_force(std::uint64_t id,Vec3 force,Vec3 point) {
    auto* body=find_body(id);require(body&&finite(force)&&finite(point),"invalid force application");
    if(body->is_static)return;
    auto candidate=*body;candidate.force=candidate.force+force;candidate.torque=candidate.torque+(point-body->position).cross(force);candidate.validate();*body=candidate;
}
void World::apply_torque(std::uint64_t id,Vec3 torque) {
    auto* body=find_body(id);require(body&&finite(torque),"invalid torque application");if(body->is_static)return;
    auto candidate=*body;candidate.torque=candidate.torque+torque;candidate.validate();*body=candidate;
}
void World::apply_impulse(std::uint64_t id,Vec3 impulse,Vec3 point) {
    auto* body=find_body(id);require(body&&finite(impulse)&&finite(point),"invalid impulse application");if(body->is_static)return;
    auto candidate=*body;body_impulse(candidate,impulse,point-body->position);candidate.validate();*body=candidate;
}
StepStats World::step(double dt,const SolverSettings& settings) {
    require(std::isfinite(dt)&&dt>0&&dt<=0.1&&bounded(gravity,1e9),"invalid dynamics timestep or gravity");settings_valid(settings);
    auto candidates=bodies_;for(auto& body:candidates){body.validate();integrate(body,gravity,dt,settings.max_angular_increment);}
    std::vector<Contact> contacts;contacts.reserve(std::min(settings.max_contacts,candidates.size()*4));StepStats stats;
    const auto append=[&](Contact contact,Material a,Material b) {
        require(contacts.size()<settings.max_contacts,"dynamics contact budget exceeded; step aborted");
        prepare(contact,candidates,a,b,settings);stats.max_penetration=std::max(stats.max_penetration,contact.penetration);contacts.push_back(contact);
    };
    for(std::size_t i=0;i<candidates.size();++i) {
        const auto& body=candidates[i];
        if(!body.is_static)for(const auto& plane:planes_) {
            const double distance=plane.normal.dot(body.position)-plane.offset;
            if(distance<=body.radius+settings.contact_margin) {
                Contact c;c.b=i;c.normal=plane.normal;c.point=body.position-plane.normal*body.radius;c.penetration=body.radius-distance;
                append(c,plane.material,body.material);
            }
        }
        for(std::size_t j=i+1;j<candidates.size();++j) {
            const auto& other=candidates[j];if(body.is_static&&other.is_static)continue;
            const auto delta=other.position-body.position;const double distance=delta.length(),radii=body.radius+other.radius;
            if(distance<=radii+settings.contact_margin) {
                Contact c;c.a=i;c.b=j;c.normal=distance>1e-12?delta*(1/distance):Vec3{1,0,0};
                c.point=(body.position+c.normal*body.radius+other.position-c.normal*other.radius)*0.5;c.penetration=radii-distance;
                append(c,body.material,other.material);
            }
        }
    }
    for(unsigned iteration=0;iteration<settings.velocity_iterations&&!contacts.empty();++iteration)for(auto& contact:contacts)solve(contact,candidates);
    for(const auto& c:contacts) {
        stats.normal_impulse_sum+=c.normal_impulse;stats.friction_impulse_sum+=std::hypot(c.tangent1,c.tangent2);
        stats.max_closing_residual=std::max(stats.max_closing_residual,std::max(0.0,c.bounce-relative_velocity(c,candidates).dot(c.normal)));
    }
    // Split geometric stabilisation: no penetration velocity is injected. It is
    // not a physical force and does not promise orbital-angular-momentum fidelity.
    for(const auto& c:contacts) {
        const double ia=c.a==no_body?0:candidates[c.a].inverse_mass(),ib=candidates[c.b].inverse_mass(),sum=ia+ib;
        const double correction=std::min(settings.max_position_correction,settings.position_correction*std::max(0.0,c.penetration-settings.penetration_slop));
        if(c.a!=no_body)candidates[c.a].position=candidates[c.a].position-c.normal*(correction*ia/sum);
        candidates[c.b].position=candidates[c.b].position+c.normal*(correction*ib/sum);
    }
    for(const auto& body:candidates)body.validate();
    std::copy(candidates.begin(),candidates.end(),bodies_.begin());stats.contacts=contacts.size();stats.velocity_iterations=contacts.empty()?0:settings.velocity_iterations;
    return stats;
}
}
