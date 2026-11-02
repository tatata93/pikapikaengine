#include "pikapika/core.hpp"
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
double number(const char* text) {
    std::size_t used=0; const std::string token(text); const auto n=std::stod(token,&used);
    if(used!=token.size()||!std::isfinite(n)) throw std::runtime_error("expected finite numeric argument");
    return n;
}
pikapika::Scene read(const char* path) {
    std::ifstream in(path); if(!in) throw std::runtime_error("cannot open scene");
    return pikapika::Scene::load(in);
}
void save(const pikapika::Scene& scene,const char* path) {
    std::ofstream out(path); if(!out) throw std::runtime_error("cannot create scene"); scene.save(out);
}
}
int main(int argc,char** argv) {
    try {
        if(argc<2) throw std::runtime_error("missing command (run pikapika help)");
        const std::string command=argv[1];
        if(command=="help") {
            std::cout<<"pikapika init <scene>\npikapika inspect <scene>\npikapika move <input> <id> <x> <y> <z> <output>\n"
                     <<"pikapika roundtrip <input> <output>\npikapika audio <distance-m> <output.wav>\npikapika simulate <seconds>\n";
        } else if(command=="init"&&argc==3) {
            pikapika::Scene scene;
            scene.entities.push_back({1,"robot","Player",{{0,1,0},{},{1,1,1}},1});
            scene.entities.push_back({2,"box","Target",{{0,1,-20},{},{2,2,2}},2});
            scene.entities.push_back({3,"plane","Ground",{{0,0,0},{},{100,1,100}},0});
            save(scene,argv[2]); std::cout<<"created scene version 1, entities=3\n";
        } else if(command=="inspect"&&argc==3) {
            const auto scene=read(argv[2]);
            std::cout<<"scene version=1 units=m,s,kg right-handed y-up entities="<<scene.entities.size()<<'\n';
            for(const auto& e:scene.entities) std::cout<<e.id<<" "<<e.type<<" "<<e.name<<'\n';
        } else if(command=="move"&&argc==8) {
            auto scene=read(argv[2]); const double raw_id=number(argv[3]);
            if(raw_id<1||raw_id>9007199254740991.0||std::floor(raw_id)!=raw_id) throw std::runtime_error("invalid stable ID");
            scene.set_position(static_cast<std::uint64_t>(raw_id),{number(argv[4]),number(argv[5]),number(argv[6])});
            save(scene,argv[7]); std::cout<<"position updated through Scene::set_position\n";
        } else if(command=="roundtrip"&&argc==4) {
            save(read(argv[2]),argv[3]); std::cout<<"scene validated and saved\n";
        } else if(command=="audio"&&argc==4) {
            const double distance=number(argv[2]); if(distance<0||distance>17000) throw std::runtime_error("distance must be 0..17000 m");
            const auto sound=pikapika::direct_sound({0,0,0},{distance,0,0});
            const auto pcm=pikapika::render_direct_impulse(sound,48000,sound.delay_seconds+0.1);
            std::ofstream out(argv[3],std::ios::binary); if(!out) throw std::runtime_error("cannot create WAV");
            pikapika::write_wav(out,pcm,48000);
            std::cout<<"ideal direct impulse delay_s="<<sound.delay_seconds<<" pressure_gain="<<sound.pressure_gain<<" sample_rate=48000\n";
        } else if(command=="simulate"&&argc==3) {
            const double seconds=number(argv[2]); if(seconds<0||seconds>3600) throw std::runtime_error("simulation duration must be 0..3600 s");
            pikapika::FixedClock clock; pikapika::Vec3 p{}; const pikapika::Vec3 velocity{10,0,0};
            for(double elapsed=0;elapsed<seconds;) {
                const double frame=std::min(1.0/60,seconds-elapsed);
                clock.advance(frame,[&](double dt){p=p+velocity*dt;}); elapsed+=frame;
            }
            std::cout<<"headless ticks="<<clock.ticks()<<" position_m="<<p.x<<','<<p.y<<','<<p.z
                     <<" dropped_s="<<clock.dropped_seconds()<<'\n';
        } else throw std::runtime_error("unknown command or invalid argument count (run pikapika help)");
        return 0;
    } catch(const std::exception& e) { std::cerr<<"pikapika: "<<e.what()<<'\n'; return 1; }
}
