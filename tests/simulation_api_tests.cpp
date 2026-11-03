#include "pikapika/simulation_api.h"
#include "pikapika/core.hpp"
#include "pikapika/sphere_triangle.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstddef>
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
unsigned motion_input() {
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,59,0.);p[0]=2;p[1]=1;p[2]=2;p[3]=p[4]=1;p[6]=p[7]=128;p[8]=4096;
    const double data[49]={20,10,1,0,0,0,0,0,1,1,1,1,10,0,0,0,0,0,0,0,1,2,1,1,20,0,2,0,1,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,1,2,1,1,1};std::copy_n(data,49,p+10);return 59;
}
std::array<double,16> skin_matrix(double tx=0) {return {1,0,0,0,0,1,0,0,0,0,1,0,tx,0,0,1};}
void skin_transfer(const std::vector<double>&v){check(v.size()<=pp_sim_input_f64_capacity(),"Skin test transfer bound");std::copy(v.begin(),v.end(),pp_sim_input_f64_ptr());}
std::vector<double> derived_values(unsigned vertices=3,unsigned faces=1) {
    std::vector<double> a(PP_SIM_DERIVED_HEADER_COUNT+vertices*3,0);a[0]=vertices;a[1]=faces;a[2]=2048;a[3]=32768;a[4]=128;
    if(vertices>=3){a[8]=-0.0;a[11]=1;a[15]=1;}return a;
}
void derived_transfer(const std::vector<double>&a,unsigned faces=1){skin_transfer(a);for(unsigned i=0;i<faces;++i){auto*p=pp_sim_input_u32_ptr()+i*3;p[0]=0;p[1]=1;p[2]=2;}}
void retained_output(const std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>&before,unsigned count){const auto after=result();check(pp_sim_output_count()==count&&std::memcmp(before.data(),after.data(),sizeof(before))==0,"Derived failure changed output bits/count");}
std::array<double,PP_SIM_SPHERE_TRIANGLE_INPUT_COUNT> sphere_triangle_values() {
    return {1,1,1,.5,37,0,0,0,4,0,0,0,0,4,7,128,1024,1e-7,1e-8,1e-12,0,0,0,0};
}
void sphere_triangle_transfer(const std::array<double,PP_SIM_SPHERE_TRIANGLE_INPUT_COUNT>&a){std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> derived_batch_matches_single(unsigned kind,unsigned first,unsigned count) {
    constexpr std::array<unsigned,4> strides{3,3,18,26};const auto stride=strides[kind];
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> expected{};expected[0]=kind;expected[1]=first;expected[2]=count;expected[3]=stride;
    for(unsigned j=0;j<count;++j){success(pp_sim_derived_mesh_record(kind,first+j));check(pp_sim_output_count()==stride,"Legacy derived stride changed");std::copy_n(pp_sim_output_f64_ptr(),stride,expected.begin()+4+std::size_t(j)*stride);}
    success(pp_sim_derived_mesh_records(kind,first,count));const auto actual=result();
    check(pp_sim_output_count()==4+stride*count&&std::memcmp(actual.data(),expected.data(),sizeof(expected))==0,"Batch differs from exact legacy payload/header/count");return actual;
}
std::vector<double> skin_bind_values(unsigned bones=1) {
    std::vector<double> a{double(bones),128,65536,262144,1e10,1e-10,0,0};
    for(unsigned j=0;j<bones;++j){a.push_back(j+1);const auto m=skin_matrix();a.insert(a.end(),m.begin(),m.end());}return a;
}
std::vector<double> skin_deform_values(unsigned bones=1,unsigned vertices=1,unsigned per_vertex=1) {
    std::vector<double> a{double(bones),double(bones),double(vertices),double(vertices*per_vertex),128,65536,262144,1e10,1e-10,0,0,0};
    for(unsigned j=0;j<bones;++j){a.push_back(j+1);const auto m=skin_matrix();a.insert(a.end(),m.begin(),m.end());a.insert(a.end(),m.begin(),m.end());}
    for(unsigned j=0;j<bones;++j){a.push_back(bones-j);const auto m=skin_matrix(4);a.insert(a.end(),m.begin(),m.end());}
    for(unsigned j=0;j<vertices;++j)a.insert(a.end(),{1,2,3,double(per_vertex)});
    for(unsigned j=0;j<vertices;++j)for(unsigned k=0;k<per_vertex;++k)a.insert(a.end(),{double(k%bones+1),double(k+1)});return a;
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
        test("motion ABI samples unordered hierarchy with parent-first ranks and retained world shear",[]{
            const auto n=motion_input();success(pp_sim_motion(n));const auto a=result();check(pp_sim_output_count()==10&&a[0]==0&&a[1]==1&&a[2]==2&&a[4]==1,"motion completed summary");
            success(pp_sim_motion_bone(0));const auto b=result();check(pp_sim_output_count()==45&&b[0]==20&&b[1]==10&&b[44]==1,"motion original order and rank");near(b[40],2);near(b[28]*b[32]+b[29]*b[33]+b[30]*b[34],-36./25,1e-12);
            success(pp_sim_motion_bone(1));check(result()[0]==10&&result()[44]==0,"root evaluated first");
        });
        test("motion ABI exact loop endpoint and graph failure never return partial or stale pose",[]{
            const auto n=motion_input();auto* p=pp_sim_input_f64_ptr();p[5]=1;success(pp_sim_motion(n));check(result()[0]==0&&result()[4]==0,"loop duration maps to zero");
            p[5]=0;p[11]=999;success(pp_sim_motion(n));check(result()[0]==1&&result()[1]==0&&result()[2]==0,"missing parent model failure");const auto before=result();check(pp_sim_motion_bone(0)==PP_SIM_INVALID_ARGUMENT&&result()==before,"no failed candidate getter");
            motion_input();p[6]=1;success(pp_sim_motion(n));check(result()[0]==2&&result()[1]==0,"motion budget result");motion_input();success(pp_sim_motion(n));check(result()[0]==0,"same source retry");
        });
        test("motion malformed exchange keeps output and snapshot across unrelated queries until reset",[]{
            const auto n=motion_input();success(pp_sim_motion(n));success(pp_sim_motion_bone(0));const auto before=result();auto* p=pp_sim_input_f64_ptr();p[9]=1;check(pp_sim_motion(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"reserved retains pose");p[9]=0;p[4]=std::numeric_limits<double>::quiet_NaN();check(pp_sim_motion(n)==PP_SIM_INVALID_ARGUMENT&&result()==before,"NaN retains pose");
            check(pp_sim_motion_bone(128)==PP_SIM_INVALID_ARGUMENT&&result()==before,"bad getter retains output");const auto w=pp_sim_world_create();success(pp_sim_world_info(w));success(pp_sim_motion_bone(0));check(result()==before,"world query preserves motion snapshot");success(pp_sim_reset());check(pp_sim_motion_bone(0)==PP_SIM_INVALID_ARGUMENT,"global reset clears motion");
        });
        test("skin bind ABI returns explicit inverse matrices and optional diagnostics",[]{
            auto a=skin_bind_values();a[9]=2;a[14]=4;a[19]=.5;a[21]=1;a[22]=-2;a[23]=3;skin_transfer(a);success(pp_sim_skin_bind(unsigned(a.size())));const auto s=result();check(pp_sim_output_count()==8&&s[0]==0&&s[1]==1&&s[2]==1&&s[3]==1&&s[4]==0&&s[5]==0&&s[6]==0&&s[7]==0,"skin bind summary");
            success(pp_sim_skin_bind_record(0,0));const auto j=result();check(pp_sim_output_count()==33&&j[0]==1,"skin bind ID and count");near(j[17],.5);near(j[22],.25);near(j[27],2);near(j[29],-.5);near(j[30],.5);near(j[31],-6);
            success(pp_sim_skin_bind_record(1,0));const auto d=result();check(pp_sim_output_count()==6&&d[0]==1&&d[1]==1&&d[3]==1&&d[5]==0,"skin inverse optional flags");near(d[2],8);near(d[4],0);
        });
        test("skin deform ABI returns copied position and weight snapshots using stable IDs",[]{
            auto a=skin_deform_values(4,2,4);skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));const auto s=result();check(pp_sim_output_count()==8&&s[0]==0&&s[1]==1&&s[2]==2&&s[3]==4&&s[4]==2,"skin deform summary");
            success(pp_sim_skin_deform_record(0,1));const auto p=result();check(pp_sim_output_count()==3,"skin position count");near(p[0],5);near(p[1],2);near(p[2],3);
            std::fill_n(pp_sim_input_f64_ptr(),a.size(),999.);success(pp_sim_skin_deform_record(0,1));check(result()==p,"skin snapshot copied input");success(pp_sim_skin_deform_record(1,3));check(result()[0]==4&&result()[1]==1,"deform diagnostic input order");success(pp_sim_skin_deform_record(2,1));check(pp_sim_output_count()==1,"weight residual count");near(result()[0],0,1e-14);near(p[0],5);
        });
        test("skin bad exchange and getters preserve prior bind and deform output records",[]{
            auto b=skin_bind_values();skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));success(pp_sim_skin_bind_record(0,0));const auto old_bind=result();
            for(unsigned slot:{0u,1u,2u,3u,6u,7u,8u,9u}){auto bad=b;bad[slot]=slot==9?std::numeric_limits<double>::infinity():slot==8?0:slot==0?1.5:slot==6||slot==7?1:0;skin_transfer(bad);check(pp_sim_skin_bind(unsigned(bad.size()))==PP_SIM_INVALID_ARGUMENT&&result()==old_bind,"bad skin bind exchange preserves output");success(pp_sim_skin_bind_record(0,0));check(result()==old_bind,"bad bind preserves record");}
            auto a=skin_deform_values();skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));success(pp_sim_skin_deform_record(0,0));const auto old=result();
            for(unsigned slot:{0u,2u,3u,4u,5u,6u,9u,10u,11u,12u,65u,66u}){auto bad=a;bad[slot]=slot==65?1.5:slot==66?0:slot==12?0:slot>=9&&slot<=11?1:slot<=3?1.5:0;skin_transfer(bad);check(pp_sim_skin_deform(unsigned(bad.size()))==PP_SIM_INVALID_ARGUMENT&&result()==old,"bad skin deform exchange preserves output");success(pp_sim_skin_deform_record(0,0));check(result()==old,"bad deform preserves record");}
            skin_transfer(a);check(pp_sim_skin_deform(unsigned(a.size()-1))==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin truncated packet preserves output");check(pp_sim_skin_deform(PP_SIM_INPUT_F64_CAPACITY+1)==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin oversized packet preserves output");check(pp_sim_skin_bind_record(2,0)==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin bind invalid kind");check(pp_sim_skin_bind_record(0,128)==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin bind invalid index");check(pp_sim_skin_deform_record(3,0)==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin deform invalid kind");check(pp_sim_skin_deform_record(0,2048)==PP_SIM_INVALID_ARGUMENT&&result()==old,"skin deform invalid index");
            success(pp_sim_skin_bind_record(0,0));check(result()==old_bind,"deform exchange did not rewrite bind");
        });
        test("skin accepted model failure replaces candidate with no result and supports retry",[]{
            auto b=skin_bind_values(2);skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));b[25]=1;skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));check(result()[0]==1&&result()[1]==0,"skin duplicate bind model invalid");const auto failed=result();check(pp_sim_skin_bind_record(0,0)==PP_SIM_INVALID_ARGUMENT&&result()==failed,"failed binding has no old joints");
            b=skin_bind_values(2);b[26]=0;b[31]=0;b[36]=0;skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));check(result()[0]==3&&result()[1]==0&&result()[3]==2,"singular bind diagnostic prefix");success(pp_sim_skin_bind_record(1,1));check(result()[0]==2&&result()[1]==0&&result()[3]==0&&result()[5]==1,"singular pivot optional diagnostics");
            auto a=skin_deform_values(2,2,1);a.back()=0;skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==1&&result()[1]==0&&result()[2]==0,"all-zero vertex model failure");const auto f=result();check(pp_sim_skin_deform_record(0,0)==PP_SIM_INVALID_ARGUMENT&&result()==f,"failed deformation exposes no prefix positions");a=skin_deform_values();a[7]=.5;skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==1&&result()[1]==0,"finite invalid quality setting is model failure");a=skin_deform_values();skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==0&&result()[1]==1,"skin failure retry");
        });
        test("skin query hard limits admit all simultaneous boundary counts without truncation",[]{
            auto a=skin_deform_values(128,2048,4);check(a.size()==30988,"skin maximum layout length");skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));const auto s=result();check(s[0]==0&&s[1]==1&&s[2]==2048&&s[3]==128&&s[4]==2048,"skin simultaneous boundary");success(pp_sim_skin_deform_record(0,2047));near(result()[0],5);success(pp_sim_skin_deform_record(1,127));check(result()[0]==128,"last bind diagnostic");success(pp_sim_skin_deform_record(2,2047));const auto before=result();
            for(const auto slot:{0u,1u,2u,3u}){auto bad=a;bad[slot]=slot<=1?129:slot==2?2049:8193;skin_transfer(bad);check(pp_sim_skin_deform(unsigned(bad.size()))==PP_SIM_INVALID_ARGUMENT&&result()==before,"skin one over query limit preserves output");}
            a[5]=2047;skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==2&&result()[1]==0,"smaller caller budget remains core result");auto b=skin_bind_values(128);skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));check(result()[2]==128,"skin bind boundary");b[0]=129;skin_transfer(b);const auto s2=result();check(pp_sim_skin_bind(unsigned(b.size()))==PP_SIM_INVALID_ARGUMENT&&result()==s2,"skin bind one over boundary");
        });
        test("skin finite quality and normalization failure snapshots retain diagnostic prefixes",[]{
            auto a=skin_deform_values(2,2,2);const unsigned inf=12+66+34+8;a[inf+1]=std::numeric_limits<double>::max();a[inf+3]=std::numeric_limits<double>::max();a[inf+5]=std::numeric_limits<double>::denorm_min();a[inf+7]=std::numeric_limits<double>::max();skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==4&&result()[1]==0&&result()[3]==2&&result()[4]==1,"normalization underflow retains residual prefix");success(pp_sim_skin_deform_record(2,0));near(result()[0],0);const auto p=result();check(pp_sim_skin_deform_record(2,1)==PP_SIM_INVALID_ARGUMENT&&result()==p,"no residual beyond prefix");
            a=skin_deform_values();a[12+17+12]=1e-4;skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==3&&result()[1]==0&&result()[3]==1&&result()[4]==0,"imported inverse residual failure");success(pp_sim_skin_deform_record(1,0));check(result()[1]==1&&result()[3]==1,"failed inverse optional diagnostics");near(result()[4],1e-4);
        });
        test("skin empty geometry valid no-result models and numeric ID boundaries are distinct",[]{
            auto a=skin_deform_values(1,0);skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));check(result()[0]==0&&result()[1]==1&&result()[2]==0,"empty positions success flag");auto b=skin_bind_values(0);skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));check(result()[0]==1&&result()[1]==0,"empty binding accepted model invalid");
            b=skin_bind_values();b[8]=9007199254740991.;skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));success(pp_sim_skin_bind_record(0,0));check(result()[0]==9007199254740991.,"largest exact skin ID");const auto old=result();for(double bad:{0.,.5,9007199254740992.,std::numeric_limits<double>::quiet_NaN()}){b[8]=bad;skin_transfer(b);check(pp_sim_skin_bind(unsigned(b.size()))==PP_SIM_INVALID_ARGUMENT&&result()==old,"unsafe skin exchange ID");}
        });
        test("skin records remain independent of motion optics World clocks and clear on global reset",[]{
            auto b=skin_bind_values();skin_transfer(b);success(pp_sim_skin_bind(unsigned(b.size())));success(pp_sim_skin_bind_record(0,0));const auto saved_bind=result();auto a=skin_deform_values();skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));success(pp_sim_skin_deform_record(0,0));const auto saved_position=result();
            const auto nm=motion_input();success(pp_sim_motion(nm));success(pp_sim_motion_bone(0));const auto saved_motion=result();const auto nr=polarized_input();success(pp_sim_polarized_route(nr));success(pp_sim_polarized_route_segment(0,1));const auto saved_optics=result();const auto w=pp_sim_world_create();body(1,0);success(pp_sim_world_body_add(w,28));gravity(w);success(pp_sim_world_info(w));const auto clock=result();
            skin_transfer(a);success(pp_sim_skin_deform(unsigned(a.size())));success(pp_sim_skin_deform_record(0,0));check(result()==saved_position,"skin retry snapshot");success(pp_sim_motion_bone(0));check(result()==saved_motion,"skin leaves motion record");success(pp_sim_polarized_route_segment(0,1));check(result()==saved_optics,"skin leaves optical record");success(pp_sim_world_info(w));check(result()==clock,"skin does not advance world clock");success(pp_sim_world_reset(w));success(pp_sim_skin_bind_record(0,0));check(result()==saved_bind,"world reset leaves skin bind");success(pp_sim_skin_deform_record(0,0));check(result()==saved_position,"world reset leaves skin deform");
            success(pp_sim_reset());check(pp_sim_skin_bind_record(0,0)==PP_SIM_INVALID_ARGUMENT&&pp_sim_output_count()==0,"global reset clears skin bind");check(pp_sim_skin_deform_record(0,0)==PP_SIM_INVALID_ARGUMENT&&pp_sim_output_count()==0,"global reset clears skin deform");
        });
        test("derived ABI publishes full copied local Float32 geometry and certificate packets",[]{
            const auto a=derived_values();derived_transfer(a);const std::array<uint32_t,3> indices{0,1,2};
            success(pp_sim_derived_mesh(unsigned(a.size()),3));const auto summary=result();
            check(pp_sim_output_count()==20&&summary[0]==0&&summary[1]==0&&summary[2]==1&&summary[3]==3&&summary[4]==1&&summary[5]==1&&summary[6]==18&&summary[7]==0&&summary[9]==0&&summary[13]==0,"Derived summary layout");
            check(summary[14]==0&&summary[15]==0&&summary[16]==0&&summary[17]==1&&summary[18]==1&&summary[19]==0,"Derived local bounds");
            check(std::memcmp(pp_sim_input_f64_ptr(),a.data(),a.size()*sizeof(double))==0&&std::equal(indices.begin(),indices.end(),pp_sim_input_u32_ptr()),"Derived mutates scratch input");
            success(pp_sim_derived_mesh_record(0,0));check(pp_sim_output_count()==3&&std::signbit(result()[0]),"Float32 negative zero copied");
            success(pp_sim_derived_mesh_record(1,0));check(pp_sim_output_count()==3&&result()[0]==0&&result()[1]==1&&result()[2]==2,"Derived triangle copy");
            success(pp_sim_derived_mesh_record(2,0));const auto saved=result();check(pp_sim_output_count()==18&&saved[5]==1&&saved[6]==1&&saved[11]==1&&saved[13]==1&&saved[17]==1,"Expanded positions and flat normal");
            success(pp_sim_derived_mesh_record(3,0));const auto audit=result();check(pp_sim_output_count()==26&&audit[0]==0&&audit[7]>1e-24&&audit[9]==1&&audit[16]==1&&audit[19]==1&&audit[20]==1&&audit[21]>=0&&audit[22]>=0&&audit[23]<=1e-6,"Derived audit layout");
            std::fill_n(pp_sim_input_f64_ptr(),a.size(),99.);std::fill_n(pp_sim_input_u32_ptr(),3,99u);success(pp_sim_derived_mesh_record(2,0));check(result()==saved,"Derived snapshot aliases scratch");
        });
        test("derived malformed exchange and getters retain prior model and exact output",[]{
            const auto a=derived_values();derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));success(pp_sim_derived_mesh_record(2,0));const auto before=result();const auto count=pp_sim_output_count();
            const auto reject=[&](std::vector<double> bad,unsigned nf,unsigned ni){skin_transfer(bad);check(pp_sim_derived_mesh(nf,ni)==PP_SIM_INVALID_ARGUMENT,"Malformed derived exchange accepted");retained_output(before,count);success(pp_sim_derived_mesh_record(2,0));retained_output(before,count);};
            reject(a,7,3);reject(a,unsigned(a.size()-1),3);reject(a,unsigned(a.size()+1),3);reject(a,unsigned(a.size()),2);reject(a,unsigned(a.size()),4);
            reject(a,PP_SIM_INPUT_F64_CAPACITY+1,3);reject(a,unsigned(a.size()),PP_SIM_INPUT_U32_CAPACITY+1);
            for(unsigned slot=0;slot<5;++slot)for(double value:{-.5,.5,-1.,4294967296.,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){auto bad=a;bad[slot]=value;reject(bad,unsigned(a.size()),3);}
            for(unsigned slot=5;slot<8;++slot){auto bad=a;bad[slot]=1;reject(bad,unsigned(a.size()),3);}
            auto bad=a;bad[8]=std::numeric_limits<double>::quiet_NaN();reject(bad,unsigned(a.size()),3);bad=a;bad[8]=std::numeric_limits<double>::infinity();reject(bad,unsigned(a.size()),3);
            bad=a;bad[0]=2049;reject(bad,unsigned(a.size()),3);bad=a;bad[1]=32769;reject(bad,unsigned(a.size()),3);
            for(const auto kind:{4u,std::numeric_limits<unsigned>::max()}){check(pp_sim_derived_mesh_record(kind,0)==PP_SIM_INVALID_ARGUMENT,"Bad derived kind accepted");retained_output(before,count);}
            for(unsigned kind=0;kind<4;++kind){check(pp_sim_derived_mesh_record(kind,std::numeric_limits<unsigned>::max())==PP_SIM_INVALID_ARGUMENT,"Bad derived index accepted");retained_output(before,count);}
        });
        test("derived empty arrays uint32 model settings and bad indices reach unchanged core",[]{
            auto a=derived_values(0,0);derived_transfer(a,0);success(pp_sim_derived_mesh(unsigned(a.size()),0));check(result()[0]==1&&result()[1]==2&&result()[2]==0,"Empty derived positions must be core invalid data");
            a=derived_values(3,0);derived_transfer(a,0);success(pp_sim_derived_mesh(unsigned(a.size()),0));check(result()[0]==1&&result()[1]==3,"Empty derived faces must be core invalid data");
            for(unsigned slot=2;slot<5;++slot)for(double value:{0.,4294967295.}){a=derived_values();a[slot]=value;derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==1&&result()[1]==1&&result()[2]==0,"Typed settings did not reach core invalid model");}
            a=derived_values();derived_transfer(a);pp_sim_input_u32_ptr()[2]=std::numeric_limits<uint32_t>::max();success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==1&&result()[1]==5&&result()[9]==1&&result()[10]==0,"Index out of range not core invalid data");
            derived_transfer(a);pp_sim_input_u32_ptr()[2]=1;success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==1&&result()[1]==6,"Duplicate index not core invalid data");
        });
        test("derived accepted failures replace geometry but retain diagnostic prefixes and recover",[]{
            auto a=derived_values();derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));a=derived_values(4,2);derived_transfer(a,2);pp_sim_input_u32_ptr()[5]=3;success(pp_sim_derived_mesh(unsigned(a.size()),6));const auto failure=result();
            check(failure[0]==3&&failure[1]==9&&failure[2]==0&&failure[3]==0&&failure[4]==0&&failure[5]==2&&failure[6]==0&&failure[9]==1&&failure[10]==1,"Derived accepted failure summary");
            for(unsigned kind=0;kind<3;++kind){check(pp_sim_derived_mesh_record(kind,0)==PP_SIM_INVALID_ARGUMENT,"Failed derived exposed render geometry");retained_output(failure,20);}
            success(pp_sim_derived_mesh_record(3,0));check(result()[16]==1&&result()[20]==1,"Successful prefix normal lost");success(pp_sim_derived_mesh_record(3,1));check(result()[16]==0&&result()[20]==0,"Degenerate prefix invented normal");
            a=derived_values();a[4]=1;derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==5&&result()[1]==13&&result()[2]==0,"Limited normal failure status");
            a=derived_values();a[8]=1e300;derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==1&&result()[1]==4&&result()[7]==1&&result()[8]==0,"Finite coordinate model failure");
            a=derived_values();derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));check(result()[0]==0&&result()[2]==1,"Derived failure retry");
        });
        test("derived simultaneous exchange limits produce every face without truncation",[]{
            auto a=derived_values(2048,32768);derived_transfer(a,32768);success(pp_sim_derived_mesh(unsigned(a.size()),98304));const auto summary=result();
            check(a.size()==6152&&summary[0]==0&&summary[3]==2048&&summary[4]==32768&&summary[5]==32768&&summary[6]==589824,"Derived actual exchange boundaries");
            success(pp_sim_derived_mesh_record(0,2047));check(result()[0]==0,"Last derived vertex missing");success(pp_sim_derived_mesh_record(2,32767));check(pp_sim_output_count()==18&&result()[17]==1,"Last derived expanded face missing");success(pp_sim_derived_mesh_record(3,32767));check(result()[0]==32767&&result()[16]==1,"Last derived audit missing");
            derived_batch_matches_single(0,2028,20);derived_batch_matches_single(1,32748,20);derived_batch_matches_single(2,32765,3);const auto batch=derived_batch_matches_single(3,32766,2);check(batch[4]==32766&&batch[30]==32767,"Maximum snapshot audit batch lost final ordinal");
            success(pp_sim_derived_mesh_record(3,32767));
            const auto before=result();a[1]=32769;skin_transfer(a);check(pp_sim_derived_mesh(unsigned(a.size()),98304)==PP_SIM_INVALID_ARGUMENT,"Too many derived faces accepted");retained_output(before,26);
        });
        test("derived snapshot is independent of skin motion optics and World and reset clears it",[]{
            auto bind=skin_bind_values();skin_transfer(bind);success(pp_sim_skin_bind(unsigned(bind.size())));success(pp_sim_skin_bind_record(0,0));const auto old_bind=result();
            auto deform=skin_deform_values();skin_transfer(deform);success(pp_sim_skin_deform(unsigned(deform.size())));success(pp_sim_skin_deform_record(0,0));const auto old_deform=result();
            success(pp_sim_motion(motion_input()));success(pp_sim_motion_bone(0));const auto old_motion=result();success(pp_sim_polarized_route(polarized_input()));success(pp_sim_polarized_route_segment(0,1));const auto old_optics=result();
            const auto w=pp_sim_world_create();body(1,0);success(pp_sim_world_body_add(w,28));success(pp_sim_world_info(w));const auto clock=result();
            const auto a=derived_values();derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));success(pp_sim_derived_mesh_record(2,0));const auto own=result();
            success(pp_sim_skin_bind_record(0,0));check(result()==old_bind,"Derived changed skin bind");success(pp_sim_skin_deform_record(0,0));check(result()==old_deform,"Derived changed skin deform");success(pp_sim_motion_bone(0));check(result()==old_motion,"Derived changed motion");success(pp_sim_polarized_route_segment(0,1));check(result()==old_optics,"Derived changed optics");success(pp_sim_world_info(w));check(result()==clock,"Derived advanced World");
            success(pp_sim_world_reset(w));success(pp_sim_derived_mesh_record(2,0));check(result()==own,"World reset cleared derived record");
            success(pp_sim_reset());check(pp_sim_derived_mesh_record(2,0)==PP_SIM_INVALID_ARGUMENT&&pp_sim_output_count()==0,"Global reset did not clear derived");
        });
        test("derived batches carry all kinds full packets and tails with independent rational geometry",[]{
            auto a=derived_values(41,23);
            for(unsigned j=3;j<41;++j){a[8+3*j]=j/8.;a[9+3*j]=j/16.;a[10+3*j]=-double(j)/32.;}
            a[14]=0;a[15]=4;a[16]=-3;derived_transfer(a,23);
            for(unsigned j=0;j<23;++j){auto* indices=pp_sim_input_u32_ptr()+3*j;indices[1]=j%2?2:1;indices[2]=j%2?1:2;}
            const std::vector<uint32_t> source_indices(pp_sim_input_u32_ptr(),pp_sim_input_u32_ptr()+69);
            success(pp_sim_derived_mesh(unsigned(a.size()),69));check(result()[0]==0,"Rational batch fixture must complete");
            constexpr std::array<unsigned,4> available{41,23,23,23},max_count{20,20,3,2};
            for(unsigned kind=0;kind<4;++kind)for(unsigned first=0;first<available[kind];first+=max_count[kind])derived_batch_matches_single(kind,first,std::min(max_count[kind],available[kind]-first));
            const auto vertex=derived_batch_matches_single(0,0,1);check(std::signbit(vertex[4])&&vertex[5]==0&&vertex[6]==0,"Batch lost source negative zero");
            const auto last=derived_batch_matches_single(0,40,1);check(last[4]==5&&last[5]==2.5&&last[6]==-1.25,"Batch tail vertex differs from analytic source");
            const auto face=derived_batch_matches_single(2,0,1);near(face[7],0,0);near(face[8],.6,3e-8);near(face[9],.8,3e-8);
            const auto audit=derived_batch_matches_single(3,0,2);check(audit[4]==0&&audit[30]==1,"Audit batch ordinal/order");
            check(audit[5]<=0&&audit[6]>=0&&audit[7]<=3&&audit[8]>=3&&audit[9]<=4&&audit[10]>=4&&audit[11]<=25&&audit[12]>=25,"Rational cross(0,3,4) Q25 not enclosed");
            near(audit[22],.6,3e-8);near(audit[23],.8,3e-8);near(audit[48],-.6,3e-8);near(audit[49],-.8,3e-8);
            check(std::memcmp(pp_sim_input_f64_ptr(),a.data(),a.size()*sizeof(double))==0&&std::equal(source_indices.begin(),source_indices.end(),pp_sim_input_u32_ptr()),"Batch mutates source exchange");
        });
        test("derived batch rejects counts ranges overflow and kinds atomically and retries",[]{
            const auto a=derived_values(41,23);derived_transfer(a,23);success(pp_sim_derived_mesh(unsigned(a.size()),69));
            const auto before=derived_batch_matches_single(2,0,1);const unsigned output_size=22;
            const auto reject=[&](unsigned kind,unsigned first,unsigned count){check(pp_sim_derived_mesh_records(kind,first,count)==PP_SIM_INVALID_ARGUMENT,"Invalid derived batch accepted");check(pp_sim_last_status()==PP_SIM_INVALID_ARGUMENT&&pp_sim_error_length()>0&&pp_sim_error_length()<PP_SIM_ERROR_CAPACITY,"Batch error diagnostic unavailable");retained_output(before,output_size);success(pp_sim_derived_mesh_records(2,0,1));retained_output(before,output_size);};
            constexpr std::array<unsigned,4> available{41,23,23,23},max_count{20,20,3,2};const auto maximum=std::numeric_limits<unsigned>::max();
            reject(4,0,1);reject(maximum,0,1);
            for(unsigned kind=0;kind<4;++kind){reject(kind,0,0);reject(kind,0,max_count[kind]+1);reject(kind,0,maximum);reject(kind,available[kind],1);reject(kind,available[kind]-1,2);reject(kind,maximum,1);reject(kind,maximum-1,2);reject(kind,maximum,max_count[kind]);}
            derived_batch_matches_single(3,22,1);derived_batch_matches_single(0,21,20);
        });
        test("derived batch failure audits retain mixed prefix evidence without render geometry",[]{
            auto a=derived_values(4,3);derived_transfer(a,3);pp_sim_input_u32_ptr()[8]=3;success(pp_sim_derived_mesh(unsigned(a.size()),9));const auto failure=result();check(failure[0]==3&&failure[2]==0&&failure[5]==3&&failure[10]==2,"Expected third-face failure prefix");
            for(unsigned kind=0;kind<3;++kind){check(pp_sim_derived_mesh_records(kind,0,1)==PP_SIM_INVALID_ARGUMENT,"Failure prefix exposed geometry");retained_output(failure,20);}
            const auto good=derived_batch_matches_single(3,0,2);check(good[20]==1&&good[24]==1&&good[46]==1&&good[50]==1,"Successful audit evidence lost in prefix batch");
            const auto bad=derived_batch_matches_single(3,2,1);check(bad[4]==2&&bad[20]==0&&bad[24]==0,"Failed audit optional normal invented");
            check(pp_sim_derived_mesh_records(3,2,2)==PP_SIM_INVALID_ARGUMENT,"Diagnostic batch silently truncated");retained_output(bad,30);
            a=derived_values();a[4]=0;derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));const auto empty=result();check(empty[0]==1&&empty[5]==0,"Invalid settings must have zero audits");check(pp_sim_derived_mesh_records(3,0,1)==PP_SIM_INVALID_ARGUMENT,"Empty audit synthesized a packet");retained_output(empty,20);
            a=derived_values();derived_transfer(a);success(pp_sim_derived_mesh(unsigned(a.size()),3));derived_batch_matches_single(2,0,1);
        });
        test("derived batch snapshot and caller copies survive source scratch changes and later reads",[]{
            const auto a=derived_values(21,4);derived_transfer(a,4);success(pp_sim_derived_mesh(unsigned(a.size()),12));const auto copied=derived_batch_matches_single(0,0,20),saved=copied;
            std::fill_n(pp_sim_input_f64_ptr(),a.size(),99.);std::fill_n(pp_sim_input_u32_ptr(),12,99u);success(pp_sim_derived_mesh_records(0,0,20));retained_output(saved,64);
            const auto audit=derived_batch_matches_single(3,2,2);check(pp_sim_output_count()==56,"Audit maximum output length");check(std::memcmp(copied.data(),saved.data(),sizeof(saved))==0,"Owned batch caller copy changed");
            auto failed=derived_values(0,0);derived_transfer(failed,0);success(pp_sim_derived_mesh(unsigned(failed.size()),0));check(result()[0]==1,"Accepted model failure must replace batch snapshot");
            const auto invalid=result();check(pp_sim_derived_mesh_records(0,0,1)==PP_SIM_INVALID_ARGUMENT,"Old batch geometry retained after accepted failure");retained_output(invalid,20);check(audit[4]==2&&audit[30]==3,"Owned audit copy changed after prepare");
        });
        test("derived batches leave every independent snapshot and World clocks intact and reset clears them",[]{
            struct Saved {std::function<int32_t()> read;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values;unsigned count;};std::vector<Saved> snapshots;
            const auto retain=[&](const std::function<int32_t()>& read){success(read());snapshots.push_back({read,result(),pp_sim_output_count()});};
            auto bind=skin_bind_values();skin_transfer(bind);success(pp_sim_skin_bind(unsigned(bind.size())));retain([]{return pp_sim_skin_bind_record(0,0);});
            auto deform=skin_deform_values();skin_transfer(deform);success(pp_sim_skin_deform(unsigned(deform.size())));retain([]{return pp_sim_skin_deform_record(0,0);});
            success(pp_sim_motion(motion_input()));retain([]{return pp_sim_motion_bone(0);});
            success(pp_sim_polarized_route(polarized_input()));retain([]{return pp_sim_polarized_route_initial();});retain([]{return pp_sim_polarized_route_segment(0,1);});
            success(pp_sim_polarized_packet(packet_input()));retain([]{return pp_sim_polarized_packet_record(0,1);});retain([]{return pp_sim_polarized_packet_segment(1,1,1);});
            success(pp_sim_optical_spot(spot_input()));retain([]{return pp_sim_optical_spot_sample(0,0);});
            success(pp_sim_optical_selection(selection_input({{9,2}})));retain([]{return pp_sim_optical_selection_surface(0,0);});
            double route[35]{};route[10]=route[11]=1;route[13]=10;route[14]=route[15]=1;route[16]=550e-9;route[17]=64;route[18]=1e6;route[19]=128;route[20]=1;route[27]=-1;route[29]=10;route[30]=1;route[31]=route[32]=1;route[34]=10;std::copy_n(route,35,pp_sim_input_f64_ptr());success(pp_sim_optical_route(35));retain([]{return pp_sim_optical_route_segment(0);});
            const auto w=pp_sim_world_create();check(w!=0,"Batch independence world create");body(1,.25);success(pp_sim_world_body_add(w,28));gravity(w);
            const double plane[8]={100,0,1,0,0,0,0,0};std::copy_n(plane,8,pp_sim_input_f64_ptr());success(pp_sim_world_plane_add(w,8));
            const double support_settings[10]={1e-8,1e-9,1e-8,1e-7,1e-8,1e-10,1e24,20000,128,100000};std::copy_n(support_settings,10,pp_sim_input_f64_ptr());success(pp_sim_world_support(w,10));retain([w]{return pp_sim_world_support_constraint(w,0);});retain([w]{return pp_sim_world_support_body(w,0);});retain([w]{return pp_sim_world_body_get(w,1);});retain([w]{return pp_sim_world_info(w);});
            const auto hull=hull_box();hydro_input();success(pp_sim_hydro_query(hull,16));const auto hydro=result();const auto hydro_count=pp_sim_output_count();
            const auto a=derived_values(21,4);derived_transfer(a,4);success(pp_sim_derived_mesh(unsigned(a.size()),12));const auto own=derived_batch_matches_single(2,1,3);
            for(const auto&s:snapshots){success(s.read());retained_output(s.values,s.count);}
            hydro_input();success(pp_sim_hydro_query(hull,16));retained_output(hydro,hydro_count);
            success(pp_sim_derived_mesh_records(2,1,3));retained_output(own,58);
            success(pp_sim_world_reset(w));success(pp_sim_derived_mesh_records(2,1,3));retained_output(own,58);
            success(pp_sim_reset());for(unsigned kind=0;kind<4;++kind){check(pp_sim_derived_mesh_records(kind,0,1)==PP_SIM_INVALID_ARGUMENT,"Global reset retained derived batch snapshot");check(pp_sim_output_count()==0,"Missing snapshot changed reset output");}
            check(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64,"Batch changed legacy ABI capacity/version");
        });
        test("sphere triangle exposes full geometry and all seven exact candidate packets",[]{
            const auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(unsigned(a.size())));const auto summary=result();
            check(pp_sim_output_count()==58&&summary[0]==0&&summary[1]==0&&summary[2]==1&&summary[3]==37&&summary[4]==1&&summary[5]==0&&summary[6]==7&&summary[7]==7&&summary[10]==1&&summary[13]==1,"Sphere triangle summary metadata");
            const auto encloses=[&](unsigned offset,double value){check(summary[offset]<=value&&summary[offset+1]>=value,"Sphere triangle analytic enclosure");};
            encloses(16,.5);encloses(18,.25);encloses(20,.25);encloses(28,1);encloses(30,0);encloses(32,1);encloses(34,0);encloses(36,1);encloses(38,0);encloses(40,0);encloses(42,1);encloses(44,0);encloses(46,1);encloses(48,.5);encloses(50,1);encloses(52,1);encloses(54,1);encloses(56,.5);
            namespace st=pikapika::sphere_triangle;const auto direct=st::query_sphere_triangle({{1,1,1},.5},{37,{{{0,0,0},{4,0,0},{0,0,4}}}});
            for(unsigned j=0;j<7;++j){success(pp_sim_sphere_triangle_candidate(j));const auto packet=result();const auto&c=direct.candidates[j];std::array<double,64> expected{};expected[0]=unsigned(c.feature);expected[1]=unsigned(c.disposition);expected[2]=c.kkt_count;
                for(unsigned k=0;k<3;++k){expected[3+2*k]=c.barycentric[k].lower();expected[4+2*k]=c.barycentric[k].upper();}for(unsigned k=0;k<2;++k){expected[9+2*k]=c.kkt[k].lower();expected[10+2*k]=c.kkt[k].upper();}
                check(pp_sim_output_count()==13&&std::memcmp(packet.data(),expected.data(),sizeof(expected))==0,"Sphere triangle candidate changed exact core bits");
                if(j==0)check(packet[2]==0&&std::signbit(packet[9])&&!std::signbit(packet[10])&&std::signbit(packet[11])&&!std::signbit(packet[12]),"Unused KKT signed zeros not preserved");}
            check(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64&&pp_sim_input_f64_capacity()==49152&&pp_sim_input_u32_capacity()==98304,"Sphere triangle changed exchange capacities");
        });
        test("sphere triangle malformed exchanges and getter ranges preserve old output and snapshot",[]{
            auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));success(pp_sim_sphere_triangle_candidate(6));const auto old=result();
            const auto reject=[&](const auto&bad,unsigned count){sphere_triangle_transfer(bad);check(pp_sim_sphere_triangle(count)==PP_SIM_INVALID_ARGUMENT,"Malformed sphere triangle exchange accepted");retained_output(old,13);check(pp_sim_last_status()==PP_SIM_INVALID_ARGUMENT&&pp_sim_error_length()>0&&pp_sim_error_length()<256,"Missing bounded host error");success(pp_sim_sphere_triangle_candidate(6));retained_output(old,13);};
            for(unsigned count:{0u,23u,25u,std::numeric_limits<unsigned>::max()})reject(a,count);
            for(unsigned slot:{0u,3u,5u,13u,17u,18u,19u})for(double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){auto bad=a;bad[slot]=value;reject(bad,24);}
            for(unsigned slot=20;slot<24;++slot){auto bad=a;bad[slot]=1;reject(bad,24);}
            for(double id:{0.,-1.,1.5,9007199254740992.}){auto bad=a;bad[4]=id;reject(bad,24);}
            for(unsigned slot=14;slot<17;++slot)for(double value:{-1.,.5,4294967296.}){auto bad=a;bad[slot]=value;reject(bad,24);}
            for(unsigned index:{7u,8u,std::numeric_limits<unsigned>::max()}){check(pp_sim_sphere_triangle_candidate(index)==PP_SIM_INVALID_ARGUMENT,"Bad candidate ordinal accepted");retained_output(old,13);}
        });
        test("sphere triangle uint32 settings and finite bad physical inputs are real model failures",[]{
            auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));
            for(unsigned slot=14;slot<17;++slot)for(double value:{0.,4294967295.}){auto bad=a;bad[slot]=value;sphere_triangle_transfer(bad);success(pp_sim_sphere_triangle(24));const auto r=result();check(r[0]==1&&r[1]==1&&r[2]==0&&r[3]==37&&r[6]==0,"Integer profile synthesized or rejected by host");check(std::all_of(r.begin()+16,r.begin()+58,[](double x){return x==0;}),"Failure has geometry payload");check(pp_sim_sphere_triangle_candidate(0)==PP_SIM_INVALID_ARGUMENT,"Old geometry survived accepted failure");retained_output(r,58);}
            for(const auto [slot,value]:std::array<std::pair<unsigned,double>,5>{{{3,0},{3,-1},{0,1e151},{17,-1},{19,2}}}){auto bad=a;bad[slot]=value;sphere_triangle_transfer(bad);success(pp_sim_sphere_triangle(24));check(result()[0]==1&&result()[2]==0,"Finite model invalidity became host rejection");}
            auto maximum=a;maximum[4]=9007199254740991.;sphere_triangle_transfer(maximum);success(pp_sim_sphere_triangle(24));check(result()[3]==9007199254740991.&&result()[2]==1,"Maximum stable ID lost precision");
        });
        test("sphere triangle failed model replaces record with real candidate prefix and retries",[]{
            auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));a[14]=6;sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));const auto partial=result();
            check(partial[0]==5&&partial[1]==8&&partial[2]==0&&partial[4]==0&&partial[5]==0&&partial[6]==6&&partial[7]==6,"Candidate budget failure prefix");success(pp_sim_sphere_triangle_candidate(5));check(result()[0]==5,"Last actual failure candidate missing");const auto tail=result();check(pp_sim_sphere_triangle_candidate(6)==PP_SIM_INVALID_ARGUMENT,"Old seventh candidate survived failure");retained_output(tail,13);
            a=sphere_triangle_values();a[1]=0;sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));const auto undefined=result();check(undefined[0]==4&&undefined[2]==0&&undefined[6]==7,"Undefined normal became successful geometry");check(std::all_of(undefined.begin()+16,undefined.begin()+58,[](double x){return x==0;}),"Unresolved query exposed geometry");success(pp_sim_sphere_triangle_candidate(6));
            a=sphere_triangle_values();a[15]=1;a[0]=2;a[1]=3;a[2]=-4;sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));check(result()[0]==4&&result()[1]==14&&result()[9]==1,"Limited normal enclosure model failure lost");
            a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));check(result()[0]==0&&result()[2]==1,"Failed model retry");
        });
        test("sphere triangle copied candidate snapshot ignores changed scratch and later independent calls",[]{
            const auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));success(pp_sim_sphere_triangle_candidate(0));const auto old=result(),copied=old;
            std::fill_n(pp_sim_input_f64_ptr(),24,99.);std::fill_n(pp_sim_input_u32_ptr(),12,99u);success(pp_sim_sphere_triangle_candidate(0));retained_output(old,13);
            auto model=a;model[0]=2;model[1]=3;model[2]=-4;sphere_triangle_transfer(model);success(pp_sim_sphere_triangle(24));success(pp_sim_sphere_triangle_candidate(1));check(std::memcmp(copied.data(),old.data(),sizeof(old))==0,"Owned caller candidate changed after new query");
            auto derived=derived_values();derived_transfer(derived);success(pp_sim_derived_mesh(unsigned(derived.size()),3));success(pp_sim_sphere_triangle_candidate(1));check(result()[0]==1,"Derived query changed triangle snapshot");
        });
        test("sphere triangle preserves every independent snapshot World state loads clocks and reset lifetime",[]{
            struct Saved {std::function<int32_t()> read;std::array<double,64> values;unsigned count;};std::vector<Saved> snapshots;
            const auto retain=[&](const std::function<int32_t()>&read){success(read());snapshots.push_back({read,result(),pp_sim_output_count()});};
            auto bind=skin_bind_values();skin_transfer(bind);success(pp_sim_skin_bind(unsigned(bind.size())));retain([]{return pp_sim_skin_bind_record(0,0);});auto deform=skin_deform_values();skin_transfer(deform);success(pp_sim_skin_deform(unsigned(deform.size())));retain([]{return pp_sim_skin_deform_record(0,0);});
            success(pp_sim_motion(motion_input()));retain([]{return pp_sim_motion_bone(0);});success(pp_sim_polarized_route(polarized_input()));retain([]{return pp_sim_polarized_route_initial();});retain([]{return pp_sim_polarized_route_segment(0,1);});
            success(pp_sim_polarized_packet(packet_input()));retain([]{return pp_sim_polarized_packet_record(0,1);});retain([]{return pp_sim_polarized_packet_segment(1,1,1);});success(pp_sim_optical_spot(spot_input()));retain([]{return pp_sim_optical_spot_sample(0,0);});success(pp_sim_optical_selection(selection_input({{9,2}})));retain([]{return pp_sim_optical_selection_surface(0,0);});
            double route[35]{};route[10]=route[11]=1;route[13]=10;route[14]=route[15]=1;route[16]=550e-9;route[17]=64;route[18]=1e6;route[19]=128;route[20]=1;route[27]=-1;route[29]=10;route[30]=1;route[31]=route[32]=1;route[34]=10;std::copy_n(route,35,pp_sim_input_f64_ptr());success(pp_sim_optical_route(35));retain([]{return pp_sim_optical_route_segment(0);});
            auto derived=derived_values();derived_transfer(derived);success(pp_sim_derived_mesh(unsigned(derived.size()),3));retain([]{return pp_sim_derived_mesh_record(3,0);});retain([]{return pp_sim_derived_mesh_records(2,0,1);});
            const auto w=pp_sim_world_create();check(w!=0,"Triangle independence World create");body(1,.25);pp_sim_input_f64_ptr()[20]=2;pp_sim_input_f64_ptr()[23]=.5;success(pp_sim_world_body_add(w,28));gravity(w);const double plane[8]={100,0,1,0,0,0,0,0};std::copy_n(plane,8,pp_sim_input_f64_ptr());success(pp_sim_world_plane_add(w,8));
            const double support[10]={1e-8,1e-9,1e-8,1e-7,1e-8,1e-10,1e24,20000,128,100000};std::copy_n(support,10,pp_sim_input_f64_ptr());success(pp_sim_world_support(w,10));retain([w]{return pp_sim_world_support_constraint(w,0);});retain([w]{return pp_sim_world_support_body(w,0);});retain([w]{return pp_sim_world_body_get(w,1);});retain([w]{return pp_sim_world_info(w);});
            const auto hull=hull_box();hydro_input();success(pp_sim_hydro_query(hull,16));const auto hydro=result();const auto hydro_count=pp_sim_output_count();
            const auto a=sphere_triangle_values();sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));success(pp_sim_sphere_triangle_candidate(6));const auto own=result();
            for(const auto&s:snapshots){success(s.read());retained_output(s.values,s.count);}hydro_input();success(pp_sim_hydro_query(hull,16));retained_output(hydro,hydro_count);success(pp_sim_sphere_triangle_candidate(6));retained_output(own,13);
            success(pp_sim_world_reset(w));success(pp_sim_sphere_triangle_candidate(6));retained_output(own,13);success(pp_sim_reset());check(pp_sim_sphere_triangle_candidate(0)==PP_SIM_INVALID_ARGUMENT&&pp_sim_output_count()==0,"Global reset retained triangle candidate");
        });
        test("sphere triangle Native unsupported environment is a core failure and then recovers",[]{
            const auto a=sphere_triangle_values();sphere_triangle_transfer(a);
#if defined(_M_X64) || defined(__x86_64__)
            const auto rounding=std::fegetround();check(std::fesetround(FE_UPWARD)==0,"Set isolated rounding test");const auto code=pp_sim_sphere_triangle(24);const auto after=std::fegetround();std::fesetround(rounding);success(code);const auto unsupported=result();check(after==FE_UPWARD&&unsupported[0]==7&&unsupported[1]==17&&unsupported[2]==0&&unsupported[6]==0,"Core environment failure was changed into exchange failure");
#endif
            sphere_triangle_transfer(a);success(pp_sim_sphere_triangle(24));check(result()[0]==0,"Environment failure recovery");
        });
        success(pp_sim_reset());std::cout<<passed<<" simulation C ABI test groups passed\n";return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';pp_sim_reset();return 1;}
}
