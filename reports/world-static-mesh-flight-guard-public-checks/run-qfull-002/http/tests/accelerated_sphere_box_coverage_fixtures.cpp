#include "accelerated_sphere_box_coverage_test_support.hpp"
#include <cmath>
#include <iomanip>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <utility>
namespace sphere_box_fixture {
namespace c=coverage;
namespace {
void number(std::ostream& o,double x){if(!std::isfinite(x)){throw std::runtime_error("Nonfinite fixture bound");}if(x==0&&std::signbit(x)){o<<"-0";}else{o<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x;}}
void vec(std::ostream& o,pikapika::Vec3 v){o<<'[';number(o,v.x);o<<',';number(o,v.y);o<<',';number(o,v.z);o<<']';}
void sphere(std::ostream& o,const pikapika::accelerated::Sphere& s){o<<"{\"center\":";vec(o,s.center);o<<",\"velocity\":";vec(o,s.velocity);o<<",\"acceleration\":";vec(o,s.acceleration);o<<",\"radius\":";number(o,s.radius);o<<'}';}
void source(std::ostream& o,const c::Input& x){o<<"{\"first\":";sphere(o,x.first);o<<",\"second\":";sphere(o,x.second);o<<",\"firstPositionError\":";number(o,x.first_position_error);o<<",\"secondPositionError\":";number(o,x.second_position_error);o<<",\"contactMargin\":";number(o,x.contact_margin);o<<'}';}
void settings(std::ostream& o,const c::Settings& s){o<<"{\"timeTolerance\":";number(o,s.time_tolerance);o<<",\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<",\"sqrtRefinements\":"<<s.sqrt_refinements<<'}';}
void whole_input(std::ostream& o,const c::Input& input,double h,const c::Settings& s){o<<"{\"input\":";source(o,input);o<<",\"horizon\":";number(o,h);o<<",\"settings\":";settings(o,s);o<<'}';}
template<class T>void index(std::ostream& o,const std::optional<T>& x){if(x){o<<*x;}else{o<<"null";}}
void cell(std::ostream& o,const c::Cell& x){o<<"{\"timeBounds\":[";number(o,x.time_bounds[0]);o<<',';number(o,x.time_bounds[1]);o<<"],\"depth\":"<<x.depth<<",\"parentAudit\":";index(o,x.parent_audit);o<<'}';}
void interval(std::ostream& o,const pikapika::interval::Interval& x){o<<'[';number(o,x.lower());o<<',';number(o,x.upper());o<<']';}
void evaluation(std::ostream& o,const c::Evaluation& x){const auto coords=[&](const auto& a){o<<'[';for(std::size_t i=0;i<3;++i){if(i){o<<',';}interval(o,a[i]);}o<<']';};o<<"{\"firstCoordinates\":";coords(x.first_coordinates);o<<",\"secondCoordinates\":";coords(x.second_coordinates);o<<",\"delta\":";coords(x.delta);o<<",\"rawSquaredDistance\":";interval(o,x.raw_squared_distance);o<<",\"nonnegativeSquaredDistance\":";interval(o,x.nonnegative_squared_distance);o<<",\"root\":{\"value\":";interval(o,x.root.value);o<<",\"refinements\":"<<x.root.refinements<<",\"refinementLimited\":"<<(x.root.refinement_limited?"true":"false")<<"},\"distance\":";interval(o,x.distance);o<<",\"threshold\":";interval(o,x.threshold);o<<",\"gap\":";interval(o,x.gap);o<<'}';}
const char* reason(c::Reason r){constexpr const char* names[]={"none","settings","horizon","input_domain","position_error","contact_margin","evaluation_budget","leaf_budget","depth_budget","width_limit","time_resolution","nonpositive_value","value_exception","allocation_failure","environment","coverage_inconsistent"};return names[unsigned(r)];}
const char* status(c::Status s){constexpr const char* names[]={"certified","not_certified","invalid_input","unsupported_environment"};return names[unsigned(s)];}
void audit(std::ostream& o,const c::Audit& a){constexpr const char* outcomes[]={"pending","positive","split","blocked"};o<<"{\"cell\":";cell(o,a.cell);o<<",\"callAttempted\":"<<(a.call_attempted?"true":"false")<<",\"evaluation\":";if(a.evaluation){evaluation(o,*a.evaluation);}else{o<<"null";}o<<",\"outcome\":\""<<outcomes[unsigned(a.outcome)]<<"\",\"blockedReason\":\""<<reason(a.blocked_reason)<<"\",\"splitTime\":";if(a.split_time){number(o,*a.split_time);}else{o<<"null";}o<<'}';}
void leaf(std::ostream& o,const c::PartitionLeaf& x){constexpr const char* states[]={"unqueried","certified","blocked","current"};o<<"{\"cell\":";cell(o,x.cell);o<<",\"state\":\""<<states[unsigned(x.state)]<<"\",\"auditIndex\":";index(o,x.audit_index);o<<",\"blockedReason\":\""<<reason(x.blocked_reason)<<"\"}";}
template<class T,class F>void array(std::ostream& o,const std::vector<T>& a,F writer){o<<'[';for(std::size_t i=0;i<a.size();++i){if(i){o<<',';}writer(o,a[i]);}o<<']';}
void invalid(Case& x,c::Reason r,std::optional<std::size_t> input={}){x.expected=c::Status::invalid_input;x.reason=r;x.failed_input=input;}
}
Case base_case(){Case x;x.name="static-safe-original-radii";return x;}
std::vector<Case> cases(){std::vector<Case> out;auto add=[&](Case x){out.push_back(std::move(x));};Case x=base_case();add(x);
    x=base_case();x.name="explicit-negative-zero-both-b-margin";x.input.first_position_error=-0.;x.input.second_position_error=-0.;x.input.contact_margin=-0.;add(x);
    x=base_case();x.name="safe-both-positive-b-and-margin";x.input.first_position_error=.125;x.input.second_position_error=.25;x.input.contact_margin=.0625;add(x);
    x=base_case();x.name="safe-parabolic-subdivision";x.input.second.center={-1,1.75,0};x.input.second.velocity={32,-64,0};x.input.second.acceleration={0,2048,0};x.input.first_position_error=.03125;x.input.second_position_error=.03125;x.input.contact_margin=.0625;add(x);
    x=base_case();x.name="unsafe-interior-safe-endpoints";x.input.second.center.x=2;x.input.second.velocity.x=-64;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="initial-overlap-static";x.input.second.center.x=.125;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="initial-boundary-then-separates";x.input.second.center.x=.5;x.input.second.velocity.x=4;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="quadratic-tangent-interior";x.input.second.center={0,.5009765625,0};x.input.second.velocity.y=-.0625;x.input.second.acceleration.y=2;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="static-contact-full-capacity";x.input.second.center.x=.5;x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x.name="contact-127-evaluations-full-frontier";x.settings.max_evaluations=127;x.reason=c::Reason::evaluation_budget;add(x);
    x.name="contact-one-evaluation";x.settings.max_evaluations=1;add(x);
    x.name="contact-one-leaf";x.settings.max_evaluations=255;x.settings.max_leaves=1;x.reason=c::Reason::leaf_budget;add(x);
    x.name="contact-depth-zero";x.settings.max_leaves=128;x.settings.max_depth=0;x.reason=c::Reason::depth_budget;add(x);
    x.name="contact-width-limit";x.settings.max_depth=24;x.settings.time_tolerance=.1;x.reason=c::Reason::width_limit;add(x);
    x=base_case();x.name="safe-one-call-one-leaf-depth-zero";x.settings.max_evaluations=1;x.settings.max_leaves=1;x.settings.max_depth=0;add(x);
    x=base_case();x.name="safe-minimum-duration";x.horizon=std::numeric_limits<double>::denorm_min();add(x);
    x=base_case();x.name="contact-two-subnormal-seconds";x.input.second.center.x=.5;x.horizon=2*std::numeric_limits<double>::denorm_min();x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="contact-nonuniform-global-seconds";x.input.second.center.x=.5;x.horizon=.03;x.settings.time_tolerance=.003;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="safe-maximum-depth-setting";x.settings.max_depth=32;x.horizon=.1;add(x);
    for(unsigned ref:{1U,128U,256U}){x=base_case();x.name="safe-root-refinements-"+std::to_string(ref);x.settings.sqrt_refinements=ref;add(x);}
    x=base_case();x.name="safe-oblique-moving-both";x.input.first.velocity={1,-2,.5};x.input.first.acceleration={-3,4,2};x.input.second.center={4,3,-2};x.input.second.velocity={-2,1,-.5};x.input.second.acceleration={2,-3,4};x.input.first_position_error=.0625;x.input.second_position_error=.125;add(x);
    x=base_case();x.name="first-b-omission-would-certify";x.input.second.center.x=.75;x.input.first_position_error=.375;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;x.reason=c::Reason::evaluation_budget;add(x);
    x=base_case();x.name="second-b-omission-would-certify";x.input.second.center.x=.75;x.input.second_position_error=.375;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;x.reason=c::Reason::evaluation_budget;add(x);
    x=base_case();x.name="margin-zero-geometrically-safe";x.input.second.center.x=.53125;add(x);
    x.name="margin-contact-counterexample";x.input.contact_margin=.0625;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="subtraction-rounds-away-real-gap";x.input.first.center.x=-0x1p-53;x.input.second.center.x=1;x.input.first.radius=.5;x.input.second.radius=.5;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="dot-rounds-away-real-gap";x.input.second.center={1,0x1p-27,0};x.input.first.radius=.5;x.input.second.radius=.5;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="sqrt-rounds-away-real-gap";x.input.second.center={1,0x1p-26,0};x.input.first.radius=.5;x.input.second.radius=.5;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="left-associated-threshold-counterexample";x.input.first.radius=1;x.input.second.radius=0x1p-53;x.input.contact_margin=0x1p-53;x.input.second.center.x=1.25;add(x);
    x=base_case();x.name="huge-common-offset-cancellation-safe";x.input.first.center={0x1p39,0x1p39,0x1p39};x.input.second.center={0x1p39+4,0x1p39,0x1p39};add(x);
    for(int direction:{-1,0,1}){x=base_case();x.name=direction<0?"binade-before":direction>0?"binade-after":"binade-at";const double center=direction<0?std::nextafter(0x1p39,0.):direction>0?std::nextafter(0x1p39,1e12):0x1p39;x.input.first.center.x=center;x.input.second.center.x=center+4;add(x);}
    x=base_case();x.name="subnormal-half-acceleration-preserved";x.input.first.acceleration.y=std::numeric_limits<double>::denorm_min();x.horizon=.1;add(x);
    x=base_case();x.name="tiny-original-radii-safe";x.input.first.radius=std::numeric_limits<double>::denorm_min();x.input.second.radius=std::numeric_limits<double>::denorm_min();add(x);
    x=base_case();x.name="zero-distance-clamps-raw-negative-lower";x.input.second.center={0,0,0};x.input.first_position_error=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="maximum-point-domains";x.input.first.center={-1e12,1e12,0};x.input.second.center={1e12,-1e12,1e12};x.input.first.velocity.x=1e12;x.input.second.acceleration.z=-1e12;x.input.first.radius=1e12;x.input.second.radius=1e12;x.horizon=.1;x.expected.reset();add(x);
    for(unsigned which=0;which<2;++which){x=base_case();x.name=which?"maximum-second-b":"maximum-first-b";(which?x.input.second_position_error:x.input.first_position_error)=1e12;x.settings.max_leaves=1;x.expected=c::Status::not_certified;add(x);}
    for(unsigned field=0;field<5;++field){for(unsigned high=0;high<2;++high){x=base_case();x.name="invalid-setting-"+std::to_string(field)+(high?"-high":"-low");switch(field){case 0:x.settings.time_tolerance=high?std::nextafter(.1,1.):-0.;break;case 1:x.settings.max_evaluations=high?256:0;break;case 2:x.settings.max_leaves=high?129:0;break;case 3:if(!high){continue;}x.settings.max_depth=33;break;default:x.settings.sqrt_refinements=high?257:0;break;}invalid(x,c::Reason::settings);add(x);}}
    for(unsigned which=0;which<3;++which){x=base_case();x.name="invalid-horizon-"+std::to_string(which);x.horizon=which==0?-0.:which==1?-.01:std::nextafter(.1,1.);invalid(x,c::Reason::horizon);add(x);}
    for(unsigned sphere_index=0;sphere_index<2;++sphere_index){for(unsigned field=0;field<5;++field){x=base_case();x.name="invalid-sphere-"+std::to_string(sphere_index)+"-field-"+std::to_string(field);auto& s=sphere_index?x.input.second:x.input.first;switch(field){case 0:s.center.x=std::nextafter(1e12,2e12);break;case 1:s.velocity.y=-std::nextafter(1e12,2e12);break;case 2:s.acceleration.z=std::nextafter(1e12,2e12);break;case 3:s.radius=-0.;break;default:s.radius=std::nextafter(1e12,2e12);break;}invalid(x,c::Reason::input_domain,sphere_index);add(x);}}
    for(unsigned field=0;field<3;++field){for(unsigned high=0;high<2;++high){x=base_case();x.name="invalid-error-margin-"+std::to_string(field)+(high?"-high":"-negative");double& v=field==0?x.input.first_position_error:field==1?x.input.second_position_error:x.input.contact_margin;v=high?std::nextafter(field==2?.1:1e12,2e12):-std::numeric_limits<double>::denorm_min();invalid(x,field==2?c::Reason::contact_margin:c::Reason::position_error,field+2);add(x);}}
    x=base_case();x.name="invalid-settings-before-horizon";x.settings.sqrt_refinements=0;x.horizon=-0.;invalid(x,c::Reason::settings);add(x);
    x=base_case();x.name="invalid-horizon-before-first-sphere";x.horizon=-0.;x.input.first.radius=0;invalid(x,c::Reason::horizon);add(x);
    x=base_case();x.name="invalid-first-before-second-sphere";x.input.first.radius=0;x.input.second.radius=0;invalid(x,c::Reason::input_domain,0);add(x);
    x=base_case();x.name="invalid-second-sphere-before-first-b";x.input.second.radius=0;x.input.first_position_error=-1;invalid(x,c::Reason::input_domain,1);add(x);
    x=base_case();x.name="invalid-first-b-before-second-b";x.input.first_position_error=-1;x.input.second_position_error=-1;invalid(x,c::Reason::position_error,2);add(x);
    x=base_case();x.name="invalid-second-b-before-margin";x.input.second_position_error=-1;x.input.contact_margin=-1;invalid(x,c::Reason::position_error,3);add(x);
    return out;
}
void input_json(std::ostream& o,const Case& x){whole_input(o,x.input,x.horizon,x.settings);}
void snapshot_json(std::ostream& o,const c::Snapshot& s){whole_input(o,s.input,s.horizon,s.settings);}
void result_json(std::ostream& o,const c::Result& r){o<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"snapshot\":";if(r.snapshot){snapshot_json(o,*r.snapshot);}else{o<<"null";}o<<",\"snapshotValidated\":"<<(r.snapshot_validated?"true":"false")<<",\"failedInput\":";index(o,r.failed_input);o<<",\"partitionComplete\":"<<(r.partition_complete?"true":"false")<<",\"audits\":";array(o,r.audits,audit);o<<",\"partition\":";array(o,r.partition,leaf);o<<",\"frontier\":";array(o,r.frontier,cell);o<<",\"current\":";if(r.current){cell(o,*r.current);}else{o<<"null";}o<<",\"work\":{\"valueCallsAttempted\":"<<r.work.value_calls_attempted<<",\"valueCallsReturned\":"<<r.work.value_calls_returned<<",\"sqrtResultsReturned\":"<<r.work.sqrt_results_returned<<",\"sqrtRefinementsReturned\":"<<r.work.sqrt_refinements_returned<<",\"sqrtLimitedReturns\":"<<r.work.sqrt_limited_returns<<",\"sqrtRefinementsUpper\":"<<r.work.sqrt_refinements_upper<<",\"exact\":"<<(r.work.exact?"true":"false")<<"}}";}
void emit_fixtures(std::ostream& o,const std::vector<Case>& corpus){o<<"{\"schema\":1,\"kind\":\"accelerated-sphere-box-coverage-fixtures\",\"fixtures\":[";for(std::size_t i=0;i<corpus.size();++i){if(i){o<<',';}const auto& x=corpus[i];o<<"{\"name\":\""<<x.name<<"\",\"input\":";input_json(o,x);o<<",\"result\":";result_json(o,c::query(x.input,x.horizon,x.settings));o<<'}';}o<<"]}\n";}
}
