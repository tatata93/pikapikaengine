#include "pikapika/sphere_triangle_mesh_held_load.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <numeric>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Held-load certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle_mesh_held_load {
namespace {
using I=interval::Interval;
namespace mesh=sphere_triangle_mesh;
namespace tri=sphere_triangle;
constexpr double coordinate_limit=1e12;
struct Stop {Status status;Reason reason;const char* text;};
void need(bool b,Status status,Reason reason,const char* text){if(!b)throw Stop{status,reason,text};}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
I checked(I x){need(finite(x),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite held-load interval");return x;}
bool bounded(Vec3 v,double cap=coordinate_limit){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=cap;}
Bounds3 point(Vec3 p){return {I::point(p.x),I::point(p.y),I::point(p.z)};}
Bounds3 path(const Bounds3& origin,const Bounds3& velocity,const Bounds3& acceleration,I time){
    if(time.lower()==0&&time.upper()==0)return origin;
    const I squared=checked(interval::square(time)),half=I::point(.5);
    return {checked(origin[0]+velocity[0]*time+half*acceleration[0]*squared),
            checked(origin[1]+velocity[1]*time+half*acceleration[1]*squared),
            checked(origin[2]+velocity[2]*time+half*acceleration[2]*squared)};
}
Bounds3 speed(const Bounds3& velocity,const Bounds3& acceleration,I time){
    if(time.lower()==0&&time.upper()==0)return velocity;
    return {checked(velocity[0]+acceleration[0]*time),checked(velocity[1]+acceleration[1]*time),checked(velocity[2]+acceleration[2]*time)};
}
bool bounded(const Bounds3& b,double cap){
    return std::all_of(b.begin(),b.end(),[cap](const I& v){return finite(v)&&v.lower()>=-cap&&v.upper()<=cap;});
}
Bounds3 acceleration(const HeldSphere& input){
    const auto g=point(input.gravity),f=point(input.force);const I mass=I::point(input.mass);
    return {checked(g[0]+f[0]/mass),checked(g[1]+f[1]/mass),checked(g[2]+f[2]/mass)};
}
I norm_squared(const Bounds3& b,Vec3 c){I sum=I::point(0);const std::array<double,3> a{c.x,c.y,c.z};
    for(unsigned j=0;j<3;++j){sum=checked(sum+interval::square(checked(b[j]-I::point(a[j]))));}return sum;}
bool profile(const Settings& s){const auto& p=s.mesh.primitive;
    return s.mesh.max_surfaces>=1&&s.mesh.max_surfaces<=64&&p.max_candidates>=1&&p.max_candidates<=7&&p.sqrt_refinements>=1&&p.sqrt_refinements<=256&&p.max_total_sqrt_refinements>=1&&p.max_total_sqrt_refinements<=1024&&
        std::isfinite(p.maximum_local_width)&&p.maximum_local_width>0&&p.maximum_local_width<=1e6&&std::isfinite(p.maximum_normal_width)&&p.maximum_normal_width>0&&p.maximum_normal_width<=2&&
        std::isfinite(p.minimum_sine_squared)&&p.minimum_sine_squared>0&&p.minimum_sine_squared<=1&&std::isfinite(s.time_tolerance)&&s.time_tolerance>0&&s.time_tolerance<=.1&&
        s.max_evaluations>=1&&s.max_evaluations<=256&&s.max_leaves>=1&&s.max_leaves<=128&&s.max_depth<=32&&s.enclosure_sqrt_refinements>=1&&s.enclosure_sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=16777216;
}
bool same_cell(const Cell& a,const Cell& b){return a.depth==b.depth&&a.time_bounds==b.time_bounds;}
void fail(Result& out,Status status,Reason reason,const char* text) noexcept {
    out.status=status;out.reason=reason;out.window.reset();out.candidate_surface_ids.clear();
    if(out.current){
        if(!out.audits.empty()&&same_cell(out.audits.back().cell,*out.current)&&out.audits.back().outcome==Outcome::pending)out.audits.back().outcome=Outcome::unresolved;
        for(auto& leaf:out.partition)if(leaf.state==LeafState::current&&same_cell(leaf.cell,*out.current))leaf.blocked_reason=reason;
    }
    try{out.message=text;}catch(...){out.message.clear();}
}
void sync(Work& w){w.sqrt_refinements=w.primitive_sqrt_refinements+w.enclosure_sqrt_refinements;if(w.exact)w.sqrt_refinements_upper=w.sqrt_refinements;}
struct InFlight {std::size_t global_before{},audit_before{},reserved{},audit_index{};};
void uncertain(Result& out,const InFlight& f) noexcept {
    out.work.exact=false;out.work.sqrt_refinements_upper=f.global_before+f.reserved;
    auto& w=out.audits[f.audit_index].work;w.exact=false;w.sqrt_refinements_upper=f.audit_before+f.reserved;
}
bool unknown_work(const mesh::Result& m){
    if(m.status==mesh::Status::numerical_failure)return true;
    for(const auto& r:m.rows)if(!r.query||r.query->status==tri::Status::numerical_failure)return true;
    return false;
}
bool environment_failure(const mesh::Result& m){
    if(m.status==mesh::Status::unsupported_environment)return true;
    for(const auto& r:m.rows)if(r.query&&r.query->status==tri::Status::unsupported_environment)return true;
    return false;
}
bool recoverable_rows(const mesh::Result& m){
    if(m.status!=mesh::Status::row_failure||m.failed_rows==0)return false;
    for(const auto& row:m.rows){if(!row.query)return false;const auto status=row.query->status;
        if(status!=tri::Status::completed&&status!=tri::Status::degenerate&&status!=tri::Status::ill_conditioned&&status!=tri::Status::quality_unresolved&&status!=tri::Status::budget_exceeded)return false;
    }return true;
}
void update_prefix(Result& out){
    if(!out.initial_separation_proven)return;
    double end=0;
    for(const auto& leaf:out.partition){if(leaf.state!=LeafState::certified)break;
        need(leaf.cell.time_bounds[0]==end,Status::numerical_failure,Reason::coverage_inconsistent,"Gap in certified held-load prefix");end=leaf.cell.time_bounds[1];}
    out.safe_prefix=std::array<double,2>{0,end};
}
bool accept_window(Result& out,const Settings& s){
    if(!out.initial_separation_proven||!out.safe_prefix||!out.best_witness||!out.work.exact)return false;
    const double l=(*out.safe_prefix)[1],u=out.best_witness->time;
    need(l<u,Status::numerical_failure,Reason::coverage_inconsistent,"Negative witness conflicts with strict certified prefix");
    const I width=checked(I::point(u)-I::point(l));
    if(width.upper()>s.time_tolerance)return false;
    need(out.snapshot&&out.acceleration,Status::numerical_failure,Reason::coverage_inconsistent,"Missing held-load source for entry window");
    const auto& input=out.snapshot->input;
    const auto box=path(point(input.position),point(input.velocity),*out.acceleration,I(l,u));
    I diameter=I::point(0);
    for(const auto& component:box){diameter=checked(diameter+checked(I::point(component.upper())-I::point(component.lower())));}
    for(const auto& triangle:out.snapshot->triangles)out.candidate_surface_ids.push_back(triangle.id);
    std::sort(out.candidate_surface_ids.begin(),out.candidate_surface_ids.end());
    out.window=EntryWindow{{l,u},width,box,diameter,out.best_witness->audit_index};out.status=Status::entry_window;out.reason=Reason::none;return true;
}
std::optional<std::size_t> next_leaf(const Result& out){
    std::optional<std::size_t> chosen;
    for(std::size_t i=0;i<out.partition.size();++i){const auto& l=out.partition[i];
        if(l.state!=LeafState::unqueried||(out.best_witness&&l.cell.time_bounds[0]>=out.best_witness->time))continue;
        if(!chosen||l.cell.depth<out.partition[*chosen].cell.depth||
            (l.cell.depth==out.partition[*chosen].cell.depth&&l.cell.time_bounds[0]<out.partition[*chosen].cell.time_bounds[0]))chosen=i;
    }return chosen;
}
// All capacities are reserved before a partition is installed. This final
// owned-view refresh uses only trivial Cell copies within existing capacity.
void finish(Result& out) noexcept {
    static_assert(std::is_nothrow_copy_constructible_v<Cell>);
    static_assert(std::is_nothrow_move_constructible_v<CertifiedLeaf>&&std::is_nothrow_move_assignable_v<CertifiedLeaf>);
    out.partition_leaves=out.partition.size();out.frontier.clear();
    for(const auto& l:out.partition)if(l.state==LeafState::unqueried)out.frontier.push_back(l.cell);
    // Bounded insertion sort, without allocating during an exception finalizer.
    for(std::size_t i=1;i<out.certified_leaves.size();++i){auto value=std::move(out.certified_leaves[i]);std::size_t j=i;
        while(j>0&&value.cell.time_bounds[0]<out.certified_leaves[j-1].cell.time_bounds[0]){out.certified_leaves[j]=std::move(out.certified_leaves[j-1]);--j;}
        out.certified_leaves[j]=std::move(value);
    }
}
}

static Result query_impl(const HeldSphere& input,std::span<const tri::StaticTriangle> triangles,
                         double horizon,const Settings& s,const WorldBodySnapshot* world_body){
    Result out;std::optional<InFlight> in_flight;std::optional<std::size_t> current_leaf;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        if(world_body){out.world_body=*world_body;}
        need(profile(s),Status::invalid_input,Reason::settings,"Invalid held-load profile");
        need(!triangles.empty()&&triangles.size()<=64,Status::invalid_input,Reason::surface_count,"Held-load requires 1..64 surfaces");
        need(std::isfinite(horizon)&&horizon>0&&horizon<=.1&&input.id>0&&input.id<=9007199254740991ULL&&
            bounded(input.position)&&bounded(input.velocity,1e9)&&bounded(input.force,1e24)&&bounded(input.gravity,1e9)&&
            std::isfinite(input.mass)&&input.mass>=1e-12&&input.mass<=1e18&&std::isfinite(input.radius)&&input.radius>0&&input.radius<=1e9,
            Status::invalid_input,Reason::input_domain,"Held-load body/horizon outside finite domain");
        for(std::size_t i=0;i<triangles.size();++i){out.failed_index=i;const auto& t=triangles[i];
            need(t.id>0&&t.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid held-load surface ID");
            for(std::size_t j=0;j<i;++j)need(t.id!=triangles[j].id,Status::invalid_input,Reason::duplicate_id,"Duplicate held-load surface ID");
            need(std::all_of(t.vertices.begin(),t.vertices.end(),[](Vec3 p){return bounded(p);}),Status::invalid_input,Reason::input_domain,"Held-load source outside finite domain");
        }
        out.failed_index.reset();out.snapshot=Snapshot{input,horizon,{triangles.begin(),triangles.end()},s};
        out.frontier.reserve(s.max_leaves);out.partition.reserve(s.max_leaves);out.certified_leaves.reserve(s.max_leaves);out.audits.reserve(s.max_evaluations);out.candidate_surface_ids.reserve(triangles.size());
        out.partition.push_back({Cell{{0,horizon},0},LeafState::unqueried,std::nullopt,Reason::none});out.partition_leaves=1;
        need(!world_body||!world_body->body.is_static,Status::not_certified,Reason::unsupported_body,"Held-load adapter supports dynamic sphere proxies only");
        need(triangles.size()<=s.mesh.max_surfaces,Status::not_certified,Reason::surface_budget,"Held-load source exceeds mesh budget");
        out.acceleration=acceleration(input);
        need(bounded(*out.acceleration,1e12),Status::not_certified,Reason::derived_domain,"Held-load acceleration enclosure exceeds domain");
        const auto origin=point(input.position),velocity=point(input.velocity);const I whole_time(0,horizon);
        out.whole_path_bounds=path(origin,velocity,*out.acceleration,whole_time);
        out.whole_velocity_bounds=speed(velocity,*out.acceleration,whole_time);
        need(bounded(*out.whole_path_bounds,1e12)&&bounded(*out.whole_velocity_bounds,1e9),Status::not_certified,Reason::derived_domain,"Held-load whole path/velocity enclosure exceeds domain");
        const auto evaluate=[&](AuditKind kind,const Cell& cell){
            out.current=cell;out.maximum_depth=std::max(out.maximum_depth,cell.depth);
            need(out.work.mesh_queries<s.max_evaluations,Status::not_certified,Reason::evaluation_budget,"Held-load mesh evaluation budget exhausted");
            out.audits.emplace_back();const std::size_t index=out.audits.size()-1;auto& a=out.audits.back();a.kind=kind;a.cell=cell;
            if(current_leaf)out.partition[*current_leaf].audit_index=index;
            a.time=kind==AuditKind::initial_point?0:std::midpoint(cell.time_bounds[0],cell.time_bounds[1]);
            if(kind==AuditKind::cell)need(cell.time_bounds[0]<a.time&&a.time<cell.time_bounds[1],Status::not_certified,Reason::time_resolution,"Held-load midpoint has no representable interior");
            a.path_bounds=kind==AuditKind::initial_point?origin:path(origin,velocity,*out.acceleration,I(cell.time_bounds[0],cell.time_bounds[1]));
            a.point_bounds=kind==AuditKind::initial_point?origin:path(origin,velocity,*out.acceleration,I::point(a.time));
            const auto& p=*a.point_bounds;const Vec3 c=kind==AuditKind::initial_point?input.position:Vec3{p[0].lower()/2+p[0].upper()/2,p[1].lower()/2+p[1].upper()/2,p[2].lower()/2+p[2].upper()/2};a.anchor=c;
            need(bounded(c,tri::coordinate_limit),Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid derived held-load anchor");
            const auto reserve=[&](std::size_t worst){
                need(out.work.sqrt_refinements_upper<=s.max_total_sqrt_refinements&&worst<=s.max_total_sqrt_refinements-out.work.sqrt_refinements_upper,Status::not_certified,Reason::sqrt_budget,"Held-load sqrt block reservation failed");
                in_flight=InFlight{out.work.sqrt_refinements,a.work.sqrt_refinements,worst,index};
            };
            reserve(triangles.size()*512);a.mesh_queried=true;++a.work.mesh_queries;++out.work.mesh_queries;
            auto m=mesh::query({c,input.radius},out.snapshot->triangles,s.mesh);a.mesh_status=m.status;a.mesh_reason=m.reason;
            need(m.queries<=triangles.size()&&m.candidates_examined<=triangles.size()*7&&m.sqrt_refinements<=triangles.size()*512,Status::numerical_failure,Reason::coverage_inconsistent,"Invalid returned held-load mesh work");
            a.work.primitive_queries=m.queries;a.work.candidates_examined=m.candidates_examined;a.work.primitive_sqrt_refinements=m.sqrt_refinements;a.work.mesh_sqrt_limited_rows=m.sqrt_limited_rows;
            out.work.primitive_queries+=m.queries;out.work.candidates_examined+=m.candidates_examined;out.work.primitive_sqrt_refinements+=m.sqrt_refinements;out.work.mesh_sqrt_limited_rows+=m.sqrt_limited_rows;sync(a.work);sync(out.work);
            const bool unknown=unknown_work(m),environment=environment_failure(m),recoverable=recoverable_rows(m);
            if(unknown)uncertain(out,*in_flight);
            in_flight.reset();
            static_assert(std::is_nothrow_move_assignable_v<std::optional<mesh::Result>>);
            out.last_mesh=std::move(m);out.last_mesh_audit_index=index;const auto& last=*out.last_mesh;
            need(!environment,Status::unsupported_environment,Reason::environment,"Held-load mesh environment rejected");
            need(!unknown,Status::not_certified,Reason::mesh_query_failed,"Held-load mesh has unknown executed work");
            if(last.status!=mesh::Status::completed){
                need(recoverable,Status::numerical_failure,Reason::coverage_inconsistent,"Unexpected held-load mesh failure classification");
                need(kind!=AuditKind::initial_point,Status::not_certified,Reason::mesh_query_failed,"Initial held-load point has no certified distance");return index;
            }
            need(last.nearest.has_value(),Status::numerical_failure,Reason::coverage_inconsistent,"Completed held-load mesh lacks nearest bounds");a.distance=last.nearest->distance;
            a.displacement_squared_bound=norm_squared(*a.path_bounds,c);a.error_squared_bound=norm_squared(*a.point_bounds,c);
            const auto root=[&](I squared){
                need(finite(squared)&&squared.upper()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid held-load norm square");
                reserve(512);++a.work.enclosure_sqrt_calls;++out.work.enclosure_sqrt_calls;
                const auto result=interval::sqrt_enclosure(I::point(squared.upper()),s.enclosure_sqrt_refinements);
                need(result.refinements<=512,Status::numerical_failure,Reason::coverage_inconsistent,"Held-load root exceeded block bound");
                a.work.enclosure_sqrt_refinements+=result.refinements;out.work.enclosure_sqrt_refinements+=result.refinements;
                a.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;out.work.enclosure_sqrt_limited_calls+=result.refinement_limited?1u:0u;sync(a.work);sync(out.work);in_flight.reset();
                need(finite(result.value)&&result.value.lower()>=0,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid held-load norm root");return result.value;
            };
            a.displacement_root=root(*a.displacement_squared_bound);a.error_root=root(*a.error_squared_bound);
            a.clearance_certificate=checked(I::point(a.distance->lower())-I::point(a.displacement_root->upper())-I::point(input.radius));
            a.penetration_certificate=checked(I::point(a.distance->upper())+I::point(a.error_root->upper())-I::point(input.radius));return index;
        };
        const auto initial_index=evaluate(AuditKind::initial_point,Cell{{0,0},0});auto& initial=out.audits[initial_index];
        need(initial.clearance_certificate&&initial.penetration_certificate,Status::numerical_failure,Reason::coverage_inconsistent,"Initial held-load proof missing bounds");
        out.initial=InitialProof{*initial.clearance_certificate,*initial.penetration_certificate,initial_index};out.current.reset();
        if(initial.clearance_certificate->strictly_positive()){initial.outcome=Outcome::initial_separated;out.initial_separation_proven=true;out.safe_prefix=std::array<double,2>{0,0};}
        else if(initial.penetration_certificate->strictly_negative()){initial.outcome=Outcome::initial_penetration;out.status=Status::initial_penetration;out.reason=Reason::none;finish(out);return out;}
        else{initial.outcome=Outcome::initial_uncertain;fail(out,Status::not_certified,Reason::initial_boundary,"Initial held-load sign is not strict");finish(out);return out;}
        while(const auto chosen=next_leaf(out)){
            current_leaf=*chosen;auto& selected=out.partition[*chosen];selected.state=LeafState::current;const auto cell=selected.cell;
            const auto index=evaluate(AuditKind::cell,cell);auto& a=out.audits[index];
            if(a.penetration_certificate&&a.penetration_certificate->strictly_negative()&&(!out.best_witness||a.time<out.best_witness->time))
                out.best_witness=Witness{cell,a.time,*a.point_bounds,*a.anchor,a.error_root->upper(),*a.penetration_certificate,index};
            auto& leaf=out.partition[*chosen];
            if(a.clearance_certificate&&a.clearance_certificate->strictly_positive()){
                leaf.state=LeafState::certified;a.outcome=Outcome::separated;out.certified_leaves.push_back({cell,*a.clearance_certificate,index});out.current.reset();current_leaf.reset();update_prefix(out);
                if(accept_window(out,s)){finish(out);return out;}continue;
            }
            leaf.state=LeafState::unresolved;a.outcome=Outcome::unresolved;out.current.reset();current_leaf.reset();
            if(accept_window(out,s)){finish(out);return out;}
            if(cell.depth>=s.max_depth){leaf.blocked_reason=Reason::depth_budget;continue;}
            if(out.partition.size()>=s.max_leaves){leaf.blocked_reason=Reason::leaf_budget;continue;}
            const PartitionLeaf left{Cell{{cell.time_bounds[0],a.time},cell.depth+1},LeafState::unqueried,std::nullopt,Reason::none};
            const PartitionLeaf right{Cell{{a.time,cell.time_bounds[1]},cell.depth+1},LeafState::unqueried,std::nullopt,Reason::none};
            out.partition[*chosen]=left;out.partition.insert(out.partition.begin()+*chosen+1,right);out.partition_leaves=out.partition.size();a.outcome=Outcome::split;
        }
        update_prefix(out);
        if(accept_window(out,s)){finish(out);return out;}
        const bool all_separated=std::all_of(out.partition.begin(),out.partition.end(),[](const auto& leaf){return leaf.state==LeafState::certified;});
        if(all_separated){need(out.work.exact&&!out.best_witness&&out.safe_prefix&&(*out.safe_prefix)[1]==horizon,Status::numerical_failure,Reason::coverage_inconsistent,"Incomplete separated held-load partition");out.status=Status::separated;out.reason=Reason::none;}
        else{
            Reason blocked=Reason::none;
            for(const auto& leaf:out.partition)if(leaf.state==LeafState::unresolved&&leaf.blocked_reason!=Reason::none){blocked=leaf.blocked_reason;break;}
            need(blocked!=Reason::none,Status::numerical_failure,Reason::coverage_inconsistent,"Held-load has remaining cells without blocking reason");
            fail(out,Status::not_certified,blocked,"Unresolved held-load partition exhausted eligible work");
        }
    }catch(const Stop& e){if(in_flight)uncertain(out,*in_flight);fail(out,e.status,e.reason,e.text);}
    catch(const std::bad_alloc&){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::allocation_failure,"Held-load diagnostic allocation failed");}
    catch(const std::exception& e){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    catch(...){if(in_flight)uncertain(out,*in_flight);fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown held-load exception");}
    finish(out);return out;
}

Result query(const HeldSphere& input,std::span<const tri::StaticTriangle> triangles,double horizon,const Settings& settings){
    return query_impl(input,triangles,horizon,settings,nullptr);
}

Result query_body(const dynamics::World& world,std::uint64_t body_id,
                  std::span<const tri::StaticTriangle> triangles,double horizon,const Settings& settings){
    Result out;
    try{
        if(const char* issue=interval::environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(body_id>0&&body_id<=9007199254740991ULL,Status::invalid_input,Reason::body_invalid,"Invalid held-load body lookup ID");
        const auto* source=world.find_body(body_id);
        need(source!=nullptr,Status::invalid_input,Reason::body_not_found,"Held-load body lookup failed");
        static_assert(std::is_nothrow_copy_constructible_v<WorldBodySnapshot>);
        const WorldBodySnapshot captured{*source,world.gravity};out.world_body=captured;
        try{captured.body.validate();}
        catch(const std::bad_alloc&){throw;}
        catch(const std::exception&){throw Stop{Status::invalid_input,Reason::body_invalid,"Invalid selected held-load World body"};}
        const auto& b=captured.body;
        const HeldSphere input{b.id,b.position,b.velocity,b.mass,b.force,captured.gravity,b.radius};
        return query_impl(input,triangles,horizon,settings,&captured);
    }catch(const Stop& e){fail(out,e.status,e.reason,e.text);}
    catch(const std::bad_alloc&){fail(out,Status::numerical_failure,Reason::allocation_failure,"Held-load adapter allocation failed");}
    catch(const std::exception& e){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,e.what());}
    catch(...){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown held-load adapter exception");}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
