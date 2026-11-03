#include "pikapika/simulation_api.h"
#include "pikapika/core.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {
unsigned passed{};
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void success(int32_t code){if(code!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
void near(double a,double b,double tolerance=1e-8){check(std::abs(a-b)<=tolerance,"C ABI analytic tolerance");}
void test(const char* name,const std::function<void()>& call){success(pp_sim_reset());call();++passed;std::cout<<"PASS "<<name<<'\n';}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> result(){std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};std::copy_n(pp_sim_output_f64_ptr(),pp_sim_output_count(),values.begin());return values;}
void body(double id,double y,double mass=16000) {
    auto* in=pp_sim_input_f64_ptr();std::fill_n(in,PP_SIM_BODY_INPUT_COUNT,0.);in[0]=id;in[2]=mass;in[3]=.25;
    in[4]=mass*20/12;in[5]=mass*32/12;in[6]=mass*20/12;in[8]=y;in[13]=1;in[27]=.6;
}
unsigned selection_input(std::initializer_list<std::pair<double,double>> disks) {
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,21+10*disks.size(),0.);
    p[10]=p[11]=1;p[13]=10;p[14]=1e6;p[15]=128;p[16]=128;p[17]=512;p[18]=16384;p[19]=1;p[20]=double(disks.size());
    unsigned o=21;for(const auto& [id,z]:disks){p[o]=id;p[o+4]=z;p[o+7]=-1;p[o+9]=10;o+=10;}return o;
}
unsigned spot_input() {
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,51,0.);p[0]=2;p[2]=p[3]=1;p[4]=550e-9;p[10]=-1;p[11]=10;p[13]=10;
    p[14]=64;p[15]=1e-7;p[16]=128;p[17]=1024;p[18]=1024;p[19]=1000000;
    for(unsigned j=0;j<2;++j){const unsigned o=21+15*j;p[o]=p[o+1]=j==0?-1:1;p[o+4]=p[o+5]=-1;p[o+10]=p[o+11]=2;p[o+13]=10;p[o+14]=j==0?1:3;}return 51;
}
unsigned polarized_input(bool rational=false) {
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,59,0.);p[10]=p[11]=rational?1:2;p[13]=100;p[14]=p[15]=rational?25:1;p[16]=550e-9;p[17]=64;p[18]=1e-7;p[19]=128;p[20]=2;
    p[rational?22:21]=rational?-1:1;p[24]=1;p[28]=128;p[29]=1000000;
    if(rational){const double steps[28]={0,0,0,1,3,0,-4,0,1000,0,39,39,0,100,0,24,0,-6,-543,300,-76,0,1000,0,39,39,0,100};std::copy_n(steps,28,p+31);}
    else{p[4]=p[5]=-1;const double steps[28]={0,0,0,0,0,0,-1,0,10,1,1.5,1.5,0,100,0,0,0,.25,0,0,1,0,10,1,1,1,0,100};std::copy_n(steps,28,p+31);}return 59;
}
unsigned packet_input() {
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,93,0.);p[0]=p[1]=2;p[2]=p[3]=1;p[4]=550e-9;p[7]=3;p[10]=-1;p[11]=10;p[13]=100;
    p[14]=64;p[15]=1e-7;p[16]=128;p[17]=p[18]=1024;p[19]=1000000;p[20]=128;p[21]=1000000;
    const double steps[28]={0,0,0,1,0,0,-1,0,10,1,1.5,1.5,0,100,0,0,0,2,0,0,-1,0,10,1,1,1,0,100};std::copy_n(steps,28,p+23);
    for(unsigned j=0;j<2;++j){const unsigned o=51+21*j;p[o+10]=p[o+11]=1;p[o+13]=100;p[o+14]=j==0?.25:.75;p[o+17]=p[o+14];p[o+18]=1;}return 93;
}
void gravity(pp_sim_handle world,double y=-10){auto* in=pp_sim_input_f64_ptr();in[0]=0;in[1]=y;in[2]=0;success(pp_sim_world_set_gravity(world,3));}
void mesh_input(const pikapika::Mesh& mesh) {
    auto* f=pp_sim_input_f64_ptr();auto* indices=pp_sim_input_u32_ptr();
    for(std::size_t i=0;i<mesh.positions.size();++i){f[i*3]=mesh.positions[i].x;f[i*3+1]=mesh.positions[i].y;f[i*3+2]=mesh.positions[i].z;}
    for(std::size_t i=0;i<mesh.triangles.size();++i)std::copy_n(mesh.triangles[i].begin(),3,indices+i*3);
}
pp_sim_handle hull_box(pikapika::Vec3 size={4,2,4}) {
    const auto mesh=pikapika::make_box_mesh(size);mesh_input(mesh);const auto handle=pp_sim_hull_create(uint32_t(mesh.positions.size()),uint32_t(mesh.triangles.size()));
    check(handle!=0,pp_sim_error_ptr());return handle;
}
void hydro_input(double density=1000,double g=10,double y=0) {
    auto* in=pp_sim_input_f64_ptr();std::fill_n(in,PP_SIM_HYDRO_INPUT_COUNT,0.);in[0]=density;in[1]=g;in[4]=y;in[9]=1;in[10]=in[11]=in[12]=1;in[14]=y;
}
void buoy_input(double origin_y=0){auto* in=pp_sim_input_f64_ptr();std::fill_n(in,PP_SIM_BUOYANCY_INPUT_COUNT,0.);in[0]=1000;in[1]=10;in[4]=origin_y;in[6]=in[7]=in[8]=1;}
void ccd_input(double max_events=32) {
    const double settings[16]={1e-7,1e-6,1e-6,1e-7,1e-10,max_events,65,100000,1000000,32768,4096,64,16,8192,0,.5};
    std::copy_n(settings,16,pp_sim_input_f64_ptr());
}
void supported_input(double max_segments=4096){
    const double values[33]={1./240,1e-10,1e-7,5e-8,1e-9,1e-6,1e-5,1e-5,1e-10,16384,max_segments,512,1000000,4000000,
        32,64,16,128,1e-10,1e-10,1e-10,.5,.5,48,1000000,128,100000,1e24,1e-7,1e-8,1e-10,1e-10,0};
    std::copy_n(values,33,pp_sim_input_f64_ptr());
}
pp_sim_handle ccd_corridor() {
    const auto world=pp_sim_world_create();gravity(world,-9.8);
    body(1,0,1);auto* p=pp_sim_input_f64_ptr();p[3]=.5;p[14]=100;p[21]=4;p[25]=1;p[26]=1;p[27]=0;success(pp_sim_world_body_add(world,28));
    double plane[8]={100,1,0,0,-1.5,1,0,0};std::copy_n(plane,8,p);success(pp_sim_world_plane_add(world,8));
    plane[0]=101;plane[1]=-1;std::copy_n(plane,8,p);success(pp_sim_world_plane_add(world,8));return world;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> heave(double dt) {
    const auto hull=hull_box(),world=pp_sim_world_create();check(world!=0,pp_sim_error_ptr());gravity(world);body(1,.1);success(pp_sim_world_body_add(world,28));
    buoy_input();for(unsigned i=0;i<unsigned(std::lround(2/dt));++i)success(pp_sim_world_buoyancy_step(world,hull,1,dt,1,9));
    success(pp_sim_world_body_get(world,1));const auto values=result();success(pp_sim_world_destroy(world));success(pp_sim_hull_destroy(hull));return values;
}
}
int main() {
    try {
        test("version exchange capacities and output spans are explicit",[]{
            check(pp_sim_api_version()==1&&pp_sim_input_f64_capacity()==49152&&pp_sim_input_u32_capacity()==98304&&pp_sim_output_f64_capacity()==64,"ABI capacities");
            check(pp_sim_input_f64_ptr()!=nullptr&&pp_sim_input_u32_ptr()!=nullptr&&pp_sim_output_f64_ptr()!=nullptr,"module owned buffers");
        });
        test("stale wrong-type and double-destroy handles are rejected",[]{
            const auto world=pp_sim_world_create(),hull=hull_box();success(pp_sim_world_destroy(world));
            check(pp_sim_world_destroy(world)==PP_SIM_INVALID_HANDLE,"double destroy");const auto next=pp_sim_world_create();check(next!=world,"generation must advance");
            check(pp_sim_world_info(world)==PP_SIM_INVALID_HANDLE&&pp_sim_world_info(hull)==PP_SIM_INVALID_HANDLE,"stale/type mismatch");
            success(pp_sim_hull_destroy(hull));check(pp_sim_hull_destroy(hull)==PP_SIM_INVALID_HANDLE,"double hull destroy");success(pp_sim_world_info(next));
        });
        test("global reset invalidates live resources while world reset preserves other hulls",[]{
            const auto hull=hull_box(),world=pp_sim_world_create();body(1,0);success(pp_sim_world_body_add(world,28));success(pp_sim_world_reset(world));
            success(pp_sim_world_info(world));near(pp_sim_output_f64_ptr()[3],0);hydro_input();success(pp_sim_hydro_query(hull,16));
            success(pp_sim_reset());check(pp_sim_world_info(world)==PP_SIM_INVALID_HANDLE,"global world invalidation");check(pp_sim_hydro_query(hull,16)==PP_SIM_INVALID_HANDLE,"global hull invalidation");
        });
        test("static cube query matches independent Archimedes centroid and eccentric torque",[]{
            const auto hull=hull_box({2,2,2});hydro_input();auto* in=pp_sim_input_f64_ptr();in[13]=1;in[14]=2;in[15]=3;
            success(pp_sim_hydro_query(hull,16));check(pp_sim_output_count()==14,"hydro output count");const auto v=result();near(v[1],40000);near(v[3],120000);near(v[5],-40000);near(v[6],12);near(v[7],4);near(v[8],8);near(v[9],1);near(v[10],1);near(v[12],-.5);
            hydro_input(1000,10,2);success(pp_sim_hydro_query(hull,16));const auto dry=result();near(dry[7],0);near(dry[10],0);near(dry[11],0);near(dry[12],0);near(dry[13],0);
        });
        test("indexed hull replacement is atomic and failed shell remains reusable",[]{
            const auto hull=hull_box({2,2,2});hydro_input();success(pp_sim_hydro_query(hull,16));const auto before=result();
            auto mesh=pikapika::make_box_mesh({2,2,2});mesh.triangles.pop_back();mesh_input(mesh);check(pp_sim_hull_replace(hull,8,11)==PP_SIM_CORE_REJECTED,"open shell rejection");
            check(pp_sim_output_count()==14&&result()==before,"failed replacement output unchanged");hydro_input();success(pp_sim_hydro_query(hull,16));check(result()==before,"original hull unchanged");
            mesh_input(pikapika::make_box_mesh({4,2,4}));success(pp_sim_hull_replace(hull,8,12));hydro_input();success(pp_sim_hydro_query(hull,16));near(pp_sim_output_f64_ptr()[7],16);
        });
        test("count nonfinite ID and material errors preserve output and body",[]{
            const auto world=pp_sim_world_create();body(9007199254740991.,2);success(pp_sim_world_body_add(world,28));success(pp_sim_world_body_get(world,9007199254740991.));const auto before=result();
            check(pp_sim_world_body_add(world,27)==PP_SIM_INVALID_ARGUMENT&&result()==before,"exact input count failure");
            body(9007199254740992.,0);check(pp_sim_world_body_set(world,28)==PP_SIM_INVALID_ARGUMENT,"unsafe ID");
            body(9007199254740991.,0);pp_sim_input_f64_ptr()[2]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_world_body_set(world,28)==PP_SIM_CORE_REJECTED,"nonfinite body rejection");
            check(pp_sim_error_length()>0&&pp_sim_error_length()<256&&std::strlen(pp_sim_error_ptr())==pp_sim_error_length(),"bounded null-terminated diagnostic");
            success(pp_sim_world_body_get(world,9007199254740991.));check(result()==before,"failed updates preserve body");check(pp_sim_error_length()==0,"success clears diagnostic");
        });
        test("generic world integrates freefall and held force through common C++",[]{
            const auto world=pp_sim_world_create();gravity(world);body(1,100,2);pp_sim_input_f64_ptr()[20]=6;success(pp_sim_world_body_add(world,28));
            success(pp_sim_world_step(world,.1,1));success(pp_sim_world_body_get(world,1));auto v=result();near(v[7],.015);near(v[14],.3);near(v[8],99.95);near(v[15],-1);near(v[20],0);near(v[32],.1);near(v[33],1);
            success(pp_sim_world_step(world,.1,9));success(pp_sim_world_body_get(world,1));v=result();near(v[8],95,1e-10);near(v[15],-10,1e-10);near(v[32],1);near(v[33],10);
        });
        test("generic contacts return actual sphere-plane solver impulses",[]{
            const auto world=pp_sim_world_create();gravity(world,0);body(1,.25,2);auto* in=pp_sim_input_f64_ptr();in[15]=-2;in[26]=.5;success(pp_sim_world_body_add(world,28));
            const double plane[8]={2,0,1,0,0,.5,0,0};std::copy_n(plane,8,in);success(pp_sim_world_plane_add(world,8));success(pp_sim_world_step(world,.01,1));const auto stats=result();near(stats[14],1);check(stats[17]>0,"contact impulse");
            success(pp_sim_world_body_get(world,1));near(pp_sim_output_f64_ptr()[15],1);
        });
        test("generic batch failure rolls back earlier ticks and consumed loads",[]{
            const auto world=pp_sim_world_create();gravity(world,0);body(1,0,1);auto* in=pp_sim_input_f64_ptr();in[4]=in[5]=in[6]=1;in[25]=100;
            success(pp_sim_world_body_add(world,28));success(pp_sim_world_body_get(world,1));const auto before=result();
            check(pp_sim_world_step(world,.1,3)==PP_SIM_CORE_REJECTED,"second/third tick angular increment rejection");
            check(pp_sim_output_count()==34&&result()==before,"failed batch output unchanged");success(pp_sim_world_body_get(world,1));check(result()==before,"all prior candidate ticks rolled back");
            body(1,0,1);success(pp_sim_world_body_set(world,28));success(pp_sim_world_step(world,.01,1));
        });
        test("isolated buoyancy equilibrium and exact time counters survive reset",[]{
            const auto hull=hull_box(),world=pp_sim_world_create();gravity(world);body(1,0);success(pp_sim_world_body_add(world,28));buoy_input();
            for(unsigned i=0;i<120;++i)success(pp_sim_world_buoyancy_step(world,hull,1,1./120,1,9));const auto step=result();near(step[14],0);near(step[20],1);near(step[21],120);
            success(pp_sim_world_body_get(world,1));near(pp_sim_output_f64_ptr()[8],0,1e-12);near(pp_sim_output_f64_ptr()[15],0,1e-12);success(pp_sim_world_reset(world));success(pp_sim_world_info(world));near(pp_sim_output_f64_ptr()[5],0);near(pp_sim_output_f64_ptr()[6],0);
        });
        test("coupled heave retains analytic second-order convergence across C ABI",[]{
            double error[3]{};for(unsigned i=0;i<3;++i){const auto v=heave(1./(30U<<i));const double w=std::sqrt(10.);error[i]=std::hypot(v[8]-.1*std::cos(2*w),(v[15]+.1*w*std::sin(2*w))/w);}
            check(error[0]/error[1]>3.5&&error[1]/error[2]>3.5,"ABI heave second-order convergence");
        });
        test("failed buoyancy inputs retain state and permit correction",[]{
            const auto hull=hull_box(),world=pp_sim_world_create();gravity(world);body(1,.1);success(pp_sim_world_body_add(world,28));success(pp_sim_world_body_get(world,1));const auto before=result();
            buoy_input();pp_sim_input_f64_ptr()[7]=-1;check(pp_sim_world_buoyancy_step(world,hull,1,1./120,1,9)==PP_SIM_CORE_REJECTED,"invalid scale");
            success(pp_sim_world_body_get(world,1));check(result()==before,"failed coupled state unchanged");buoy_input();success(pp_sim_world_buoyancy_step(world,hull,1,1./120,1,9));
            check(pp_sim_world_buoyancy_step(world,hull,1,1./120,33,9)==PP_SIM_INVALID_ARGUMENT,"bounded step batch");
        });
        test("resource and mesh count budgets fail without handle/state corruption",[]{
            std::vector<pp_sim_handle> handles;for(unsigned i=0;i<PP_SIM_MAX_WORLDS;++i){const auto h=pp_sim_world_create();check(h!=0,"world capacity");handles.push_back(h);}
            check(pp_sim_world_create()==0&&pp_sim_last_status()==PP_SIM_BUDGET_EXCEEDED,"world budget");success(pp_sim_world_destroy(handles.back()));handles.pop_back();check(pp_sim_world_create()!=0,"reuse freed capacity");
            check(pp_sim_hull_create(PP_SIM_MAX_HULL_VERTICES+1,1)==0&&pp_sim_last_status()==PP_SIM_BUDGET_EXCEEDED,"mesh count preflight");
        });
        test("world body plane and hull object count boundaries are enforced",[]{
            const auto world=pp_sim_world_create();for(unsigned i=0;i<PP_SIM_MAX_BODIES;++i){body(i+1,3);success(pp_sim_world_body_add(world,28));}
            body(PP_SIM_MAX_BODIES+1,3);check(pp_sim_world_body_add(world,28)==PP_SIM_BUDGET_EXCEEDED,"body count budget");
            auto* in=pp_sim_input_f64_ptr();for(unsigned i=0;i<PP_SIM_MAX_PLANES;++i){const double p[8]={1000.+i,0,1,0,-double(i),0,.6,0};std::copy_n(p,8,in);success(pp_sim_world_plane_add(world,8));}
            check(pp_sim_world_plane_add(world,8)==PP_SIM_BUDGET_EXCEEDED,"plane count budget");
            std::vector<pp_sim_handle> handles;for(unsigned i=0;i<PP_SIM_MAX_HULLS;++i)handles.push_back(hull_box());
            check(pp_sim_hull_create(8,12)==0&&pp_sim_last_status()==PP_SIM_BUDGET_EXCEEDED,"hull object count budget");
            success(pp_sim_hull_destroy(handles.back()));handles.pop_back();check(hull_box()!=0,"hull capacity is reusable");
        });
        test("total live hull vertex quota includes boundary-sized exchange uploads",[]{
            pikapika::Mesh combined;const auto unit=pikapika::make_box_mesh();
            for(uint32_t i=0;i<2048;++i){const auto base=uint32_t(combined.positions.size());for(auto p:unit.positions)combined.positions.push_back(p+pikapika::Vec3{double(i)*2,0,0});
                for(auto face:unit.triangles){for(auto& index:face)index+=base;combined.triangles.push_back(face);}}
            check(combined.positions.size()==PP_SIM_MAX_HULL_VERTICES,"upload spans exact input capacity");mesh_input(combined);
            std::vector<pp_sim_handle> handles;for(unsigned i=0;i<4;++i){const auto h=pp_sim_hull_create(uint32_t(combined.positions.size()),uint32_t(combined.triangles.size()));check(h!=0,pp_sim_error_ptr());handles.push_back(h);}
            mesh_input(unit);check(pp_sim_hull_create(8,12)==0&&pp_sim_last_status()==PP_SIM_BUDGET_EXCEEDED,"total vertex quota");
            success(pp_sim_hull_destroy(handles.back()));check(pp_sim_hull_create(8,12)!=0,"destroy releases geometry quota");
        });
        test("repeated create destroy cycles reject every prior generation",[]{
            pp_sim_handle previous=0;for(unsigned i=0;i<512;++i){const auto world=pp_sim_world_create(),hull=hull_box({2,2,2});check(world!=0&&world!=previous,"new generation");
                if(previous)check(pp_sim_world_info(previous)==PP_SIM_INVALID_HANDLE,"old generation stays stale");success(pp_sim_world_destroy(world));success(pp_sim_hull_destroy(hull));previous=world;}
        });
        test("stateless continuous sphere queries expose seconds and stable field mapping",[]{
            auto* in=pp_sim_input_f64_ptr();const double query[15]={-3,0,0,1000,0,0,.5,0,0,0,0,0,0,.5,1./120};
            std::copy_n(query,15,in);success(pp_sim_sphere_sphere_toi(15));const auto hit=result();
            check(pp_sim_output_count()==13&&hit[0]==double(PP_SIM_TOI_IMPACT)&&hit[1]==double(PP_SIM_TOI_APPROACHING)&&hit[2]==1,"TOI result tags");
            near(hit[3],.002,1e-15);near(hit[4],1,1e-15);near(hit[10],2);near(hit[11],-1000);near(hit[12],-1000);
            check(hit[7]==1&&hit[8]==0,"TOI normal and horizon flags");
            check(pp_sim_sphere_sphere_toi(14)==PP_SIM_INVALID_ARGUMENT&&result()==hit&&pp_sim_output_count()==13,"query count failure retains output");
            in[6]=0;check(pp_sim_sphere_sphere_toi(15)==PP_SIM_CORE_REJECTED&&result()==hit,"query domain failure retains output");
            in[6]=.5;in[14]=.001;success(pp_sim_sphere_sphere_toi(15));check(result()[0]==double(PP_SIM_TOI_NONE)&&result()[2]==0&&result()[3]==0,"absent time is explicit");
        });
        test("moving plane continuous query leaves existing world state unchanged",[]{
            const auto world=pp_sim_world_create();body(42,5);success(pp_sim_world_body_add(world,28));success(pp_sim_world_body_get(world,42));const auto before=result();
            const double query[15]={-3,0,0,1000,0,0,.5,-1,0,0,0,100,0,0,.01};std::copy_n(query,15,pp_sim_input_f64_ptr());
            success(pp_sim_sphere_plane_toi(15));const auto hit=result();check(hit[0]==double(PP_SIM_TOI_IMPACT)&&hit[2]==1,"moving-plane impact");
            near(hit[3],2.5/900,1e-15);near(hit[4],-1);near(hit[10],2.5);near(hit[11],-900);
            success(pp_sim_world_body_get(world,42));check(result()==before,"stateless query must not advance world");
        });
        test("accelerated plane ABI preserves existence certificates and output on invalid calls",[]{
            const double query[19]={0,3,0,0,0,0,0,-4,0,1,0,1,0,0,2,1e-7,32768,4096,64};
            std::copy_n(query,19,pp_sim_input_f64_ptr());success(pp_sim_accelerated_plane(19));const auto hit=result();
            check(pp_sim_output_count()==21&&hit[0]==double(PP_SIM_ACCEL_ENTRY_BRACKET)&&hit[1]==double(PP_SIM_ACCEL_REASON_NONE),"entry kind and reason");
            check(hit[2]==1&&hit[4]==1&&hit[5]>0&&hit[7]==1&&hit[8]>0,"positive initial and closed safe prefix");
            check(hit[10]==1&&hit[11]<=1&&hit[12]>=1&&hit[12]-hit[11]<=1e-7,"known entry enclosed");
            check(hit[13]==1&&hit[14]==hit[12]&&hit[15]==1&&hit[17]<0,"negative witness certificate");
            check(hit[18]<=32768&&hit[19]>0,"bounded exploration statistics");
            check(pp_sim_accelerated_plane(18)==PP_SIM_INVALID_ARGUMENT&&result()==hit,"count failure retains proof output");
            pp_sim_input_f64_ptr()[16]=32769;check(pp_sim_accelerated_plane(19)==PP_SIM_INVALID_ARGUMENT&&result()==hit,"ABI evaluation ceiling");
            pp_sim_input_f64_ptr()[16]=1;success(pp_sim_accelerated_plane(19));const auto limited=result();
            check(limited[0]==double(PP_SIM_ACCEL_UNRESOLVED)&&limited[1]==double(PP_SIM_ACCEL_EVALUATION_BUDGET)&&limited[10]==0,"budget unresolved, never none");
        });
        test("accelerated sphere query finds an intermediate entry and never mutates a world",[]{
            const auto world=pp_sim_world_create();body(42,5);success(pp_sim_world_body_add(world,28));success(pp_sim_world_body_get(world,42));const auto before=result();
            const double query[25]={0,3,0,0,0,0,0,-4,0,.5,0,0,0,0,0,0,0,0,0,.5,2,1e-7,32768,4096,64};
            std::copy_n(query,25,pp_sim_input_f64_ptr());success(pp_sim_accelerated_spheres(25));const auto hit=result();
            check(hit[0]==double(PP_SIM_ACCEL_ENTRY_BRACKET)&&hit[11]<=1&&hit[12]>=1,"accelerated pair known entry");
            check(hit[5]>0&&hit[17]<0,"pair sign evidence");
            pp_sim_input_f64_ptr()[9]=0;check(pp_sim_accelerated_spheres(25)==PP_SIM_CORE_REJECTED&&result()==hit,"invalid sphere preserves output");
            success(pp_sim_world_body_get(world,42));check(result()==before,"query does not change poses loads time or tick");
        });
        test("accelerated initial boundary and zero horizon use explicit proof flags",[]{
            double query[19]={0,1,0,0,0,0,0,-4,0,1,0,1,0,0,2,1e-7,32768,4096,64};
            std::copy_n(query,19,pp_sim_input_f64_ptr());success(pp_sim_accelerated_plane(19));auto r=result();
            check(r[0]==double(PP_SIM_ACCEL_UNRESOLVED)&&r[1]==double(PP_SIM_ACCEL_INITIAL_BOUNDARY)&&r[2]==0&&r[10]==0,"initial boundary not invented impact");
            query[1]=3;query[14]=0;std::copy_n(query,19,pp_sim_input_f64_ptr());success(pp_sim_accelerated_plane(19));r=result();
            check(r[0]==double(PP_SIM_ACCEL_NONE)&&r[2]==1&&r[3]==0&&r[10]==0&&r[13]==0,"zero horizon and missing payload mapping");
        });
        test("optical ABI exposes normal-flux Fresnel power and retains output on rejection",[]{
            const double q[9]={0,-1,0,0,1,0,1,1.5,550e-9};std::copy_n(q,9,pp_sim_input_f64_ptr());
            success(pp_sim_dielectric_interface(9));const auto r=result();
            check(pp_sim_output_count()==31&&r[0]==double(PP_SIM_OPTICS_TRANSMISSION)&&r[1]==double(PP_SIM_OPTICS_RESOLVED),"optical tags");
            check(r[11]==1&&r[15]==1&&r[23]==1,"optional optical fields");
            near(r[9],1);near(r[13],-1);near(r[16],.04);near(r[17],.96);near(r[18],.04);near(r[19],.96);near(r[25],550e-9,1e-20);
            check(r[26]>0&&r[29]<0,"original-input interval certificates");
            check(pp_sim_dielectric_interface(8)==PP_SIM_INVALID_ARGUMENT&&result()==r,"optics count failure retains span");
            pp_sim_input_f64_ptr()[6]=0;check(pp_sim_dielectric_interface(9)==PP_SIM_CORE_REJECTED&&result()==r,"invalid optical medium retains output");
            pp_sim_input_f64_ptr()[6]=1;pp_sim_input_f64_ptr()[1]=1;
            check(pp_sim_dielectric_interface(9)==PP_SIM_CORE_REJECTED&&result()==r,"wrong incident side rejected");
        });
        test("optical total reflection and critical uncertainty have distinct optional fields",[]{
            double q[9]={4,-3,0,0,1,0,1.5,1,550e-9};std::copy_n(q,9,pp_sim_input_f64_ptr());success(pp_sim_dielectric_interface(9));auto r=result();
            check(r[0]==double(PP_SIM_OPTICS_TIR)&&r[27]<0&&r[11]==0&&r[23]==0&&r[15]==1,"TIR has power and no propagating transmitted ray");
            near(r[16],1);near(r[17],0);near(r[18],1);near(r[19],0);
            q[0]=3;q[1]=-4;q[6]=5;q[7]=3;std::copy_n(q,9,pp_sim_input_f64_ptr());success(pp_sim_dielectric_interface(9));r=result();
            check(r[0]==double(PP_SIM_OPTICS_UNCERTAIN)&&r[1]==double(PP_SIM_OPTICS_CRITICAL_ANGLE),"critical case unresolved");
            check(r[26]<=0&&r[27]>=0&&r[11]==0&&r[15]==0&&r[23]==0,"uncertain does not invent direction or power");
        });
        test("optical surface ABI distinguishes parameter distance and cap hemisphere",[]{
            double q[19]={0,0,0,-3,0,0,2,0,10,0,0,0,0,0,-1,0,1,1e-8,128};
            std::copy_n(q,19,pp_sim_input_f64_ptr());success(pp_sim_optical_geometry(19));auto r=result();
            check(pp_sim_output_count()==52&&r[0]==0&&r[2]==1&&r[3]==1,"disk hit mapping");
            check(r[18]<=1.5&&r[19]>=1.5&&r[20]<=3&&r[21]>=3&&r[51]==1,"parameter physical distance front face");
            near(r[44],0);near(r[50],-1);
            q[0]=2;q[3]=3;q[6]=-1;q[14]=1;q[15]=1;q[16]=.5;
            std::copy_n(q,19,pp_sim_input_f64_ptr());success(pp_sim_optical_geometry(19));r=result();
            check(r[0]==0&&r[3]==2&&r[4]==2&&r[12]==4&&r[16]==1,"near opposite hemisphere rejected before second root");
            check(r[18]<=3&&r[19]>=3,"vertex cap far root");
            check(pp_sim_optical_geometry(18)==PP_SIM_INVALID_ARGUMENT&&result()==r,"geometry count failure retains output");
            q[0]=1;q[16]=0;std::copy_n(q,19,pp_sim_input_f64_ptr());
            check(pp_sim_optical_geometry(19)==PP_SIM_INVALID_ARGUMENT&&result()==r,"sphere reserved axis is not ignored");
        });
        test("polarized interface ABI retains TIR relative phase and absent critical branches",[]{
            double q[16]={.8,-.6,0,0,1,0,1.5,1,550e-9,0,0,-1,1,0,1,0};
            std::copy_n(q,16,pp_sim_input_f64_ptr());success(pp_sim_polarized_interface(16));auto r=result();
            check(pp_sim_output_count()==57&&r[0]==0&&r[1]==1&&r[3]==1&&r[4]==0,"polarization TIR mapping");
            near(r[23],1);near(r[25],53./75);near(r[26],16*std::sqrt(11.)/75);check(r[49]<0&&r[53]==0,"TIR certificates");
            q[0]=3;q[1]=-4;q[6]=5;q[7]=3;std::copy_n(q,16,pp_sim_input_f64_ptr());success(pp_sim_polarized_interface(16));r=result();
            check(r[0]==1&&r[1]==2&&r[2]==2&&r[3]==0&&r[4]==0,"critical no stale branch payload");
            check(pp_sim_polarized_interface(15)==PP_SIM_INVALID_ARGUMENT&&result()==r,"polarization count failure retains output");
        });
        test("continuous World ABI commits multi impact held loads once and returns event records",[]{
            const auto world=ccd_corridor();ccd_input();success(pp_sim_world_step_continuous(world,.06,16));const auto r=result();
            check(pp_sim_output_count()==21&&r[0]==1&&r[1]==0&&r[18]==3&&r[20]==1,"W1 successful tick and three events");
            near(r[2],.06);near(r[19],.06);
            success(pp_sim_world_ccd_event(world,0));const auto e=result();
            check(pp_sim_output_count()==8&&e[0]<=.01&&e[1]<=.01&&e[2]>=.01&&e[3]<=1e-6&&e[7]==1,"first bounded impact event");
            check(pp_sim_world_ccd_event(world,3)==PP_SIM_INVALID_ARGUMENT&&result()==e,"invalid event retains output");
            success(pp_sim_world_body_get(world,1));const auto b=result();near(b[7],0,4e-6);near(b[8],-.01044,1e-12);near(b[14],-100,1e-10);
            near(b[19],.06,1e-12);for(unsigned i=20;i<26;++i)near(b[i],0);
        });
        test("continuous failure data retains world clocks loads and candidate diagnostics",[]{
            const auto world=ccd_corridor();success(pp_sim_world_body_get(world,1));const auto before=result();
            ccd_input(1);success(pp_sim_world_step_continuous(world,.06,16));auto r=result();
            check(r[0]==0&&r[1]==4&&r[2]==0&&r[18]==1&&r[19]==0&&r[20]==0,"event budget rollback data");
            success(pp_sim_world_body_get(world,1));check(result()==before,"failed W1 preserves complete body and clock");
            success(pp_sim_world_ccd_event(world,0));const auto diagnostic=result();check(diagnostic[0]>0,"failed attempt candidate event retained");
            ccd_input();pp_sim_input_f64_ptr()[9]=32769;
            check(pp_sim_world_step_continuous(world,.06,16)==PP_SIM_INVALID_ARGUMENT&&result()==diagnostic,"ABI budget rejection retains output and report");
            success(pp_sim_world_ccd_event(world,0));check(result()==diagnostic,"bad ABI call does not replace last record");
            success(pp_sim_world_reset(world));check(pp_sim_world_ccd_event(world,0)==PP_SIM_INVALID_ARGUMENT,"reset clears diagnostic events");
        });
        test("dispersion ABI units bands and explicit failure",[]{
            double q[27]={0,0x1p-20,0x1p-20,1e-12,1,1e6,128,1.5,0x1p-44,0x1p-88};
            std::copy_n(q,27,pp_sim_input_f64_ptr());success(pp_sim_dispersion(27));auto r=result();
            check(pp_sim_output_count()==14&&r[0]==0&&r[2]==1&&r[13]==1,"dispersion mapping");
            check(r[7]<=401./256&&r[8]>=401./256&&r[9]<=-147456&&r[10]>=-147456&&r[11]<=437./256&&r[12]>=437./256,"Cauchy rational bounds");
            q[0]=1;q[7]=q[8]=q[9]=0;q[10]=1;q[11]=2.25;q[12]=0x1p-42;
            std::copy_n(q,27,pp_sim_input_f64_ptr());success(pp_sim_dispersion(27));r=result();
            check(r[0]==0&&r[4]==1&&r[7]<=2&&r[8]>=2&&r[11]<=2.5&&r[12]>=2.5,"Sellmeier group bounds");
            q[1]=q[2]=0x1p-21;std::copy_n(q,27,pp_sim_input_f64_ptr());success(pp_sim_dispersion(27));r=result();
            check(r[0]==2&&r[1]==1&&r[2]==0,"resonance is explicit unresolved data");
            check(pp_sim_dispersion(26)==PP_SIM_INVALID_ARGUMENT&&result()==r,"invalid count retains output");
            q[25]=1;std::copy_n(q,27,pp_sim_input_f64_ptr());check(pp_sim_dispersion(27)==PP_SIM_INVALID_ARGUMENT&&result()==r,"unused term rejected");
        });
        test("bounded geometry ABI retains families and incident-side normal",[]{
            double q[25]={0,0,0,0,0,-3.1,-2.9,0,0,0,0,1,2,0,10,0,0,0,0,0,-1,0,1,1e6,128};
            std::copy_n(q,25,pp_sim_input_f64_ptr());success(pp_sim_bounded_geometry(25));auto r=result();
            check(pp_sim_output_count()==41&&r[0]==0&&r[2]==1&&r[3]==1&&r[40]==1,"bounded disk family mapping");
            check(r[18]<=1.45&&r[19]>=3.1&&r[26]==0&&r[27]==0,"family root and exact plane position");
            check(r[38]<=-1&&r[39]>=-1,"incident-side normal bounds");
            check(pp_sim_bounded_geometry(24)==PP_SIM_INVALID_ARGUMENT&&result()==r,"bad bounded geometry count retains output");
            q[11]=-1;q[12]=1;std::copy_n(q,25,pp_sim_input_f64_ptr());success(pp_sim_bounded_geometry(25));r=result();
            check(r[0]==2&&r[1]==1&&r[2]==0,"zero-containing direction family unresolved");
        });
        test("bounded interface ABI carries independent index bounds and critical uncertainty",[]{
            double q[19]={0,0,0,0,1,2,0,0,0,0,-1,-1,1,1,1.4,1.6,550e-9,1e6,128};
            std::copy_n(q,19,pp_sim_input_f64_ptr());success(pp_sim_bounded_interface(19));auto r=result();
            check(pp_sim_output_count()==59&&r[0]==0&&r[8]==1&&r[9]==1&&r[10]==1,"bounded interface flags");
            check(r[38]<=1./36&&r[39]>=9./169&&r[36]<=1&&r[37]>=1,"index-family power and transmitted Z");
            q[0]=q[1]=4;q[4]=q[5]=3;q[12]=1.2;q[13]=1.3;q[14]=q[15]=1;
            std::copy_n(q,19,pp_sim_input_f64_ptr());success(pp_sim_bounded_interface(19));r=result();
            check(r[0]==2&&r[1]==13&&r[8]==0&&r[9]==0&&r[10]==0,"mixed critical family has no outgoing success");
            check(pp_sim_bounded_interface(18)==PP_SIM_INVALID_ARGUMENT&&result()==r,"bad bounded interface count retains output");
        });
        test("support ABI returns immutable query records without advancing or consuming loads",[]{
            success(pp_sim_reset());const auto w=pp_sim_world_create();check(w!=0,"support World create");
            double gravity[3]={0,-10,0};std::copy_n(gravity,3,pp_sim_input_f64_ptr());success(pp_sim_world_set_gravity(w,3));
            double plane[8]={100,0,1,0,0,0,0,0};std::copy_n(plane,8,pp_sim_input_f64_ptr());success(pp_sim_world_plane_add(w,8));
            double body[28]={1,0,2,.5,.2,.2,.2,0,.5,0,0,0,0,1,0,0,0,0,0,.6,0,2,0,1,2,3,0,.6};
            std::copy_n(body,28,pp_sim_input_f64_ptr());success(pp_sim_world_body_add(w,28));success(pp_sim_world_body_get(w,1));const auto before=result();
            double settings[10]={1e-8,1e-9,1e-8,1e-7,1e-8,1e-10,1e24,20000,128,100000};
            std::copy_n(settings,10,pp_sim_input_f64_ptr());success(pp_sim_world_support(w,10));const auto r=result();
            check(pp_sim_output_count()==21&&r[0]==1&&r[1]==0&&r[4]==1&&r[15]==1&&r[16]==1&&r[19]==0&&r[20]==0,"support successful read-only summary");
            success(pp_sim_world_support_constraint(w,0));auto c=result();check(c[0]==100&&c[1]==1&&c[2]==0&&c[3]==1,"guarded rest constraint");near(c[20],18);
            success(pp_sim_world_support_body(w,0));const auto b=result();near(b[2],18);near(b[14],0);for(unsigned j=4;j<=6;++j)near(b[j],0);
            check(pp_sim_world_support(w,9)==PP_SIM_INVALID_ARGUMENT&&result()==b,"invalid count retains previous output and record");
            success(pp_sim_world_support_constraint(w,0));check(result()==c,"invalid ABI attempt retains support record");
            success(pp_sim_world_body_get(w,1));check(result()==before,"support preserves all body state loads and clock");
            body[15]=-1e-20;std::copy_n(body,28,pp_sim_input_f64_ptr());success(pp_sim_world_body_set(w,28));
            std::copy_n(settings,10,pp_sim_input_f64_ptr());success(pp_sim_world_support(w,10));const auto fail=result();check(fail[0]==0&&fail[1]==4,"tiny closing velocity requires impact data");
            check(pp_sim_world_support_constraint(w,0)==PP_SIM_INVALID_ARGUMENT,"failed empty attempt replaces previous record");
            success(pp_sim_world_reset(w));check(pp_sim_world_support_body(w,0)==PP_SIM_INVALID_ARGUMENT,"reset clears support diagnostics");
        });
        test("optical route ABI carries three surfaces and bounded totals with immutable records",[]{
            double q[63]{};q[4]=q[5]=-1;q[10]=q[11]=1;q[13]=10;q[14]=q[15]=1;q[16]=550e-9;q[17]=64;q[18]=1e6;q[19]=128;q[20]=3;
            for(unsigned j=0;j<3;++j){const auto o=21+14*j;q[o+3]=j==0?0:j==1?.25:1.25;q[o+6]=-1;q[o+8]=10;q[o+9]=1;q[o+10]=q[o+11]=j==0?1.5:1;q[o+13]=10;}
            std::copy_n(q,63,pp_sim_input_f64_ptr());success(pp_sim_optical_route(63));auto r=result();
            check(pp_sim_output_count()==31&&r[0]==0&&r[1]==3&&r[2]==3&&r[3]==3&&r[4]==1,"completed route mapping");
            check(r[22]<=2.25&&r[23]>=2.25&&r[24]<=2.375&&r[25]>=2.375&&r[26]<=.9216&&r[27]>=.9216,"route total enclosures");
            check(r[12]<=1.25&&r[13]>=1.25,"final origin Z");
            success(pp_sim_optical_route_segment(0));const auto s=result();check(pp_sim_output_count()==64&&s[0]==1&&s[1]==1&&s[4]==1&&s[7]==1&&s[8]==1&&s[9]==1,"segment optional flags");
            check(s[24]==1&&s[25]==1&&s[26]==1.5&&s[27]==1.5&&s[36]<=1&&s[37]>=1,"incident and other media, distance");
            check(pp_sim_optical_route_segment(3)==PP_SIM_INVALID_ARGUMENT&&result()==s,"bad segment preserves prior output");
            check(pp_sim_optical_route(62)==PP_SIM_INVALID_ARGUMENT&&result()==s,"bad route count preserves prior output");
            success(pp_sim_optical_route_segment(0));check(result()==s,"invalid ABI attempt retains route record");
            q[17]=2;std::copy_n(q,63,pp_sim_input_f64_ptr());success(pp_sim_optical_route(63));r=result();check(r[0]==6&&r[1]==0&&r[3]==0&&r[4]==0,"preflight budget has no final completion");
            check(pp_sim_optical_route_segment(0)==PP_SIM_INVALID_ARGUMENT,"valid failed route replaces old record");
        });
        test("route ABI leaves exact source surface zero hit visible and reset clears its record",[]{
            double q[35]{};q[10]=q[11]=1;q[13]=10;q[14]=q[15]=1;q[16]=550e-9;q[17]=64;q[18]=1e6;q[19]=128;q[20]=1;
            q[27]=-1;q[29]=10;q[30]=1;q[31]=q[32]=1;q[34]=10;
            std::copy_n(q,35,pp_sim_input_f64_ptr());success(pp_sim_optical_route(35));const auto r=result();check(r[0]==0&&r[22]==0&&r[23]==0,"explicit zero-domain source hit is not skipped");
            success(pp_sim_optical_route_segment(0));const auto s=result();check(s[34]==0&&s[35]==0,"zero t is retained");
            success(pp_sim_reset());check(pp_sim_optical_route_segment(0)==PP_SIM_INVALID_ARGUMENT,"global reset clears route record");
        });
        test("supported ABI advances the complete tick and consumes held loads once",[]{
            const auto w=pp_sim_world_create();gravity(w);body(1,.5,1);auto* p=pp_sim_input_f64_ptr();p[3]=.5;p[20]=2;p[25]=1;p[27]=0;success(pp_sim_world_body_add(w,28));
            const double plane[8]={100,0,1,0,0,0,0,0};std::copy_n(plane,8,p);success(pp_sim_world_plane_add(w,8));
            supported_input();success(pp_sim_world_step_supported(w,.1,33));const auto r=result();check(pp_sim_output_count()==32&&r[0]==1&&r[1]==0&&r[2]==.1&&r[30]==.1&&r[31]==1,"W2 summary and clock");near(r[17],1,1e-7);
            success(pp_sim_world_body_get(w,1));const auto b=result();near(b[7],.01);near(b[8],.5);near(b[14],.2);near(b[15],0);near(b[19],.1);near(b[20],0);near(b[25],0);
        });
        test("supported ABI rollback retains body loads and clock and can retry",[]{
            const auto w=pp_sim_world_create();gravity(w);body(1,.5,1);auto* p=pp_sim_input_f64_ptr();p[3]=.5;p[20]=2;p[27]=0;success(pp_sim_world_body_add(w,28));
            const double plane[8]={100,0,1,0,0,0,0,0};std::copy_n(plane,8,p);success(pp_sim_world_plane_add(w,8));success(pp_sim_world_body_get(w,1));const auto before=result();
            supported_input(1);success(pp_sim_world_step_supported(w,.1,33));const auto fail=result();check(fail[0]==0&&fail[1]==6&&fail[2]==0&&fail[30]==0&&fail[31]==0,"W2 model failure is data");
            success(pp_sim_world_body_get(w,1));check(result()==before,"W2 rollback all state loads and clock");supported_input();success(pp_sim_world_step_supported(w,.1,33));check(result()[0]==1,"W2 same world retry");
        });
        test("supported ABI event snapshots survive other queries and invalid calls",[]{
            const auto w=pp_sim_world_create();gravity(w,0);auto* p=pp_sim_input_f64_ptr();for(unsigned id=1;id<=2;++id){body(id,0,1);p[3]=.5;p[7]=id==1?-2:2;p[14]=id==1?1000:-1000;p[26]=1;p[27]=0;success(pp_sim_world_body_add(w,28));}
            supported_input();success(pp_sim_world_step_supported(w,1./120,33));const auto r=result();check(r[0]==1&&r[27]>0,"W2 fast impact snapshot");success(pp_sim_world_supported_event(w,0));const auto e=result();check(pp_sim_output_count()==12&&e[0]==0&&e[2]==1&&e[3]==2,"W2 event mapping");near(e[1],.0015,2e-9);
            supported_input();p[0]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_world_step_supported(w,.01,33)==PP_SIM_INVALID_ARGUMENT&&result()==e,"W2 bad finite input preserves output");
            success(pp_sim_world_body_get(w,1));success(pp_sim_world_supported_event(w,0));check(result()==e,"W2 event immutable after query");check(pp_sim_world_supported_event(w,999)==PP_SIM_INVALID_ARGUMENT&&result()==e,"W2 bad getter retains output");
            success(pp_sim_world_reset(w));check(pp_sim_world_supported_event(w,0)==PP_SIM_INVALID_ARGUMENT,"W2 reset clears snapshot");
        });
        test("optical selection ABI certifies a unique surface with full bounds and canonical diagnostic IDs",[]{
            const auto n=selection_input({{20,2},{10,4}});auto* p=pp_sim_input_f64_ptr();p[10]=p[11]=2;
            const std::vector<double> input(p,p+n);success(pp_sim_optical_selection(n));const auto r=result();
            check(pp_sim_output_count()==31&&r[0]==0&&r[1]==1&&r[2]==20&&r[3]==2&&r[4]==2,"selection summary");
            check(r[8]<=1&&r[9]>=1&&r[10]<=2&&r[11]>=2&&r[16]<=2&&r[17]>=2,"selection parameter/distance/position");
            check(std::equal(input.begin(),input.end(),p),"selection mutated input exchange");
            success(pp_sim_optical_selection_surface(0,0));const auto d=result();check(pp_sim_output_count()==46&&d[0]==10&&d[1]==1&&d[2]==0&&d[4]==1&&d[5]==0,"canonical first diagnostic");
            success(pp_sim_optical_selection_surface(1,0));check(result()[0]==20,"canonical second diagnostic");
            success(pp_sim_optical_selection_surface(0,1));check(result()[4]==0,"absent prefix represented explicitly");
        });
        test("optical selection ABI keeps aperture uncertainty budgets and duplicate IDs as model failure data",[]{
            auto n=selection_input({{1,1},{2,2}});auto* p=pp_sim_input_f64_ptr();p[0]=.9;p[1]=1.1;p[30]=1;
            success(pp_sim_optical_selection(n));auto r=result();check(r[0]==2&&r[1]==0&&r[2]==0&&r[8]==0,"mixed aperture cannot choose rear disk");
            n=selection_input({{1,1},{2,2}});p[17]=1;success(pp_sim_optical_selection(n));r=result();check(r[0]==4&&r[1]==0&&r[4]==1,"selection partial budget data");
            success(pp_sim_optical_selection_surface(1,0));check(result()[0]==2&&result()[1]==0&&result()[4]==0,"unqueried surface diagnostic");
            p[17]=512;success(pp_sim_optical_selection(n));check(result()[0]==0&&result()[2]==1,"selection budget reuse");
            n=selection_input({{7,1},{7,2}});success(pp_sim_optical_selection(n));check(result()[0]==3&&result()[1]==0,"duplicate IDs are invalid model data");
        });
        test("optical selection snapshots survive bad exchange and unrelated queries and reset explicitly",[]{
            auto n=selection_input({{9,2}});auto* p=pp_sim_input_f64_ptr();success(pp_sim_optical_selection(n));
            success(pp_sim_optical_selection_surface(0,0));const auto record=result();
            check(pp_sim_optical_selection(n-1)==PP_SIM_INVALID_ARGUMENT&&result()==record,"bad selection count retains output");
            p[0]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_optical_selection(n)==PP_SIM_INVALID_ARGUMENT&&result()==record,"selection NaN retains output");
            n=selection_input({{9,2}});p[29]=1;check(pp_sim_optical_selection(n)==PP_SIM_INVALID_ARGUMENT&&result()==record,"reserved selection radius retains output");
            p[29]=0;p[21]=9007199254740992.;check(pp_sim_optical_selection(n)==PP_SIM_INVALID_ARGUMENT&&result()==record,"selection exact ID domain");
            check(pp_sim_optical_selection_surface(0,2)==PP_SIM_INVALID_ARGUMENT&&result()==record,"bad selection part retains output");
            const auto world=pp_sim_world_create();check(world!=0,"unrelated world");success(pp_sim_world_info(world));success(pp_sim_optical_selection_surface(0,0));check(result()==record,"selection record survives unrelated output");
            success(pp_sim_reset());check(pp_sim_optical_selection_surface(0,0)==PP_SIM_INVALID_ARGUMENT,"reset clears selection snapshot");
        });
        test("spot ABI preserves independent weighted moments and nonunit sensor distance",[]{
            const auto n=spot_input();success(pp_sim_optical_spot(n));const auto r=result();check(pp_sim_output_count()==32&&r[0]==0&&r[1]==2&&r[3]==2&&r[12]==1&&r[13]==1,"spot completed summary");
            check(r[14]<=4&&r[15]>=4&&r[16]<=4&&r[17]>=4&&r[18]<=.5&&r[19]>=.5&&r[24]<=.75&&r[25]>=.75,"independent weighted moments");
            success(pp_sim_optical_spot_sample(1,0));check(pp_sim_output_count()==34&&result()[0]==1&&result()[1]==3&&result()[2]==1&&result()[11]==1,"route identity snapshot");
            success(pp_sim_optical_spot_sample(1,1));const auto g=result();check(pp_sim_output_count()==46&&g[3]==1&&g[23]<=.5&&g[24]>=.5&&g[25]<=1&&g[26]>=1,"sensor parameter physical distance");
        });
        test("spot ABI prohibits partial statistics and recovers on the same input",[]{
            const auto n=spot_input();auto* p=pp_sim_input_f64_ptr();p[18]=1;success(pp_sim_optical_spot(n));const auto r=result();check(r[0]==3&&r[2]==1&&r[12]==0&&r[13]==0,"partial budget cannot publish moments");
            success(pp_sim_optical_spot_sample(1,0));check(result()[2]==0&&result()[3]==0,"unevaluated sample retained");
            p[18]=1024;success(pp_sim_optical_spot(n));check(result()[0]==0&&result()[12]==1,"budget recovery");p[35]=0;success(pp_sim_optical_spot(n));check(result()[0]==2&&result()[12]==0,"invalid weight is model failure");
        });
        test("spot ABI atomic exchange snapshots reset and exact finite source difference",[]{
            const auto n=spot_input();auto* p=pp_sim_input_f64_ptr();success(pp_sim_optical_spot(n));success(pp_sim_optical_spot_sample(0,1));const auto g=result();
            check(pp_sim_optical_spot(n-1)==PP_SIM_INVALID_ARGUMENT&&result()==g,"bad count retains output");p[20]=1;check(pp_sim_optical_spot(n)==PP_SIM_INVALID_ARGUMENT&&result()==g,"reserved slot retains output");
            p[20]=0;p[2]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_optical_spot(n)==PP_SIM_INVALID_ARGUMENT&&result()==g,"NaN retains output");
            check(pp_sim_optical_spot_sample(999,0)==PP_SIM_INVALID_ARGUMENT&&result()==g,"bad sample retains output");check(pp_sim_optical_spot_sample(0,2)==PP_SIM_INVALID_ARGUMENT&&result()==g,"bad part retains output");
            const double launch[9]={0,524288,0,-1,0x1p-40,0,-.01,0,1e6};std::copy_n(launch,9,p);success(pp_sim_optical_launch_ray(9));const auto a=result();check(pp_sim_output_count()==14&&a[6]<=-524288&&a[7]>-524288,"finite source outward difference retains lost term");
            success(pp_sim_optical_spot_sample(0,1));check(result()==g,"unrelated launch retains sample record");success(pp_sim_reset());check(pp_sim_optical_spot_sample(0,0)==PP_SIM_INVALID_ARGUMENT,"reset clears spot snapshot");
        });
        test("polarized route ABI retains world coherency without a normal reflection sign error",[]{
            const auto n=polarized_input();auto* p=pp_sim_input_f64_ptr();p[27]=1;success(pp_sim_polarized_route(n));const auto a=result();
            check(pp_sim_output_count()==64&&a[0]==0&&a[2]==1&&a[3]==0&&a[4]==2&&a[9]==2&&a[10]==2&&a[17]==1&&a[55]==1,"polarized completion flags");
            check(a[32]<=576./625&&a[33]>=576./625&&a[42]<=288./625&&a[43]>=288./625,"normal circular tensor imaginary sign and power");
            success(pp_sim_polarized_route_initial());check(pp_sim_output_count()==40&&result()[0]==1&&result()[1]==1&&result()[30]<=.5&&result()[31]>=.5,"initial frame and source tensor");
            success(pp_sim_polarized_route_segment(0,0));check(pp_sim_output_count()==64&&result()[0]==1&&result()[1]==1,"unchanged geometry segment packet");
            success(pp_sim_polarized_route_segment(1,1));check(pp_sim_output_count()==35&&result()[0]==1&&result()[4]==1&&result()[6]==1,"normal power snapshot");
        });
        test("polarized route ABI preserves noncoplanar polarization rather than resetting to unpolarized",[]{
            const auto n=polarized_input(true);success(pp_sim_polarized_route(n));const auto a=result();
            check(a[0]==0&&a[17]==1&&a[32]<=42544./17294403&&a[33]>=42544./17294403,"independent noncoplanar rational power");
            check(!(a[32]<=1263376./466948881&&a[33]>=1263376./466948881),"wrong per-surface reset excluded");
            check(a[56]<=26&&a[57]>=26&&a[58]<=650&&a[59]>=650,"rational path distance and OPL");
        });
        test("polarized route failure keeps geometric evidence separate and never publishes stale tensor",[]{
            const auto n=polarized_input(true);auto* p=pp_sim_input_f64_ptr();success(pp_sim_polarized_route(n));p[29]=1;success(pp_sim_polarized_route(n));const auto a=result();check(a[0]==4&&a[17]==0&&a[32]==0&&a[34]==0,"budget has no completed tensor");
            p[29]=1000000;success(pp_sim_polarized_route(n));check(result()[0]==0,"budget recovery");p[25]=2;success(pp_sim_polarized_route(n));check(result()[0]==3&&result()[17]==0,"outside exact source cone rejected as model data");
            polarized_input(true);success(pp_sim_polarized_route(n));success(pp_sim_polarized_route_segment(0,1));const auto before=result();
            p[30]=1;check(pp_sim_polarized_route(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"reserved exchange retains snapshot");p[30]=0;p[24]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_polarized_route(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"NaN retains snapshot");
            check(pp_sim_polarized_route_segment(0,2)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad segment part retains output");check(pp_sim_polarized_route_segment(64,1)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad segment index retains output");
            const auto w=pp_sim_world_create();success(pp_sim_world_info(w));success(pp_sim_polarized_route_segment(0,1));check(result()==before,"unrelated query preserves record");success(pp_sim_reset());check(pp_sim_polarized_route_initial()==PP_SIM_INVALID_ARGUMENT,"reset clears record");
        });
        test("finite polarized packet ABI tallies explicit watts and retains per-packet geometry and phase",[]{
            const auto n=packet_input();success(pp_sim_polarized_packet(n));const auto a=result();
            check(pp_sim_output_count()==24&&a[0]==0&&a[1]==2&&a[2]==2&&a[3]==2&&a[7]==0&&a[15]==1,"packet final flags");
            check(a[16]<=1&&a[17]>=1&&a[18]<=1&&a[19]>=1&&a[20]<=576./625&&a[21]>=576./625,"packet watts tally");
            success(pp_sim_polarized_packet_record(0,0));check(pp_sim_output_count()==12&&result()[0]==0&&result()[1]==1&&result()[2]==.25&&result()[5]==.25&&result()[8]==1,"source watt metadata");
            success(pp_sim_polarized_packet_record(0,1));check(pp_sim_output_count()==64&&result()[17]==1&&result()[32]<=144./625&&result()[33]>=144./625,"full route snapshot");
            success(pp_sim_polarized_packet_record(0,2));check(pp_sim_output_count()==40&&result()[1]==1,"initial snapshot");
            success(pp_sim_polarized_packet_record(0,3));check(pp_sim_output_count()==41&&result()[0]==0&&result()[2]==1,"sensor geometry without fake interface");
            success(pp_sim_polarized_packet_segment(1,1,0));check(pp_sim_output_count()==64&&result()[1]==1,"packet geometry prefix");
            success(pp_sim_polarized_packet_segment(1,1,1));check(pp_sim_output_count()==35&&result()[6]==1,"packet coherency prefix");
        });
        test("finite packet unknown and not-examined prohibit final tally while retaining original watts",[]{
            const auto n=packet_input();auto* p=pp_sim_input_f64_ptr();p[18]=1;success(pp_sim_polarized_packet(n));const auto a=result();
            check(a[0]==3&&a[1]==2&&a[2]==1&&a[7]==1&&a[15]==0&&a[20]==0,"budget prohibits tally");
            success(pp_sim_polarized_packet_record(1,0));check(result()[1]==0&&result()[2]==.75&&result()[6]==0&&result()[8]==0,"unexamined source retained");
            p[18]=1024;success(pp_sim_polarized_packet(n));check(result()[0]==0&&result()[15]==1,"same packet recovery");
            p[11]=.1;p[51]=p[52]=.2;p[72]=p[73]=.2;success(pp_sim_polarized_packet(n));check(result()[0]==0&&result()[6]==2&&result()[15]==1&&result()[20]==0&&result()[21]==0,"certified sensor misses are zero arrival");
        });
        test("finite packet bad exchange and getters preserve prior snapshots and reset clears them",[]{
            const auto n=packet_input();success(pp_sim_polarized_packet(n));success(pp_sim_polarized_packet_record(0,1));const auto before=result();auto* p=pp_sim_input_f64_ptr();p[22]=1;
            check(pp_sim_polarized_packet(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"reserved exchange retains output");p[22]=0;p[51]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_polarized_packet(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"nonfinite retains output");
            check(pp_sim_polarized_packet_record(2,0)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad packet index retains output");check(pp_sim_polarized_packet_record(0,4)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad packet part retains output");
            check(pp_sim_polarized_packet_segment(0,64,1)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad segment retains output");
            polarized_input();success(pp_sim_polarized_route(59));success(pp_sim_polarized_packet_record(0,1));check(result()==before,"standalone optical query preserves packet record");
            success(pp_sim_reset());check(pp_sim_polarized_packet_record(0,0)==PP_SIM_INVALID_ARGUMENT,"reset clears packet record");
        });
        success(pp_sim_reset());std::cout<<passed<<" simulation C ABI test groups passed\n";return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';pp_sim_reset();return 1;}
}
