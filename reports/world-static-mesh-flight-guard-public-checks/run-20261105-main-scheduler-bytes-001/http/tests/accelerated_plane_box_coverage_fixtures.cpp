#include "accelerated_plane_box_coverage_test_support.hpp"
#include <cmath>
#include <iomanip>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <utility>
namespace box_fixture {
namespace c=coverage;
namespace {
void number(std::ostream& o,double x){if(!std::isfinite(x)){throw std::runtime_error("Nonfinite fixture bound");}if(x==0&&std::signbit(x)){o<<"-0";}else{o<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x;}}
void vec(std::ostream& o,pikapika::Vec3 v){o<<'[';number(o,v.x);o<<',';number(o,v.y);o<<',';number(o,v.z);o<<']';}
void source(std::ostream& o,const c::Input& x){const auto& s=x.sphere;const auto& p=x.plane;o<<"{\"sphere\":{\"center\":";vec(o,s.center);o<<",\"velocity\":";vec(o,s.velocity);o<<",\"acceleration\":";vec(o,s.acceleration);o<<",\"radius\":";number(o,s.radius);o<<"},\"plane\":{\"normal\":";vec(o,p.normal);o<<",\"offset\":";number(o,p.offset);o<<"},\"positionError\":";number(o,x.position_error);o<<",\"contactMargin\":";number(o,x.contact_margin);o<<'}';}
void settings(std::ostream& o,const c::Settings& s){o<<"{\"timeTolerance\":";number(o,s.time_tolerance);o<<",\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<'}';}
void whole_input(std::ostream& o,const c::Input& input,double h,const c::Settings& s){o<<"{\"input\":";source(o,input);o<<",\"horizon\":";number(o,h);o<<",\"settings\":";settings(o,s);o<<'}';}
template<class T>void index(std::ostream& o,const std::optional<T>& x){if(x){o<<*x;}else{o<<"null";}}
void cell(std::ostream& o,const c::Cell& x){o<<"{\"timeBounds\":[";number(o,x.time_bounds[0]);o<<',';number(o,x.time_bounds[1]);o<<"],\"depth\":"<<x.depth<<",\"parentAudit\":";index(o,x.parent_audit);o<<'}';}
void interval(std::ostream& o,const pikapika::interval::Interval& x){o<<'[';number(o,x.lower());o<<',';number(o,x.upper());o<<']';}
void evaluation(std::ostream& o,const c::Evaluation& x){o<<"{\"tubeCoordinates\":[";for(std::size_t i=0;i<3;++i){if(i){o<<',';}interval(o,x.tube_coordinates[i]);}o<<"],\"distance\":";interval(o,x.distance);o<<",\"threshold\":";interval(o,x.threshold);o<<",\"gap\":";interval(o,x.gap);o<<'}';}
const char* reason(c::Reason r){constexpr const char* names[]={"none","settings","horizon","input_domain","zero_normal","position_error","contact_margin","evaluation_budget","leaf_budget","depth_budget","width_limit","time_resolution","nonpositive_value","value_exception","allocation_failure","environment","coverage_inconsistent"};return names[unsigned(r)];}
const char* status(c::Status s){constexpr const char* names[]={"certified","not_certified","invalid_input","unsupported_environment"};return names[unsigned(s)];}
void audit(std::ostream& o,const c::Audit& a){constexpr const char* outcomes[]={"pending","positive","split","blocked"};o<<"{\"cell\":";cell(o,a.cell);o<<",\"callAttempted\":"<<(a.call_attempted?"true":"false")<<",\"evaluation\":";if(a.evaluation){evaluation(o,*a.evaluation);}else{o<<"null";}o<<",\"outcome\":\""<<outcomes[unsigned(a.outcome)]<<"\",\"blockedReason\":\""<<reason(a.blocked_reason)<<"\",\"splitTime\":";if(a.split_time){number(o,*a.split_time);}else{o<<"null";}o<<'}';}
void leaf(std::ostream& o,const c::PartitionLeaf& x){constexpr const char* states[]={"unqueried","certified","blocked","current"};o<<"{\"cell\":";cell(o,x.cell);o<<",\"state\":\""<<states[unsigned(x.state)]<<"\",\"auditIndex\":";index(o,x.audit_index);o<<",\"blockedReason\":\""<<reason(x.blocked_reason)<<"\"}";}
template<class T,class F>void array(std::ostream& o,const std::vector<T>& a,F writer){o<<'[';for(std::size_t i=0;i<a.size();++i){if(i){o<<',';}writer(o,a[i]);}o<<']';}
void invalid(Case& x,c::Reason r,std::optional<std::size_t> input={}){x.expected=c::Status::invalid_input;x.reason=r;x.failed_input=input;}
}
Case base_case(){Case x;x.name="static-safe-explicit-zero-b-margin";return x;}
std::vector<Case> cases(){std::vector<Case> out;auto add=[&](Case x){out.push_back(std::move(x));};Case x=base_case();add(x);
    x=base_case();x.name="explicit-negative-zero-b-margin";x.input.position_error=-0.;x.input.contact_margin=-0.;add(x);
    x=base_case();x.name="safe-positive-b-and-margin";x.input.position_error=.125;x.input.contact_margin=.0625;add(x);
    x=base_case();x.name="safe-parabolic-subdivision";x.input.sphere.center.y=1.75;x.input.sphere.velocity.y=-64;x.input.sphere.acceleration.y=2048;x.input.sphere.radius=.5;x.input.position_error=.125;add(x);
    x=base_case();x.name="unsafe-interior-safe-endpoints";x.input.sphere.center.y=1;x.input.sphere.velocity.y=-64;x.input.sphere.acceleration.y=2048;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="initial-negative";x.input.sphere.center.y=-2;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="initial-boundary-then-separates";x.input.sphere.center.y=.25;x.input.sphere.velocity.y=4;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="quadratic-tangent";x.input.sphere.center.y=1+.0009765625;x.input.sphere.velocity.y=-.0625;x.input.sphere.acceleration.y=2;x.input.sphere.radius=1;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="static-contact-full-capacity";x.input.sphere.center.y=.25;x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x.name="contact-127-evaluations-full-frontier";x.settings.max_evaluations=127;x.reason=c::Reason::evaluation_budget;add(x);
    x.name="contact-one-evaluation";x.settings.max_evaluations=1;add(x);
    x.name="contact-one-leaf";x.settings.max_evaluations=255;x.settings.max_leaves=1;x.reason=c::Reason::leaf_budget;add(x);
    x.name="contact-depth-zero";x.settings.max_leaves=128;x.settings.max_depth=0;x.reason=c::Reason::depth_budget;add(x);
    x.name="contact-width-limit";x.settings.max_depth=24;x.settings.time_tolerance=.1;x.reason=c::Reason::width_limit;add(x);
    x=base_case();x.name="safe-one-call-one-leaf-depth-zero";x.settings.max_evaluations=1;x.settings.max_leaves=1;x.settings.max_depth=0;add(x);
    x=base_case();x.name="safe-minimum-duration";x.horizon=std::numeric_limits<double>::denorm_min();add(x);
    x=base_case();x.name="contact-two-subnormal-seconds";x.input.sphere.center.y=.25;x.horizon=2*std::numeric_limits<double>::denorm_min();x.settings.time_tolerance=std::numeric_limits<double>::denorm_min();x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="contact-nonuniform-global-seconds";x.input.sphere.center.y=.25;x.horizon=.03;x.settings.time_tolerance=.003;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="safe-maximum-depth-setting";x.settings.max_depth=32;x.horizon=.1;add(x);
    x=base_case();x.name="nonunit-axis-normal";x.input.plane.normal={0,2,0};add(x);
    x=base_case();x.name="negative-axis-normal";x.input.plane.normal={0,-3,0};x.input.sphere.center.y=-2;x.input.plane.offset=-.125;add(x);
    x=base_case();x.name="oblique-normal-with-b";x.input.plane.normal={1,2,-1};x.input.sphere.center={2,3,-2};x.input.sphere.velocity={-1,2,.5};x.input.sphere.acceleration={3,-4,2};x.input.position_error=.125;add(x);
    x=base_case();x.name="three-component-normal";x.input.plane.normal={2,-3,6};x.input.sphere.center={2,-3,6};x.input.sphere.radius=.5;add(x);
    x=base_case();x.name="metric-unsafe-raw-safe-near-unit";x.input.plane.normal.y=1+0x1p-30;x.input.sphere.center.y=1-0x1p-31;x.input.sphere.radius=1;add(x);
    x=base_case();x.name="metric-safe-raw-unsafe-near-unit";x.input.plane.normal.y=1-0x1p-30;x.input.sphere.center.y=1+0x1p-31;x.input.sphere.radius=1;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="omitted-b-would-change-classification";x.input.sphere.center.y=1;x.input.position_error=.8;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;x.reason=c::Reason::evaluation_budget;add(x);
    x=base_case();x.name="margin-zero-safe";x.input.sphere.center.y=.3;add(x);
    x.name="margin-positive-unsafe";x.input.contact_margin=.1;x.expected=c::Status::not_certified;x.reason=c::Reason::nonpositive_value;add(x);
    x=base_case();x.name="threshold-maximum-radius-positive-margin";x.input.sphere.radius=1e12;x.input.contact_margin=.1;x.input.sphere.center.y=1e12;x.settings.max_leaves=1;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="lost-low-term-rounded-world-counterexample";x.input.plane.normal={1,1,1};x.input.sphere.center={1e12,0x1p-20,-1e12};x.input.sphere.radius=0x1p-22;x.settings.max_evaluations=7;x.expected=c::Status::not_certified;x.reason=c::Reason::evaluation_budget;add(x);
    x=base_case();x.name="fma-and-separate-products-differ";x.input.plane.normal={1+0x1p-27,-1,0};x.input.sphere.center={1-0x1p-27,1,0};x.input.sphere.radius=std::numeric_limits<double>::denorm_min();x.settings.max_evaluations=7;x.expected=c::Status::not_certified;add(x);
    x=base_case();x.name="huge-common-offset-cancellation-safe";x.input.plane.normal={1,-1,0};x.input.sphere.center={0x1p39,0x1p39,0};x.input.plane.offset=-1;add(x);
    for(int direction:{-1,0,1}){x=base_case();x.name=direction<0?"binade-before":direction>0?"binade-after":"binade-at";const double center=direction<0?std::nextafter(0x1p39,0.):direction>0?std::nextafter(0x1p39,1e12):0x1p39;x.input.sphere.center.y=center;x.input.plane.offset=center-1;add(x);}
    x=base_case();x.name="subnormal-half-acceleration-preserved";x.input.sphere.center.y=0;x.input.sphere.acceleration.y=std::numeric_limits<double>::denorm_min();x.input.sphere.radius=std::numeric_limits<double>::denorm_min();x.input.plane.offset=-1;x.horizon=.1;add(x);
    x=base_case();x.name="tiny-axis-normal";x.input.plane.normal.y=std::numeric_limits<double>::denorm_min();x.input.sphere.radius=std::numeric_limits<double>::denorm_min();x.expected.reset();add(x);
    x=base_case();x.name="tiny-oblique-normal";x.input.plane.normal={std::numeric_limits<double>::denorm_min(),std::numeric_limits<double>::denorm_min(),-0.};x.input.sphere.center={4,4,0};x.input.sphere.radius=std::numeric_limits<double>::denorm_min();x.expected.reset();add(x);
    x=base_case();x.name="maximum-point-domains";x.input.plane.normal={0,1e12,0};x.input.plane.offset=-1e12;x.input.sphere.center.y=1e12;x.input.sphere.velocity.x=1e12;x.input.sphere.acceleration.z=-1e12;x.horizon=.1;add(x);
    x=base_case();x.name="maximum-b-domain";x.input.position_error=1e12;x.settings.max_leaves=1;x.expected=c::Status::not_certified;add(x);
    for(unsigned field=0;field<4;++field){for(unsigned high=0;high<2;++high){x=base_case();x.name="invalid-setting-"+std::to_string(field)+(high?"-high":"-low");switch(field){case 0:x.settings.time_tolerance=high?std::nextafter(.1,1.):-0.;break;case 1:x.settings.max_evaluations=high?256:0;break;case 2:x.settings.max_leaves=high?129:0;break;default:if(!high){continue;}x.settings.max_depth=33;break;}invalid(x,c::Reason::settings);add(x);}}
    for(unsigned which=0;which<3;++which){x=base_case();x.name="invalid-horizon-"+std::to_string(which);x.horizon=which==0?-0.:which==1?-.01:std::nextafter(.1,1.);invalid(x,c::Reason::horizon);add(x);}
    for(unsigned field=0;field<5;++field){x=base_case();x.name="invalid-sphere-field-"+std::to_string(field);switch(field){case 0:x.input.sphere.center.x=std::nextafter(1e12,2e12);break;case 1:x.input.sphere.velocity.y=-std::nextafter(1e12,2e12);break;case 2:x.input.sphere.acceleration.z=std::nextafter(1e12,2e12);break;case 3:x.input.sphere.radius=-0.;break;default:x.input.sphere.radius=std::nextafter(1e12,2e12);break;}invalid(x,c::Reason::input_domain,0);add(x);}
    x=base_case();x.name="invalid-normal-domain";x.input.plane.normal.x=std::nextafter(1e12,2e12);invalid(x,c::Reason::input_domain,1);add(x);
    x=base_case();x.name="invalid-offset-domain";x.input.plane.offset=-std::nextafter(1e12,2e12);invalid(x,c::Reason::input_domain,1);add(x);
    x=base_case();x.name="invalid-zero-normal";x.input.plane.normal={-0.,0,-0.};invalid(x,c::Reason::zero_normal,1);add(x);
    for(unsigned high=0;high<2;++high){x=base_case();x.name=high?"invalid-b-high":"invalid-b-negative";x.input.position_error=high?std::nextafter(1e12,2e12):-std::numeric_limits<double>::denorm_min();invalid(x,c::Reason::position_error,2);add(x);x=base_case();x.name=high?"invalid-margin-high":"invalid-margin-negative";x.input.contact_margin=high?std::nextafter(.1,1.):-std::numeric_limits<double>::denorm_min();invalid(x,c::Reason::contact_margin,3);add(x);}
    x=base_case();x.name="invalid-settings-before-horizon";x.settings.max_evaluations=0;x.horizon=-0.;invalid(x,c::Reason::settings);add(x);
    x=base_case();x.name="invalid-horizon-before-sphere";x.horizon=-0.;x.input.sphere.radius=0;invalid(x,c::Reason::horizon);add(x);
    x=base_case();x.name="invalid-sphere-before-plane";x.input.sphere.radius=0;x.input.plane.normal={0,0,0};invalid(x,c::Reason::input_domain,0);add(x);
    x=base_case();x.name="invalid-plane-before-b";x.input.plane.normal={0,0,0};x.input.position_error=-1;invalid(x,c::Reason::zero_normal,1);add(x);
    x=base_case();x.name="invalid-b-before-margin";x.input.position_error=-1;x.input.contact_margin=-1;invalid(x,c::Reason::position_error,2);add(x);
    return out;
}
void input_json(std::ostream& o,const Case& x){whole_input(o,x.input,x.horizon,x.settings);}
void snapshot_json(std::ostream& o,const c::Snapshot& s){whole_input(o,s.input,s.horizon,s.settings);}
void result_json(std::ostream& o,const c::Result& r){o<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"snapshot\":";if(r.snapshot){snapshot_json(o,*r.snapshot);}else{o<<"null";}o<<",\"snapshotValidated\":"<<(r.snapshot_validated?"true":"false")<<",\"failedInput\":";index(o,r.failed_input);o<<",\"partitionComplete\":"<<(r.partition_complete?"true":"false")<<",\"audits\":";array(o,r.audits,audit);o<<",\"partition\":";array(o,r.partition,leaf);o<<",\"frontier\":";array(o,r.frontier,cell);o<<",\"current\":";if(r.current){cell(o,*r.current);}else{o<<"null";}o<<",\"work\":{\"valueCallsAttempted\":"<<r.work.value_calls_attempted<<",\"valueCallsReturned\":"<<r.work.value_calls_returned<<"}}";}
void emit_fixtures(std::ostream& o,const std::vector<Case>& corpus){o<<"{\"schema\":1,\"kind\":\"accelerated-plane-box-coverage-fixtures\",\"fixtures\":[";for(std::size_t i=0;i<corpus.size();++i){if(i){o<<',';}const auto& x=corpus[i];o<<"{\"name\":\""<<x.name<<"\",\"input\":";input_json(o,x);o<<",\"result\":";result_json(o,c::query(x.input,x.horizon,x.settings));o<<'}';}o<<"]}\n";}
}
