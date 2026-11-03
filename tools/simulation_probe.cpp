#include "pikapika/simulation_api.h"
#include "pikapika/core.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void ok(int32_t code){if(code!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
void array(std::ostream& out,const double* values,std::size_t count){out<<'[';for(std::size_t i=0;i<count;++i){if(i)out<<',';out<<values[i];}out<<']';}
pp_sim_handle hull() {
    const auto mesh=pikapika::make_box_mesh({4,2,4});auto* f=pp_sim_input_f64_ptr();auto* u=pp_sim_input_u32_ptr();
    for(std::size_t i=0;i<mesh.positions.size();++i){f[i*3]=mesh.positions[i].x;f[i*3+1]=mesh.positions[i].y;f[i*3+2]=mesh.positions[i].z;}
    for(std::size_t i=0;i<mesh.triangles.size();++i)std::copy_n(mesh.triangles[i].begin(),3,u+i*3);
    const auto h=pp_sim_hull_create(8,12);if(!h)throw std::runtime_error(pp_sim_error_ptr());return h;
}
std::array<double,28> body(double y,double mass,bool ballast) {
    std::array<double,28> b{};b[0]=1;b[2]=mass;b[3]=.25;b[4]=ballast?24000:mass*20/12;b[5]=ballast?48000:mass*32/12;b[6]=ballast?40000:mass*20/12;
    b[8]=y;b[12]=ballast?std::sin(.15/2):0;b[13]=ballast?std::cos(.15/2):1;b[27]=.6;return b;
}
void trace(const char* name,double dt,uint32_t ticks,const std::array<double,28>& initial,const std::array<double,9>& fluid,pp_sim_handle source) {
    const auto world=pp_sim_world_create();if(!world)throw std::runtime_error(pp_sim_error_ptr());auto* in=pp_sim_input_f64_ptr();in[0]=0;in[1]=-10;in[2]=0;ok(pp_sim_world_set_gravity(world,3));
    std::copy(initial.begin(),initial.end(),in);ok(pp_sim_world_body_add(world,28));
    std::cout<<"{\"name\":\""<<name<<"\",\"dt\":"<<dt<<",\"ticks\":"<<ticks<<",\"gravity\":[0,-10,0],\"initialBody\":";array(std::cout,initial.data(),initial.size());std::cout<<",\"buoyancyInput\":";array(std::cout,fluid.data(),fluid.size());std::cout<<",\"states\":[";
    ok(pp_sim_world_body_get(world,1));array(std::cout,pp_sim_output_f64_ptr(),34);
    for(uint32_t i=0;i<ticks;++i){std::copy(fluid.begin(),fluid.end(),in);ok(pp_sim_world_buoyancy_step(world,source,1,dt,1,9));ok(pp_sim_world_body_get(world,1));std::cout<<',';array(std::cout,pp_sim_output_f64_ptr(),34);}
    std::cout<<"]}";ok(pp_sim_world_destroy(world));
}
void world_trace() {
    const auto world=pp_sim_world_create();if(!world)throw std::runtime_error(pp_sim_error_ptr());auto* in=pp_sim_input_f64_ptr();in[0]=0;in[1]=-10;in[2]=0;ok(pp_sim_world_set_gravity(world,3));
    auto initial=body(100,2,false);initial[20]=6;initial[25]=8;std::copy(initial.begin(),initial.end(),in);ok(pp_sim_world_body_add(world,28));
    std::cout<<"{\"name\":\"freeFallAndForce\",\"dt\":0.01,\"ticks\":100,\"gravity\":[0,-10,0],\"initialBody\":";array(std::cout,initial.data(),initial.size());std::cout<<",\"states\":[";
    ok(pp_sim_world_body_get(world,1));array(std::cout,pp_sim_output_f64_ptr(),34);
    for(unsigned i=0;i<100;++i){ok(pp_sim_world_step(world,.01,1));ok(pp_sim_world_body_get(world,1));std::cout<<',';array(std::cout,pp_sim_output_f64_ptr(),34);}
    std::cout<<"]}";ok(pp_sim_world_destroy(world));
}
void toi_fixtures() {
    struct Fixture {const char* name;bool plane;std::array<double,15> input;};
    const std::vector<Fixture> fixtures={
        {"fast_spheres",false,{-3,0,0,1000,0,0,.5,0,0,0,0,0,0,.5,1./120}},
        {"oblique_spheres",false,{-4,0,0,1000,0,0,.5,0,.6,0,0,0,0,.5,.01}},
        {"tangent",false,{-2,0,0,1000,0,0,.5,0,1,0,0,0,0,.5,.01}},
        {"near_tangent_uncertain",false,{-2,0,0,1000,0,0,.5,0,1+std::numeric_limits<double>::epsilon(),0,0,0,0,.5,.01}},
        {"short_horizon_miss",false,{-3,0,0,1000,0,0,.5,0,0,0,0,0,0,.5,.001}},
        {"initial_overlap",false,{0,0,0,0,0,0,.5,0,0,0,0,0,0,.5,0}},
        {"initial_touch_departing",false,{-1,0,0,-1,0,0,.5,0,0,0,0,0,0,.5,1}},
        {"horizon_endpoint",false,{-3,0,0,1000,0,0,.5,0,0,0,0,0,0,.5,.002}},
        {"moving_plane",true,{-3,0,0,1000,0,0,.5,-1,0,0,0,100,0,0,.01}},
        {"inclined_plane",true,{0,4.8,6.4,0,-60,-80,2,0,.6,.8,0,0,6,8,.1}},
        {"plane_touch",true,{0,.5,0,0,1,0,.5,0,1,0,0,0,0,0,0}},
        {"subnormal_scale",false,{0,0,0,1e-310,0,0,1e-310,4e-310,0,0,0,0,0,1e-310,3}}
    };
    for(std::size_t i=0;i<fixtures.size();++i){if(i)std::cout<<',';const auto& fixture=fixtures[i];
        std::copy(fixture.input.begin(),fixture.input.end(),pp_sim_input_f64_ptr());
        ok(fixture.plane?pp_sim_sphere_plane_toi(15):pp_sim_sphere_sphere_toi(15));
        std::cout<<"{\"name\":\""<<fixture.name<<"\",\"type\":\""<<(fixture.plane?"sphere_plane":"sphere_sphere")<<"\",\"input\":";
        array(std::cout,fixture.input.data(),fixture.input.size());std::cout<<",\"output\":";array(std::cout,pp_sim_output_f64_ptr(),PP_SIM_TOI_OUTPUT_COUNT);std::cout<<'}';
    }
}
}
int main(int argc,char** argv) {
    try {
        for(int i=1;i<argc;++i)if(std::string(argv[i])!="--fixtures"&&std::string(argv[i])!="--traces")throw std::runtime_error("usage: pikapika-simulation-probe [--fixtures|--traces] (both are included)");
        ok(pp_sim_reset());const auto source=hull();std::cout<<std::setprecision(17)<<"{\"apiVersion\":"<<pp_sim_api_version()<<",\"mesh\":{\"version\":1,\"positions\":[";
        const auto mesh=pikapika::make_box_mesh({4,2,4});for(std::size_t i=0;i<mesh.positions.size();++i){if(i)std::cout<<',';const double p[3]={mesh.positions[i].x,mesh.positions[i].y,mesh.positions[i].z};array(std::cout,p,3);}std::cout<<"],\"triangles\":[";
        for(std::size_t i=0;i<mesh.triangles.size();++i){if(i)std::cout<<',';const auto t=mesh.triangles[i];std::cout<<'['<<t[0]<<','<<t[1]<<','<<t[2]<<']';}std::cout<<"]},\"hydroFixtures\":[";
        const std::array<std::array<double,16>,4> fixtures={{{1000,10,0,0,0,0,0,0,0,1,1,1,1,0,0,0},
            {1000,10,0,0,2,0,0,0,0,1,1,1,1,0,2,0},{1000,10,0,0,-3,0,0,0,0,1,1,1,1,0,-3,0},
            {1000,10,0,0,0,0,0,0,0,1,1,1,1,1,2,3}}};
        for(std::size_t i=0;i<fixtures.size();++i){if(i)std::cout<<',';std::copy(fixtures[i].begin(),fixtures[i].end(),pp_sim_input_f64_ptr());ok(pp_sim_hydro_query(source,16));std::cout<<"{\"input\":";array(std::cout,fixtures[i].data(),16);std::cout<<",\"output\":";array(std::cout,pp_sim_output_f64_ptr(),14);std::cout<<'}';}
        std::cout<<"],\"traces\":[";const std::array<double,9> plain={1000,10,0,0,0,0,1,1,1},ballast={1000,10,0,0,.5,0,1,1,1};
        trace("equilibrium",1./120,120,body(0,16000,false),plain,source);std::cout<<',';
        trace("heave30",1./30,60,body(.1,16000,false),plain,source);std::cout<<',';trace("heave60",1./60,120,body(.1,16000,false),plain,source);std::cout<<',';
        trace("heave120",1./120,240,body(.1,16000,false),plain,source);std::cout<<',';trace("ballastedRoll",1./120,240,body(-4,32000,true),ballast,source);
        std::cout<<"],\"worldTraces\":[";world_trace();std::cout<<"],\"toiFixtures\":[";toi_fixtures();std::cout<<"],\"limits\":\"common C++ reference;linear TOI has no response or acceleration;no waves,drag,added mass,rendering or cross-backend bit identity claim\"}\n";
        ok(pp_sim_hull_destroy(source));ok(pp_sim_reset());return 0;
    }catch(const std::exception& error){std::cerr<<"pikapika-simulation-probe: "<<error.what()<<'\n';pp_sim_reset();return 1;}
}
