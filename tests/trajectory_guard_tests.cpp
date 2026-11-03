#include "pikapika/trajectory_guard.hpp"
#include <bit>
#include <cfenv>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace tg=pikapika::trajectory_guard;
namespace {
unsigned passed=0;
void check(bool b,const std::string& m){if(!b)throw std::runtime_error(m);}
RigidBody body(std::uint64_t id,double r,Vec3 p={},Vec3 v={},bool fixed=false){RigidBody b;b.id=id;b.radius=r;b.position=p;b.velocity=v;b.is_static=fixed;return b;}
std::string snapshot(const std::vector<RigidBody>& b,const std::vector<Plane>& p){std::ostringstream o;o<<std::setprecision(17);
    for(const auto& x:b)o<<x.id<<' '<<x.radius<<' '<<x.is_static<<' '<<x.position.x<<' '<<x.position.y<<' '<<x.position.z<<' '<<x.velocity.x<<' '<<x.velocity.y<<' '<<x.velocity.z<<' '<<x.mass<<' '<<x.force.x<<' '<<x.force.y<<' '<<x.torque.z<<' '<<x.orientation.w<<' '<<x.angular_momentum.x<<'\n';
    for(const auto& x:p)o<<x.id<<' '<<x.normal.x<<' '<<x.normal.y<<' '<<x.normal.z<<' '<<x.offset<<' '<<x.material.friction<<'\n';return o.str();}
tg::Result query(const std::vector<RigidBody>& a,const std::vector<RigidBody>& z,const std::vector<Plane>& p,double dt=.01,const tg::Settings& s={}){
    const auto first=snapshot(a,p),last=snapshot(z,p);const auto* storage=a.data();auto r=tg::audit(a,z,p,dt,s);
    check(first==snapshot(a,p)&&last==snapshot(z,p)&&storage==a.data(),"read-only guard mutated input");return r;
}
void safe(const tg::Result& r){check(r.success&&r.failure==tg::Failure::none&&!r.has_point_witness,"expected complete safe certificate: "+r.message);check(r.first_id==0&&r.second_id==0,"success has stale pair IDs");}
void failed(const tg::Result& r,tg::Failure f){check(!r.success&&r.failure==f,"unexpected failure "+std::to_string(static_cast<int>(r.failure))+": "+r.message);}
void witness(const tg::Result& r){failed(r,tg::Failure::penetration_witness);check(r.has_point_witness&&r.witness_parameter>=0&&r.witness_parameter<=1&&r.predicate_bounds[1]<0,"negative point enclosure absent");}
void test(const char* name,const std::function<void()>& f){f();++passed;std::cout<<"PASS "<<name<<'\n';}
void tests(){
    test("resting and moving plane tangency certify the complete path",[]{auto a=std::vector{body(1,.5,{0,.5,0},{3,0,0})},z=a;z[0].position.x=.03;z[0].velocity={99,99,99};auto r=query(a,z,{{100}});safe(r);check(r.pair_queries==1&&r.certified_intervals>0,"missing full-cell audit");});
    test("1000 m/s crossing is caught despite separated endpoints",[]{auto a=std::vector{body(1,.5,{-2,0,0},{1000,0,0}),body(2,.5,{2,0,0},{-1000,0,0})},z=a;const double dt=1./120;z[0].position.x=-2+1000*dt;z[1].position.x=2-1000*dt;const auto r=query(a,z,{},dt);witness(r);check(r.witness_parameter>0&&r.witness_parameter<1,"endpoint-only crossing probe");});
    test("parabola dips through plane with both endpoints legal",[]{auto a=std::vector{body(1,.5,{0,1,0},{0,-400,0})},z=a;witness(query(a,z,{{100}}));});
    test("far side of plane is rejected before squaring",[]{auto a=std::vector{body(1,.5,{0,-10,0})};auto r=query(a,a,{{100}});witness(r);check(r.witness_parameter==0&&r.predicate==tg::Predicate::plane_signed_offset,"wrong-side proof lost");});
    test("plane zero offset negative squared witness is not lost to side rounding",[]{auto a=std::vector{body(1,.5,{0,0,0})};auto r=query(a,a,{{100}});witness(r);check(r.predicate==tg::Predicate::plane_squared_clearance,"squared witness expected at plane");});
    test("plane normal scaling preserves distance band",[]{auto a=std::vector{body(1,.5,{0,.500001,0},{2,0,0})},z=a;z[0].position.x=.02;safe(query(a,z,{{100,{0,8,0},0}}));z[0].position.y=.49;witness(query(a,z,{{100,{0,8,0},0}}));});
    test("nonaxis plane raw normal is measured by exact real norm",[]{auto a=std::vector{body(1,.5,{.3,.4,0})};safe(query(a,a,{{100,{3,4,0},0}}));a[0].position={.27,.36,0};witness(query(a,a,{{100,{3,4,0},0}}));});
    test("curved support midpath remains inside explicit admissible band",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{0,1,0},{1,0,0})},z=a;z[1].position={.01,std::sqrt(1-.0001),0};tg::Settings s;s.spatial_tolerance=1e-4;safe(query(a,z,{},.01,s));s.spatial_tolerance=1e-14;witness(query(a,z,{},.01,s));});
    test("quartic cancellation certifies O(h4) curved gap without coordinate-box explosion",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{0,1,0},{1,0,0})},z=a;z[1].position={.01,std::sqrt(1-.0001),0};tg::Settings s;s.spatial_tolerance=1e-8;auto r=query(a,z,{},.01,s);safe(r);check(r.evaluations<=8&&r.maximum_depth==0,"quartic coefficient cancellation not retained");});
    test("narrow obstacle away from dyadic midpoint is found by adaptive subdivision",[]{const double centre=13107./32768;auto a=std::vector{body(1,1e-7,{centre,0,0},{},true),body(2,1e-7,{0,0,0},{100,0,0})},z=a;z[1].position.x=1;tg::Settings s;s.spatial_tolerance=1e-10;const auto r=query(a,z,{},.01,s);witness(r);check(r.maximum_depth>=12,"narrow contact did not require subdivision");});
    test("safe near pass requires full interval subdivision",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{-2,.765625,0},{400,50,0})},z=a;z[1].position={2,1.265625,0};auto r=query(a,z,{});safe(r);check(r.certified_intervals>1,"near-pass accepted endpoints alone");});
    test("depth exhaustion is unresolved rather than safe or invented collision",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{-2,.765625,0},{400,50,0})},z=a;z[1].position={2,1.265625,0};tg::Settings s;s.max_depth=0;auto r=query(a,z,{},.01,s);failed(r,tg::Failure::depth_budget);check(!r.has_point_witness&&r.parameter_bounds[0]==0&&r.parameter_bounds[1]==1,"depth failure misclassified");});
    test("evaluation budget reports actual unfinished pair",[]{auto a=std::vector{body(1,.5,{0,2,0})};tg::Settings s;s.max_evaluations=1;auto r=query(a,a,{{100}},.01,s);failed(r,tg::Failure::evaluation_budget);check(r.first_id==100&&r.second_id==1&&r.evaluations==1,"evaluation accounting");});
    test("pair budget never drops the next pair",[]{auto a=std::vector{body(1,.5,{0,2,0}),body(2,.5,{2,2,0})};tg::Settings s;s.max_pair_queries=1;auto r=query(a,a,{{100}},.01,s);failed(r,tg::Failure::pair_budget);check(r.first_id==100&&r.second_id==2&&r.pair_queries==1,"pair accounting");});
    test("huge common translation cancels before sphere propagation",[]{auto a=std::vector{body(1,.5,{0,0,0},{5,0,0}),body(2,.5,{0,2,0},{5,0,0})},z=a;z[0].position.x=z[1].position.x=.5;auto plain=query(a,z,{},.1);safe(plain);for(auto& b:a){b.position.x+=0x1p39;b.position.y+=0x1p39;b.position.z+=0x1p39;}for(auto& b:z){b.position.x+=0x1p39;b.position.y+=0x1p39;b.position.z+=0x1p39;}auto shifted=query(a,z,{},.1);safe(shifted);check(shifted.evaluations==plain.evaluations&&shifted.certified_intervals==plain.certified_intervals,"common translation inflated relative enclosure");});
    test("final ID order radius or static mismatch rejects before pair queries",[]{auto a=std::vector{body(1,.5,{0,1,0}),body(2,.5,{2,1,0})},z=a;std::swap(z[0],z[1]);failed(query(a,z,{}),tg::Failure::invalid_input);z=a;z[0].radius=.6;failed(query(a,z,{}),tg::Failure::invalid_input);z=a;z[0].is_static=true;failed(query(a,z,{}),tg::Failure::invalid_input);});
    test("static geometry consistency and skip counter are explicit",[]{auto a=std::vector{body(1,.5,{0,0,0},{},true),body(2,.5,{0,0,0},{},true),body(3,.5,{0,3,0})},z=a;witness(query(a,z,{{100}}));tg::Settings s;s.include_static_pairs=false;auto r=query(a,z,{{100}},.01,s);safe(r);check(r.skipped_static_pairs==3&&r.pair_queries==3,"incorrect static omission");z[0].position.x=.1;failed(query(a,z,{{100}},.01,s),tg::Failure::invalid_input);z=a;z[0].velocity.x=1;failed(query(a,z,{{100}},.01,s),tg::Failure::invalid_input);});
    test("dynamic/static penetration is never hidden by skip setting",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{0,.9,0})};tg::Settings s;s.include_static_pairs=false;witness(query(a,a,{},.01,s));});
    test("duplicate or nonfinite IDs geometry and zero normal reject",[]{auto a=std::vector{body(1,.5,{0,1,0})},z=a;failed(query(a,z,{{1}}),tg::Failure::invalid_input);failed(query(a,z,{{100,{0,0,0},0}}),tg::Failure::invalid_input);z[0].position.x=std::numeric_limits<double>::quiet_NaN();failed(query(a,z,{}),tg::Failure::invalid_input);a[0].velocity.y=std::numeric_limits<double>::infinity();failed(query(a,a,{}),tg::Failure::invalid_input);});
    test("tolerance domain and explicit budgets reject invalid configurations",[]{auto a=std::vector{body(1,.5,{0,1,0})};tg::Settings s;s.spatial_tolerance=.5;failed(query(a,a,{},.01,s),tg::Failure::invalid_input);s={};s.max_evaluations=0;failed(query(a,a,{},.01,s),tg::Failure::invalid_input);s={};s.max_depth=53;failed(query(a,a,{},.01,s),tg::Failure::invalid_input);failed(query(a,a,{},0),tg::Failure::invalid_input);});
    test("empty geometry is a vacuous certificate without numerical probes",[]{const auto r=query({}, {}, {});safe(r);check(r.pair_queries==0&&r.evaluations==0,"empty audit counts");});
    test("physical time scaling leaves identical normalized polynomial",[]{auto a=std::vector{body(1,.5,{}, {},true),body(2,.5,{-2,.765625,0},{400,50,0})},z=a;z[1].position={2,1.265625,0};auto r=query(a,z,{},.01);safe(r);a[1].velocity={200,25,0};auto slower=query(a,z,{},.02);safe(slower);check(r.evaluations==slower.evaluations&&r.certified_intervals==slower.certified_intervals,"normalized-time scaling");});
    test("unsupported tiny plane norm fails without pretending to normalize",[]{auto a=std::vector{body(1,.5,{0,1,0})};auto r=query(a,a,{{100,{0,std::numeric_limits<double>::denorm_min(),0},0}});failed(r,tg::Failure::numerical_uncertainty);check(!r.has_point_witness,"underflow is not penetration proof");});
#if !defined(__wasm__)
    test("changed floating point environment explicitly rejects before geometry",[]{
        const int mode=std::fegetround();check(std::fesetround(FE_UPWARD)==0,"cannot set rounding for rejection test");
        const auto r=tg::audit({}, {}, {},.01);std::fesetround(mode);
        failed(r,tg::Failure::numerical_failure);check(r.evaluations==0,"invalid environment reached path evaluation");
    });
#endif
}
void bits(double x){std::cout<<std::hex<<std::setw(16)<<std::setfill('0')<<std::bit_cast<std::uint64_t>(x)<<std::dec;}
void oracle(){
    std::cout<<"type,x0,y0,x1,y1,vx,vy,dt,r1,r2,tol,status,witness,predicateLo,predicateHi\n";
    for(unsigned type=0;type<4;++type)for(unsigned k=0;k<160;++k){
        const double dt=type!=3&&k%3==0?1./120:1./64;double tol=1./1024;const bool good=k%2==0;const double target=good?1.+(k+1)/512.:.5+(k+1)/2048.;
        Vec3 p,v,z;const double start=k/256.+1;
        if(type==0||type==2){p={0,target+start,0};v={0,-4*start/dt,0};z=p;}
        else if(type==1){p={-start,target,0};v={2*start/dt,0,0};z={start,target,0};}
        else {
            const double b=(k/2+1)/1024.,b2=b*b,b4=b2*b2,c=b2/2+b4/8;
            p={0,1,0};v={b/dt,0,0};z={b,1-c,0};tol=good?b4/4:b4/128;
        }
        std::vector<RigidBody> a,final;std::vector<Plane> planes;
        if(type==0){a={body(1,1,p,v)};planes={{100}};}
        else a={body(1,.5,{}, {},true),body(2,.5,p,v)};
        final=a;final.back().position=z;tg::Settings s;s.spatial_tolerance=tol;
        const auto r=query(a,final,planes,dt,s);
        // Dyadic dt gives exact minimum target at s=1/2. Rounded 1/120
        // gives nearby minima; the independent Fraction oracle uses raw inputs,
        // not target or rounded coefficients, to prove each classification.
        if(good)safe(r);else witness(r);
        std::cout<<(type==0?'P':type==1?'L':type==2?'Q':'C');
        for(double x:{p.x,p.y,z.x,z.y,v.x,v.y,dt,type==0?1.:.5,type==0?0.:.5,tol}){std::cout<<',';bits(x);}
        std::cout<<','<<(r.success?"safe":"witness")<<',';bits(r.witness_parameter);std::cout<<',';bits(r.predicate_bounds[0]);std::cout<<',';bits(r.predicate_bounds[1]);std::cout<<'\n';
    }
}
}
int main(int argc,char** argv){try{if(argc==2&&std::string(argv[1])=="--oracle")oracle();else{tests();std::cout<<"Trajectory guard: "<<passed<<" groups\n";}return 0;}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
