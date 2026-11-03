#include "pikapika/accelerated.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using pikapika::Vec3;
using namespace pikapika::accelerated;
using I=pikapika::interval::Interval;
namespace {
unsigned passed=0,entries=0;
double maximum_width=0;
std::size_t maximum_evaluations=0;
void check(bool yes,const char* message) {if(!yes)throw std::runtime_error(message);}
void test(const char* name,const std::function<void()>& body) {body();++passed;std::cout<<"PASS "<<name<<'\n';}
void rejects(const std::function<void()>& body) {bool threw=false;try{body();}catch(const std::exception&){threw=true;}check(threw,"expected invalid-input exception");}
Vec3 add(Vec3 a,Vec3 b) {return {a.x+b.x,a.y+b.y,a.z+b.z};}
Vec3 mul(Vec3 a,double s) {return {a.x*s,a.y*s,a.z*s};}
Settings precise() {Settings s;s.time_tolerance=1e-7;return s;}
void entry(const Result& result,double expected,const Settings& settings) {
    if(result.kind!=Kind::entry_bracket) {
        std::cerr<<"entry diagnostic kind="<<int(result.kind)<<" reason="<<int(result.reason)<<" evaluations="<<result.evaluations<<" depth="<<result.depth_reached<<" safe="<<result.safe_until<<'\n';
        throw std::runtime_error("expected proven entry bracket");
    }
    check(result.initial_separation_proven&&result.initial_value&&result.initial_value->strictly_positive(),"initial positive certificate");
    check(result.value_at_safe&&result.value_at_safe->strictly_positive(),"positive left-end certificate");
    check(result.negative_value&&result.negative_value->strictly_negative(),"negative right-end certificate");
    check(result.bracket&&result.negative_witness,"entry bracket and witness");
    check(result.bracket->contains(expected),"known first entry is enclosed");
    check(result.bracket->lower()==result.safe_until&&result.bracket->upper()==*result.negative_witness,"prefix/bracket endpoints");
    const double width=result.bracket->upper()-result.bracket->lower();
    check(width<=settings.time_tolerance&&width>0,"bracket width budget");
    check(result.evaluations<=settings.max_evaluations,"evaluation budget");
    maximum_width=std::max(maximum_width,width);maximum_evaluations=std::max(maximum_evaluations,result.evaluations);++entries;
}
void none(const Result& result,double horizon) {
    check(result.kind==Kind::none&&result.reason==Reason::none,"expected entire-interval exclusion");
    check(result.initial_separation_proven&&result.safe_until==horizon&&!result.bracket&&!result.negative_witness,"none needs full safe prefix");
}
void unresolved(const Result& result) {check(result.kind==Kind::unresolved&&result.reason!=Reason::none&&!result.bracket,"unresolved is explicit without successful bracket");}
void input_out(double x) {std::cout<<','<<std::hex<<std::bit_cast<std::uint64_t>(x)<<std::dec;}
void sphere_out(const Sphere& s) {for(double x:{s.center.x,s.center.y,s.center.z,s.velocity.x,s.velocity.y,s.velocity.z,s.acceleration.x,s.acceleration.y,s.acceleration.z,s.radius})input_out(x);}
void oracle_pair(const Sphere& a,const Sphere& b,I time) {
    const I value=sphere_sphere_value(a,b,time);std::cout<<'S';sphere_out(a);sphere_out(b);input_out(time.lower());input_out(time.upper());input_out(value.lower());input_out(value.upper());std::cout<<'\n';
}
void oracle_plane(const Sphere& s,const StaticPlane& plane,I time) {
    const I value=sphere_plane_value(s,plane,time);std::cout<<'P';sphere_out(s);for(double x:{plane.normal.x,plane.normal.y,plane.normal.z,plane.offset})input_out(x);
    input_out(time.lower());input_out(time.upper());input_out(value.lower());input_out(value.upper());std::cout<<'\n';
}
void oracle() {
    const std::array<double,8> scale{1e-150,1e-9,0x1p-20,1,3,0x1p20,1e9,1e11};
    for(double s:scale)for(double t:{0.,0.125,0.5,1.,2.}) {
        const Sphere a{{s,2*s,-s},{-0.25*s,0.5*s,0.125*s},{0.5*s,-s,0.25*s},0.5*s};
        const Sphere b{{-2*s,s,s},{0.75*s,-s,0.25*s},{-0.5*s,s,-0.125*s},0.25*s};
        oracle_pair(a,b,I::point(t));oracle_pair(a,b,I{t,t+0.125});
        for(Vec3 n:{Vec3{0,1,0},Vec3{3,4,0},Vec3{8,15,0},Vec3{1,2,3},Vec3{0,-0.125,0}}) {
            oracle_plane(a,{n,0.125*s},I::point(t));oracle_plane(a,{n,0.125*s},I{t,t+0.125});
        }
    }
    const double high=0x1p38;
    oracle_pair({{0x1p-20,0,0},{0.1,0.2,0.3},{0.4,0.5,0.6},high},{{2*high,0,0},{-0.7,0.8,-0.9},{0.3,-0.2,0.1},high},I{0,0.5});
    oracle_plane({{0x1p-20,0x1p39,-0x1p38},{0.1,0.2,0.3},{0.4,0.5,0.6},0.25},{{3,4,5},0x1p39},I{0,0.5});
    oracle_pair({{},{},{},1e-320},{{4e-320,0,0},{-1e-320,0,0},{1e-320,0,0},1e-320},I{0,1});
    oracle_pair({{},{},{},0.5},{{2,0,0},{-4,0,0},{2,0,0},0.5},I{0,4});
    oracle_plane({{0,2,0},{0,-2,0},{0,2,0},1},{},I{0,2});
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--oracle"){oracle();return 0;}
        test("gravity sphere-plane fall has independent square-root contact time",[]{
            const auto settings=precise();entry(sphere_plane({{0,11,0},{},{0,-10,0},1},{},2,settings),std::sqrt(2.),settings);
        });
        test("initially departing accelerated sphere returns to plane",[]{
            const auto settings=precise();entry(sphere_plane({{0,3,0},{0,3,0},{0,-2,0},1},{},5,settings),(3+std::sqrt(17.))/2,settings);
        });
        test("unequal accelerations create a sphere-pair quartic",[]{
            const auto settings=precise();Sphere a{{},{},{1,0,0},1},b{{10,0,0},{-1,0,0},{-1,0,0},1};
            entry(sphere_sphere(a,b,4,settings),(-1+std::sqrt(33.))/2,settings);
        });
        test("static sphere under gravity uses nonzero relative acceleration",[]{
            const auto settings=precise();entry(sphere_sphere({{0,10,0},{},{0,-10,0},1},{{},{},{},1},2,settings),std::sqrt(1.6),settings);
        });
        test("3D accelerated contact constructed at exact time",[]{
            const auto settings=precise();
            // Relative centre at t=1 is (3,0,4), radius sum5, and derivative points inward.
            Sphere a{{},{},{},2},b{{6,1,8},{-2,-1,-3},{-2,0,-2},3};
            entry(sphere_sphere(a,b,1.5,settings),1,settings);
        });
        test("four crossings with positive endpoints and positive midpoint retain first entry",[]{
            const auto settings=precise();Sphere a{{},{},{},0.5},b{{2,0,0},{-4,0,0},{2,0,0},0.5};
            // r=(t-2)^2-2: contacts at 2-sqrt(3),1,3,2+sqrt(3).
            entry(sphere_sphere(a,b,4,settings),2-std::sqrt(3.),settings);
        });
        test("high-speed pass-through detected with separated interval endpoints",[]{
            const auto settings=precise();entry(sphere_sphere({{-100,0,0},{20000,0,0},{},1},{{},{},{},1},0.01,settings),0.0049,settings);
        });
        test("dyadic boundary root still gains a negative witness in the adjacent interval",[]{
            const auto settings=precise();entry(sphere_sphere({{},{},{},1},{{6,0,0},{-2,0,0},{},1},4,settings),2,settings);
            entry(sphere_plane({{0,5,0},{0,-2,0},{},1},{},4,settings),2,settings);
        });
        test("plane arbitrary normal norm and positive scale preserve physical contact",[]{
            const auto settings=precise();const Sphere s{{0,6,8},{},{0,-6,-8},1};
            for(double scale:{1e-150,1e-6,0.125,1.,8.,1e6,1e11})entry(sphere_plane(s,{{0,3*scale,4*scale},5.9375*scale},2,settings),1.25,settings);
            // |(8,15,0)|=17 exactly: norm bisection must not stop with an unproved sqrt guess.
            const I value=sphere_plane_value({{8,15,0},{},{},1},{{8,15,0},0},I::point(0));
            check(value.contains(272)&&value.upper()-value.lower()<1e-10,"Pythagorean real normal magnitude");
            none(sphere_plane({{0,5,0},{},{},1},{{0,4,0},8},2,settings),2);
            unresolved(sphere_plane(s,{{0,3e-200,4e-200},5.9375e-200},2,settings));
        });
        test("plane normal sign changes the solid half-space",[]{
            none(sphere_plane({{0,5,0},{},{},1},{{0,1,0},0},2),2);
            auto r=sphere_plane({{0,5,0},{},{},1},{{0,-1,0},0},2);unresolved(r);check(r.reason==Reason::initial_overlap,"negative normal solid side");
            none(sphere_plane({{0,-5,0},{},{},1},{{0,-1,0},0},2),2);
        });
        test("only strictly excluded whole intervals yield none",[]{
            none(sphere_sphere({{},{},{},1},{{0,4,0},{2,0,0},{3,0,0},1},4),4);
            none(sphere_plane({{0,5,0},{0,1,0},{0,2,0},1},{},4),4);
            none(sphere_sphere({{},{},{},1},{{6,0,0},{-2,0,0},{},1},1.9),1.9);
            none(sphere_plane({{0,5,0},{},{},1},{},0),0);
        });
        test("initial overlap and boundary never masquerade as future entry or none",[]{
            auto r=sphere_sphere({{},{},{},1},{{1,0,0},{1,0,0},{},1},4);unresolved(r);check(r.reason==Reason::initial_overlap,"initial overlap");
            r=sphere_sphere({{},{},{},1},{{2,0,0},{-1,0,0},{},1},4);unresolved(r);check(r.reason==Reason::initial_boundary,"initial touching");
            r=sphere_plane({{0,1,0},{},{0,-10,0},1},{},1);unresolved(r);check(r.reason==Reason::initial_boundary,"initial plane boundary");
        });
        test("tangent and repeated roots explicitly remain unresolved",[]{
            Settings settings=precise();settings.max_depth=44;
            unresolved(sphere_plane({{0,2,0},{0,-2,0},{0,2,0},1},{},2,settings)); // phi=(t-1)^2
            unresolved(sphere_sphere({{},{},{},0.5},{{-1,1,0},{1,0,0},{},0.5},2,settings));
            unresolved(sphere_sphere({{},{},{},0.5},{{2,0,0},{-2,0,0},{2,0,0},0.5},2,settings)); // r=1+(t-1)^2
            const I quadratic=sphere_plane_value({{0,2,0},{0,-2,0},{0,2,0},1},{},I{0,2});
            check(quadratic.contains(0)&&quadratic.contains(1),"known full quadratic range [0,1]");
            const I quartic=sphere_sphere_value({{},{},{},0.5},{{2,0,0},{-4,0,0},{2,0,0},0.5},I{0,4});
            check(quartic.contains(-1)&&quartic.contains(3),"known full quartic range [-1,3], interior irrational extrema");
        });
        test("near boundary miss is either proved outside or honestly unresolved",[]{
            const double near=std::nextafter(1.,2.);
            const auto r=sphere_sphere({{},{},{},0.5},{{-1,near,0},{1,0,0},{},0.5},2);
            check(r.kind!=Kind::entry_bracket,"near miss cannot become certified contact");
            if(r.kind==Kind::none)check(r.safe_until==2,"whole-horizon near miss certificate");else unresolved(r);
            unresolved(sphere_plane({{0,1+std::numeric_limits<double>::epsilon(),0},{0,-1,0},{},1},{},1));
        });
        test("horizon-only contact has no in-domain negative witness",[]{
            unresolved(sphere_sphere({{},{},{},1},{{6,0,0},{-2,0,0},{},1},2));
            unresolved(sphere_plane({{0,5,0},{0,-2,0},{},1},{},2));
        });
        test("Galilean common acceleration and spatial scaling preserve entry",[]{
            const auto settings=precise();Sphere a{{},{},{1,0,0},1},b{{10,0,0},{-1,0,0},{-1,0,0},1};const double expected=(-1+std::sqrt(33.))/2;
            const Vec3 shift{64,-128,256},boost{5,-7,11},common_a{0,-10,0};
            a.center=add(a.center,shift);b.center=add(b.center,shift);a.velocity=add(a.velocity,boost);b.velocity=add(b.velocity,boost);
            a.acceleration=add(a.acceleration,common_a);b.acceleration=add(b.acceleration,common_a);entry(sphere_sphere(a,b,4,settings),expected,settings);
            entry(sphere_sphere(b,a,4,settings),expected,settings);
            for(double scale:{1e-6,1.,1e6}) {
                Sphere c{{},{},mul({1,0,0},scale),scale},d{mul({10,0,0},scale),mul({-1,0,0},scale),mul({-1,0,0},scale),scale};
                entry(sphere_sphere(c,d,4,settings),expected,settings);
            }
        });
        test("budgets depth and representable time resolution cannot create success",[]{
            Settings settings=precise();settings.max_evaluations=1;
            auto r=sphere_plane({{0,5,0},{0,-2,0},{},1},{},4,settings);unresolved(r);check(r.reason==Reason::evaluation_budget&&r.evaluations==1,"evaluation limit");
            settings=precise();settings.max_frontier=1;r=sphere_plane({{0,5,0},{0,-2,0},{},1},{},4,settings);unresolved(r);check(r.reason==Reason::frontier_budget,"frontier limit even with negative witness");
            check(r.negative_witness&&r.safe_until==0,"witness does not bypass unresolved prefix");
            settings=precise();settings.max_depth=0;r=sphere_plane({{0,5,0},{0,-2,0},{},1},{},4,settings);unresolved(r);check(r.reason==Reason::depth_limit,"depth limit");
            settings=precise();settings.time_tolerance=std::numeric_limits<double>::denorm_min();settings.max_depth=128;
            unresolved(sphere_plane({{0,5,0},{0,-2,0},{},1},{},4,settings));
        });
        test("coefficient construction retains lost low terms and subnormal ambiguity",[]{
            const double high=0x1p38;const I value=sphere_sphere_value({{0x1p-20,0,0},{},{},high},{{2*high,0,0},{},{},high},I::point(0));
            // Exact result -2^20+2^-40. Rounded subtraction before point() would erase the low input.
            check(value.lower()<=-0x1p20&&value.upper()>-0x1p20,"lost coordinate term enclosure");
            unresolved(sphere_sphere({{},{},{},1e-320},{{4e-320,0,0},{-1e-320,0,0},{},1e-320},3));
        });
        test("invalid input domain and environment failures do not poison later queries",[]{
            Sphere s;StaticPlane p;
            for(double bad:{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN(),1e308,-1e308,1e12+1}) {
                rejects([&]{auto x=s;x.acceleration.z=bad;(void)sphere_sphere(x,s,1);});
                rejects([&]{auto x=p;x.normal.x=bad;(void)sphere_plane(s,x,1);});
            }
            rejects([&]{(void)sphere_plane(s,{{},0},1);});rejects([&]{auto x=s;x.radius=0;(void)sphere_sphere(x,s,1);});
            rejects([&]{(void)sphere_plane(s,p,-1);});rejects([&]{(void)sphere_plane(s,p,1e6+1);});
            rejects([&]{Settings x;x.time_tolerance=0;(void)sphere_sphere(s,s,1,x);});
            rejects([&]{Settings x;x.max_evaluations=0;(void)sphere_sphere(s,s,1,x);});
            rejects([&]{(void)sphere_plane_value(s,p,I{-1,1});});
            const int old_rounding=std::fegetround();
            if(std::fesetround(FE_UPWARD)==0&&std::fegetround()==FE_UPWARD) {
                bool rejected=false;try{(void)sphere_plane(s,p,1);}catch(const std::runtime_error&){rejected=true;}
                std::fesetround(old_rounding);check(rejected,"invalid FP environment must be rejected");
            } else std::fesetround(old_rounding);
            const auto settings=precise();entry(sphere_plane({{0,11,0},{},{0,-10,0},1},{},2,settings),std::sqrt(2.),settings);
        });
        std::cout<<std::setprecision(17)<<"RESULT groups="<<passed<<" known_entry_cases="<<entries<<" max_bracket_width_s="<<maximum_width<<" max_entry_evaluations="<<maximum_evaluations<<'\n';return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<passed<<" groups: "<<error.what()<<'\n';return 1;}
}
