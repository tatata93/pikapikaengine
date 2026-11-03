#include "pikapika/optical_spot.hpp"
#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
using namespace pikapika;
namespace s=pikapika::optical_spot;
namespace r=pikapika::optical_route;
namespace b=pikapika::optical_bounds;
namespace g=pikapika::optical_geometry;
using I=interval::Interval;
namespace {
unsigned groups=0;
I p(double v){return I::point(v);}
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void contains(I value,double reference){check(value.contains(reference),"reference inside interval");}
void test(const char* name,const std::function<void()>& f){f();++groups;std::cout<<"PASS "<<name<<'\n';}
template<class F>void rejects(F f){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}check(failed,"invalid helper input rejected");}
struct Case {
    std::string name;std::vector<s::Sample> samples;
    std::vector<r::Step> steps;I initial_index=p(1);double wavelength{550e-9};
    g::PlaneDisk sensor{{0,0,1},{0,0,-1},10};double sensor_lo{0},sensor_hi{10};s::Settings settings;
    s::Input input()const{return {samples,steps,initial_index,wavelength,sensor,sensor_lo,sensor_hi};}
};
std::vector<s::Sample> bundle(){std::vector<s::Sample> samples;const Vec3 points[]{{-1,0,0},{1,0,0},{0,-1,0},{0,1,0}};for(unsigned j=0;j<4;++j)samples.push_back({s::make_launch_ray({s::SourceKind::parallel_beam,{0,0,2}},points[j],0,10),double(j+1)});return samples;}
std::vector<r::Step> plates(I n=p(1.5)){return {{g::PlaneDisk{{},{0,0,-1},10},r::Branch::transmitted,n,0,10},{g::PlaneDisk{{0,0,.25},{0,0,1},10},r::Branch::transmitted,p(1),0,10}};}
Case lens(double h){Case c;c.sensor.center.z=639./11800.;c.steps={{g::SphericalCap{{},{0,0,1},.05,.015},r::Branch::transmitted,p(1.5),0,10},{g::SphericalCap{{0,0,.005},{0,0,1},-.05,.015},r::Branch::transmitted,p(1),0,10}};
    for(Vec3 point:std::initializer_list<Vec3>{{h,0,-.025},{-h,0,-.025},{0,h,-.025},{0,-h,-.025}})c.samples.push_back({s::make_launch_ray({s::SourceKind::parallel_beam,{0,0,1}},point,0,10),1});return c;
}
std::vector<Case> cases(){std::vector<Case> out;
    const auto add=[&](const char* name){out.push_back({});out.back().name=name;out.back().samples=bundle();return &out.back();};
    add("identity");auto c=add("scaled-weights");for(auto& v:c->samples)v.weight*=8;
    c=add("tilted-sensor");c->sensor.normal={3,0,4};
    c=add("plates");c->steps=plates();c->sensor.center.z=1.25;for(auto& v:c->samples)v.ray.origin[2]=p(-1);
    c=add("route-miss");c->samples.resize(1);c->steps={{g::PlaneDisk{{},{0,0,-1},.25},r::Branch::transmitted,p(1),0,10}};
    c=add("mixed-route-miss");c->samples.resize(2);c->samples[0].ray.origin[0]=p(0);c->steps={{g::PlaneDisk{{},{0,0,-1},.25},r::Branch::transmitted,p(1),0,10}};
    c=add("sensor-miss");c->samples.resize(1);c->sensor.aperture_radius=.25;
    c=add("mixed-sensor-miss");c->samples.resize(2);c->samples[0].ray.origin[0]=p(0);c->sensor.aperture_radius=.25;
    c=add("unknown-sensor");c->samples.resize(2);c->samples[0].ray.origin[0]=p(0);c->samples[1].ray.origin[0]=p(.25);c->sensor.aperture_radius=.25;
    c=add("unknown-route");c->samples.resize(2);c->samples[0].ray.origin[0]=p(0);c->steps={{g::PlaneDisk{{},{0,0,-1},1},r::Branch::transmitted,p(1),0,10}};
    c=add("unavailable-transmission");c->samples={{b::enclose_ray({{0,0,-1},{4,0,3},0,10}),1}};c->initial_index=p(1.5);c->steps={{g::PlaneDisk{{},{0,0,-1},10},r::Branch::transmitted,p(1),0,10}};
    c=add("evaluation-budget");c->settings.max_evaluations=1;
    c=add("total-sqrt-budget");*c=lens(.001);c->name="total-sqrt-budget";c->settings.max_sqrt_refinements=1;
    c=add("primitive-budget");c->samples={{b::enclose_ray({{0,0,0},{.125,0,1},0,10}),1}};c->steps={{g::FullSphere{{0,0,3},1},r::Branch::transmitted,p(1.5),0,10}};c->settings.route.primitive.max_sqrt_refinements=1;c->settings.route.primitive.maximum_parameter_width=.01;
    c=add("invalid-late-weight");c->samples.back().weight=0;
    c=add("invalid-late-shape");c->steps=plates();c->steps[1].surface=g::FullSphere{{},-1};
    c=add("empty");c->samples.clear();
    c=add("sample-budget");c->settings.max_samples=1;
    c=add("step-budget");c->steps=plates();c->settings.route.maximum_steps=1;
    c=add("zero-direction");c->samples.resize(1);c->samples[0].ray.direction=b::enclose({});
    c=add("sensor-boundary");c->samples.resize(1);c->sensor_hi=.5;
    c=add("spectral-interval");c->steps=plates(I(1.49,1.51));c->sensor.center.z=1.25;for(auto& v:c->samples)v.ray.origin[2]=p(-1);
    c=add("lens-small");*c=lens(.0005);c->name="lens-small";
    c=add("lens-marginal");*c=lens(.014);c->name="lens-marginal";
    c=add("finite-source");c->samples.clear();const Vec3 pts[]{{-1,0,0},{1,0,0},{0,-1,0},{0,1,0}};for(unsigned j=0;j<4;++j)c->samples.push_back({s::make_launch_ray({s::SourceKind::finite_point,{0,0,-1}},pts[j],0,10),double(j+1)});
    return out;
}
const Case& named(const std::vector<Case>& all,const char* name){const auto i=std::find_if(all.begin(),all.end(),[&](const auto& c){return c.name==name;});check(i!=all.end(),"fixture exists");return *i;}
s::Result run(const std::vector<Case>& all,const char* name){const auto& c=named(all,name);return s::evaluate(c.input(),c.settings);}
const s::Moments& moments(const s::Result& result){check(result.status==s::Status::completed&&result.final_stats&&result.final_stats->moments,"final moments exist");return *result.final_stats->moments;}
I focus(const s::Result& result){const auto& ray=result.records[0].route->completion->ray;check(!ray.direction[0].contains_zero(),"nonaxial focus denominator");return ray.origin[2]-ray.origin[0]*ray.direction[2]/ray.direction[0];}
double middle(I i){return (i.lower()+i.upper())*.5;}
void tests(){const auto all=cases();
    test("identity weighted geometric moments have independent rational values",[&]{const auto r=run(all,"identity");const auto& m=moments(r);contains(r.final_stats->total_weight,10);contains(r.final_stats->accepted_weight,10);contains(m.centroid[0],.1);contains(m.centroid[1],.1);contains(m.centroid[2],1);contains(m.mean_squared_radius,.98);check(r.records.size()==4&&r.accepted==4&&r.evaluations==4&&r.geometry_queries==4&&r.interface_queries==0,"all samples sensor-only");});
    test("weight scale invariance preserves moments and scales geometric measure",[&]{const auto a=run(all,"identity"),z=run(all,"scaled-weights");contains(moments(z).mean_squared_radius,.98);contains(z.final_stats->total_weight,80);for(unsigned k=0;k<3;++k)check(interval::intersection(moments(a).centroid[k],moments(z).centroid[k]).has_value(),"same centroid");});
    test("nonunit direction and tilted sensor use 3D plane distances",[&]{const auto r=run(all,"tilted-sensor");const auto& m=moments(r);contains(m.centroid[2],37./40);contains(m.mean_squared_radius,1829./1600);contains(r.records[0].sensor->nearest->parameter,.875);contains(r.records[0].sensor->nearest->physical_distance,1.75);});
    test("prescribed parallel plates preserve spot and have no sensor interface",[&]{const auto r=run(all,"plates");contains(moments(r).mean_squared_radius,.98);check(r.geometry_queries==12&&r.interface_queries==8,"two interfaces and one geometry sensor per sample");contains(r.records[0].route->completion->totals.throughput,.9216);contains(r.records[0].route->completion->totals.optical_path_length,1.375);});
    test("all missed rays and empty bundle have defined zero accepted measure",[&]{for(const char* n:{"route-miss","sensor-miss","empty","unavailable-transmission"}){const auto r=run(all,n);check(r.status==s::Status::completed&&r.final_stats&&!r.final_stats->moments,"no artificial centroid for empty acceptance");contains(r.final_stats->accepted_weight,0);check(r.unknown==0,"known omissions only");}});
    test("mixed accepted and proved missed samples preserve both weights",[&]{for(const char* n:{"mixed-route-miss","mixed-sensor-miss"}){const auto r=run(all,n);contains(r.final_stats->total_weight,3);contains(r.final_stats->accepted_weight,1);contains(moments(r).centroid[0],0);contains(moments(r).mean_squared_radius,0);check(r.accepted==1&&r.records[1].weight==2,"omitted input weight retained");}});
    test("unknown sensor or route cannot be blackened or normalized away",[&]{for(const char* n:{"unknown-sensor","unknown-route","zero-direction","sensor-boundary"}){const auto r=run(all,n);check(r.status==s::Status::unresolved&&!r.final_stats&&r.unknown>0,"unknown suppresses final stats");}});
    test("evaluation budget retains all input records and not examined entries",[&]{const auto r=run(all,"evaluation-budget");check(r.status==s::Status::budget_exceeded&&!r.final_stats&&r.evaluations==1&&r.records.size()==4&&r.accepted==1&&r.unknown==3,"bounded partial batch");check(r.records[1].status==s::SampleStatus::not_examined&&!r.records[1].route,"unexamined is explicit");});
    test("actual reported sqrt overshoot fails atomically after one sample",[&]{const auto r=run(all,"total-sqrt-budget");check(r.status==s::Status::budget_exceeded&&!r.final_stats&&r.evaluations==1&&r.sqrt_refinements>1&&r.accepted==0&&r.unknown==4,"overshoot kept as budget unknown");check(r.records[0].sensor&&r.records[0].status==s::SampleStatus::budget_exceeded,"geometry diagnostics retained");});
    test("primitive refinement budget is not converted to miss",[&]{const auto r=run(all,"primitive-budget");check(r.status==s::Status::budget_exceeded&&!r.final_stats&&r.refinement_limited&&r.route_misses==0,"primitive budget retained");});
    test("whole batch weight and shape validation precedes evaluations",[&]{for(const char* n:{"invalid-late-weight","invalid-late-shape"}){const auto r=run(all,n);check(r.status==s::Status::invalid_input&&!r.final_stats&&r.evaluations==0&&r.records.empty(),"preflight atomic");}for(const char* n:{"sample-budget","step-budget"}){const auto r=run(all,n);check(r.status==s::Status::budget_exceeded&&r.evaluations==0,"preflight quota");}});
    test("full phase index interval is retained through each plate",[&]{const auto r=run(all,"spectral-interval");contains(moments(r).mean_squared_radius,.98);check(r.records[0].route->completion->index.contains(1),"final medium retained");});
    test("finite source and parallel helper retain exact launch geometry",[&]{const auto r=run(all,"finite-source");contains(moments(r).centroid[0],.2);contains(moments(r).centroid[1],.2);contains(moments(r).mean_squared_radius,98./25);const auto finite=s::make_launch_ray({s::SourceKind::finite_point,{.1,0,-1}},{.3,0,0});check(finite.direction[0].lower()<finite.direction[0].upper(),"finite subtraction is outward not point-rounded");const auto parallel=s::make_launch_ray({s::SourceKind::parallel_beam,{0,0,2}},{.3,0,0});contains(parallel.direction[2],2);contains(parallel.origin[0],.3);});
    test("finite launch preserves a term lost by rounded source subtraction",[]{const auto ray=s::make_launch_ray({s::SourceKind::finite_point,{std::ldexp(1.,19),0,-1}},{std::ldexp(1.,-40),0,-.01});check(ray.direction[0].lower()<=-std::ldexp(1.,19)&&ray.direction[0].upper()>-std::ldexp(1.,19),"true positive low term enclosed beyond rounded difference");});
    test("helper rejects invalid source type domain and generated vector extent",[]{rejects([]{s::make_launch_ray({s::SourceKind(99),{}},{});});rejects([]{s::make_launch_ray({}, {},-1,1);});rejects([]{s::make_launch_ray({s::SourceKind::finite_point,{-1e6,0,0}},{1e6,0,0});});});
    test("paraxial focus has second-order small pupil convergence",[]{double errors[3]{};for(unsigned j=0;j<3;++j){const auto c=lens(.002/std::pow(2.,j));const auto r=s::evaluate(c.input());moments(r);const I f=focus(r);errors[j]=639./11800-middle(f);check(errors[j]>0&&f.lower()>.005,"finite radius focus before paraxial sensor");}check(errors[0]/errors[1]>3.8&&errors[0]/errors[1]<4.2&&errors[1]/errors[2]>3.8&&errors[1]/errors[2]<4.2,"paraxial second order");});
    test("finite pupil spherical aberration survives interval rendering data",[&]{const auto a=run(all,"lens-small"),z=run(all,"lens-marginal");check(focus(z).upper()<focus(a).lower(),"marginal focus earlier");check(moments(z).mean_squared_radius.lower()>moments(a).mean_squared_radius.upper(),"finite aperture spread");});
    test("input wavelength ray and budget validation is reusable",[&]{auto c=named(all,"identity");c.wavelength=0;check(s::evaluate(c.input()).status==s::Status::invalid_input,"bad wavelength");c=named(all,"identity");c.samples[0].weight=std::numeric_limits<double>::infinity();check(s::evaluate(c.input()).status==s::Status::invalid_input,"nonfinite weight");c=named(all,"identity");c.settings.max_evaluations=1025;check(s::evaluate(c.input(),c.settings).status==s::Status::invalid_input,"budget range");moments(run(all,"identity"));});
#if !defined(__EMSCRIPTEN__)
    test("unsupported rounding environment fails numerically then recovers",[&]{const auto& c=named(all,"identity");const auto input=c.input();const int old=std::fegetround();check(std::fesetround(FE_UPWARD)==0,"set rounding");const auto r=s::evaluate(input);std::fesetround(old);check(r.status==s::Status::numerical_failure&&!r.final_stats&&r.evaluations==0,"environment is not input error");moments(s::evaluate(input));});
#endif
}
void emit(I x){std::cout<<'['<<x.lower()<<','<<x.upper()<<']';}
void emit(const b::Bounds3& x){std::cout<<'[';for(unsigned k=0;k<3;++k){if(k)std::cout<<',';emit(x[k]);}std::cout<<']';}
void emit(Vec3 x){std::cout<<'['<<x.x<<','<<x.y<<','<<x.z<<']';}
void emit(const b::BoundedRay& ray){std::cout<<"{\"origin\":";emit(ray.origin);std::cout<<",\"direction\":";emit(ray.direction);std::cout<<",\"minimumParameter\":"<<ray.minimum_parameter<<",\"maximumParameter\":"<<ray.maximum_parameter<<'}';}
void emit(const r::Totals& t){std::cout<<"{\"distance\":";emit(t.distance);std::cout<<",\"opticalPathLength\":";emit(t.optical_path_length);std::cout<<",\"throughput\":";emit(t.throughput);std::cout<<'}';}
void emit(const r::Completion& c){std::cout<<"{\"ray\":";emit(c.ray);std::cout<<",\"index\":";emit(c.index);std::cout<<",\"totals\":";emit(c.totals);std::cout<<'}';}
void emit(const b::Hit& h){std::cout<<"{\"parameter\":";emit(h.parameter);std::cout<<",\"distance\":";emit(h.physical_distance);std::cout<<",\"position\":";emit(h.position);std::cout<<",\"geometricNormal\":";emit(h.geometric_normal);std::cout<<",\"incidentNormal\":";emit(h.incident_normal);std::cout<<",\"frontFace\":"<<(h.front_face?"true":"false")<<'}';}
void emit(const b::Result& g){std::cout<<"{\"status\":"<<int(g.status)<<",\"reason\":"<<int(g.reason)<<",\"rootCount\":"<<g.root_count<<",\"consideredCount\":"<<g.considered_count<<",\"sqrtRefinements\":"<<g.sqrt_refinements<<",\"refinementLimited\":"<<(g.refinement_limited?"true":"false")<<",\"nearest\":";if(g.nearest)emit(*g.nearest);else std::cout<<"null";std::cout<<'}';}
void emit(const s::Moments& m){std::cout<<"{\"centroid\":";emit(m.centroid);std::cout<<",\"meanSquaredRadius\":";emit(m.mean_squared_radius);std::cout<<",\"hull\":";emit(m.hull);std::cout<<'}';}
void emit(const s::Result& result){std::cout<<"{\"status\":"<<int(result.status)<<",\"evaluations\":"<<result.evaluations<<",\"accepted\":"<<result.accepted<<",\"routeMisses\":"<<result.route_misses<<",\"branchUnavailable\":"<<result.branch_unavailable<<",\"sensorMisses\":"<<result.sensor_misses<<",\"unknown\":"<<result.unknown<<",\"geometryQueries\":"<<result.geometry_queries<<",\"interfaceQueries\":"<<result.interface_queries<<",\"sqrtRefinements\":"<<result.sqrt_refinements<<",\"refinementLimited\":"<<(result.refinement_limited?"true":"false")<<",\"finalStats\":";if(result.final_stats){const auto& st=*result.final_stats;std::cout<<"{\"totalWeight\":";emit(st.total_weight);std::cout<<",\"acceptedWeight\":";emit(st.accepted_weight);std::cout<<",\"moments\":";if(st.moments)emit(*st.moments);else std::cout<<"null";std::cout<<'}';}else std::cout<<"null";std::cout<<",\"records\":[";
    bool first=true;for(const auto& rec:result.records){if(!first)std::cout<<',';first=false;std::cout<<"{\"ordinal\":"<<rec.ordinal<<",\"weight\":"<<rec.weight<<",\"status\":"<<int(rec.status)<<",\"route\":";if(rec.route){const auto& q=*rec.route;std::cout<<"{\"status\":"<<int(q.status)<<",\"completedSteps\":"<<q.completed_steps<<",\"failedStep\":"<<q.failed_step<<",\"geometryQueries\":"<<q.geometry_queries<<",\"interfaceQueries\":"<<q.interface_queries<<",\"sqrtRefinements\":"<<q.sqrt_refinements<<",\"refinementLimited\":"<<(q.refinement_limited?"true":"false")<<",\"completion\":";if(q.completion)emit(*q.completion);else std::cout<<"null";std::cout<<'}';}else std::cout<<"null";std::cout<<",\"sensor\":";if(rec.sensor)emit(*rec.sensor);else std::cout<<"null";std::cout<<'}';}std::cout<<"]}";
}
void emit(const r::Surface& surface){std::cout<<"{\"kind\":"<<surface.index()<<",\"center\":";std::visit([](const auto& shape){using T=std::decay_t<decltype(shape)>;if constexpr(std::is_same_v<T,g::PlaneDisk>){emit(shape.center);std::cout<<",\"axis\":";emit(shape.normal);std::cout<<",\"radius\":0,\"aperture\":"<<shape.aperture_radius;}else if constexpr(std::is_same_v<T,g::FullSphere>){emit(shape.center);std::cout<<",\"axis\":[0,0,1],\"radius\":"<<shape.radius<<",\"aperture\":0";}else{emit(shape.vertex);std::cout<<",\"axis\":";emit(shape.axis);std::cout<<",\"radius\":"<<shape.signed_radius<<",\"aperture\":"<<shape.aperture_radius;}},surface);std::cout<<'}';}
void emit(const Case& c){std::cout<<"{\"samples\":[";bool first=true;for(const auto& x:c.samples){if(!first)std::cout<<',';first=false;std::cout<<"{\"ray\":";emit(x.ray);std::cout<<",\"weight\":"<<x.weight<<'}';}std::cout<<"],\"steps\":[";first=true;for(const auto& step:c.steps){if(!first)std::cout<<',';first=false;std::cout<<"{\"surface\":";emit(step.surface);std::cout<<",\"branch\":"<<int(step.branch)<<",\"nextIndex\":";emit(step.next_index);std::cout<<",\"minimumParameter\":"<<step.minimum_parameter<<",\"maximumParameter\":"<<step.maximum_parameter<<'}';}std::cout<<"],\"initialIndex\":";emit(c.initial_index);std::cout<<",\"wavelength\":"<<c.wavelength<<",\"sensor\":";emit(r::Surface(c.sensor));std::cout<<",\"sensorMinimumParameter\":"<<c.sensor_lo<<",\"sensorMaximumParameter\":"<<c.sensor_hi<<",\"settings\":{\"maximumSteps\":"<<c.settings.route.maximum_steps<<",\"maximumParameterWidth\":"<<c.settings.route.primitive.maximum_parameter_width<<",\"primitiveMaxSqrtRefinements\":"<<c.settings.route.primitive.max_sqrt_refinements<<",\"maxSamples\":"<<c.settings.max_samples<<",\"maxEvaluations\":"<<c.settings.max_evaluations<<",\"maxSqrtRefinements\":"<<c.settings.max_sqrt_refinements<<"}}";}
void fixtures(){std::cout<<std::setprecision(17)<<"{\"version\":1,\"model\":\"prescribed-route finite geometric spot\",\"fixtures\":[";bool first=true;for(const auto& c:cases()){if(!first)std::cout<<',';first=false;std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":";emit(c);std::cout<<",\"result\":";emit(s::evaluate(c.input(),c.settings));std::cout<<'}';}std::cout<<"],\"launch\":[";for(unsigned j=0;j<2;++j){if(j)std::cout<<',';const s::Source source=j==0?s::Source{s::SourceKind::finite_point,{std::ldexp(1.,19),0,-1}}:s::Source{s::SourceKind::parallel_beam,{.125,.25,2}};const Vec3 point=j==0?Vec3{std::ldexp(1.,-40),0,-.01}:Vec3{.3,-.2,-.01};std::cout<<"{\"kind\":"<<int(source.kind)<<",\"reference\":";emit(source.reference);std::cout<<",\"point\":";emit(point);std::cout<<",\"ray\":";emit(s::make_launch_ray(source,point));std::cout<<'}';}std::cout<<"],\"paraxial\":[";for(unsigned j=0;j<3;++j){if(j)std::cout<<',';const double h=.002/std::pow(2.,j);const auto c=lens(h);const auto result=s::evaluate(c.input());std::cout<<"{\"pupilRadius\":"<<h<<",\"focus\":";emit(focus(result));std::cout<<",\"meanSquaredRadius\":";emit(moments(result).mean_squared_radius);std::cout<<'}';}std::cout<<"]}\n";}
void hex(double value){std::cout<<std::hex<<std::setfill('0')<<std::setw(16)<<std::bit_cast<std::uint64_t>(value)<<std::dec;}
void oracle(){std::cout<<"k,a,weight0,weight1,weight2,weight3,totalLo,totalHi,cxLo,cxHi,cyLo,cyHi,czLo,czHi,varLo,varHi,hxLo,hxHi,hyLo,hyHi,hzLo,hzHi\n";for(unsigned k=1;k<=128;++k){Case c;const double a=double(k)/256;c.samples=bundle();const Vec3 points[]{{-a,0,0},{a,0,0},{0,-a,0},{0,a,0}};for(unsigned j=0;j<4;++j){c.samples[j].ray.origin=b::enclose(points[j]);c.samples[j].weight=double((k+j)%7+1);}const auto result=s::evaluate(c.input());const auto& m=moments(result);std::cout<<k;for(double v:{a,c.samples[0].weight,c.samples[1].weight,c.samples[2].weight,c.samples[3].weight}){std::cout<<',';hex(v);}for(I v:{result.final_stats->total_weight,m.centroid[0],m.centroid[1],m.centroid[2],m.mean_squared_radius,m.hull[0],m.hull[1],m.hull[2]}){std::cout<<',';hex(v.lower());std::cout<<',';hex(v.upper());}std::cout<<'\n';}}
}
int main(int argc,char** argv){try{if(argc==2&&std::string(argv[1])=="--fixtures")fixtures();else if(argc==2&&std::string(argv[1])=="--oracle")oracle();else{tests();std::cout<<"Optical spot: "<<groups<<" groups\n";}return 0;}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
