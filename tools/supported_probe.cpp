// Complete raw C ABI fixtures: the same shared C++ entry point as WebAssembly.
#include "pikapika/simulation_api.h"
#include "pikapika/dynamics.hpp"
#include <algorithm>
#include <array>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using pikapika::Vec3;
namespace dy=pikapika::dynamics;
using B=std::array<double,28>;
using P=std::array<double,8>;
using S=std::array<double,33>;
struct Fixture {std::string name;Vec3 gravity{0,-10,0};double dt{.1};unsigned ticks{1};std::vector<B> bodies;std::vector<P> planes;S settings{1./240,1e-10,1e-7,5e-8,1e-9,1e-6,1e-5,1e-5,1e-10,16384,4096,512,1000000,4000000,32,64,16,128,1e-10,1e-10,1e-10,.5,.5,48,1000000,128,100000,1e24,1e-7,1e-8,1e-10,1e-10,0};};
B body(double id,Vec3 p,double mass=1,bool fixed=false){const double ii=.1*mass;return {id,fixed?1.:0.,mass,.5,ii,ii,ii,p.x,p.y,p.z,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0};}
P floor(){return {100,0,1,0,0,0,0,0};}
void check(int32_t status){if(status)throw std::runtime_error(pp_sim_error_ptr());}
template<class A>void input(const A& a){std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());}
template<class A>void print(const A& a){std::cout<<'[';bool comma=false;for(auto n:a){if(comma)std::cout<<',';comma=true;std::cout<<n;}std::cout<<']';}
std::vector<double> result(){auto p=pp_sim_output_f64_ptr();return {p,p+pp_sim_output_count()};}
std::vector<Fixture> cases(){
    std::vector<Fixture> out;Fixture f;f.name="floor-torque";f.bodies={body(1,{0,.5,0})};f.bodies[0][14]=3;f.bodies[0][20]=2;f.bodies[0][25]=1;f.planes={floor()};out.push_back(f);
    f=Fixture{};f.name="stack";for(unsigned i=1;i<=3;++i){auto b=body(i,{0,i-.5,0},double(i));b[20]=2*i;b[21]=i==1?5:i==2?-4:7;f.bodies.push_back(b);}f.planes={floor()};out.push_back(f);
    f=Fixture{};f.name="wedge";f.gravity={-6,-10,0};f.bodies={body(1,{})};f.planes={{100,0,1,0,-.5,0,0,0},{101,.6,.8,0,-.5,0,0,0}};out.push_back(f);
    f.name="wedge-release";f.gravity={-6,-1,0};out.push_back(f);
    f=Fixture{};f.name="active-set-counterexample";f.gravity={6,-7,0};f.bodies={body(1,{})};f.planes={{100,0,1,0,-.5,0,0,0},{101,.6,-.8,0,-.5,0,0,0}};out.push_back(f);
    f=Fixture{};f.name="return-and-rest";f.gravity={0,-40,0};f.bodies={body(1,{0,.5,0})};f.bodies[0][15]=1;f.planes={floor()};out.push_back(f);
    f=Fixture{};f.name="supported-collision";f.bodies={body(1,{0,.5,0}),body(2,{2,.5,0})};f.bodies[0][14]=20;for(auto& b:f.bodies){b[20]=2;b[26]=1;}f.planes={floor()};f.planes[0][5]=1;out.push_back(f);
    f=Fixture{};f.name="fast-crossing";f.gravity={};f.dt=1./120;f.bodies={body(1,{-2,0,0}),body(2,{2,0,0})};f.bodies[0][14]=1000;f.bodies[1][14]=-1000;for(auto& b:f.bodies)b[26]=1;out.push_back(f);
    f=Fixture{};f.name="curved-release";f.gravity={0,-4,0};f.ticks=8;f.bodies={body(1,{0,1,0}),body(2,{},1,true)};f.bodies[0][14]=1;out.push_back(f);
    f=Fixture{};f.name="terminal-impact";f.gravity={};f.dt=.05;f.ticks=2;f.bodies={body(1,{0,.55,0})};f.bodies[0][15]=-1;f.bodies[0][26]=1;f.planes={floor()};f.planes[0][5]=1;out.push_back(f);
    f=Fixture{};f.name="tiny-cold-newton";f.gravity={};f.dt=1./120;f.bodies={body(1,{0,.5,0})};f.bodies[0][15]=-1e-20;f.bodies[0][26]=1;f.planes={floor()};f.planes[0][5]=1;out.push_back(f);
    f=Fixture{};f.name="segment-budget";f.bodies={body(1,{0,.5,0})};f.bodies[0][20]=2;f.planes={floor()};f.settings[10]=1;out.push_back(f);
    f.name="attempt-budget";f.settings[10]=4096;f.settings[9]=1;out.push_back(f);
    f.name="guard-budget";f.settings[9]=16384;f.settings[13]=1;out.push_back(f);
    f=Fixture{};f.name="impact-then-rollback";f.bodies={body(1,{0,.5,0})};f.bodies[0][15]=-2;f.bodies[0][26]=1;f.bodies[0][20]=2;f.planes={floor()};f.planes[0][5]=1;f.settings[10]=1;out.push_back(f);
    f=Fixture{};f.name="friction-rejected";f.bodies={body(1,{0,.5,0})};f.bodies[0][27]=.5;f.planes={floor()};out.push_back(f);
    f=Fixture{};f.name="penetrated-rejected";f.bodies={body(1,{0,.49,0})};f.planes={floor()};out.push_back(f);
    return out;
}
int main(int argc,char** argv){try{
    if(argc!=2||std::string(argv[1])!="--fixtures")throw std::runtime_error("usage: pikapika-supported-probe --fixtures");
    std::cout<<std::setprecision(17)<<"{\"version\":1,\"model\":\"W2 normal-only RATTLE plus audited numerical paths\",\"fixtures\":[";
    bool first=true;for(const auto& f:cases()){
        if(!first)std::cout<<',';first=false;check(pp_sim_reset());const auto w=pp_sim_world_create();if(!w)throw std::runtime_error(pp_sim_error_ptr());
        input(std::array<double,3>{f.gravity.x,f.gravity.y,f.gravity.z});check(pp_sim_world_set_gravity(w,3));
        std::cout<<"{\"name\":\""<<f.name<<"\",\"input\":{\"gravity\":";print(std::array<double,3>{f.gravity.x,f.gravity.y,f.gravity.z});std::cout<<",\"dt\":"<<f.dt<<",\"ticks\":"<<f.ticks<<",\"settings\":";print(f.settings);
        std::cout<<",\"bodies\":[";bool comma=false;for(const auto& b:f.bodies){if(comma)std::cout<<',';comma=true;print(b);input(b);check(pp_sim_world_body_add(w,28));}
        std::cout<<"],\"planes\":[";comma=false;for(const auto& p:f.planes){if(comma)std::cout<<',';comma=true;print(p);input(p);check(pp_sim_world_plane_add(w,8));}std::cout<<"]},\"steps\":[";
        for(unsigned step=0;step<f.ticks;++step){
            if(step)std::cout<<',';
            for(const auto& b:f.bodies){check(pp_sim_world_body_get(w,b[0]));auto current=result();std::copy(b.begin()+20,b.begin()+26,current.begin()+20);input(current);check(pp_sim_world_body_set(w,28));}
            std::cout<<"{\"before\":[";comma=false;for(const auto& b:f.bodies){if(comma)std::cout<<',';comma=true;check(pp_sim_world_body_get(w,b[0]));print(result());}
            input(f.settings);check(pp_sim_world_step_supported(w,f.dt,33));auto summary=result();std::cout<<"],\"summary\":";print(summary);std::cout<<",\"events\":[";
            for(unsigned j=0;j<unsigned(summary[27]);++j){if(j)std::cout<<',';check(pp_sim_world_supported_event(w,j));print(result());}
            std::cout<<"],\"after\":[";comma=false;for(const auto& b:f.bodies){if(comma)std::cout<<',';comma=true;check(pp_sim_world_body_get(w,b[0]));print(result());}std::cout<<"]}";
            if(summary[0]==0)break;
        }
        std::cout<<"]}";check(pp_sim_world_destroy(w));
    }
    std::cout<<"]}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
