#pragma once
// Original test/probe transport and independent DTO-to-wire encoder. No solver.
#include "pikapika/simulation_api.h"
#include "sphere_triangle_mesh_free_flight_guard_test_support.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>
#include <string>
#include <vector>

namespace flight_sdk {
namespace held=pikapika::sphere_triangle_mesh_held_load;
namespace guard=pikapika::sphere_triangle_mesh_free_flight_guard;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
using Packet=std::vector<double>;
using Triangle=std::array<double,10>;
inline void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
inline void ok(int32_t value){if(value!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
inline Packet output(){const auto n=pp_sim_output_count();need(n<=64,"Output exceeds64");const auto* p=pp_sim_output_f64_ptr();return {p,p+n};}
inline bool same(const Packet& a,const Packet& b){return a.size()==b.size()&&std::equal(a.begin(),a.end(),b.begin(),[](double x,double y){return std::bit_cast<std::uint64_t>(x)==std::bit_cast<std::uint64_t>(y);});}
inline void equal(const Packet& a,const Packet& b,const char* message){need(same(a,b),message);}
inline void zeros(const Packet& p,std::size_t begin,std::size_t end){need(end<=p.size(),"Padding bounds");for(auto i=begin;i<end;++i){need(p[i]==0&&!std::signbit(p[i]),"Padding/absent payload is not positive zero");}}
inline void put(Packet& p,std::size_t at,Vec3 v){p.at(at)=v.x;p.at(at+1)=v.y;p.at(at+2)=v.z;}
inline void put(Packet& p,std::size_t at,I v){p.at(at)=v.lower();p.at(at+1)=v.upper();}
inline void put(Packet& p,std::size_t at,const single::Bounds3& v){for(unsigned i=0;i<3;++i){put(p,at+2*i,v[i]);}}
inline void put_body(Packet& p,std::size_t at,const pikapika::dynamics::RigidBody& b){
    p.at(at)=double(b.id);p.at(at+1)=b.is_static?1.:0.;p.at(at+2)=b.mass;p.at(at+3)=b.radius;put(p,at+4,b.inertia_diagonal);put(p,at+7,b.position);
    p.at(at+10)=b.orientation.x;p.at(at+11)=b.orientation.y;p.at(at+12)=b.orientation.z;p.at(at+13)=b.orientation.w;put(p,at+14,b.velocity);put(p,at+17,b.angular_momentum);put(p,at+20,b.force);put(p,at+23,b.torque);p.at(at+26)=b.material.restitution;p.at(at+27)=b.material.friction;
}
inline void put_settings(Packet& q,std::size_t at,const held::Settings& s){
    const auto& p=s.mesh.primitive;const std::array<double,13> a{double(s.mesh.max_surfaces),double(p.max_candidates),double(p.sqrt_refinements),double(p.max_total_sqrt_refinements),p.maximum_local_width,p.maximum_normal_width,p.minimum_sine_squared,s.time_tolerance,double(s.max_evaluations),double(s.max_leaves),double(s.max_depth),double(s.enclosure_sqrt_refinements),double(s.max_total_sqrt_refinements)};
    std::copy(a.begin(),a.end(),q.begin()+std::ptrdiff_t(at));
}
inline Packet held_input(const held::HeldSphere& b,double horizon,const held::Settings& settings){Packet q(32,0.);q[0]=double(b.id);put(q,1,b.position);put(q,4,b.velocity);q[7]=b.mass;put(q,8,b.force);put(q,11,b.gravity);q[14]=b.radius;q[15]=horizon;put_settings(q,16,settings);return q;}
inline Packet guard_input(const pikapika::dynamics::RigidBody& b,Vec3 gravity,double horizon,const guard::Settings& settings){Packet q(48,0.);put_body(q,0,b);put(q,28,gravity);q[31]=horizon;put_settings(q,32,settings.held_load);q[45]=settings.max_angular_increment;return q;}
struct Input{std::string cohort,name;unsigned mode{};Packet query;std::vector<Triangle> triangles;};
inline std::vector<Triangle> encode_source(const std::vector<single::StaticTriangle>& source){std::vector<Triangle> result;for(const auto& t:source){result.push_back({double(t.id),t.vertices[0].x,t.vertices[0].y,t.vertices[0].z,t.vertices[1].x,t.vertices[1].y,t.vertices[1].z,t.vertices[2].x,t.vertices[2].y,t.vertices[2].z});}return result;}
inline Input encode(const held_fixture::Case& c){return {"held",c.name,0,held_input(c.sphere,c.horizon,c.settings),encode_source(c.triangles)};}
inline Input encode(const free_fixture::Case& c,const char* cohort="guard"){return {cohort,c.name,1,guard_input(c.body,c.gravity,c.horizon,c.settings),encode_source(c.triangles)};}
inline std::vector<Input> corpus(){std::vector<Input> inputs;for(const auto& c:held_fixture::cases()){inputs.push_back(encode(c));}for(const auto& c:free_fixture::cases()){inputs.push_back(encode(c));}for(const auto& c:free_fixture::supplemental_cases()){inputs.push_back(encode(c,"supplemental"));}return inputs;}
inline void write_input(const Packet& p){std::copy(p.begin(),p.end(),pp_sim_input_f64_ptr());}
inline void append(unsigned mode,const std::vector<Triangle>& source,std::size_t first,std::size_t count){for(std::size_t j=0;j<count;++j){std::copy(source[first+j].begin(),source[first+j].end(),pp_sim_input_f64_ptr()+10*j);}ok(pp_sim_sphere_triangle_mesh_flight_append(mode,uint32_t(10*count)));}
inline void stage(const Input& i){ok(pp_sim_sphere_triangle_mesh_flight_begin(i.mode,uint32_t(i.triangles.size())));for(std::size_t j=0;j<i.triangles.size();j+=6){append(i.mode,i.triangles,j,std::min<std::size_t>(6,i.triangles.size()-j));}}
inline Packet run(const Input& i){stage(i);write_input(i.query);ok(pp_sim_sphere_triangle_mesh_flight_query(i.mode,uint32_t(i.query.size())));return output();}
inline Packet record(unsigned mode,unsigned kind,unsigned index=0){ok(pp_sim_sphere_triangle_mesh_flight_record(mode,kind,index));return output();}
inline Packet last_mesh(unsigned mode,unsigned part,unsigned index=0){ok(pp_sim_sphere_triangle_mesh_flight_last_mesh(mode,part,index));return output();}
inline Packet candidate(unsigned mode,unsigned row,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_flight_candidate(mode,row,ordinal));return output();}
inline Vec3 vec(const Packet& q,std::size_t at){return {q.at(at),q.at(at+1),q.at(at+2)};}
inline held::Settings settings(const Packet& q,std::size_t at){held::Settings s;auto as_uint=[&](std::size_t index){const double v=q.at(at+index);need(std::isfinite(v)&&v>=0&&v<=4294967295.&&std::floor(v)==v,"Pure host uint32 range");return uint32_t(v);};s.mesh.max_surfaces=as_uint(0);s.mesh.primitive.max_candidates=as_uint(1);s.mesh.primitive.sqrt_refinements=as_uint(2);s.mesh.primitive.max_total_sqrt_refinements=as_uint(3);s.mesh.primitive.maximum_local_width=q.at(at+4);s.mesh.primitive.maximum_normal_width=q.at(at+5);s.mesh.primitive.minimum_sine_squared=q.at(at+6);s.time_tolerance=q.at(at+7);s.max_evaluations=as_uint(8);s.max_leaves=as_uint(9);s.max_depth=as_uint(10);s.enclosure_sqrt_refinements=as_uint(11);s.max_total_sqrt_refinements=as_uint(12);return s;}
struct Expected{
    Input input;std::optional<held::Result> held_result;std::optional<guard::Result> guard_result;
    const held::Result* held_value()const{return held_result?&*held_result:guard_result&&guard_result->inflated?&*guard_result->inflated:nullptr;}
};
inline Expected pure(const Input& i){
    Expected e;e.input=i;std::vector<single::StaticTriangle> source;for(const auto& t:i.triangles){source.push_back({uint64_t(t[0]),{{{t[1],t[2],t[3]},{t[4],t[5],t[6]},{t[7],t[8],t[9]}}}});}const auto& q=i.query;
    if(i.mode==0){const held::HeldSphere b{uint64_t(q[0]),vec(q,1),vec(q,4),q[7],vec(q,8),vec(q,11),q[14]};e.held_result=held::query(b,source,q[15],settings(q,16));}
    else{pikapika::dynamics::RigidBody b;b.id=uint64_t(q[0]);b.is_static=q[1]!=0;b.mass=q[2];b.radius=q[3];b.inertia_diagonal=vec(q,4);b.position=vec(q,7);b.orientation={q[10],q[11],q[12],q[13]};b.velocity=vec(q,14);b.angular_momentum=vec(q,17);b.force=vec(q,20);b.torque=vec(q,23);b.material={q[26],q[27]};guard::Settings s;s.held_load=settings(q,32);s.max_angular_increment=q[45];e.guard_result=guard::query(b,vec(q,28),source,q[31],s);}
    return e;
}
inline void put_cell(Packet& p,std::size_t at,const held::Cell& c){p.at(at)=c.time_bounds[0];p.at(at+1)=c.time_bounds[1];p.at(at+2)=c.depth;}
inline void put_work(Packet& p,std::size_t at,const held::Work& w){const std::array<double,11> a{double(w.mesh_queries),double(w.primitive_queries),double(w.candidates_examined),double(w.primitive_sqrt_refinements),double(w.enclosure_sqrt_refinements),double(w.sqrt_refinements),double(w.sqrt_refinements_upper),double(w.mesh_sqrt_limited_rows),double(w.enclosure_sqrt_calls),double(w.enclosure_sqrt_limited_calls),w.exact?1.:0.};std::copy(a.begin(),a.end(),p.begin()+std::ptrdiff_t(at));}
inline Packet summary(const Expected& e){Packet p(24,0.);p[0]=e.input.mode;p[3]=double(e.input.triangles.size());if(e.held_result){const auto& r=*e.held_result;p[1]=unsigned(r.status);p[2]=unsigned(r.reason);p[4]=bool(r.snapshot);p[5]=bool(r.failed_index);if(r.failed_index){p[6]=double(*r.failed_index);}p[15]=1;}
    else{const auto& r=*e.guard_result;p[1]=unsigned(r.status);p[2]=unsigned(r.reason);p[4]=bool(r.snapshot);p[5]=bool(r.failed_index);if(r.failed_index){p[6]=double(*r.failed_index);}p[7]=bool(r.world_body);p[8]=bool(r.tube);p[9]=bool(r.flight_failure);if(r.flight_failure){p[10]=unsigned(*r.flight_failure);}p[11]=r.candidate_evaluated;p[12]=bool(r.endpoint);p[13]=bool(r.inflated);p[14]=bool(r.candidate);p[15]=bool(r.inflated);}return p;}
inline Packet held_header(const held::Result& r,std::size_t count){Packet p(48,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=double(count);p[3]=bool(r.snapshot);p[4]=bool(r.failed_index);if(r.failed_index){p[5]=double(*r.failed_index);}p[6]=bool(r.world_body);p[7]=bool(r.acceleration);p[8]=bool(r.whole_path_bounds);p[9]=bool(r.whole_velocity_bounds);p[10]=bool(r.initial);p[11]=r.initial_separation_proven;p[12]=double(r.certified_leaves.size());p[13]=double(r.partition.size());p[14]=double(r.frontier.size());p[15]=double(r.audits.size());p[16]=bool(r.safe_prefix);if(r.safe_prefix){p[17]=(*r.safe_prefix)[0];p[18]=(*r.safe_prefix)[1];}p[19]=bool(r.best_witness);p[20]=bool(r.window);p[21]=double(r.candidate_surface_ids.size());p[22]=bool(r.current);p[23]=bool(r.last_mesh);p[24]=bool(r.last_mesh_audit_index);if(r.last_mesh_audit_index){p[25]=double(*r.last_mesh_audit_index);}p[26]=double(r.partition_leaves);p[27]=r.maximum_depth;put_work(p,28,r.work);return p;}
inline Packet audit_packet(const held::CellAudit& a,std::size_t index){Packet p(64,0.);p[0]=double(index);p[1]=unsigned(a.kind);put_cell(p,2,a.cell);p[5]=a.time;p[6]=unsigned(a.outcome);if(a.path_bounds){p[7]=1;put(p,8,*a.path_bounds);}if(a.point_bounds){p[14]=1;put(p,15,*a.point_bounds);}if(a.anchor){p[21]=1;put(p,22,*a.anchor);}p[25]=a.mesh_queried;if(a.mesh_status){p[26]=1;p[27]=unsigned(*a.mesh_status);}if(a.mesh_reason){p[28]=1;p[29]=unsigned(*a.mesh_reason);}const std::array<const std::optional<I>*,7> fields{&a.distance,&a.displacement_squared_bound,&a.error_squared_bound,&a.displacement_root,&a.error_root,&a.clearance_certificate,&a.penetration_certificate};for(unsigned j=0;j<fields.size();++j){if(*fields[j]){p[30+3*j]=1;put(p,31+3*j,**fields[j]);}}put_work(p,51,a.work);return p;}
inline Packet mesh_header(const mesh::Result& r,std::size_t count){Packet p(24,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=bool(r.nearest);p[3]=double(count);p[4]=double(r.rows.size());p[5]=bool(r.failed_index);if(r.failed_index){p[6]=double(*r.failed_index);}p[7]=bool(r.first_failed_row);if(r.first_failed_row){p[8]=double(*r.first_failed_row);}p[9]=double(r.queries);p[10]=double(r.candidates_examined);p[11]=double(r.sqrt_refinements);p[12]=double(r.sqrt_limited_rows);p[13]=double(r.failed_rows);if(r.nearest){p[14]=double(r.nearest->possible_surface_ids.size());put(p,15,r.nearest->squared_distance);put(p,17,r.nearest->distance);put(p,19,r.nearest->gap);}return p;}
inline Packet row_packet(const single::Result& r,uint64_t id){Packet p(58,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=bool(r.geometry);p[3]=double(id);p[6]=double(r.candidates.size());p[7]=double(r.candidates_examined);p[8]=double(r.sqrt_refinements);p[9]=r.sqrt_refinement_limited;if(r.squared_cross){p[10]=1;put(p,11,*r.squared_cross);}if(r.sine_squared){p[13]=1;put(p,14,*r.sine_squared);}if(r.geometry){const auto& g=*r.geometry;p[4]=g.surviving_features;p[5]=unsigned(g.relation);put(p,16,g.barycentric);put(p,22,g.closest_local);put(p,28,g.closest);put(p,34,g.delta);put(p,40,g.normal);put(p,46,g.sphere_point);put(p,52,g.squared_distance);put(p,54,g.distance);put(p,56,g.gap);}return p;}
inline Packet candidate_packet(const single::CandidateAudit& c){Packet p(13,0.);p[0]=unsigned(c.feature);p[1]=unsigned(c.disposition);p[2]=c.kkt_count;put(p,3,c.barycentric);put(p,9,c.kkt[0]);put(p,11,c.kkt[1]);return p;}
struct EncodedRecord{unsigned kind{},index{};Packet values;};
inline std::vector<EncodedRecord> expected_records(const Expected& e){
    std::vector<EncodedRecord> rows;auto add=[&](unsigned kind,unsigned index,Packet p){rows.push_back({kind,index,std::move(p)});};const auto* h=e.held_value();const auto* g=e.guard_result?&*e.guard_result:nullptr;
    add(0,0,e.input.query);
    for(unsigned i=0;i<e.input.triangles.size();++i){Packet p(14,0.);p[0]=i;std::copy(e.input.triangles[i].begin(),e.input.triangles[i].end(),p.begin()+1);if(h&&h->last_mesh&&i<h->last_mesh->rows.size()){p[11]=1;p[12]=bool(h->last_mesh->rows[i].query);if(h->last_mesh->nearest){p[13]=std::find(h->last_mesh->nearest->possible_surface_ids.begin(),h->last_mesh->nearest->possible_surface_ids.end(),uint64_t(e.input.triangles[i][0]))!=h->last_mesh->nearest->possible_surface_ids.end();}}add(1,i,std::move(p));}
    if(e.held_result&&e.held_result->snapshot){const auto& s=*e.held_result->snapshot;add(2,0,held_input(s.input,s.horizon,s.settings));}
    if(g&&g->snapshot){const auto& s=*g->snapshot;add(2,0,guard_input(s.body,s.gravity,s.horizon,s.settings));}
    if(h){add(3,0,held_header(*h,e.input.triangles.size()));if(h->snapshot){const auto& s=*h->snapshot;add(4,0,held_input(s.input,s.horizon,s.settings));}}
    if(g&&g->world_body){Packet p(32,0.);put_body(p,0,g->world_body->body);put(p,28,g->world_body->gravity);add(5,0,std::move(p));}
    if(g&&g->tube){const auto& t=*g->tube;Packet p(24,0.);put(p,0,t.nominal_acceleration);put(p,3,t.exact_acceleration);put(p,9,t.acceleration_difference);p[15]=t.position_error;p[16]=t.roundoff;p[17]=t.guard_radius;add(6,0,std::move(p));}
    if(g&&g->endpoint){const auto& a=*g->endpoint;Packet p(40,0.);put(p,0,a.nominal_position);put(p,6,a.nominal_allowed);put(p,12,a.exact_position);put(p,18,a.exact_allowed);put(p,24,a.exact_difference);put(p,30,a.l1_error_bound);p[32]=a.nominal_contained;p[33]=a.exact_contained;p[34]=a.l1_within_tube;add(7,0,std::move(p));}
    if(g&&g->candidate){Packet p(32,0.);put_body(p,0,*g->candidate);add(8,0,std::move(p));}
    if(h){const std::array<const std::optional<single::Bounds3>*,3> bounds{&h->acceleration,&h->whole_path_bounds,&h->whole_velocity_bounds};for(unsigned j=0;j<bounds.size();++j){if(*bounds[j]){Packet p(8,0.);put(p,1,**bounds[j]);add(9+j,0,std::move(p));}}
        for(unsigned i=0;i<h->audits.size();++i){add(12,i,audit_packet(h->audits[i],i));}
        for(unsigned i=0;i<h->certified_leaves.size();++i){const auto& a=h->certified_leaves[i];Packet p(6,0.);put_cell(p,0,a.cell);put(p,3,a.lower_gap_certificate);p[5]=double(a.audit_index);add(13,i,std::move(p));}
        for(unsigned i=0;i<h->partition.size();++i){const auto& a=h->partition[i];Packet p(8,0.);p[0]=i;put_cell(p,1,a.cell);p[4]=unsigned(a.state);p[5]=bool(a.audit_index);if(a.audit_index){p[6]=double(*a.audit_index);}p[7]=unsigned(a.blocked_reason);add(14,i,std::move(p));}
        for(unsigned i=0;i<h->frontier.size();++i){Packet p(4,0.);p[0]=i;put_cell(p,1,h->frontier[i]);add(15,i,std::move(p));}
        if(h->current){Packet p(4,0.);put_cell(p,1,*h->current);add(16,0,std::move(p));}
        if(h->initial){Packet p(6,0.);put(p,1,h->initial->lower_gap_certificate);put(p,3,h->initial->upper_gap_certificate);p[5]=double(h->initial->audit_index);add(17,0,std::move(p));}
        if(h->best_witness){const auto& w=*h->best_witness;Packet p(18,0.);put_cell(p,1,w.cell);p[4]=w.time;put(p,5,w.exact_path_bounds);put(p,11,w.anchor);p[14]=w.error_upper;put(p,15,w.upper_gap_certificate);p[17]=double(w.audit_index);add(18,0,std::move(p));}
        if(h->window){const auto& w=*h->window;Packet p(14,0.);p[1]=w.time_bounds[0];p[2]=w.time_bounds[1];put(p,3,w.time_width);put(p,5,w.path_bounds);put(p,11,w.l1_diameter_bound);p[13]=double(w.witness_audit_index);add(19,0,std::move(p));}
        for(unsigned i=0;i<h->candidate_surface_ids.size();++i){add(20,i,Packet{double(i),double(h->candidate_surface_ids[i])});}
    }
    return rows;
}
inline void verify_packets(const Input& i,const Packet& actual){
    const auto e=pure(i);equal(actual,summary(e),"Family summary24 differs from Native pure result");zeros(actual,16,24);
    for(const auto& r:expected_records(e)){equal(record(i.mode,r.kind,r.index),r.values,"Full owned Native record fields/padding/bits differ");}
    if(const auto* h=e.held_value();h&&h->last_mesh){equal(last_mesh(i.mode,0),mesh_header(*h->last_mesh,i.triangles.size()),"Last mesh24 differs");for(unsigned j=0;j<h->last_mesh->rows.size();++j){const auto& row=h->last_mesh->rows[j];if(row.query){equal(last_mesh(i.mode,1,j),row_packet(*row.query,row.triangle.id),"Full last mesh row58 differs");for(unsigned k=0;k<row.query->candidates.size();++k){equal(candidate(i.mode,j,k),candidate_packet(row.query->candidates[k]),"Complete candidate13 KKT bits differ");}}}}
}
}
