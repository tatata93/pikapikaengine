#include "pikapika/hydrostatics.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace pikapika::hydrostatics {
namespace {
void require(bool ok,const char* detail) {if(!ok)throw std::runtime_error(detail);}
bool finite(Vec3 v) {return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
bool bounded(Vec3 v) {return finite(v)&&std::abs(v.x)<=1e6&&std::abs(v.y)<=1e6&&std::abs(v.z)<=1e6;}
void fluid_valid(const Fluid& f) {
    require(std::isfinite(f.density)&&f.density>0&&std::isfinite(f.gravity)&&f.gravity>0,"fluid density and gravity must be finite positive SI values");
    require(std::isfinite(f.water_level)&&std::abs(f.water_level)<=1e6,"water level outside finite +/-1000000 metre range");
}
struct Sum {
    double value{},correction{};
    void add(double x) {const double adjusted=x-correction,next=value+adjusted;correction=(next-value)-adjusted;value=next;}
};
Vec3 rotate(Quaternion q,Vec3 p) {
    const Vec3 xyz{q.x,q.y,q.z};const auto uv=xyz.cross(p),uuv=xyz.cross(uv);
    return p+uv*(2*q.w)+uuv*2;
}
double component(Vec3 v,unsigned axis) {return axis==0?v.x:axis==1?v.y:v.z;}
std::vector<Vec3> wet_polygon(const std::array<Vec3,3>& points,double level) {
    std::vector<Vec3> result;result.reserve(4);
    for(std::size_t i=0;i<points.size();++i) {
        const auto a=points[i],b=points[(i+1)%points.size()];const bool inside_a=a.y<=level,inside_b=b.y<=level;
        if(inside_a)result.push_back(a);
        if(inside_a!=inside_b) {
            const double t=(level-a.y)/(b.y-a.y);result.push_back({a.x+t*(b.x-a.x),level,a.z+t*(b.z-a.z)});
        }
    }
    return result;
}
Pose body_pose(const dynamics::RigidBody& body,Vec3 origin,Vec3 scale) {
    require(bounded(origin),"hull origin offset outside numeric range");
    Pose pose;pose.transform.position=body.position+rotate(body.orientation,origin);pose.transform.rotation=body.orientation;
    pose.transform.scale=scale;pose.center_of_mass=body.position;return pose;
}
void gravity_matches(const dynamics::World& world,const Fluid& fluid) {
    fluid_valid(fluid);const double tolerance=1e-12*std::max(1.,fluid.gravity);
    require(finite(world.gravity)&&std::abs(world.gravity.x)<=tolerance&&std::abs(world.gravity.z)<=tolerance&&
        std::abs(world.gravity.y+fluid.gravity)<=tolerance,"buoyancy coupling requires matching world gravity along -Y");
}
void add_load(dynamics::RigidBody& body,const Result& load) {
    auto candidate=body;candidate.force=candidate.force+load.force;candidate.torque=candidate.torque+load.torque;
    candidate.validate();body=candidate;
}
}
Hull::Hull(Mesh mesh):mesh_(std::move(mesh)) {
    mesh_.validate();
    struct Edge {int orientation{};std::size_t count{};std::array<std::size_t,2> faces{};};
    std::unordered_map<std::uint64_t,Edge> edges;edges.reserve(mesh_.triangles.size()*3);
    std::vector<std::vector<std::size_t>> adjacency(mesh_.triangles.size());
    for(std::size_t face=0;face<mesh_.triangles.size();++face) {
        const auto triangle=mesh_.triangles[face];
        for(unsigned e=0;e<3;++e) {
            const auto a=triangle[e],b=triangle[(e+1)%3];const auto lo=std::min(a,b),hi=std::max(a,b);
            auto& edge=edges[(std::uint64_t(lo)<<32)|hi];
            require(edge.count<2,"displacement mesh has a non-manifold edge");
            edge.faces[edge.count++]=face;edge.orientation+=a<b?1:-1;
        }
    }
    for(const auto& entry:edges) {
        const auto& edge=entry.second;require(edge.count==2,"displacement mesh must be closed; boundary edge found");
        require(edge.orientation==0,"displacement mesh has inconsistent triangle winding");
        adjacency[edge.faces[0]].push_back(edge.faces[1]);adjacency[edge.faces[1]].push_back(edge.faces[0]);
    }
    std::vector<bool> visited(mesh_.triangles.size(),false);Sum total;
    for(std::size_t start=0;start<visited.size();++start) {
        if(visited[start])continue;
        ++shells_;Sum part;const auto origin=mesh_.positions[mesh_.triangles[start][0]];
        std::vector<std::size_t> pending{start};visited[start]=true;
        while(!pending.empty()) {
            const auto face=pending.back();pending.pop_back();const auto triangle=mesh_.triangles[face];
            const auto a=mesh_.positions[triangle[0]]-origin,b=mesh_.positions[triangle[1]]-origin,c=mesh_.positions[triangle[2]]-origin;
            part.add(a.dot(b.cross(c))/6);
            for(const auto neighbor:adjacency[face])if(!visited[neighbor]){visited[neighbor]=true;pending.push_back(neighbor);}
        }
        require(std::isfinite(part.value)&&part.value>0,"every displacement shell must have positive signed volume and outward winding");total.add(part.value);
    }
    require(std::isfinite(total.value)&&total.value>0,"invalid displacement shell volume");volume_=total.value;
}
double pressure(double depth,const Fluid& fluid) {
    fluid_valid(fluid);require(std::isfinite(depth),"fluid depth must be finite metres");
    const double result=fluid.density*fluid.gravity*std::max(0.,depth);require(std::isfinite(result),"fluid pressure exceeds finite numeric range");return result;
}
Result forces(const Hull& hull,const Fluid& fluid,const Pose& pose) {
    fluid_valid(fluid);const auto& t=pose.transform;const auto& q=t.rotation;const auto& s=t.scale;
    require(bounded(t.position),"fluid mesh position outside finite world range");
    require(bounded(s)&&s.x>0&&s.y>0&&s.z>0,"fluid scale must be finite positive components within 1000000");
    const double q_length=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);
    require(std::isfinite(q_length)&&std::abs(q_length-1)<=1e-10,"fluid orientation must be a unit quaternion");
    const auto center=pose.center_of_mass.value_or(t.position);require(bounded(center),"fluid center of mass outside finite world range");
    std::vector<Vec3> positions;positions.reserve(hull.mesh().positions.size());
    for(const auto& p:hull.mesh().positions) {
        const auto world=t.position+rotate(q,{p.x*s.x,p.y*s.y,p.z*s.z});
        require(bounded(world),"transformed fluid mesh exceeds finite world range");positions.push_back(world);
    }
    const Vec3 reference{t.position.x,fluid.water_level,t.position.z};
    std::array<Sum,3> force{},torque{},first_moment{};Sum wet_area,volume;
    for(const auto& face:hull.mesh().triangles) {
        const auto polygon=wet_polygon({positions[face[0]],positions[face[1]],positions[face[2]]},fluid.water_level);
        for(std::size_t i=1;i+1<polygon.size();++i) {
            const std::array<Vec3,3> points={polygon[0],polygon[i],polygon[i+1]};
            const auto area_vector=(points[1]-points[0]).cross(points[2]-points[0])*0.5;
            const double area=area_vector.length();if(area==0)continue;
            const std::array<Vec3,3> relative={points[0]-reference,points[1]-reference,points[2]-reference};
            const std::array<double,3> h={relative[0].y,relative[1].y,relative[2].y};const double sum_h=h[0]+h[1]+h[2];
            const std::array<double,3> p={-fluid.density*fluid.gravity*h[0],-fluid.density*fluid.gravity*h[1],-fluid.density*fluid.gravity*h[2]};
            const double sum_p=p[0]+p[1]+p[2];Vec3 pressure_moment;
            for(unsigned vertex=0;vertex<3;++vertex)pressure_moment=pressure_moment+(points[vertex]-center)*((sum_p+p[vertex])/12);
            const auto moment=pressure_moment.cross(area_vector),triangle_force=area_vector*(-sum_p/3);
            for(unsigned axis=0;axis<3;++axis){force[axis].add(component(triangle_force,axis));torque[axis].add(-component(moment,axis));}
            wet_area.add(area);volume.add(area_vector.y*sum_h/3);
            for(unsigned axis:{0U,2U}) {
                const double sum=component(relative[0],axis)+component(relative[1],axis)+component(relative[2],axis);
                const double diagonal=component(relative[0],axis)*h[0]+component(relative[1],axis)*h[1]+component(relative[2],axis)*h[2];
                first_moment[axis].add(area_vector.y*(sum*sum_h+diagonal)/12);
            }
            first_moment[1].add(area_vector.y*(sum_h*sum_h+h[0]*h[0]+h[1]*h[1]+h[2]*h[2])/24);
        }
    }
    Result result;result.force={force[0].value,force[1].value,force[2].value};result.torque={torque[0].value,torque[1].value,torque[2].value};
    result.wet_area=wet_area.value;result.submerged_volume=result.force.y/(fluid.density*fluid.gravity);
    result.total_volume=hull.volume()*s.x*s.y*s.z;result.shells=hull.shells();
    if(result.submerged_volume>0) {
        require(volume.value>0,"submerged moment volume is ill-conditioned");
        result.center_of_buoyancy=reference+Vec3{first_moment[0].value,first_moment[1].value,first_moment[2].value}*(1/volume.value);
    }
    require(finite(result.force)&&finite(result.torque)&&std::isfinite(result.wet_area)&&std::isfinite(result.submerged_volume)&&
        std::isfinite(result.total_volume)&&(!result.center_of_buoyancy||finite(*result.center_of_buoyancy)),"fluid calculation exceeds finite numeric range");
    require(result.submerged_volume>=0,"negative displaced volume; invalid shell or numerical conditioning");return result;
}
Result apply_buoyancy(dynamics::World& world,std::uint64_t id,const Hull& hull,const Fluid& fluid,Vec3 origin,Vec3 scale) {
    gravity_matches(world,fluid);auto* body=world.find_body(id);require(body&&!body->is_static,"buoyancy coupling requires a dynamic body ID");body->validate();
    const auto load=forces(hull,fluid,body_pose(*body,origin,scale));add_load(*body,load);return load;
}
CoupledStep step_isolated_buoyant_body(dynamics::World& world,std::uint64_t id,const Hull& hull,double dt,const Fluid& fluid,Vec3 origin,Vec3 scale,const dynamics::SolverSettings& settings) {
    require(world.bodies().size()==1&&world.planes().empty(),"midpoint buoyancy reference requires one body and no contact planes");
    require(std::isfinite(dt)&&dt>0&&dt<=0.1,"invalid buoyancy coupling timestep");
    auto prediction=world;apply_buoyancy(prediction,id,hull,fluid,origin,scale);prediction.step(dt*0.5,settings);
    const auto* predicted=prediction.find_body(id);const auto midpoint=forces(hull,fluid,body_pose(*predicted,origin,scale));
    auto candidate=world;auto* body=candidate.find_body(id);add_load(*body,midpoint);const auto stats=candidate.step(dt,settings);
    *world.find_body(id)=*candidate.find_body(id);return {midpoint,stats};
}
}
