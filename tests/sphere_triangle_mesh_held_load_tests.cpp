#include "sphere_triangle_mesh_held_load_test_support.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#include <utility>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

namespace held=pikapika::sphere_triangle_mesh_held_load;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace dynamics=pikapika::dynamics;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
using held_fixture::Case;
using held_fixture::require;
using held_fixture::named_case;
using held_fixture::flat;

std::uint64_t bits(double value){return std::bit_cast<std::uint64_t>(value);}
bool same(I a,I b){return bits(a.lower())==bits(b.lower())&&bits(a.upper())==bits(b.upper());}
bool same_cell(const held::Cell& a,const held::Cell& b){return a.depth==b.depth&&bits(a.time_bounds[0])==bits(b.time_bounds[0])&&bits(a.time_bounds[1])==bits(b.time_bounds[1]);}
void append(std::vector<std::uint64_t>& out,Vec3 v){out.insert(out.end(),{bits(v.x),bits(v.y),bits(v.z)});}
std::vector<std::uint64_t> body_bits(const dynamics::RigidBody& b){
    std::vector<std::uint64_t> out{b.id,b.is_static?1u:0u,bits(b.mass),bits(b.radius)};
    for(auto v:{b.inertia_diagonal,b.position,b.velocity,b.angular_momentum,b.force,b.torque}){append(out,v);}
    out.insert(out.end(),{bits(b.orientation.x),bits(b.orientation.y),bits(b.orientation.z),bits(b.orientation.w),bits(b.material.restitution),bits(b.material.friction)});return out;
}
std::vector<std::uint64_t> world_bits(const dynamics::World& w){
    std::vector<std::uint64_t> out;append(out,w.gravity);out.push_back(w.bodies().size());out.push_back(w.planes().size());
    for(const auto& b:w.bodies()){const auto stored=body_bits(b);out.insert(out.end(),stored.begin(),stored.end());}
    for(const auto& p:w.planes()){out.push_back(p.id);append(out,p.normal);out.insert(out.end(),{bits(p.offset),bits(p.material.restitution),bits(p.material.friction)});}return out;
}
std::vector<std::uint64_t> source_bits(const Case& c){
    const auto& b=c.sphere;std::vector<std::uint64_t> out{b.id,bits(b.mass),bits(b.radius),bits(c.horizon)};
    for(auto v:{b.position,b.velocity,b.force,b.gravity}){append(out,v);}out.push_back(c.triangles.size());
    for(const auto& t:c.triangles){out.push_back(t.id);for(auto v:t.vertices){append(out,v);}}
    const auto& s=c.settings;const auto& p=s.mesh.primitive;
    out.insert(out.end(),{s.mesh.max_surfaces,p.max_candidates,p.sqrt_refinements,p.max_total_sqrt_refinements,bits(p.maximum_local_width),bits(p.maximum_normal_width),bits(p.minimum_sine_squared),bits(s.time_tolerance),s.max_evaluations,s.max_leaves,s.max_depth,s.enclosure_sqrt_refinements,s.max_total_sqrt_refinements});return out;
}
held::Result run(const Case& c){return held::query(c.sphere,c.triangles,c.horizon,c.settings);}
std::string serialized(const held::Result& r){
    std::ostringstream stream;auto* previous=std::cout.rdbuf(stream.rdbuf());
    try{held_fixture::result_json(r);}catch(...){std::cout.rdbuf(previous);throw;}
    std::cout.rdbuf(previous);return stream.str();
}
void verify_partition(const Case& c,const held::Result& r){
    require(r.partition.size()==r.partition_leaves&&r.partition.size()<=128&&r.frontier.size()<=128&&r.audits.size()<=256,"Held-load hard capacity/count changed");
    if(!r.partition.empty()){
        double end=0;
        for(const auto& p:r.partition){
            require(p.cell.time_bounds[0]==end&&p.cell.time_bounds[1]>end&&p.cell.time_bounds[1]<=c.horizon,"Seconds partition has gap/overlap or normalized endpoint");end=p.cell.time_bounds[1];
            if(p.audit_index){require(*p.audit_index<r.audits.size()&&same_cell(p.cell,r.audits[*p.audit_index].cell),"Partition lost actual audit link");}
            if(p.state==held::LeafState::certified){require(p.audit_index&&r.audits[*p.audit_index].outcome==held::Outcome::separated,"Certified partition lacks actual proof");}
        }
        require(end==c.horizon,"Seconds partition lost the final unqueried tail");
    }
    double prefix=0;bool blocked=false;
    for(const auto& leaf:r.certified_leaves){
        require(leaf.audit_index<r.audits.size()&&same_cell(leaf.cell,r.audits[leaf.audit_index].cell)&&leaf.lower_gap_certificate.strictly_positive(),"Certified island proof/link invalid");
        require(r.audits[leaf.audit_index].clearance_certificate&&same(leaf.lower_gap_certificate,*r.audits[leaf.audit_index].clearance_certificate),"Certified expression changed");
        if(!blocked&&leaf.cell.time_bounds[0]==prefix){prefix=leaf.cell.time_bounds[1];}else{blocked=true;}
    }
    if(r.initial_separation_proven){require(r.initial&&r.initial->lower_gap_certificate.strictly_positive()&&r.safe_prefix&&(*r.safe_prefix)[0]==0&&(*r.safe_prefix)[1]==prefix,"Later certified island filled an unknown earlier time");}
    else{require(!r.safe_prefix,"Safe prefix without initial strict positive");}
    if(r.status==held::Status::separated){require(prefix==c.horizon&&r.work.exact,"Separated lacks whole-time strict proof");}
    if(r.window){
        const auto& w=*r.window;require(r.status==held::Status::entry_window&&r.initial_separation_proven&&r.work.exact&&r.best_witness&&r.safe_prefix,"Window lacks required proof object");
        require(w.time_bounds[0]==prefix&&w.time_bounds[0]<w.time_bounds[1]&&w.time_bounds[1]<=c.horizon&&w.time_bounds[1]==r.best_witness->time,"Window does not use prefix/witness seconds");
        require(w.witness_audit_index==r.best_witness->audit_index&&w.time_width.lower()>0&&w.time_width.upper()<=c.settings.time_tolerance,"Window seconds tolerance/link not certified");
        require(w.time_width.contains(w.time_bounds[1]-w.time_bounds[0]),"Seconds-width enclosure misses endpoint difference");
        long double sum=0;for(const auto& coordinate:w.path_bounds){sum+=static_cast<long double>(coordinate.upper())-coordinate.lower();}
        require(static_cast<long double>(w.l1_diameter_bound.lower())<=sum&&sum<=static_cast<long double>(w.l1_diameter_bound.upper()),"Spatial L1 bound is not the sum of stored coordinate widths");
        auto ids=r.candidate_surface_ids;std::vector<std::uint64_t> expected;for(const auto& t:c.triangles){expected.push_back(t.id);}std::sort(expected.begin(),expected.end());require(ids==expected,"Window narrowed conservative IDs to nearest features");
    }else{require(r.status!=held::Status::entry_window&&r.candidate_surface_ids.empty(),"Window or candidate ID flag invented");}
    if(r.best_witness){
        const auto& w=*r.best_witness;require(w.audit_index<r.audits.size()&&r.audits[w.audit_index].kind==held::AuditKind::cell&&w.upper_gap_certificate.strictly_negative(),"Non-strict or initial witness published");
        const auto& a=r.audits[w.audit_index];require(a.penetration_certificate&&same(w.upper_gap_certificate,*a.penetration_certificate)&&w.time==a.time&&same_cell(w.cell,a.cell),"Witness detached from real seconds audit");
    }
    if(r.initial){require(r.initial->audit_index==0&&!r.audits.empty()&&r.audits[0].kind==held::AuditKind::initial_point&&r.audits[0].time==0,"Initial proof lost singleton audit");}
    if(r.status==held::Status::initial_penetration){require(r.initial&&r.initial->upper_gap_certificate.strictly_negative()&&!r.initial_separation_proven&&!r.best_witness&&!r.window,"Initial negative became later entry");}
    std::vector<held::Cell> unqueried;for(const auto& p:r.partition){if(p.state==held::LeafState::unqueried){unqueried.push_back(p.cell);}}
    require(unqueried.size()==r.frontier.size(),"Frontier discarded unqueried tail");for(std::size_t i=0;i<unqueried.size();++i){require(same_cell(unqueried[i],r.frontier[i]),"Frontier reordered or copied from an old DFS");}
}
constexpr std::array<std::size_t held::Work::*,10> work_fields{{&held::Work::mesh_queries,&held::Work::primitive_queries,&held::Work::candidates_examined,&held::Work::primitive_sqrt_refinements,&held::Work::enclosure_sqrt_refinements,&held::Work::sqrt_refinements,&held::Work::sqrt_refinements_upper,&held::Work::mesh_sqrt_limited_rows,&held::Work::enclosure_sqrt_calls,&held::Work::enclosure_sqrt_limited_calls}};
void verify_work(const Case& c,const held::Result& r){
    held::Work total;unsigned previous_depth=0;double previous_left=-1;bool previous_cell=false;
    for(std::size_t index=0;index<r.audits.size();++index){const auto& a=r.audits[index];const auto& w=a.work;held::Work expected;
        if(a.kind==held::AuditKind::initial_point){require(index==0&&a.cell.time_bounds==std::array<double,2>{0,0}&&a.time==0,"Initial seconds domain changed");}
        else{
            require(a.time>=a.cell.time_bounds[0]&&a.time<=a.cell.time_bounds[1],"Audit time outside its original global cell");
            if(a.path_bounds){require(a.time>a.cell.time_bounds[0]&&a.time<a.cell.time_bounds[1],"Evaluated cell lacks representable interior time");}
            if(previous_cell){require(a.cell.depth>previous_depth||(a.cell.depth==previous_depth&&a.cell.time_bounds[0]>previous_left),"Exploration not breadth-first/left-tied");}
            previous_depth=a.cell.depth;previous_left=a.cell.time_bounds[0];previous_cell=true;
        }
        if(a.mesh_queried){
            require(a.anchor.has_value(),"Real mesh query missing arbitrary anchor");const auto m=mesh::query({*a.anchor,c.sphere.radius},c.triangles,c.settings.mesh);
            require(a.mesh_status==m.status&&a.mesh_reason==m.reason,"Anchor mesh requery status/reason differs");
            expected.mesh_queries=1;expected.primitive_queries=m.queries;expected.candidates_examined=m.candidates_examined;expected.primitive_sqrt_refinements=m.sqrt_refinements;expected.mesh_sqrt_limited_rows=m.sqrt_limited_rows;
        }
        const std::array<std::pair<const std::optional<I>*,const std::optional<I>*>,2> roots{{{&a.displacement_root,&a.displacement_squared_bound},{&a.error_root,&a.error_squared_bound}}};
        for(const auto& [root,squared]:roots){if(*root){
            require(squared->has_value(),"Returned root missing squared input");const auto actual=pikapika::interval::sqrt_enclosure(I::point((*squared)->upper()),c.settings.enclosure_sqrt_refinements);
            require(same(**root,actual.value),"R/E root differs from actual strict sqrt call");expected.enclosure_sqrt_calls++;expected.enclosure_sqrt_refinements+=actual.refinements;expected.enclosure_sqrt_limited_calls+=actual.refinement_limited?1u:0u;
        }}
        expected.sqrt_refinements=expected.primitive_sqrt_refinements+expected.enclosure_sqrt_refinements;expected.sqrt_refinements_upper=expected.sqrt_refinements;
        require(w.exact,"Natural finite test unexpectedly contains unreturned work (no fault injection claimed)");
        for(auto member:work_fields){require(w.*member==expected.*member,"Audit delta differs from actual anchor/root work (not an independent math oracle)");total.*member+=w.*member;}
    }
    require(r.work.exact,"Natural corpus unknown-work result needs explicit investigation");
    for(auto member:work_fields){require(r.work.*member==total.*member,"Aggregate work differs from every audit delta");}
    require(r.work.mesh_queries<=c.settings.max_evaluations&&r.work.sqrt_refinements_upper<=c.settings.max_total_sqrt_refinements,"Configured work budget exceeded");
    require(r.work.primitive_sqrt_refinements<=8388608&&r.work.enclosure_sqrt_refinements<=262144&&r.work.sqrt_refinements<=8650752,"Absolute bounded work exceeded");
    if(r.last_mesh){require(r.last_mesh_audit_index&&*r.last_mesh_audit_index<r.audits.size()&&r.audits[*r.last_mesh_audit_index].mesh_status==r.last_mesh->status,"Last mesh ownership index not returned query");}
    else{require(!r.last_mesh_audit_index,"Last mesh index without a returned mesh");}
}
unsigned groups{};
template<class F>void test(const std::string& name,F body){body();++groups;std::cout<<"PASS "<<name<<'\n';}
int main(int argc,char** argv){try{
    const auto corpus=held_fixture::cases();std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);
    if(argc==2&&std::string(argv[1])=="--fixtures"){held_fixture::emit_fixtures(corpus);return 0;}
    require(argc==1,"Usage: sphere_triangle_mesh_held_load_tests [--fixtures]");
    for(const auto& c:corpus){test(c.name,[&]{
        const auto original=source_bits(c);const auto r=run(c);
        if(r.status!=c.expected||(c.why&&r.reason!=*c.why)){std::cerr<<"actual status="<<unsigned(r.status)<<" reason="<<unsigned(r.reason)<<' '<<r.message<<'\n';throw std::runtime_error("Unexpected held-load classification: "+c.name+"; original input unchanged");}
        require(source_bits(c)==original,"Held sphere/source/settings mutated");require(!r.world_body,"Raw query fabricated a World body snapshot");verify_partition(c,r);verify_work(c,r);
        if(r.snapshot){Case copied=c;copied.sphere=r.snapshot->input;copied.horizon=r.snapshot->horizon;copied.triangles=r.snapshot->triangles;copied.settings=r.snapshot->settings;require(source_bits(copied)==original,"Snapshot lost original SI inputs/bits/profile");}
    });}
    test("nonvacuous chord edge vertex and rescaled analytic first entries are certified in seconds",[]{
        for(const char* name:{"analytic-chord-false-safe","analytic-chord-false-safe-force-gravity","analytic-edge-quartic","analytic-vertex-quartic","seconds-rescale-half","seconds-rescale-quarter"}){
            const auto c=named_case(name);const auto r=run(c);require(r.window&&r.window->time_bounds[0]<c.horizon/4&&r.window->time_bounds[1]>c.horizon/4,"Window misses independent exact H/4 entry");
            require(r.window->time_width.upper()<=c.settings.time_tolerance&&r.window->time_bounds[1]<.1,"Time output became normalized parameter");
        }
        const auto r=run(named_case("analytic-irrational-minimum-entry"));long double lo=0,hi=.75L;
        for(unsigned i=0;i<100;++i){const long double m=(lo+hi)/2;const long double f=m*m*m*m-2*m+9.L/4-289.L/256;if(f>0){lo=m;}else{hi=m;}}
        const long double root=(lo+hi)/2/16;require(r.window&&r.window->time_bounds[0]<root&&root<r.window->time_bounds[1],"Window misses independent monotone quartic bisection");
    });
    test("curved safe paths are proved and tangent cannot become separated or negative",[]{
        for(const char* name:{"analytic-chord-false-collision","analytic-irrational-minimum-safe"}){const auto c=named_case(name);const auto r=run(c);require(r.status==held::Status::separated&&r.safe_prefix&&(*r.safe_prefix)[1]==c.horizon,"Required curved all-time safety replaced by vacuous unresolved");}
        const auto tangent=run(named_case("analytic-tangent-no-negative"));require(tangent.status==held::Status::not_certified&&!tangent.best_witness&&!tangent.window,"Tangency promoted to strict proof");
    });
    test("whole quadratic box includes interior turning point rather than the endpoint chord",[]{
        const auto r=run(named_case("analytic-chord-false-safe"));require(r.whole_path_bounds&&(*r.whole_path_bounds)[1].contains(0)&&(*r.whole_path_bounds)[1].contains(1),"Quadratic turning point lost by chord enclosure");
        require(r.audits.size()>2&&r.audits[1].mesh_status==mesh::Status::row_failure&&r.audits[1].outcome==held::Outcome::split&&r.best_witness&&r.best_witness->audit_index>1,"Failed zero-distance ancestor was reused as proof or stopped child recovery");
    });
    test("exact force over mass cancellation cannot be replaced by zero point acceleration",[]{
        const auto c=named_case("force-mass-cancellation-not-point");require(c.sphere.gravity.y+c.sphere.force.y*(1/c.sphere.mass)==0,"Cancellation counterexample no longer rounds to point zero");
        const auto r=run(c);const long double exact=-1.L/(3.L*18014398509481984.L);require(r.acceleration&&(*r.acceleration)[1].lower()<=exact&&exact<=(*r.acceleration)[1].upper(),"Acceleration excludes exact g+F/m");
        require((*r.acceleration)[1].lower()<0&&r.status!=held::Status::separated,"Rounded-zero acceleration invented safety");
    });
    test("256audits128leaves255budget and breadth127tail are actually reached",[]{
        const auto full=run(named_case("actual-256-audits-128-leaves"));require(full.status==held::Status::separated&&full.audits.size()==256&&full.certified_leaves.size()==128&&full.partition.size()==128&&full.work.mesh_queries==256,"Actual full capacity missing");
        const auto budget=run(named_case("255-evaluation-budget-includes-initial"));require(budget.audits.size()==255&&budget.work.mesh_queries==255&&budget.partition.size()==128&&budget.current&&!budget.window,"Initial attempt not charged or current stop omitted");
        const auto breadth=run(named_case("breadth-frontier-budget"));require(breadth.partition.size()==128&&breadth.frontier.size()==127&&breadth.current&&breadth.safe_prefix&&(*breadth.safe_prefix)[1]==0,"BFS frontier truncated or later island filled prefix");
        const auto leaves=run(named_case("127-leaf-budget-preserves-prefix"));require(leaves.partition.size()==127&&leaves.certified_leaves.size()==126&&leaves.safe_prefix&&(*leaves.safe_prefix)[1]<.0625,"Blocked prefix/later tail lost");
    });
    test("all64conservativeIDs and final source row candidate remain owned",[]{
        const auto r=run(named_case("actual-64-entry-all-conservative-ids"));require(r.window&&r.candidate_surface_ids.size()==64&&r.candidate_surface_ids.front()==1&&r.candidate_surface_ids.back()==64,"Window omitted conservative IDs");
        require(r.last_mesh&&r.last_mesh->rows.size()==64&&r.last_mesh->rows.back().triangle.id==1&&r.last_mesh->rows.back().query&&r.last_mesh->rows.back().query->candidates.size()==7,"Final source/query/candidate truncated");
        const auto a=run(named_case("multiple-entries-source-order"));const auto b=run(named_case("multiple-entries-source-reversed"));require(a.candidate_surface_ids==std::vector<std::uint64_t>{5,37}&&a.candidate_surface_ids==b.candidate_surface_ids&&a.window&&b.window,"Source order removed conservative candidates");
    });
    test("narrow seconds width is separate from spatial enclosure and unresolved prefix",[]{
        const auto tight=run(named_case("tight-time-tolerance-depth-budget"));require(!tight.window&&tight.best_witness&&tight.safe_prefix,"Witness alone became a window");
        const auto c=named_case("linear-entry-quarter");const auto r=run(c);require(r.window&&r.window->l1_diameter_bound.upper()>r.window->time_width.upper(),"Spatial width was relabelled seconds tolerance");
        const auto& p=r.window->path_bounds;require(p[1].contains(c.sphere.position.y+c.sphere.velocity.y*r.window->time_bounds[0])&&p[1].contains(c.sphere.position.y+c.sphere.velocity.y*r.window->time_bounds[1]),"Window spatial box misses original endpoints");
    });
    test("snapshots retain signed zero all fields and old results across caller mutations",[]{
        Case c=named_case("signed-source-zero");auto r=run(c);const auto original=serialized(r);require(r.snapshot&&std::signbit(r.snapshot->input.position.x)&&std::signbit(r.snapshot->input.velocity.x)&&std::signbit(r.snapshot->triangles[0].vertices[0].x),"Signed zero lost");
        c.sphere.position.x=9;c.sphere.mass=2;c.sphere.force.y=3;c.sphere.gravity.y=4;c.triangles[0].id=999;c.triangles[0].vertices[0].z=2;c.horizon=.03125;c.settings.time_tolerance=.05;c.settings.mesh.primitive.maximum_local_width=1;
        const auto later=run(c);require(later.snapshot&&serialized(r)==original,"Caller/subsequent query mutated previous owned result");r.snapshot->input.force.y=77;require(c.sphere.force.y==3&&later.snapshot->input.force.y==3,"Snapshot shares caller/later storage");
    });
    test("const World adapter captures all body fields and leaves every object and pointer unchanged",[]{
        const auto c=named_case("analytic-chord-false-safe");dynamics::World world;world.gravity=c.sphere.gravity;
        auto body=dynamics::make_sphere(c.sphere.id,c.sphere.radius,c.sphere.mass,c.sphere.position);body.velocity=c.sphere.velocity;body.force=c.sphere.force;body.torque={4,-5,6};body.angular_momentum={1,2,-3};body.orientation={0,0,1,0};body.inertia_diagonal={.2,.3,.4};body.material={.25,.75};world.add_body(body);
        auto other=dynamics::make_sphere(202,.5,2,{100,20,-10});other.force={7,8,9};other.torque={10,11,12};world.add_body(other);world.add_plane({303,{0,1,0},-10,{.1,.8}});
        const auto& constant=world;const auto before=world_bits(constant);const auto* first=constant.find_body(body.id);const auto* second=constant.find_body(other.id);const auto* storage=constant.bodies().data();const auto* planes=constant.planes().data();
        pikapika::FixedClock clock(.01,10);clock.advance(.0075,[](double){});const auto alpha=bits(clock.alpha());const auto dropped=bits(clock.dropped_seconds());const auto ticks=clock.ticks();
        auto result=held::query_body(constant,body.id,c.triangles,c.horizon,c.settings);require(result.world_body&&body_bits(result.world_body->body)==body_bits(body),"Adapter dropped selected rotational/material/load fields");
        require(bits(result.world_body->gravity.y)==bits(world.gravity.y),"Adapter world gravity not owned");auto raw=run(c);result.world_body.reset();require(serialized(result)==serialized(raw),"Adapter center trajectory differs from raw held inputs");
        for(const auto id:{std::uint64_t(0),std::uint64_t(999),std::uint64_t(9007199254740992ULL)}){const auto missing=held::query_body(constant,id,c.triangles,c.horizon,c.settings);require(missing.status==held::Status::invalid_input&&!missing.world_body,"Unknown or unsafe adapter ID manufactured snapshot");}
        require(world_bits(constant)==before&&constant.find_body(body.id)==first&&constant.find_body(other.id)==second&&constant.bodies().data()==storage&&constant.planes().data()==planes,"Read-only query mutated World/body/plane/load/storage/pointer");
        require(bits(clock.alpha())==alpha&&bits(clock.dropped_seconds())==dropped&&clock.ticks()==ticks,"Query advanced external clock");
        auto captured=held::query_body(constant,body.id,c.triangles,c.horizon,c.settings);world.find_body(body.id)->torque.x=99;world.gravity.x=7;require(captured.world_body&&captured.world_body->body.torque.x==4&&captured.world_body->gravity.x==0,"Adapter snapshot borrows mutable World");
    });
    test("static and invalid selected bodies reject without changing their held loads",[]{
        dynamics::World world;world.gravity={0,0,0};auto body=dynamics::make_sphere(1,.25,1,{1,1,1},true);body.force={2,3,4};body.torque={5,6,7};world.add_body(body);const Case c;const auto before=world_bits(world);const auto* pointer=static_cast<const dynamics::World&>(world).find_body(1);
        const auto r=held::query_body(world,1,c.triangles,c.horizon,c.settings);require(r.status==held::Status::not_certified&&r.reason==held::Reason::unsupported_body&&r.world_body&&r.world_body->body.is_static&&r.snapshot&&r.audits.empty(),"Static body silently moved under force or lost owned structural snapshot");
        require(world_bits(world)==before&&static_cast<const dynamics::World&>(world).find_body(1)==pointer,"Static refusal mutated World");world.find_body(1)->is_static=false;world.find_body(1)->mass=0;const auto invalid_before=world_bits(world);
        const auto invalid=held::query_body(world,1,c.triangles,c.horizon,c.settings);require(invalid.status==held::Status::invalid_input&&invalid.reason==held::Reason::body_invalid&&invalid.world_body&&world_bits(world)==invalid_before,"Invalid body accepted or mutated");
    });
    test("nonfinite raw inputs and all floating profiles reject then finite retry recovers",[]{
        for(double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){
            for(unsigned field=0;field<8;++field){Case c;switch(field){case 0:c.sphere.position.z=value;break;case 1:c.sphere.velocity.x=value;break;case 2:c.sphere.mass=value;break;case 3:c.sphere.force.y=value;break;case 4:c.sphere.gravity.z=value;break;case 5:c.sphere.radius=value;break;case 6:c.horizon=value;break;default:c.triangles[0].vertices[2].z=value;break;}const auto before=source_bits(c);const auto r=run(c);require(r.status==held::Status::invalid_input&&!r.snapshot&&r.audits.empty()&&source_bits(c)==before,"Nonfinite input accepted or modified");}
            for(unsigned field=0;field<4;++field){Case c;switch(field){case 0:c.settings.time_tolerance=value;break;case 1:c.settings.mesh.primitive.maximum_local_width=value;break;case 2:c.settings.mesh.primitive.maximum_normal_width=value;break;default:c.settings.mesh.primitive.minimum_sine_squared=value;break;}const auto r=run(c);require(r.status==held::Status::invalid_input&&r.reason==held::Reason::settings&&!r.snapshot,"Nonfinite floating profile accepted");}
        }require(run(Case{}).status==held::Status::separated,"Finite retry failed after invalid input");
    });
    test("unsupported FP environment precedes invalid profile input and missing World ID",[]{
        Case c;c.triangles.clear();c.settings.time_tolerance=0;dynamics::World world;const auto before=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set upward rounding");
        const auto raw=run(c);const auto adapter=held::query_body(world,0,c.triangles,c.horizon,c.settings);const auto after=std::fegetround();std::fesetround(before);
        require(raw.status==held::Status::unsupported_environment&&adapter.status==held::Status::unsupported_environment&&raw.reason==held::Reason::environment&&!raw.snapshot&&!raw.acceleration&&!adapter.world_body&&after==FE_UPWARD,"Environment was not first or caller rounding changed");require(run(Case{}).status==held::Status::separated,"Nearest retry failed");
    });
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ refusal preserves controls and gradual-underflow retry succeeds",[]{
        const auto before=_mm_getcsr();_mm_setcsr(before|0x8040u);const auto r=run(Case{});const auto after=_mm_getcsr();_mm_setcsr(before);
        require(r.status==held::Status::unsupported_environment&&!r.snapshot&&!r.acceleration&&(after&0x8040u)==0x8040u,"FTZ/DAZ accepted or changed");require(run(Case{}).status==held::Status::separated,"Gradual-underflow retry failed");
    });
#endif
    std::cout<<"PASS "<<groups<<" groups; "<<corpus.size()<<" complete-input finite held-load fixtures\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
