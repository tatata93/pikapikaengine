#include "pikapika/hydrostatics.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace pikapika;
namespace hydro=pikapika::hydrostatics;
namespace dyn=pikapika::dynamics;
namespace {
const hydro::Fluid water{1000,10,0};
Quaternion yaw(double angle){return {0,std::sin(angle/2),0,std::cos(angle/2)};}
Quaternion roll(double angle){return {0,0,std::sin(angle/2),std::cos(angle/2)};}
void vec(std::ostream& out,Vec3 v){out<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void provenance(std::ostream& out) {
    const auto raw=std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());std::tm utc{};
#ifdef _WIN32
    gmtime_s(&utc,&raw);
#else
    gmtime_r(&raw,&utc);
#endif
    out<<"\"timestamp_utc\":\""<<std::put_time(&utc,"%Y-%m-%dT%H:%M:%SZ")<<"\",\"code_revision_base\":\""<<PP_BUOY_REVISION
       <<"\",\"worktree_dirty_at_configure\":"<<(PP_BUOY_DIRTY?"true":"false")<<",\"hydrostatics_source_sha256\":\""<<PP_BUOY_SOURCE
       <<"\",\"hydrostatics_header_sha256\":\""<<PP_BUOY_HEADER<<"\",\"benchmark_source_sha256\":\""<<PP_BUOY_BENCH
       <<"\",\"dynamics_source_sha256\":\""<<PP_BUOY_DYNAMICS<<"\",\"compiler\":\""<<PP_BUOY_COMPILER<<"\",\"build_config\":\""<<PP_BUOY_CONFIG<<'"';
}
struct Fixture {std::string name;Mesh mesh;hydro::Fluid fluid{water};hydro::Pose pose;};
void fixtures() {
    std::vector<Fixture> list;
    const auto cube=make_box_mesh({2,2,2});
    const auto add=[&](const char* name,Mesh mesh,hydro::Pose pose = {},hydro::Fluid fluid = water){list.push_back({name,std::move(mesh),fluid,pose});};
    hydro::Pose p;p.transform.position={0,2,0};add("dry_cube",cube,p);
    add("half_cube",cube);p.transform.position={0,-2,0};add("full_cube",cube,p);
    auto f=water;f.water_level=.4;add("waterline_cube",cube,{},f);
    p={};p.transform.position={12345,54321,-23456};f=water;f.water_level=54321;add("translated_cube",cube,p,f);
    p={};p.transform.scale={2,4,6};p.transform.rotation=yaw(.73);add("scaled_yawed_box",make_box_mesh(),p);
    p={};p.transform.rotation=roll(3.141592653589793/2);add("rolled_box",make_box_mesh({2,4,6}),p);
    const double a=.37,b=.21;p={};p.transform.rotation={std::sin(a/2)*std::cos(b/2),std::cos(a/2)*std::sin(b/2),std::sin(a/2)*std::sin(b/2),std::cos(a/2)*std::cos(b/2)};add("tilted_cube",cube,p);
    p={};p.center_of_mass=Vec3{1,2,3};add("offset_center_of_mass",cube,p);
    auto deformed=cube;deformed.positions[6]={1.4,1.7,1.2};p={};p.transform.position={2,-.4,-1};p.transform.rotation=yaw(.6);p.center_of_mass=Vec3{1,0,2};f=water;f.water_level=.23;add("deformed_clipped_box",deformed,p,f);
    Mesh tetra;tetra.positions={{0,0,0},{2,0,0},{0,2,0},{0,0,2}};tetra.triangles={{0,2,1},{0,1,3},{0,3,2},{1,2,3}};f=water;f.water_level=1;add("partial_tetrahedron",tetra,{},f);
    auto joined=cube;for(auto point:cube.positions)joined.positions.push_back(point+Vec3{4,0,0});for(auto face:cube.triangles){for(auto& index:face)index+=8;joined.triangles.push_back(face);}add("two_disjoint_shells",joined);
    std::cout<<std::setprecision(17)<<'{';provenance(std::cout);std::cout<<",\"fixtures\":[";
    for(std::size_t index=0;index<list.size();++index) {
        if(index)std::cout<<',';const auto& entry=list[index];const hydro::Hull hull(entry.mesh);const auto r=hydro::forces(hull,entry.fluid,entry.pose);const auto& t=entry.pose.transform;
        std::cout<<"{\"name\":\""<<entry.name<<"\",\"mesh\":{\"version\":1,\"positions\":[";
        for(std::size_t i=0;i<entry.mesh.positions.size();++i){if(i)std::cout<<',';vec(std::cout,entry.mesh.positions[i]);}std::cout<<"],\"triangles\":[";
        for(std::size_t i=0;i<entry.mesh.triangles.size();++i){if(i)std::cout<<',';const auto tri=entry.mesh.triangles[i];std::cout<<'['<<tri[0]<<','<<tri[1]<<','<<tri[2]<<']';}
        std::cout<<"]},\"options\":{\"density\":"<<entry.fluid.density<<",\"gravity\":"<<entry.fluid.gravity<<",\"waterLevel\":"<<entry.fluid.water_level<<",\"position\":";vec(std::cout,t.position);
        std::cout<<",\"scale\":";vec(std::cout,t.scale);std::cout<<",\"orientation\":["<<t.rotation.x<<','<<t.rotation.y<<','<<t.rotation.z<<','<<t.rotation.w<<"],\"centerOfMass\":";
        vec(std::cout,entry.pose.center_of_mass.value_or(t.position));std::cout<<"},\"result\":{\"force\":";vec(std::cout,r.force);std::cout<<",\"torque\":";vec(std::cout,r.torque);
        std::cout<<",\"wetArea\":"<<r.wet_area<<",\"submergedVolume\":"<<r.submerged_volume<<",\"centerOfBuoyancy\":";
        if(r.center_of_buoyancy)vec(std::cout,*r.center_of_buoyancy);else std::cout<<"null";
        std::cout<<",\"totalVolume\":"<<r.total_volume<<",\"shells\":"<<r.shells<<"}}";
    }
    std::cout<<"]}\n";
}
dyn::World body_world(double y,double mass,Vec3 inertia,double angle=0) {
    dyn::World world;world.gravity={0,-10,0};auto body=dyn::make_sphere(1,.25,mass,{0,y,0});body.inertia_diagonal=inertia;body.orientation=roll(angle);world.add_body(body);return world;
}
dyn::World floating(double y) {return body_world(y,16000,{16000*20./12,16000*32./12,16000*20./12});}
dyn::World ballasted(double angle) {return body_world(-4,32000,{24000,48000,40000},angle);}
struct Measurement {double max_relative_energy{},final_relative_energy{},work_balance_error{},max_speed{},final_y{},final_vy{},final_angle{},final_omega{},max_cpu_ms{};};
Measurement trajectory(const hydro::Hull& hull,const char* name,dyn::World world,unsigned rate,double duration,bool ballast,std::ostream* csv) {
    const Vec3 origin=ballast?Vec3{0,.5,0}:Vec3{};const double dt=1./rate;
    const auto potential=[&](const dyn::RigidBody& b){return ballast?160000*(1-std::cos(2*std::atan2(b.orientation.z,b.orientation.w))):.5*160000*b.position.y*b.position.y;};
    const double kinetic0=world.find_body(1)->kinetic_energy(),energy0=kinetic0+potential(*world.find_body(1));double work=0;Measurement measurement;
    for(unsigned i=0;i<unsigned(std::lround(duration*rate));++i) {
        const auto before=*world.find_body(1);const auto start=std::chrono::steady_clock::now();
        const auto result=hydro::step_isolated_buoyant_body(world,1,hull,dt,water,origin);const auto& after=*world.find_body(1);
        const double cpu=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();measurement.max_cpu_ms=std::max(measurement.max_cpu_ms,cpu);
        if(result.dynamics.contacts)throw std::runtime_error("unexpected contacts in isolated buoyancy benchmark");
        const auto average_v=(before.velocity+after.velocity)*.5,average_omega=(before.angular_velocity()+after.angular_velocity())*.5;
        work+=(result.midpoint_load.force+world.gravity*after.mass).dot(average_v)*dt+result.midpoint_load.torque.dot(average_omega)*dt;
        const double energy=after.kinetic_energy()+potential(after),relative=(energy-energy0)/(energy0>0?energy0:1);
        measurement.max_relative_energy=std::max(measurement.max_relative_energy,std::abs(relative));measurement.final_relative_energy=relative;
        measurement.work_balance_error=std::max(measurement.work_balance_error,std::abs(after.kinetic_energy()-kinetic0-work));measurement.max_speed=std::max(measurement.max_speed,after.velocity.length());
        const double angle=2*std::atan2(after.orientation.z,after.orientation.w);
        if(csv)*csv<<name<<','<<i<<','<<(i+1)*dt<<','<<after.position.y<<','<<after.velocity.y<<','<<angle<<','<<after.angular_velocity().z<<','<<result.midpoint_load.force.y<<','<<result.midpoint_load.torque.z<<','<<result.midpoint_load.submerged_volume<<','<<energy<<','<<relative<<','<<work<<','<<cpu<<'\n';
        measurement.final_y=after.position.y;measurement.final_vy=after.velocity.y;measurement.final_angle=angle;measurement.final_omega=after.angular_velocity().z;
    }
    return measurement;
}
void print_measurement(std::ostream& out,const Measurement& m) {
    out<<"{\"max_relative_energy_error\":"<<m.max_relative_energy<<",\"final_relative_energy_error\":"<<m.final_relative_energy
       <<",\"kinetic_minus_discrete_work_max_J\":"<<m.work_balance_error<<",\"max_speed_m_s\":"<<m.max_speed
       <<",\"final_y_m\":"<<m.final_y<<",\"final_vy_m_s\":"<<m.final_vy<<",\"final_roll_rad\":"<<m.final_angle
       <<",\"final_omega_z_rad_s\":"<<m.final_omega<<",\"cpu_coupled_step_max_ms\":"<<m.max_cpu_ms<<'}';
}
}
int main(int argc,char** argv) {
    try {
        bool fixture_mode=false;std::string csv_path;
        for(int i=1;i<argc;++i) {const std::string option=argv[i];if(option=="--fixtures")fixture_mode=true;else if(option=="--csv"&&i+1<argc)csv_path=argv[++i];
            else if(option=="--help"){std::cout<<"pikapika-buoyancy [--csv trace.csv] | --fixtures\nTwo-load midpoint, isolated no-contact hull; no drag/added mass/waves/rendering.\n";return 0;}
            else throw std::runtime_error("usage: pikapika-buoyancy [--csv path] | --fixtures");}
        if(fixture_mode){if(!csv_path.empty())throw std::runtime_error("--fixtures cannot be combined with --csv");fixtures();return 0;}
        std::ofstream csv;if(!csv_path.empty()){csv.open(csv_path);if(!csv)throw std::runtime_error("cannot create buoyancy trace CSV");csv<<std::setprecision(17)<<"case,tick,time_s,y_m,vy_m_s,roll_rad,omega_z_rad_s,buoyancy_N,torque_z_Nm,submerged_volume_m3,mechanical_energy_J,relative_energy_error,discrete_work_J,cpu_coupled_step_ms\n";}
        const hydro::Hull hull(make_box_mesh({4,2,4}));
        const auto equilibrium=trajectory(hull,"equilibrium",floating(0),120,10,false,csv.is_open()?&csv:nullptr);
        double heave_errors[3]{};
        for(unsigned i=0;i<3;++i){const auto r=trajectory(hull,"heave_convergence",floating(.1),30U<<i,2,false,nullptr);const double frequency=std::sqrt(10.);heave_errors[i]=std::hypot(r.final_y-.1*std::cos(2*frequency),(r.final_vy+.1*frequency*std::sin(2*frequency))/frequency);}
        const auto long120=trajectory(hull,"heave_120_100s",floating(.1),120,100,false,csv.is_open()?&csv:nullptr);
        const auto long240=trajectory(hull,"heave_240_100s",floating(.1),240,100,false,csv.is_open()?&csv:nullptr);
        const auto rolled=trajectory(hull,"ballasted_roll_120_10s",ballasted(.15),120,10,true,csv.is_open()?&csv:nullptr);
        if(csv.is_open()){csv.flush();if(!csv)throw std::runtime_error("buoyancy trace CSV write failed");}
        std::cout<<std::setprecision(17)<<'{';provenance(std::cout);
        std::cout<<",\"method\":\"two-load explicit midpoint;isolated one-body no-contact\",\"density_kg_m3\":1000,\"gravity_m_s2\":10,\"water_level_m\":0"
            <<",\"displacement_box_m\":[4,2,4],\"collision_sphere_proxy_radius_m\":0.25,\"contacts\":0,\"drag_enabled\":false,\"added_mass_enabled\":false,\"equilibrium\":";print_measurement(std::cout,equilibrium);
        std::cout<<",\"heave_error_30_60_120\":["<<heave_errors[0]<<','<<heave_errors[1]<<','<<heave_errors[2]<<"],\"heave_error_ratio_30_60\":"<<heave_errors[0]/heave_errors[1]<<",\"heave_120_100s\":";print_measurement(std::cout,long120);
        std::cout<<",\"heave_240_100s\":";print_measurement(std::cout,long240);std::cout<<",\"ballasted_roll_120_10s\":";print_measurement(std::cout,rolled);
        std::cout<<",\"presentation_60fps_verified\":false,\"limits\":\"prescribed horizontal still fluid;no fluid reaction,added mass,drag,waves,contact geometry equivalence or full fluid-body energy conservation\"}\n";return 0;
    }catch(const std::exception& error){std::cerr<<"pikapika-buoyancy: "<<error.what()<<'\n';return 1;}
}
