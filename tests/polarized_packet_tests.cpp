#include "pikapika/polarized_packet.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
using namespace pikapika;
namespace pp=polarized_packet;namespace pr=polarized_route;namespace rt=optical_route;namespace ob=optical_bounds;
using I=interval::Interval;
namespace {
I p(double x){return I::point(x);}
void require(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
pp::Packet packet(double watts=1,double x=0){pp::Packet v;v.power={watts,0,0,0};v.ray.origin=ob::enclose({x,0,-1});return v;}
rt::Step disk(Vec3 center,Vec3 normal,rt::Branch branch,double next){return {optical_geometry::PlaneDisk{center,normal,100},branch,p(next),0,1e6};}
struct Case {
    std::string name;std::vector<pp::Packet> packets{packet()};std::vector<rt::Step> steps;I index=p(1);optical_geometry::PlaneDisk sensor{{0,0,1.25},{0,0,-1},100};double sensorMin{0},sensorMax{1e6};pp::Settings settings;
    pp::Result run()const{return pp::evaluate({packets,steps,index,550e-9,sensor,sensorMin,sensorMax},settings);}
};
Case plate(std::string name){Case c;c.name=name;c.steps={disk({0,0,0},{0,0,-1},rt::Branch::transmitted,1.5),disk({0,0,.25},{0,0,1},rt::Branch::transmitted,1)};return c;}
Case ghost(std::string name){auto c=plate(name);c.steps={c.steps[0],disk({0,0,.25},{0,0,1},rt::Branch::reflected,1),disk({0,0,0},{0,0,-1},rt::Branch::reflected,1),c.steps[1]};return c;}
Case rational(std::string name){Case c;c.name=name;c.index=p(25);c.packets[0].ray.origin=ob::enclose({0,0,0});c.packets[0].transverse_reference={0,-1,0};c.steps={disk({0,0,1},{3,0,-4},rt::Branch::reflected,39),disk({24,0,-6},{-543,300,-76},rt::Branch::reflected,39)};c.sensor={{24,0,-7},{0,0,1},100};return c;}
std::vector<Case> cases(){
    std::vector<Case> cs;Case c;c.name="empty";c.packets.clear();cs.push_back(c);
    c=Case{};c.name="identity-bundle";c.packets={packet(2),packet(3,.25)};c.packets[1].power={3,0,0,3};cs.push_back(c);
    c=plate("normal-plate");c.packets={packet(2),packet(3,.25)};c.packets[0].power={2,0,2,0};c.packets[1].power={3,0,0,-3};cs.push_back(c);
    c=ghost("normal-ghost");c.packets={packet(2),packet(3,.25)};c.packets[1].power={3,3,0,0};cs.push_back(c);
    c=Case{};c.name="normal-reflection";c.steps={disk({0,0,0},{0,0,-1},rt::Branch::reflected,1.5)};c.sensor={{0,0,-2},{0,0,1},100};cs.push_back(c);
    c=rational("noncoplanar-unpolarized");cs.push_back(c);c.name="noncoplanar-u";c.packets[0].power={1,0,1,0};cs.push_back(c);
    c=Case{};c.name="two-tir";c.index=p(1.5);c.packets[0].ray.origin=ob::enclose({0,0,0});c.packets[0].ray.direction=ob::enclose({4,-3,0});c.packets[0].power={2,0,2,0};c.packets[0].transverse_reference={0,0,-1};c.steps={disk({4,-3,0},{0,1,0},rt::Branch::reflected,1),disk({8,0,0},{-96,3,80},rt::Branch::reflected,1)};c.sensor={{8,0,1},{0,0,-1},100};cs.push_back(c);
    c=plate("all-route-miss");c.packets[0].ray.origin[0]=p(1000);cs.push_back(c);
    c=Case{};c.name="all-sensor-miss";c.sensor.center.x=1000;c.sensor.aperture_radius=1;cs.push_back(c);
    c=Case{};c.name="mixed-sensor-miss";c.packets={packet(2),packet(3,1)};c.sensor.aperture_radius=.25;cs.push_back(c);
    c=plate("mixed-route-miss");c.packets={packet(2),packet(3,1000)};cs.push_back(c);
    c=Case{};c.name="sensor-boundary";c.packets[0].ray.origin[0]=I(.999,1.001);c.sensor.aperture_radius=1;cs.push_back(c);
    c=plate("power-prefix-route-miss");c.steps[1].surface=optical_geometry::PlaneDisk{{1000,0,.25},{0,0,1},1};cs.push_back(c);
    c=Case{};c.name="parallel-reference";c.packets[0].transverse_reference={0,0,1};cs.push_back(c);
    c=plate("near-normal-family");c.packets[0].ray.direction[0]=I(-1e-12,1e-12);cs.push_back(c);
    c=Case{};c.name="invalid-later-stokes";c.packets={packet(),packet()};c.packets[1].power={1,1,.01,0};cs.push_back(c);
    c=Case{};c.name="invalid-later-ray";c.packets={packet(),packet()};c.packets[1].ray.origin[0]=p(1000001);cs.push_back(c);
    c=plate("invalid-later-shape");c.steps[1].surface=optical_geometry::PlaneDisk{{0,0,.25},{0,0,0},1};cs.push_back(c);
    c=Case{};c.name="invalid-sensor";c.sensor.normal={0,0,0};cs.push_back(c);
    c=Case{};c.name="uncertain-cone";c.packets[0].power={5,3,4,0};cs.push_back(c);
    c=rational("batch-sqrt-budget");c.packets.push_back(c.packets[0]);c.settings.max_total_sqrt_refinements=1;cs.push_back(c);
    c=Case{};c.name="evaluation-budget";c.packets={packet(),packet()};c.settings.max_evaluations=1;cs.push_back(c);
    c=rational("packet-sqrt-budget");c.packets.push_back(c.packets[0]);c.settings.route.max_total_sqrt_refinements=1;cs.push_back(c);
    c=Case{};c.name="packet-count-budget";c.packets={packet(),packet()};c.settings.max_packets=1;cs.push_back(c);
    c=plate("step-count-budget");c.settings.route.route.maximum_steps=1;cs.push_back(c);
    c=rational("low-refinement");c.settings.route.max_sqrt_refinements=1;cs.push_back(c);
    c=plate("zero-power");c.packets[0].power={0,0,0,0};cs.push_back(c);
    c=plate("subnormal-power");c.packets={packet(std::numeric_limits<double>::denorm_min()),packet(std::numeric_limits<double>::denorm_min())};for(auto&v:c.packets)v.power.v=v.power.i;cs.push_back(c);
    c=plate("homogeneous");c.steps[0].next_index=p(1);cs.push_back(c);
    c=Case{};c.name="inclined-nonunit-sensor";c.packets[0].ray.direction=ob::enclose({3,0,4});c.sensor.normal={0,0,-13};cs.push_back(c);
    c=Case{};c.name="full-sphere";c.steps={{optical_geometry::FullSphere{{0,0,0},.5},rt::Branch::transmitted,p(1.5),0,1e6}};cs.push_back(c);
    c=Case{};c.name="spherical-cap";c.steps={{optical_geometry::SphericalCap{{0,0,0},{0,0,1},.5,.25},rt::Branch::transmitted,p(1.5),0,1e6}};cs.push_back(c);
    c=Case{};c.name="zero-power-unknown";c.packets[0].power={0,0,0,0};c.packets[0].transverse_reference={0,0,1};cs.push_back(c);
    c=Case{};c.name="mixed-known-unknown";c.packets={packet(2),packet(3)};c.packets[1].transverse_reference={0,0,1};cs.push_back(c);
    c=Case{};c.name="unavailable-branch";c.index=p(1.5);c.packets[0].ray.direction=ob::enclose({4,0,3});c.steps={disk({0,0,0},{0,0,-1},rt::Branch::transmitted,1)};cs.push_back(c);
    return cs;
}
void bound(I x){std::cout<<'['<<x.lower()<<','<<x.upper()<<']';}
void vec(const ob::Bounds3&v){std::cout<<'[';for(unsigned j=0;j<3;++j){if(j)std::cout<<',';bound(v[j]);}std::cout<<']';}
void point(Vec3 v){std::cout<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void power(pr::Stokes v){std::cout<<'['<<v.i<<','<<v.q<<','<<v.u<<','<<v.v<<']';}
void complex(pr::ComplexBounds v){std::cout<<'[';bound(v.real);std::cout<<',';bound(v.imag);std::cout<<']';}
void state(const pr::State&s){std::cout<<"{\"power\":";bound(s.power);std::cout<<",\"diagonal\":[";for(unsigned j=0;j<3;++j){if(j)std::cout<<',';bound(s.coherency.diagonal[j]);}std::cout<<"],\"upper\":[";for(unsigned j=0;j<3;++j){if(j)std::cout<<',';complex(s.coherency.upper[j]);}std::cout<<"]}";}
void route(const pr::Result&r){std::cout<<"{\"status\":"<<int(r.status)<<",\"powerFailure\":"<<int(r.power_failure)<<",\"geometryStatus\":"<<(r.geometry?int(r.geometry->status):-1)<<",\"completedPowerSteps\":"<<r.completed_power_steps<<",\"failedPowerStep\":"<<r.failed_power_step<<",\"counters\":["<<r.geometry_queries<<','<<r.interface_queries<<','<<r.geometry_sqrt_refinements<<','<<r.power_sqrt_refinements<<"],\"limited\":"<<(r.refinement_limited?"true":"false")<<",\"initial\":";if(r.initial_state)state(*r.initial_state);else std::cout<<"null";std::cout<<",\"segments\":[";
    for(unsigned j=0;j<r.segments.size();++j){if(j)std::cout<<',';const auto&s=r.segments[j];std::cout<<"{\"ordinal\":"<<s.ordinal<<",\"branch\":"<<int(s.branch)<<",\"exactNormal\":"<<(s.exact_normal?"true":"false")<<",\"homogeneous\":"<<(s.homogeneous?"true":"false")<<",\"s\":";if(s.s)complex(*s.s);else std::cout<<"null";std::cout<<",\"p\":";if(s.p)complex(*s.p);else std::cout<<"null";std::cout<<",\"state\":";if(s.outgoing)state(*s.outgoing);else std::cout<<"null";std::cout<<'}';}
    std::cout<<"],\"completion\":";if(r.completion){std::cout<<"{\"state\":";state(r.completion->state);std::cout<<",\"origin\":";vec(r.completion->ray.origin);std::cout<<",\"direction\":";vec(r.completion->ray.direction);std::cout<<",\"index\":";bound(r.completion->index);std::cout<<'}';}else std::cout<<"null";std::cout<<'}';
}
void sensor(const ob::Result&r){std::cout<<"{\"status\":"<<int(r.status)<<",\"reason\":"<<int(r.reason)<<",\"rootCount\":"<<r.root_count<<",\"consideredCount\":"<<r.considered_count<<",\"sqrt\":"<<r.sqrt_refinements<<",\"limited\":"<<(r.refinement_limited?"true":"false")<<",\"discriminant\":";if(r.discriminant)bound(*r.discriminant);else std::cout<<"null";std::cout<<",\"nearest\":";if(r.nearest){const auto&h=*r.nearest;std::cout<<"{\"parameter\":";bound(h.parameter);std::cout<<",\"distance\":";bound(h.physical_distance);std::cout<<",\"position\":";vec(h.position);std::cout<<",\"normal\":";vec(h.geometric_normal);std::cout<<",\"incidentNormal\":";vec(h.incident_normal);std::cout<<",\"frontFace\":"<<(h.front_face?"true":"false")<<'}';}else std::cout<<"null";std::cout<<'}';}
void json(const std::vector<Case>&cs){std::cout<<std::setprecision(17)<<"{\"schema\":1,\"fixtures\":[";
    for(unsigned j=0;j<cs.size();++j){if(j)std::cout<<',';const auto&c=cs[j];const auto r=c.run();std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"packets\":[";
        for(unsigned k=0;k<c.packets.size();++k){if(k)std::cout<<',';const auto&v=c.packets[k];std::cout<<"{\"origin\":";vec(v.ray.origin);std::cout<<",\"direction\":";vec(v.ray.direction);std::cout<<",\"domain\":["<<v.ray.minimum_parameter<<','<<v.ray.maximum_parameter<<"],\"power\":";power(v.power);std::cout<<",\"reference\":";point(v.transverse_reference);std::cout<<'}';}
        std::cout<<"],\"steps\":[";for(unsigned k=0;k<c.steps.size();++k){if(k)std::cout<<',';const auto&s=c.steps[k];std::cout<<"{\"kind\":"<<s.surface.index();std::visit([](const auto&d){using T=std::decay_t<decltype(d)>;if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>){std::cout<<",\"center\":";point(d.center);std::cout<<",\"normal\":";point(d.normal);std::cout<<",\"aperture\":"<<d.aperture_radius;}else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){std::cout<<",\"center\":";point(d.center);std::cout<<",\"radius\":"<<d.radius;}else{std::cout<<",\"vertex\":";point(d.vertex);std::cout<<",\"axis\":";point(d.axis);std::cout<<",\"radius\":"<<d.signed_radius<<",\"aperture\":"<<d.aperture_radius;}},s.surface);std::cout<<",\"branch\":"<<int(s.branch)<<",\"nextIndex\":";bound(s.next_index);std::cout<<",\"domain\":["<<s.minimum_parameter<<','<<s.maximum_parameter<<"]}";}
        std::cout<<"],\"index\":";bound(c.index);std::cout<<",\"wavelength\":5.5e-7,\"sensor\":{\"center\":";point(c.sensor.center);std::cout<<",\"normal\":";point(c.sensor.normal);std::cout<<",\"aperture\":"<<c.sensor.aperture_radius<<",\"domain\":["<<c.sensorMin<<','<<c.sensorMax<<"]},\"settings\":["<<c.settings.route.route.primitive.maximum_parameter_width<<','<<c.settings.route.route.primitive.max_sqrt_refinements<<','<<c.settings.route.route.maximum_steps<<','<<c.settings.route.max_sqrt_refinements<<','<<c.settings.route.max_total_sqrt_refinements<<','<<c.settings.max_packets<<','<<c.settings.max_evaluations<<','<<c.settings.max_total_sqrt_refinements<<"]},\"result\":{\"status\":"<<int(r.status)<<",\"counts\":["<<r.evaluations<<','<<r.accepted<<','<<r.route_misses<<','<<r.branch_unavailable<<','<<r.sensor_misses<<','<<r.unknown<<"],\"queries\":["<<r.geometry_queries<<','<<r.interface_queries<<','<<r.sensor_queries<<"],\"sqrt\":["<<r.geometry_sqrt_refinements<<','<<r.power_sqrt_refinements<<','<<r.sensor_sqrt_refinements<<"],\"limited\":"<<(r.refinement_limited?"true":"false")<<",\"stats\":";if(r.final_stats){std::cout<<"{\"totalSource\":";bound(r.final_stats->total_source_power);std::cout<<",\"acceptedSource\":";bound(r.final_stats->accepted_source_power);std::cout<<",\"detected\":";bound(r.final_stats->detected_power);std::cout<<'}';}else std::cout<<"null";
        std::cout<<",\"records\":[";for(unsigned k=0;k<r.records.size();++k){if(k)std::cout<<',';const auto&v=r.records[k];std::cout<<"{\"ordinal\":"<<v.ordinal<<",\"power\":";power(v.power);std::cout<<",\"status\":"<<int(v.status)<<",\"sensorPower\":";if(v.sensor_power)bound(*v.sensor_power);else std::cout<<"null";std::cout<<",\"route\":";if(v.route)route(*v.route);else std::cout<<"null";std::cout<<",\"sensor\":";if(v.sensor)sensor(*v.sensor);else std::cout<<"null";std::cout<<'}';}std::cout<<"]}}";
    }std::cout<<"]}\n";
}
void oracle(){std::cout<<"id,kind,I,Q,U,V,totalLo,totalHi,acceptedLo,acceptedHi,detectedLo,detectedHi\n"<<std::hexfloat;
    for(unsigned j=0;j<128;++j){auto c=j%3==0?Case{}:j%3==1?plate("oracle"):ghost("oracle");const double watts=1+double(j)/128;c.packets[0].power={watts,0,0,watts};const auto r=c.run();require(r.status==pp::Status::completed&&r.final_stats.has_value(),"Packet oracle corpus failed");const auto&s=*r.final_stats;std::cout<<j<<','<<j%3<<','<<watts<<",0x0p+0,0x0p+0,"<<watts;for(I x:{s.total_source_power,s.accepted_source_power,s.detected_power})std::cout<<','<<x.lower()<<','<<x.upper();std::cout<<'\n';}
}
}
int main(int argc,char**argv){try{const auto cs=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){json(cs);return 0;}if(argc==2&&std::string(argv[1])=="--oracle"){oracle();return 0;}unsigned passed=0;
    for(const auto&c:cs){const auto r=c.run();const bool invalid=c.name.starts_with("invalid-"),budget=c.name.ends_with("budget"),unknown=c.name=="sensor-boundary"||c.name=="parallel-reference"||c.name=="near-normal-family"||c.name=="uncertain-cone"||c.name=="zero-power-unknown"||c.name=="mixed-known-unknown";
        if(invalid)require(r.status==pp::Status::invalid_input&&r.evaluations==0&&!r.final_stats,"Invalid input was not preflighted");
        else if(budget)require(r.status==pp::Status::budget_exceeded&&!r.final_stats,"Budget acquired tally");
        else if(unknown){if(r.status==pp::Status::completed)std::cerr<<c.name<<" unexpectedly completed\n";require(r.status==pp::Status::unresolved&&!r.final_stats,"Unknown acquired tally");}
        else {if(r.status!=pp::Status::completed)std::cerr<<c.name<<": "<<int(r.status)<<' '<<r.message<<'\n';require(r.status==pp::Status::completed&&r.final_stats.has_value(),"Expected completed tally");const auto&s=*r.final_stats;require(s.detected_power.lower()>=0&&s.detected_power.upper()<=s.accepted_source_power.upper()&&s.accepted_source_power.upper()<=s.total_source_power.upper(),"Power sum passivity");
            if(c.name=="normal-plate")require(s.detected_power.contains(5*.96*.96),"Normal plate POWER absent");
            if(c.name=="normal-ghost")require(s.detected_power.contains(5*.96*.96*.04*.04),"Ghost POWER absent");
            if(c.name=="subnormal-power")require(s.detected_power.upper()>0,"Subnormal POWER lost");
            if(c.name=="power-prefix-route-miss")require(r.records[0].route->completed_power_steps==1&&r.records[0].route->segments[0].outgoing.has_value(),"Power diagnostic prefix lost");
            if(c.name=="low-refinement")require(r.refinement_limited,"Valid wide enclosure lost limited flag");
        }
        require(r.unknown+r.accepted+r.route_misses+r.branch_unavailable+r.sensor_misses==r.records.size(),"Classification count mismatch");++passed;
    }
    const auto stable=plate("reuse");require(stable.run().status==pp::Status::completed&&stable.run().status==pp::Status::completed,"Failure contaminated later evaluate");++passed;
    auto bad=plate("nan");bad.packets[0].power.v=std::numeric_limits<double>::quiet_NaN();require(bad.run().status==pp::Status::invalid_input,"NaN accepted");++passed;
    auto branch=Case{};branch.name="unavailable";branch.index=p(1.5);branch.packets[0].ray.direction=ob::enclose({4,0,3});branch.steps={disk({0,0,0},{0,0,-1},rt::Branch::transmitted,1)};const auto br=branch.run();require(br.status==pp::Status::completed&&br.branch_unavailable==1&&br.final_stats->detected_power.upper()==0,"Unavailable path not known zero");++passed;
    auto retry=rational("retry");retry.settings.max_total_sqrt_refinements=1;require(retry.run().status==pp::Status::budget_exceeded,"Retry setup did not fail");retry.settings.max_total_sqrt_refinements=1000000;require(retry.run().status==pp::Status::completed,"Budget failure contaminated retry");++passed;
    auto split=plate("split");split.packets={packet(.5),packet(.5)};const auto sr=split.run();require(sr.final_stats&&sr.final_stats->total_source_power.contains(1)&&sr.final_stats->detected_power.contains(.96*.96),"Explicit POWER partition changed detected watts");++passed;
    Case emptyInvalid;emptyInvalid.packets.clear();emptyInvalid.sensor.normal={0,0,0};require(emptyInvalid.run().status==pp::Status::invalid_input,"Empty packets bypassed sensor domain preflight");++passed;
    std::cout<<"polarized-packet: "<<passed<<" groups PASS\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
