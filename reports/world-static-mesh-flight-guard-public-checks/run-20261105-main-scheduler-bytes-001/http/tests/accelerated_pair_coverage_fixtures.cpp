#include "accelerated_pair_coverage_test_support.hpp"
#include <cmath>
#include <iomanip>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <utility>
namespace coverage_fixture {
namespace c=coverage;
namespace {
void number(std::ostream& o,double x){if(!std::isfinite(x)){throw std::runtime_error("Nonfinite fixture bound");}if(x==0&&std::signbit(x)){o<<"-0";}else{o<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x;}}
void vec(std::ostream& o,pikapika::Vec3 v){o<<'[';number(o,v.x);o<<',';number(o,v.y);o<<',';number(o,v.z);o<<']';}
void sphere(std::ostream& o,const accelerated::Sphere& s){o<<"{\"center\":";vec(o,s.center);o<<",\"velocity\":";vec(o,s.velocity);o<<",\"acceleration\":";vec(o,s.acceleration);o<<",\"radius\":";number(o,s.radius);o<<'}';}
void plane(std::ostream& o,const accelerated::StaticPlane& p){o<<"{\"normal\":";vec(o,p.normal);o<<",\"offset\":";number(o,p.offset);o<<'}';}
void settings(std::ostream& o,const c::Settings& s){o<<"{\"timeTolerance\":";number(o,s.time_tolerance);o<<",\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<'}';}
void source(std::ostream& o,const c::Input& input){if(const auto* pair=std::get_if<c::SpherePair>(&input)){o<<"{\"kind\":\"sphere_pair\",\"first\":";sphere(o,pair->first);o<<",\"second\":";sphere(o,pair->second);o<<'}';}else{const auto& plane_input=std::get<c::SpherePlane>(input);o<<"{\"kind\":\"sphere_plane\",\"sphere\":";sphere(o,plane_input.sphere);o<<",\"plane\":";plane(o,plane_input.plane);o<<'}';}}
void whole_input(std::ostream& o,const c::Input& input,double h,const c::Settings& s){o<<"{\"input\":";source(o,input);o<<",\"horizon\":";number(o,h);o<<",\"settings\":";settings(o,s);o<<'}';}
template<class T>void index(std::ostream& o,const std::optional<T>& x){if(x){o<<*x;}else{o<<"null";}}
void cell(std::ostream& o,const c::Cell& x){o<<"{\"timeBounds\":[";number(o,x.time_bounds[0]);o<<',';number(o,x.time_bounds[1]);o<<"],\"depth\":"<<x.depth<<",\"parentAudit\":";index(o,x.parent_audit);o<<'}';}
const char* reason(c::Reason r){constexpr const char* names[]={"none","settings","horizon","input_domain","zero_normal","evaluation_budget","leaf_budget","depth_budget","width_limit","time_resolution","nonpositive_value","value_exception","allocation_failure","environment","coverage_inconsistent"};return names[unsigned(r)];}
const char* status(c::Status s){constexpr const char* names[]={"certified","not_certified","invalid_input","unsupported_environment"};return names[unsigned(s)];}
void audit(std::ostream& o,const c::Audit& a){constexpr const char* outcomes[]={"pending","positive","split","blocked"};o<<"{\"cell\":";cell(o,a.cell);o<<",\"callAttempted\":"<<(a.call_attempted?"true":"false")<<",\"value\":";if(a.value){o<<'[';number(o,a.value->lower());o<<',';number(o,a.value->upper());o<<']';}else{o<<"null";}o<<",\"outcome\":\""<<outcomes[unsigned(a.outcome)]<<"\",\"blockedReason\":\""<<reason(a.blocked_reason)<<"\",\"splitTime\":";if(a.split_time){number(o,*a.split_time);}else{o<<"null";}o<<'}';}
void leaf(std::ostream& o,const c::PartitionLeaf& x){constexpr const char* states[]={"unqueried","certified","blocked","current"};o<<"{\"cell\":";cell(o,x.cell);o<<",\"state\":\""<<states[unsigned(x.state)]<<"\",\"auditIndex\":";index(o,x.audit_index);o<<",\"blockedReason\":\""<<reason(x.blocked_reason)<<"\"}";}
template<class T,class F>void array(std::ostream& o,const std::vector<T>& a,F writer){o<<'[';for(std::size_t i=0;i<a.size();++i){if(i){o<<',';}writer(o,a[i]);}o<<']';}
void invalid(Case& x,c::Reason r,std::optional<std::size_t> input={}){x.expected=c::Status::invalid_input;x.reason=r;x.failed_input=input;}
}
Case sphere_case(){Case x;x.name="sphere-static-safe";x.input=c::SpherePair{accelerated::Sphere{{-0.,-0.,0},{-0.,0,0},{0,-0.,0},.25},accelerated::Sphere{{4,0,-0.},{0,-0.,0},{-0.,0,0},.25}};return x;}
Case plane_case(){Case x;x.name="plane-static-safe";x.input=c::SpherePlane{accelerated::Sphere{{-0.,2,-0.},{-0.,0,0},{0,-0.,0},.25},accelerated::StaticPlane{{-0.,1,-0.},-0.}};return x;}
c::Result query(const Case& x){if(const auto* p=std::get_if<c::SpherePair>(&x.input)){return c::sphere_sphere(p->first,p->second,x.horizon,x.settings);}const auto& p=std::get<c::SpherePlane>(x.input);return c::sphere_plane(p.sphere,p.plane,x.horizon,x.settings);}
std::vector<Case> cases(){std::vector<Case> out;auto add=[&](Case x){out.push_back(std::move(x));};Case x=sphere_case();add(x);x=plane_case();add(x);
    x=sphere_case();x.name="sphere-equal-motion-common-offset";{auto& p=std::get<c::SpherePair>(x.input);p.first.center={0x1p39,1,-0.};p.second.center={0x1p39+4,1,-0.};p.first.velocity=p.second.velocity={7,-3,1};p.first.acceleration=p.second.acceleration={2,4,-1};}add(x);
    x=sphere_case();x.name="sphere-real-subtraction-lost-low-term";{auto& p=std::get<c::SpherePair>(x.input);p.first.center.x=1e12;p.second.center.x=std::numeric_limits<double>::denorm_min();}add(x);
    x=sphere_case();x.name="sphere-real-positive-difference-subnormal";{auto& p=std::get<c::SpherePair>(x.input);p.first.radius=p.second.radius=std::numeric_limits<double>::denorm_min();p.second.center.x=16*std::numeric_limits<double>::denorm_min();}x.expected=c::Status::not_certified;add(x);
    x=sphere_case();x.name="sphere-safe-parabolic-subdivision";{auto& p=std::get<c::SpherePair>(x.input);p.second.center={-1,1.75,0};p.second.velocity={32,-64,0};p.second.acceleration={0,2048,0};}add(x);
    x=sphere_case();x.name="sphere-quartic-nonrational-stationary";{auto& p=std::get<c::SpherePair>(x.input);p.second.center={-1,1,0};p.second.velocity={20,.3,0};p.second.acceleration={2,14,0};}x.horizon=.1;add(x);
    x=sphere_case();x.name="sphere-asymmetric-relative-acceleration";{auto& p=std::get<c::SpherePair>(x.input);p.first.velocity={.125,-.25,.5};p.first.acceleration={-3,2,-1};p.second.velocity={7,3,-2};p.second.acceleration={2,-5,4};}add(x);
    x=sphere_case();x.name="sphere-high-speed-interior-crossing";std::get<c::SpherePair>(x.input).second.velocity={-128,0,0};x.expected=c::Status::not_certified;add(x);
    x=sphere_case();x.name="sphere-initial-negative";std::get<c::SpherePair>(x.input).second.center={.125,0,0};x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=sphere_case();x.name="sphere-initial-boundary-then-separates";{auto& p=std::get<c::SpherePair>(x.input);p.second.center={.5,0,0};p.second.velocity={4,0,0};}x.expected=c::Status::not_certified;add(x);
    x=sphere_case();x.name="sphere-tangent-midpoint";{auto& p=std::get<c::SpherePair>(x.input);p.second.center={-1,.5,0};p.second.velocity={32,0,0};}x.expected=c::Status::not_certified;add(x);
    x=sphere_case();x.name="sphere-static-contact-full-capacity";std::get<c::SpherePair>(x.input).second.center={.5,0,0};x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x.name="sphere-contact-127-evaluations-full-frontier";x.settings.max_evaluations=127;x.reason=c::Reason::evaluation_budget;add(x);
    x.name="sphere-contact-one-evaluation";x.settings.max_evaluations=1;add(x);
    x.name="sphere-contact-one-leaf";x.settings.max_evaluations=255;x.settings.max_leaves=1;x.reason=c::Reason::leaf_budget;add(x);
    x.name="sphere-contact-depth-zero";x.settings.max_leaves=128;x.settings.max_depth=0;x.reason=c::Reason::depth_budget;add(x);
    x.name="sphere-contact-width-limit";x.settings.max_depth=24;x.settings.time_tolerance=.1;x.reason=c::Reason::width_limit;add(x);
    x=sphere_case();x.name="sphere-contact-nonuniform-seconds";std::get<c::SpherePair>(x.input).second.center={.5,0,0};x.horizon=.03;x.settings.time_tolerance=.003;x.expected=c::Status::not_certified;add(x);
    x=sphere_case();x.name="sphere-safe-minimum-duration";x.horizon=std::numeric_limits<double>::denorm_min();add(x);
    x=sphere_case();x.name="sphere-safe-one-call-one-leaf-depth-zero";x.settings.max_evaluations=1;x.settings.max_leaves=1;x.settings.max_depth=0;add(x);
    x=sphere_case();x.name="sphere-contact-adjacent-time-endpoints";std::get<c::SpherePair>(x.input).second.center={.5,0,0};x.horizon=std::numeric_limits<double>::denorm_min();x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x.name="sphere-contact-two-subnormal-seconds";x.horizon=2*std::numeric_limits<double>::denorm_min();add(x);
    x=plane_case();x.name="plane-nonunit-axis";std::get<c::SpherePlane>(x.input).plane.normal={0,2,0};add(x);
    x=plane_case();x.name="plane-negative-axis";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={0,-3,0};p.sphere.center.y=-2;p.plane.offset=-.125;}add(x);
    x=plane_case();x.name="plane-irrational-normal";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={1,1,0};p.sphere.center={2,2,-0.};}add(x);
    x=plane_case();x.name="plane-three-component-normal";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={2,-3,6};p.sphere.center={2,-3,6};p.plane.offset=.125;p.sphere.radius=.5;}add(x);
    x=plane_case();x.name="plane-oblique-dynamic";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={1,2,-1};p.sphere.center={2,3,-2};p.sphere.velocity={-1,2,.5};p.sphere.acceleration={3,-4,2};}add(x);
    x=plane_case();x.name="plane-safe-parabolic-subdivision";{auto& p=std::get<c::SpherePlane>(x.input);p.sphere.center.y=1.75;p.sphere.velocity.y=-64;p.sphere.acceleration.y=2048;p.sphere.radius=.5;}add(x);
    x=plane_case();x.name="plane-interior-crossing-safe-endpoints";{auto& p=std::get<c::SpherePlane>(x.input);p.sphere.center.y=1;p.sphere.velocity.y=-64;p.sphere.acceleration.y=2048;p.sphere.radius=.25;}x.expected=c::Status::not_certified;add(x);
    x=plane_case();x.name="plane-initial-negative";std::get<c::SpherePlane>(x.input).sphere.center.y=-2;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=plane_case();x.name="plane-initial-boundary";std::get<c::SpherePlane>(x.input).sphere.center.y=.25;x.expected=c::Status::not_certified;add(x);
    x=plane_case();x.name="plane-quadratic-tangent";{auto& p=std::get<c::SpherePlane>(x.input);p.sphere.center.y=1+.0009765625;p.sphere.velocity.y=-.0625;p.sphere.acceleration.y=2;p.sphere.radius=1;}x.settings.max_depth=32;x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x=plane_case();x.name="plane-tiny-axis-normal-preserved";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={0,std::numeric_limits<double>::denorm_min(),-0.};p.sphere.center.y=4;}x.expected.reset();add(x);
    x=plane_case();x.name="plane-tiny-oblique-normal-preserved";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={std::numeric_limits<double>::denorm_min(),std::numeric_limits<double>::denorm_min(),-0.};p.sphere.center={4,4,0};}x.expected.reset();add(x);
    x=plane_case();x.name="plane-maximum-input-domain";{auto& p=std::get<c::SpherePlane>(x.input);p.plane.normal={0,1e12,0};p.plane.offset=-1e12;p.sphere.center.y=1e12;p.sphere.velocity.x=1e12;p.sphere.acceleration.z=-1e12;}x.horizon=.1;add(x);
    x=sphere_case();x.name="sphere-maximum-radius-domain";{auto& p=std::get<c::SpherePair>(x.input);p.first.radius=p.second.radius=1e12;p.first.center.x=-1e12;p.second.center.x=1e12;}x.expected=c::Status::not_certified;add(x);
    for(unsigned field=0;field<5;++field){for(unsigned side=0;side<2;++side){x=sphere_case();x.name="invalid-setting-"+std::to_string(field)+(side?"-high":"-low");switch(field){case 0:x.settings.time_tolerance=side?std::nextafter(.1,1.):-0.;break;case 1:x.settings.max_evaluations=side?256:0;break;case 2:x.settings.max_leaves=side?129:0;break;case 3:if(!side){continue;}x.settings.max_depth=33;break;default:if(side){continue;}x.settings.time_tolerance=-.001;break;}invalid(x,c::Reason::settings);add(x);}}
    for(unsigned which=0;which<3;++which){x=sphere_case();x.name="invalid-horizon-"+std::to_string(which);x.horizon=which==0?-0.:which==1?-.01:std::nextafter(.1,1.);invalid(x,c::Reason::horizon);add(x);}
    for(unsigned sphere_index=0;sphere_index<2;++sphere_index){for(unsigned field=0;field<5;++field){x=sphere_case();x.name="invalid-sphere-"+std::to_string(sphere_index)+"-field-"+std::to_string(field);auto& pair=std::get<c::SpherePair>(x.input);auto& s=sphere_index?pair.second:pair.first;switch(field){case 0:s.center.x=std::nextafter(1e12,2e12);break;case 1:s.velocity.y=-std::nextafter(1e12,2e12);break;case 2:s.acceleration.z=std::nextafter(1e12,2e12);break;case 3:s.radius=-0.;break;default:s.radius=std::nextafter(1e12,2e12);break;}invalid(x,c::Reason::input_domain,sphere_index);add(x);}}
    x=plane_case();x.name="invalid-plane-sphere-radius";std::get<c::SpherePlane>(x.input).sphere.radius=-1;invalid(x,c::Reason::input_domain,0);add(x);
    x=plane_case();x.name="invalid-plane-normal-domain";std::get<c::SpherePlane>(x.input).plane.normal.x=std::nextafter(1e12,2e12);invalid(x,c::Reason::input_domain,1);add(x);
    x=plane_case();x.name="invalid-plane-offset-domain";std::get<c::SpherePlane>(x.input).plane.offset=-std::nextafter(1e12,2e12);invalid(x,c::Reason::input_domain,1);add(x);
    x=plane_case();x.name="invalid-plane-zero-normal-signed-zero";std::get<c::SpherePlane>(x.input).plane.normal={-0.,0,-0.};invalid(x,c::Reason::zero_normal,1);add(x);
    x.name="invalid-settings-before-zero-normal";x.settings.max_evaluations=0;invalid(x,c::Reason::settings);add(x);
    x.name="invalid-settings-before-horizon";x.horizon=-0.;add(x);
    x=plane_case();x.name="invalid-horizon-before-sphere";x.horizon=-0.;std::get<c::SpherePlane>(x.input).sphere.radius=0;invalid(x,c::Reason::horizon);add(x);
    return out;
}
void input_json(std::ostream& o,const Case& x){whole_input(o,x.input,x.horizon,x.settings);}
void snapshot_json(std::ostream& o,const c::Snapshot& s){whole_input(o,s.input,s.horizon,s.settings);}
void result_json(std::ostream& o,const c::Result& r){o<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"snapshot\":";if(r.snapshot){snapshot_json(o,*r.snapshot);}else{o<<"null";}o<<",\"snapshotValidated\":"<<(r.snapshot_validated?"true":"false")<<",\"failedInput\":";index(o,r.failed_input);o<<",\"partitionComplete\":"<<(r.partition_complete?"true":"false")<<",\"audits\":";array(o,r.audits,audit);o<<",\"partition\":";array(o,r.partition,leaf);o<<",\"frontier\":";array(o,r.frontier,cell);o<<",\"current\":";if(r.current){cell(o,*r.current);}else{o<<"null";}const auto& w=r.work;o<<",\"work\":{\"valueCallsAttempted\":"<<w.value_calls_attempted<<",\"valueCallsReturned\":"<<w.value_calls_returned<<",\"planeNormCallsUpper\":"<<w.plane_norm_calls_upper<<",\"planeNormLoopIterationsUpper\":"<<w.plane_norm_loop_iterations_upper<<"}}";}
void emit_fixtures(std::ostream& o,const std::vector<Case>& corpus){o<<"{\"schema\":1,\"kind\":\"accelerated-pair-coverage-fixtures\",\"fixtures\":[";for(std::size_t i=0;i<corpus.size();++i){if(i){o<<',';}const auto& x=corpus[i];o<<"{\"name\":\""<<x.name<<"\",\"input\":";input_json(o,x);o<<",\"result\":";result_json(o,query(x));o<<'}';}o<<"]}\n";}
}
