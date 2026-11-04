#include "sphere_triangle_mesh_free_flight_guard_test_support.hpp"
#include "../core/src/dynamics_internal.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

namespace guard=pikapika::sphere_triangle_mesh_free_flight_guard;
namespace held=pikapika::sphere_triangle_mesh_held_load;
namespace dynamics=pikapika::dynamics;
using I=pikapika::interval::Interval;
using pikapika::Vec3;
using free_fixture::Case;
using free_fixture::require;
using free_fixture::named_case;
std::uint64_t bits(double value){return std::bit_cast<std::uint64_t>(value);}
void append(std::vector<std::uint64_t>& out,Vec3 v){out.insert(out.end(),{bits(v.x),bits(v.y),bits(v.z)});}
std::vector<std::uint64_t> body_bits(const dynamics::RigidBody& b){
    std::vector<std::uint64_t> out{b.id,b.is_static?1u:0u,bits(b.mass),bits(b.radius)};
    for(auto v:{b.inertia_diagonal,b.position,b.velocity,b.angular_momentum,b.force,b.torque}){append(out,v);}
    out.insert(out.end(),{bits(b.orientation.x),bits(b.orientation.y),bits(b.orientation.z),bits(b.orientation.w),bits(b.material.restitution),bits(b.material.friction)});return out;
}
std::vector<std::uint64_t> world_bits(const dynamics::World& w){
    std::vector<std::uint64_t> out;append(out,w.gravity);out.push_back(w.bodies().size());out.push_back(w.planes().size());
    for(const auto& b:w.bodies()){const auto one=body_bits(b);out.insert(out.end(),one.begin(),one.end());}
    for(const auto& p:w.planes()){out.push_back(p.id);append(out,p.normal);out.insert(out.end(),{bits(p.offset),bits(p.material.restitution),bits(p.material.friction)});}return out;
}
std::vector<std::uint64_t> source_bits(const Case& c){
    auto out=body_bits(c.body);append(out,c.gravity);out.push_back(bits(c.horizon));out.push_back(bits(c.settings.max_angular_increment));out.push_back(c.triangles.size());
    for(const auto& t:c.triangles){out.push_back(t.id);for(auto p:t.vertices){append(out,p);}}
    const auto& h=c.settings.held_load;const auto& p=h.mesh.primitive;
    out.insert(out.end(),{h.mesh.max_surfaces,p.max_candidates,p.sqrt_refinements,p.max_total_sqrt_refinements,bits(p.maximum_local_width),bits(p.maximum_normal_width),bits(p.minimum_sine_squared),bits(h.time_tolerance),h.max_evaluations,h.max_leaves,h.max_depth,h.enclosure_sqrt_refinements,h.max_total_sqrt_refinements});return out;
}
guard::Result run(const Case& c){return guard::query(c.body,c.gravity,c.triangles,c.horizon,c.settings);}
template<class F>std::string serialized(F writer){std::ostringstream out;auto* original=std::cout.rdbuf(out.rdbuf());try{writer();}catch(...){std::cout.rdbuf(original);throw;}std::cout.rdbuf(original);return out.str();}
std::string result_text(const guard::Result& r){return serialized([&]{free_fixture::result_json(r);});}
std::string held_text(const held::Result& r){return serialized([&]{held_fixture::result_json(r);});}
double component(Vec3 p,unsigned axis){return axis==0?p.x:axis==1?p.y:p.z;}
void verify(const Case& c,const guard::Result& r){
    require(r.world_body&&body_bits(r.world_body->body)==body_bits(c.body),"Raw guard did not retain all original body fields");
    std::vector<std::uint64_t> original_gravity,captured_gravity;append(original_gravity,c.gravity);append(captured_gravity,r.world_body->gravity);require(original_gravity==captured_gravity,"Captured gravity bits changed");
    if(r.snapshot){Case saved=c;saved.body=r.snapshot->body;saved.gravity=r.snapshot->gravity;saved.horizon=r.snapshot->horizon;saved.triangles=r.snapshot->triangles;saved.settings=r.snapshot->settings;require(source_bits(saved)==source_bits(c),"Full source/profile snapshot changed");}
    if(r.tube){
        const auto& t=*r.tube;require(std::isfinite(t.position_error)&&std::isfinite(t.roundoff)&&std::isfinite(t.guard_radius)&&t.position_error>=t.roundoff&&t.roundoff>=0,"Invalid total/roundoff position tube");
        require(bits(t.guard_radius)==bits((I::point(c.body.radius)+I::point(t.position_error)).upper()),"Guard radius not outward original radius plus B");
        const auto nominal=c.gravity+c.body.force*c.body.inverse_mass();std::vector<std::uint64_t> a,b;append(a,nominal);append(b,t.nominal_acceleration);require(a==b,"Tube nominal acceleration differs from old propagator operation graph");
        for(unsigned axis=0;axis<3;++axis){const long double exact=static_cast<long double>(component(c.gravity,axis))+static_cast<long double>(component(c.body.force,axis))/c.body.mass;require(t.exact_acceleration[axis].lower()<=exact&&exact<=t.exact_acceleration[axis].upper(),"Acceleration interval excludes exact held coefficient");}
    }
    if(r.inflated){
        require(r.tube&&r.endpoint&&r.candidate_evaluated&&r.inflated->world_body==std::nullopt,"Inflated query fabricated World ownership or skipped endpoint");
        const held::HeldSphere input{c.body.id,c.body.position,c.body.velocity,c.body.mass,c.body.force,c.gravity,r.tube->guard_radius};
        const auto direct=held::query(input,c.triangles,c.horizon,c.settings.held_load);require(held_text(*r.inflated)==held_text(direct),"Nested inflated diagnostics differ from actual complete held query");
        require(r.inflated->audits.size()<=256&&r.inflated->partition.size()<=128&&r.inflated->frontier.size()<=128,"Nested diagnostics truncated or exceed bounds");
        if(r.inflated->snapshot){require(bits(r.inflated->snapshot->input.radius)==bits(r.tube->guard_radius)&&bits(r.snapshot->body.radius)==bits(c.body.radius),"Original and inflated radius ownership mixed");}
    }
    if(r.endpoint){
        require(r.candidate_evaluated&&r.tube,"Endpoint audit without isolated propagation/tube");const auto& e=*r.endpoint;
        auto actual=c.body;dynamics::detail::propagate_free(actual,c.gravity,c.horizon,c.settings.max_angular_increment);actual.validate();
        for(unsigned axis=0;axis<3;++axis){require(e.nominal_allowed[axis].contains(component(actual.position,axis))&&e.exact_allowed[axis].contains(component(actual.position,axis)),"Actual endpoint escaped published allowed box");}
        require(e.nominal_contained&&e.exact_contained&&e.l1_within_tube&&e.l1_error_bound.upper()<=r.tube->position_error,"Endpoint audit is incomplete or exceeds all-duration B");
    }
    if(r.status==guard::Status::certified_separated){
        require(r.reason==guard::Reason::none&&r.snapshot&&r.candidate&&r.endpoint&&r.inflated&&r.inflated->status==held::Status::separated&&r.inflated->work.exact,"Guard published success without whole interval/inflated/candidate proof");
        require(r.inflated->safe_prefix&&(*r.inflated->safe_prefix)[1]==c.horizon,"Guard replaced full time coverage by endpoint safety");
        auto actual=c.body;dynamics::detail::propagate_free(actual,c.gravity,c.horizon,c.settings.max_angular_increment);actual.validate();require(body_bits(actual)==body_bits(*r.candidate),"Owned candidate is not full original free propagator output");
        std::vector<std::uint64_t> loads_a,loads_b;append(loads_a,c.body.force);append(loads_a,c.body.torque);append(loads_b,r.candidate->force);append(loads_b,r.candidate->torque);require(loads_a==loads_b,"Read-only candidate consumed held loads");
    }else{require(!r.candidate,"Failed guard published partially propagated candidate");}
}
unsigned groups{};
template<class F>void test(const std::string& name,F body){body();++groups;std::cout<<"PASS "<<name<<'\n';}
int main(int argc,char** argv){try{
    std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);const auto corpus=free_fixture::cases();
    if(argc==2&&std::string(argv[1])=="--fixtures"){free_fixture::emit_fixtures(corpus);return 0;}
    if(argc==2&&std::string(argv[1])=="--binade-fixtures"){free_fixture::emit_fixtures(free_fixture::binade_cases());return 0;}
    if(argc==2&&std::string(argv[1])=="--supplemental-fixtures"){free_fixture::emit_fixtures(free_fixture::supplemental_cases());return 0;}
    require(argc==1,"Usage: sphere_triangle_mesh_free_flight_guard_tests [--fixtures|--binade-fixtures|--supplemental-fixtures]");
    for(const auto& c:corpus){test(c.name,[&]{const auto before=source_bits(c);const auto r=run(c);
        if(r.status!=c.expected||(c.reason&&r.reason!=*c.reason)){std::cerr<<"actual status="<<unsigned(r.status)<<" reason="<<unsigned(r.reason)<<' '<<r.message<<'\n';throw std::runtime_error("Unexpected free-flight classification: "+c.name+"; original input retained");}
        require(source_bits(c)==before,"Guard mutated original body/source/settings");verify(c,r);
    });}
    test("nonvacuous face edge vertex curved-safe and real held rotation all certify",[]{
        for(const char* name:{"safe-face-held-rotation","safe-edge","safe-vertex","held-input-analytic-chord-false-collision","held-input-analytic-irrational-minimum-safe","safe-cancelled-nominal-acceleration"}){const auto r=run(named_case(name));require(r.status==guard::Status::certified_separated&&r.candidate&&r.inflated&&r.inflated->status==held::Status::separated,"Ordinary complete safe path replaced by vacuous rejection");}
        const auto r=run(named_case("safe-face-held-rotation"));require(r.candidate&&r.candidate->orientation.w!=0&&r.candidate->angular_momentum.x!=.2,"Full rotation/L branch was bypassed");
    });
    test("actual center binade before at after preserves full endpoint candidate and const World",[]{
        const auto inputs=free_fixture::binade_cases();require(inputs.size()==3,"Center binade observations missing");
        for(std::size_t index=0;index<inputs.size();++index){const auto& c=inputs[index];const double expected=index==0?std::nextafter(0x1p39,0.):index==1?0x1p39:std::nextafter(0x1p39,1e12);
            require(bits(c.body.position.x)==bits(expected)&&c.body.position.x-c.triangles[0].vertices[0].x==1,"Actual center no longer straddles binade or physical gap changed");
            const auto before=source_bits(c);const auto r=run(c);require(r.status==guard::Status::certified_separated,"Actual binade-center safety rejected");verify(c,r);require(source_bits(c)==before,"Binade source changed");
            dynamics::World world;world.gravity=c.gravity;world.add_body(c.body);world.add_body(dynamics::make_sphere(202,.5,1,{-30,50,10}));world.add_plane({303,{0,1,0},-10,{.1,.7}});
            const auto& constant=world;const auto initial=world_bits(constant);const auto* body_storage=constant.bodies().data();const auto* plane_storage=constant.planes().data();const auto* pointer=constant.find_body(c.body.id);
            const auto adapted=guard::query_body(constant,c.body.id,c.triangles,c.horizon,c.settings);require(result_text(adapted)==result_text(r)&&world_bits(constant)==initial&&constant.bodies().data()==body_storage&&constant.planes().data()==plane_storage&&constant.find_body(c.body.id)==pointer,"Binade adapter changed full result/World/storage/pointer");
            std::cout<<"OBS center-binade ordinal="<<index<<" centerBits="<<bits(c.body.position.x)<<" endpointBits="<<bits(r.candidate->position.x)<<" fullCandidateAndWorld=verified\n";
        }
    });
    test("inflated entry is a guard failure and never an original contact or published candidate",[]{
        const auto c=named_case("inflated-entry-is-not-original-entry");const auto r=run(c);
        require(c.body.position.y-c.body.radius==.25+0x1p-20&&r.tube&&r.tube->position_error>0x1p-20,"Counterexample does not have a positive original minimum gap below B");
        require(r.status==guard::Status::not_certified&&r.reason==guard::Reason::held_load_not_separated&&r.inflated&&r.inflated->status!=held::Status::separated&&!r.candidate&&r.endpoint,"Inflated contact was relabelled original collision or guard success");
    });
    test("explicit coarse time profile accepts inflated window while original quadratic remains strictly separated",[]{
        const auto extras=free_fixture::supplemental_cases();require(extras.size()==4,"Supplemental4 input set changed");const auto& c=extras.back();
        require(c.name=="coarse-inflated-window-not-original-entry"&&c.settings.held_load.time_tolerance==.1,"Explicit coarse supplemental profile missing");
        const auto original=named_case("inflated-entry-is-not-original-entry");auto restored=c;restored.settings.held_load.time_tolerance=original.settings.held_load.time_tolerance;require(source_bits(restored)==source_bits(original),"Supplemental physical input or another profile field changed");
        require(c.horizon==.0625&&c.body.velocity.y==-16&&c.body.force.y==512&&c.body.mass==1&&c.gravity.y==0&&c.body.radius==1&&c.body.position.x-c.triangles[0].vertices[0].x==1&&c.body.position.z==1,"Original exact quadratic/source assumptions changed");
        // y(t)=P0y-16t+256t^2 has its minimum at t=1/32.
        // x,z stay strictly in this face, so true minimum gap is exactly2^-20.
        const double minimum_gap=c.body.position.y-.25-c.body.radius;require(minimum_gap==0x1p-20&&minimum_gap>0,"Original sphere no longer has strict positive all-time minimum gap");
        const auto r=run(c);verify(c,r);require(r.status==guard::Status::not_certified&&r.reason==guard::Reason::held_load_not_separated&&r.tube&&r.tube->position_error>minimum_gap&&r.inflated&&r.inflated->status==held::Status::entry_window&&r.inflated->window&&!r.candidate,"Inflated accepted window was mistaken for original contact/guard success");
        require(r.inflated->window->time_width.upper()<=.1&&r.endpoint&&r.candidate_evaluated,"Supplemental inflated window lacks actual endpoint and coarse-width proof");
        const auto unchanged=run(original);require(unchanged.inflated&&unchanged.inflated->status==held::Status::not_certified&&!unchanged.inflated->window,"Default-tolerance original outcome was silently changed");
    });
    test("nominal zero force over mass cancellation retains exact coefficient discrepancy in B",[]{
        const auto c=named_case("safe-cancelled-nominal-acceleration");const auto r=run(c);require(r.tube&&r.tube->nominal_acceleration.y==0&&(*r.tube).exact_acceleration[1].lower()<0,"Rounded nominal A replaced exact g+F/m");
        const long double exact=-1.L/(3.L*18014398509481984.L);const long double term=-exact*c.horizon*c.horizon/2;require(r.tube->acceleration_difference[1].lower()<=exact&&r.tube->acceleration_difference[1].upper()>=exact&&r.tube->position_error>=term,"Tube discarded exact coefficient discrepancy");
        const auto narrow=run(named_case("held-input-force-mass-cancellation-not-point"));require(narrow.status!=guard::Status::certified_separated&&!narrow.candidate,"Cancellation produced false narrow safety");
    });
    test("finite representable durations audit the established translation graph without claiming all samples prove it",[]{
        for(const char* name:{"safe-face-held-rotation","binade-before","binade-at","binade-after","subnormal-force-and-velocity","safe-cancelled-nominal-acceleration","non-dyadic-global-seconds"}){
            const auto c=named_case(name);const auto r=run(c);require(r.tube.has_value(),"Finite duration audit missing tube");const auto acceleration=c.gravity+c.body.force*c.body.inverse_mass();
            std::vector<double> times{0,c.horizon,std::nextafter(c.horizon,0.),std::numeric_limits<double>::denorm_min()};for(unsigned i=1;i<16;++i){times.push_back(c.horizon*static_cast<double>(i)/16);}
            for(double t:times){if(t<0||t>c.horizon){continue;}const auto observed=c.body.position+c.body.velocity*t+acceleration*(.5*t*t);long double l1=0;
                for(unsigned axis=0;axis<3;++axis){const long double exact_a=static_cast<long double>(component(c.gravity,axis))+static_cast<long double>(component(c.body.force,axis))/c.body.mass;const long double exact=component(c.body.position,axis)+static_cast<long double>(component(c.body.velocity,axis))*t+exact_a*.5L*t*t;l1+=std::abs(static_cast<long double>(component(observed,axis))-exact);}
                require(l1<=r.tube->position_error,"Observed one-shot translation exceeds B (finite diagnostic, not general oracle)");
            }
        }
    });
    test("rotation and final validate failures are distinct and discarded before nested geometry",[]{
        const auto angle=run(named_case("rotation-increment-failure"));require(angle.reason==guard::Reason::propagation_failure&&angle.candidate_evaluated&&angle.tube&&!angle.inflated&&!angle.candidate,"Rotation failure skipped or partial candidate published");
        const auto invalid=run(named_case("candidate-final-validation-failure"));require(invalid.reason==guard::Reason::candidate_invalid&&invalid.candidate_evaluated&&invalid.tube&&!invalid.inflated&&!invalid.candidate,"Final body validation skipped");require(run(Case{}).status==guard::Status::certified_separated,"Failure poisoned later valid query");
    });
    test("nested maximal counts conservative IDs and unqueried tails are retained without changing their success meaning",[]{
        const auto full=run(named_case("held-input-actual-256-audits-128-leaves"));require(full.inflated&&full.inflated->audits.size()==256&&full.inflated->certified_leaves.size()==128&&full.inflated->partition.size()==128,"Full nested capacity truncated");
        const auto breadth=run(named_case("held-input-breadth-frontier-budget"));require(breadth.inflated&&breadth.inflated->frontier.size()==127&&breadth.inflated->partition.size()==128&&!breadth.candidate,"Unknown tail silently certified");
        const auto ids=run(named_case("held-input-actual-64-entry-all-conservative-ids"));require(ids.inflated&&ids.inflated->candidate_surface_ids.size()==64&&ids.inflated->last_mesh&&ids.inflated->last_mesh->rows.size()==64&&!ids.candidate,"Inflated window/64sources changed into success");
    });
    test("original snapshot nested inflated snapshot body copies and all signed zero are separately owned",[]{
        auto c=named_case("held-input-signed-source-zero");auto r=run(c);const auto before=result_text(r);require(r.snapshot&&r.inflated&&r.inflated->snapshot&&std::signbit(r.snapshot->body.position.x)&&std::signbit(r.inflated->snapshot->input.position.x),"Signed zero lost");
        c.body.position.x=9;c.body.torque.x=8;c.gravity.y=2;c.triangles[0].id=999;c.settings.max_angular_increment=.25;c.settings.held_load.time_tolerance=.05;const auto later=run(c);require(result_text(r)==before,"Caller/later query changed prior DTO");
        r.snapshot->body.radius=.1;require(r.inflated->snapshot->input.radius!=.1&&c.body.radius==.25&&later.snapshot&&later.snapshot->body.radius==.25,"Original/inflated/caller/later storage aliases");
    });
    test("const World adapter leaves every body plane field load pointer and external clock unchanged",[]{
        const auto c=named_case("safe-face-held-rotation");dynamics::World world;world.gravity=c.gravity;world.add_body(c.body);auto other=dynamics::make_sphere(202,.5,2,{100,50,30});other.force={3,4,5};other.torque={6,7,8};world.add_body(other);world.add_plane({303,{0,1,0},-20,{.25,.75}});
        const auto& constant=world;const auto before=world_bits(world);const auto* storage=constant.bodies().data();const auto* planes=constant.planes().data();const auto* first=constant.find_body(c.body.id);const auto* second=constant.find_body(202);
        pikapika::FixedClock clock(.01,10);clock.advance(.0075,[](double){});const auto alpha=bits(clock.alpha());const auto ticks=clock.ticks();const auto drop=bits(clock.dropped_seconds());
        auto r=guard::query_body(constant,c.body.id,c.triangles,c.horizon,c.settings);require(result_text(r)==result_text(run(c)),"World adapter changed exact raw query result");
        for(auto id:{std::uint64_t(0),std::uint64_t(999),std::uint64_t(9007199254740992ULL)}){const auto absent=guard::query_body(constant,id,c.triangles,c.horizon,c.settings);require(absent.status==guard::Status::invalid_input&&!absent.world_body&&!absent.snapshot,"Missing/unsafe lookup fabricated snapshot");}
        require(world_bits(world)==before&&constant.bodies().data()==storage&&constant.planes().data()==planes&&constant.find_body(c.body.id)==first&&constant.find_body(202)==second,"Guard mutated World or replaced stable storage/pointers");
        require(bits(clock.alpha())==alpha&&clock.ticks()==ticks&&bits(clock.dropped_seconds())==drop,"Read-only guard advanced external clock");world.find_body(c.body.id)->torque.x=99;world.gravity.z=7;require(r.world_body&&r.world_body->body.torque.x==.1&&r.world_body->gravity.z==0,"World body snapshot borrowed caller storage");
    });
    test("World rejection paths retain loads and pointers for static invalid rotation and guard failures",[]{
        for(const char* name:{"static-body-unsupported","rotation-increment-failure","candidate-final-validation-failure","inflated-entry-is-not-original-entry"}){const auto c=named_case(name);dynamics::World world;world.gravity=c.gravity;world.add_body(c.body);const auto& constant=world;const auto before=world_bits(world);const auto* pointer=constant.find_body(c.body.id);const auto r=guard::query_body(constant,c.body.id,c.triangles,c.horizon,c.settings);require(r.status!=guard::Status::certified_separated&&!r.candidate&&world_bits(world)==before&&constant.find_body(c.body.id)==pointer,"Failure changed World/loads/pointer");}
        Case c;dynamics::World world;world.gravity=c.gravity;world.add_body(c.body);world.find_body(c.body.id)->mass=0;const auto before=world_bits(world);const auto r=guard::query_body(world,c.body.id,c.triangles,c.horizon,c.settings);require(r.status==guard::Status::invalid_input&&r.world_body&&world_bits(world)==before,"Invalid captured World body mutated or lost ownership");
    });
    test("all nonfinite body gravity horizon and angular profiles reject before work and then recover",[]{
        for(double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){
            for(unsigned field=0;field<11;++field){Case c;switch(field){case 0:c.body.position.x=value;break;case 1:c.body.velocity.y=value;break;case 2:c.body.mass=value;break;case 3:c.body.radius=value;break;case 4:c.body.force.z=value;break;case 5:c.body.torque.x=value;break;case 6:c.body.orientation.w=value;break;case 7:c.body.inertia_diagonal.y=value;break;case 8:c.body.angular_momentum.z=value;break;case 9:c.gravity.y=value;break;default:c.horizon=value;break;}const auto before=source_bits(c);const auto r=run(c);require(r.status==guard::Status::invalid_input&&!r.tube&&!r.candidate_evaluated&&source_bits(c)==before,"Nonfinite raw input accepted or mutated");}
            Case c;c.settings.max_angular_increment=value;const auto r=run(c);require(r.status==guard::Status::invalid_input&&r.reason==guard::Reason::settings&&!r.snapshot&&!r.tube,"Nonfinite angular gate accepted");
        }require(run(Case{}).status==guard::Status::certified_separated,"Valid retry after invalid input failed");
    });
    test("environment is first for invalid raw and missing World lookup without changing rounding",[]{
        Case c;c.body.mass=0;c.triangles.clear();c.settings.max_angular_increment=0;dynamics::World world;const auto before=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set upward rounding");const auto raw=run(c);const auto adapter=guard::query_body(world,0,c.triangles,c.horizon,c.settings);const auto after=std::fegetround();std::fesetround(before);
        require(raw.status==guard::Status::unsupported_environment&&raw.reason==guard::Reason::environment&&adapter.status==guard::Status::unsupported_environment&&!raw.world_body&&!raw.snapshot&&!raw.tube&&!adapter.world_body&&after==FE_UPWARD,"Environment checked late or caller control changed");require(run(Case{}).status==guard::Status::certified_separated,"Nearest retry failed");
    });
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ refuse with no partial capture and gradual retry succeeds",[]{const auto before=_mm_getcsr();_mm_setcsr(before|0x8040u);const auto r=run(Case{});const auto after=_mm_getcsr();_mm_setcsr(before);require(r.status==guard::Status::unsupported_environment&&!r.world_body&&!r.tube&&(after&0x8040u)==0x8040u,"FTZ/DAZ accepted or changed");require(run(Case{}).status==guard::Status::certified_separated,"Gradual retry failed");});
#endif
    std::cout<<"PASS "<<groups<<" groups; "<<corpus.size()<<" complete-input finite free-flight guard fixtures\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
