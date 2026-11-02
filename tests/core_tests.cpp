#include "pikapika/core.hpp"
#include "pikapika/portable.h"
#include <cmath>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <limits>

namespace {
unsigned passed=0;
void check(bool pass,const char* detail) { if(!pass) throw std::runtime_error(detail); }
bool near(double a,double b,double tolerance=1e-9) { return std::abs(a-b)<=tolerance; }
void rejects(const std::function<void()>& operation) {
    bool rejected=false; try { operation(); } catch(const std::exception&) { rejected=true; }
    check(rejected,"expected invalid input rejection");
}
void test(const char* name,const std::function<void()>& body) { body(); ++passed; std::cout<<"PASS "<<name<<'\n'; }
}
int main() {
    using namespace pikapika;
    try {
        test("right handed cross product",[]{const auto v=Vec3{1,0,0}.cross({0,1,0}); check(v.z==1,"x cross y = z");});
        test("portable C ABI scalar subset",[]{
            check(near(pp_integrate_velocity(2,10,0.1),3),"integrated position");
            check(near(pp_sweep_fraction(-100,0,0,200,0,0,1),0.495),"portable sweep");
            check(near(pp_direct_delay(343,343),1)&&near(pp_direct_pressure_gain(2,1),0.5),"portable audio");
        });
        test("quaternion transform",[]{
            const auto p=Transform{{10,0,0},{0,std::sqrt(0.5),0,std::sqrt(0.5)},{2,1,1}}.apply({1,0,0});
            check(near(p.x,10)&&near(p.z,-2),"scale then 90 degree Y rotation then translation");
        });
        test("sweep stops high speed tunneling",[]{
            const auto hit=sweep_sphere({-100,0,0},{100,0,0},0.5,{{0,0,0},0.5});
            check(hit&&near(hit->fraction,0.495)&&near(hit->position.x,-1),"analytic sweep time of impact");
        });
        test("sweep tangent miss overlap stationary",[]{
            check(sweep_sphere({-2,1,0},{2,1,0},0,{{0,0,0},1}).has_value(),"tangent");
            check(!sweep_sphere({-2,2,0},{2,2,0},0,{{0,0,0},1}),"miss");
            check(sweep_sphere({0,0,0},{0,0,0},0,{{0,0,0},1})->fraction==0,"overlap");
            check(!sweep_sphere({2,0,0},{2,0,0},0,{{0,0,0},1}),"stationary outside");
            rejects([]{sweep_sphere({},{},-1,{{},1});});
        });
        test("fixed step independent of render rate",[]{
            for(double rate:{30.,60.,144.}) {
                FixedClock clock; double position=0;
                for(int i=0;i<int(rate*10);++i) clock.advance(1/rate,[&](double dt){position+=12*dt;});
                check(clock.ticks()==1200&&near(position,120,1e-7),"ten seconds must produce 1200 ticks and 120m");
            }
        });
        test("fixed step overload is visible",[]{
            FixedClock clock(0.01,4); check(clock.advance(0.1,[](double){})==4,"step cap");
            check(near(clock.dropped_seconds(),0.06)&&clock.alpha()<1,"reported dropped time");
            rejects([&]{clock.advance(-1,[](double){});});
        });
        test("stable scene IDs survive edit save reload",[]{
            Scene scene; scene.entities.push_back({42,"box","quoted \"name\" \\ test",{},1});
            scene.annotations={"# browser-meta {\"nativeId\":\"42\",\"id\":\"authored-player\"}"};
            scene.set_position(42,{1.25,2,-3});
            std::stringstream first; scene.save(first); auto restored=Scene::load(first);
            check(restored.find(42)&&restored.find(42)->name==scene.find(42)->name,"metadata and ID");
            check(restored.annotations==scene.annotations,"opaque adapter metadata survives native roundtrip");
            check(near(restored.find(42)->transform.position.x,1.25),"position");
            std::stringstream second; restored.save(second); check(first.str()==second.str(),"canonical serialization");
            rejects([&]{restored.set_position(999,{});});
        });
        test("scene rejects duplicates invalid versions and nonfinite",[]{
            Scene scene; scene.entities.push_back({1,"box","one",{},1}); scene.entities.push_back(scene.entities[0]);
            rejects([&]{scene.validate();});
            std::stringstream version("pikapika-scene 99\nunits m s kg\naxes right-handed y-up\n");
            rejects([&]{Scene::load(version);});
            scene.entities.pop_back(); scene.entities[0].radius=std::numeric_limits<double>::infinity();
            rejects([&]{scene.validate();});
            scene.entities[0].radius=1; scene.entities[0].type="unknown-primitive";
            rejects([&]{scene.validate();});
            std::stringstream malformed("pikapika-scene 1\nunits m s kg\naxes right-handed y-up\nentity 1 broken\n");
            rejects([&]{Scene::load(malformed);});
        });
        test("camera source listener typed transforms survive native scene editing",[]{
            Scene scene;
            scene.entities={{4,"camera","Camera",{{0,18,65},{},{1,1,1}},0},
                            {5,"source","Source",{{-20,5,-10},{},{1,1,1}},0},
                            {6,"listener","Listener",{{0,5,30},{},{1,1,1}},0}};
            scene.set_position(5,{-10,6,-20});
            std::stringstream stream; scene.save(stream); const auto restored=Scene::load(stream);
            check(restored.entities.size()==3&&restored.find(4)->type=="camera"&&restored.find(6)->type=="listener","nongeometry types");
            check(restored.find(5)->type=="source"&&near(restored.find(5)->transform.position.y,6),"source edited position");
            const auto path=direct_sound(restored.find(5)->transform.position,restored.find(6)->transform.position);
            check(near(path.distance_meters,51)&&near(path.delay_seconds,51./343),"typed positions feed direct path acoustics");
            scene.entities[0].radius=1; rejects([&]{scene.validate();});
        });
        test("mesh create edit save reload preserves geometry and stable vertex indices",[]{
            Scene scene;Entity mesh{7,"mesh","Editable mesh",{},0};mesh.mesh=make_box_mesh({2,4,6});
            scene.entities.push_back(mesh);check(scene.format_version()==2,"mesh scene needs v2");
            scene.set_mesh_vertex(7,6,{1.5,2.5,3.5});std::stringstream out;scene.save(out);
            check(out.str().starts_with("pikapika-scene 2\n"),"v2 header");auto restored=Scene::load(out);
            const auto* e=restored.find(7);check(e&&e->mesh.positions.size()==8&&e->mesh.triangles==mesh.mesh.triangles,"stable indexed topology");
            check(near(e->mesh.positions[6].x,1.5)&&near(e->mesh.positions[6].z,3.5),"edited vertex survives");
            const auto previous=restored.find(7)->mesh.positions[0];
            rejects([&]{restored.set_mesh_vertex(7,0,restored.find(7)->mesh.positions[1]);});
            check(restored.find(7)->mesh.positions[0].x==previous.x,"failed edit must leave scene unchanged");
            rejects([&]{restored.set_mesh_vertex(7,999,{});});
        });
        test("mesh rejects invalid topology and incomplete or duplicate portable blocks",[]{
            auto mesh=make_box_mesh();mesh.triangles[0][2]=100;rejects([&]{mesh.validate();});
            mesh=make_box_mesh();mesh.positions[0].x=std::numeric_limits<double>::infinity();rejects([&]{mesh.validate();});
            mesh=make_box_mesh();mesh.positions.resize(65537);rejects([&]{mesh.validate();});
            mesh.positions={{999999,0,0},{999999.001,0,0},{999999,1,0}};mesh.triangles={{0,1,2}};
            rejects([&]{mesh.validate();});
            const std::string header="pikapika-scene 2\nunits m s kg\naxes right-handed y-up\n";
            const std::string entity="entity 1 \"mesh\" \"test\" 0 0 0 0 0 0 1 1 1 1 0\n";
            const std::string block="mesh 1 3 1\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\ntriangle 0 1 2\n";
            for(const auto& invalid:{header+entity,header+entity+"mesh 1 3 1\nvertex 0 0 0\n",header+entity+block+block}) {
                std::stringstream input(invalid);rejects([&]{Scene::load(input);});
            }
            std::stringstream legacy("pikapika-scene 1\nunits m s kg\naxes right-handed y-up\n"+entity+block);rejects([&]{Scene::load(legacy);});
        });
        test("direct pressure gain and delay analytic reference",[]{
            const auto a=direct_sound({},{10,0,0}), b=direct_sound({},{20,0,0});
            check(near(a.delay_seconds,10.0/343)&&near(b.pressure_gain/a.pressure_gain,0.5),"delay and inverse distance pressure");
            check(near(20*std::log10(b.pressure_gain/a.pressure_gain),-6.020599913,1e-8),"doubling distance = -6.0206 dB");
            check(direct_sound({},{}).pressure_gain==1,"near source clamp");
        });
        test("fractional sample impulse conserves pressure sum",[]{
            const DirectSound path{1,10.25/48000.,0.2}; const auto pcm=render_direct_impulse(path,48000,0.01);
            check(near(pcm[10],0.15,1e-7)&&near(pcm[11],0.05,1e-7),"fractional linear delay");
            double sum=0; for(auto x:pcm) sum+=x; check(near(sum,0.2,1e-7),"sum");
        });
        test("WAV PCM header and size",[]{
            std::ostringstream out(std::ios::binary); write_wav(out,{0,1,-1},48000); const auto bytes=out.str();
            check(bytes.size()==50&&bytes.substr(0,4)=="RIFF"&&bytes.substr(8,4)=="WAVE", "RIFF length");
            check(bytes.substr(36,4)=="data"&&static_cast<unsigned char>(bytes[40])==6,"data length");
            rejects([&]{write_wav(out,{std::numeric_limits<float>::quiet_NaN()},48000);});
        });
        std::cout<<passed<<" native core tests passed\n"; return 0;
    } catch(const std::exception& e) { std::cerr<<"FAIL "<<e.what()<<'\n'; return 1; }
}
