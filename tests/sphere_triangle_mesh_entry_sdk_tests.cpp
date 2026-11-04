#include "pikapika/simulation_api.h"
#include "pikapika/sphere_triangle_mesh_entry.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

// This is an exchange/layout/ownership suite. Pure guard calls below check the
// adapter's bits, not the independent mathematical proof (separate Fraction
// whole-path reference). No geometric solver is implemented by this test.
namespace {
namespace guard=pikapika::sphere_triangle_mesh_entry;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using Packet=std::vector<double>;
using Triangle=std::array<double,10>;
using Query=std::array<double,24>;
unsigned groups{};
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void ok(int32_t status){if(status!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
Packet output(){const auto n=pp_sim_output_count();need(n<=64,"Output capacity");const auto* p=pp_sim_output_f64_ptr();return {p,p+n};}
bool same(const Packet& a,const Packet& b){
    return a.size()==b.size()&&std::equal(a.begin(),a.end(),b.begin(),[](double x,double y){return std::bit_cast<uint64_t>(x)==std::bit_cast<uint64_t>(y);});
}
void equal(const Packet& a,const Packet& b,const char* message){need(same(a,b),message);}
template<class F>void rejected(F f){const auto before=output();need(f()==PP_SIM_INVALID_ARGUMENT,"Expected host/getter rejection");equal(before,output(),"Rejected operation changed old output bits/count");}
template<class F>void test(const char* name,F f){ok(pp_sim_reset());f();++groups;std::cout<<"PASS "<<name<<'\n';}
Triangle triangle(double id,double y=0){return {id,-0.,y,-0.,4,y,0,0,y,4};}
Triangle big_triangle(double id){return {id,-0.,0,-0.,1024,0,0,0,0,1024};}
Query query(){return {1,1,1,1,1,1,.25,64,7,128,1024,1e-7,1e-8,1e-12,256,128,24,128,1000000,1e-6,0,0,0,0};}
void input(const Query& q){std::copy(q.begin(),q.end(),pp_sim_input_f64_ptr());}
void append(const std::vector<Triangle>& triangles,std::size_t first,std::size_t count){
    for(std::size_t j=0;j<count;++j)std::copy(triangles[first+j].begin(),triangles[first+j].end(),pp_sim_input_f64_ptr()+10*j);
    ok(pp_sim_sphere_triangle_mesh_entry_append(uint32_t(10*count)));
}
void stage(const std::vector<Triangle>& triangles){ok(pp_sim_sphere_triangle_mesh_entry_begin(uint32_t(triangles.size())));for(std::size_t i=0;i<triangles.size();i+=6)append(triangles,i,std::min<std::size_t>(6,triangles.size()-i));}
Packet run(const std::vector<Triangle>& triangles,Query q=query()){stage(triangles);input(q);ok(pp_sim_sphere_triangle_mesh_entry(24));return output();}
Packet record(unsigned kind,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_entry_record(kind,ordinal));return output();}
Packet last_mesh(unsigned part,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_entry_last_mesh(part,ordinal));return output();}
Packet candidate(unsigned row,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_entry_candidate(row,ordinal));return output();}
void zeros(const Packet& p,std::size_t first,std::size_t last){need(last<=p.size(),"Padding range");for(std::size_t j=first;j<last;++j)need(p[j]==0&&!std::signbit(p[j]),"Absent payload/padding must be positive zero");}
void put(Packet& p,std::size_t at,pikapika::interval::Interval value){p.at(at)=value.lower();p.at(at+1)=value.upper();}
void put(Packet& p,std::size_t at,pikapika::Vec3 value){p.at(at)=value.x;p.at(at+1)=value.y;p.at(at+2)=value.z;}
void put(Packet& p,std::size_t at,const single::Bounds3& value){for(unsigned j=0;j<3;++j)put(p,at+2*j,value[j]);}
void put_cell(Packet& p,std::size_t at,const guard::Cell& c){p.at(at)=c.parameter[0];p.at(at+1)=c.parameter[1];p.at(at+2)=c.depth;}
void put_work(Packet& p,std::size_t at,const guard::Work& w){const std::array<double,11> values{
    double(w.mesh_queries),double(w.primitive_queries),double(w.candidates_examined),double(w.primitive_sqrt_refinements),
    double(w.enclosure_sqrt_refinements),double(w.sqrt_refinements),double(w.sqrt_refinements_upper),double(w.mesh_sqrt_limited_rows),
    double(w.enclosure_sqrt_calls),double(w.enclosure_sqrt_limited_calls),w.exact?1.:0.};std::copy(values.begin(),values.end(),p.begin()+std::ptrdiff_t(at));}
guard::Result pure(const std::vector<Triangle>& triangles,const Query& q){
    std::vector<single::StaticTriangle> source;for(const auto& t:triangles)source.push_back({uint64_t(t[0]),{{{t[1],t[2],t[3]},{t[4],t[5],t[6]},{t[7],t[8],t[9]}}}});
    const auto as_unsigned=[](double value){need(std::isfinite(value)&&value>=0&&value<=double(std::numeric_limits<unsigned>::max())&&std::floor(value)==value,"Pure comparison unsigned setting range");return static_cast<unsigned>(value);};
    guard::Settings s;s.mesh.max_surfaces=std::size_t(q[7]);s.mesh.primitive.max_candidates=as_unsigned(q[8]);s.mesh.primitive.sqrt_refinements=as_unsigned(q[9]);s.mesh.primitive.max_total_sqrt_refinements=as_unsigned(q[10]);
    s.mesh.primitive.maximum_local_width=q[11];s.mesh.primitive.maximum_normal_width=q[12];s.mesh.primitive.minimum_sine_squared=q[13];
    s.max_evaluations=std::size_t(q[14]);s.max_leaves=std::size_t(q[15]);s.max_depth=unsigned(q[16]);s.enclosure_sqrt_refinements=unsigned(q[17]);s.max_total_sqrt_refinements=std::size_t(q[18]);
    s.parameter_tolerance=q[19];
    return guard::query({q[0],q[1],q[2]},{q[3],q[4],q[5]},q[6],source,s);
}
Packet mesh_header(const mesh::Result& r,std::size_t count){
    Packet p(24,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=bool(r.nearest);p[3]=double(count);p[4]=double(r.rows.size());
    p[5]=bool(r.failed_index);if(r.failed_index)p[6]=double(*r.failed_index);p[7]=bool(r.first_failed_row);if(r.first_failed_row)p[8]=double(*r.first_failed_row);
    p[9]=double(r.queries);p[10]=double(r.candidates_examined);p[11]=double(r.sqrt_refinements);p[12]=double(r.sqrt_limited_rows);p[13]=double(r.failed_rows);
    if(r.nearest){p[14]=double(r.nearest->possible_surface_ids.size());put(p,15,r.nearest->squared_distance);put(p,17,r.nearest->distance);put(p,19,r.nearest->gap);}return p;
}
Packet row_packet(const single::Result& r,uint64_t id){
    Packet p(58,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=bool(r.geometry);p[3]=double(id);p[6]=double(r.candidates.size());p[7]=double(r.candidates_examined);p[8]=double(r.sqrt_refinements);p[9]=r.sqrt_refinement_limited;
    if(r.squared_cross){p[10]=1;put(p,11,*r.squared_cross);}if(r.sine_squared){p[13]=1;put(p,14,*r.sine_squared);}
    if(r.geometry){const auto& g=*r.geometry;p[4]=g.surviving_features;p[5]=unsigned(g.relation);put(p,16,g.barycentric);put(p,22,g.closest_local);put(p,28,g.closest);put(p,34,g.delta);put(p,40,g.normal);put(p,46,g.sphere_point);put(p,52,g.squared_distance);put(p,54,g.distance);put(p,56,g.gap);}return p;
}
Packet candidate_packet(const single::CandidateAudit& c){Packet p(13,0.);p[0]=unsigned(c.feature);p[1]=unsigned(c.disposition);p[2]=c.kkt_count;put(p,3,c.barycentric);put(p,9,c.kkt[0]);put(p,11,c.kkt[1]);return p;}
Packet header(const guard::Result& r,std::size_t count){
    Packet p(40,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=double(count);p[3]=bool(r.snapshot);p[4]=bool(r.failed_index);
    if(r.failed_index){p[5]=double(*r.failed_index);}p[6]=bool(r.initial);p[7]=r.initial_separation_proven;p[8]=double(r.certified_leaves.size());p[9]=double(r.partition.size());p[10]=double(r.frontier.size());p[11]=double(r.audits.size());p[12]=bool(r.safe_prefix);
    if(r.safe_prefix){p[13]=(*r.safe_prefix)[0];p[14]=(*r.safe_prefix)[1];}p[15]=bool(r.best_witness);p[16]=bool(r.window);p[17]=double(r.candidate_surface_ids.size());p[18]=bool(r.current);p[19]=bool(r.last_mesh);p[20]=bool(r.last_mesh_audit_index);
    if(r.last_mesh_audit_index){p[21]=double(*r.last_mesh_audit_index);}p[22]=double(r.partition_leaves);p[23]=r.maximum_depth;put_work(p,24,r.work);return p;
}
Packet audit_packet(const guard::CellAudit& a,std::size_t ordinal){
    Packet p(64,0.);p[0]=double(ordinal);p[1]=unsigned(a.kind);put_cell(p,2,a.cell);p[5]=a.parameter;p[6]=unsigned(a.outcome);
    if(a.path_bounds){p[7]=1;put(p,8,*a.path_bounds);}if(a.point_bounds){p[14]=1;put(p,15,*a.point_bounds);}if(a.anchor){p[21]=1;put(p,22,*a.anchor);}
    p[25]=a.mesh_queried;if(a.mesh_status){p[26]=1;p[27]=unsigned(*a.mesh_status);}if(a.mesh_reason){p[28]=1;p[29]=unsigned(*a.mesh_reason);}
    const std::array<const std::optional<pikapika::interval::Interval>*,7> fields{&a.distance,&a.displacement_squared_bound,&a.error_squared_bound,&a.displacement_root,&a.error_root,&a.clearance_certificate,&a.penetration_certificate};
    for(unsigned j=0;j<fields.size();++j){if(*fields[j]){p[30+3*j]=1;put(p,31+3*j,**fields[j]);}}
    put_work(p,51,a.work);return p;
}
void verify_packets(const std::vector<Triangle>& triangles,const Query& q,const Packet& actual,const guard::Result& r){
    equal(actual,header(r,triangles.size()),"Full entry header40 differs from pure result");zeros(actual,35,40);
    equal(record(0,0),Packet(q.begin(),q.end()),"Echo24 lost original input/settings bits");
    for(unsigned j=0;j<triangles.size();++j){
        Packet p(14,0.);p[0]=j;std::copy(triangles[j].begin(),triangles[j].end(),p.begin()+1);
        if(r.last_mesh&&j<r.last_mesh->rows.size()){p[11]=1;p[12]=bool(r.last_mesh->rows[j].query);if(r.last_mesh->nearest){p[13]=std::find(r.last_mesh->nearest->possible_surface_ids.begin(),r.last_mesh->nearest->possible_surface_ids.end(),uint64_t(triangles[j][0]))!=r.last_mesh->nearest->possible_surface_ids.end();}}
        equal(record(1,j),p,"Source14 bits and lastMesh flags");
    }
    for(unsigned j=0;j<r.audits.size();++j){const auto p=record(2,j);equal(p,audit_packet(r.audits[j],j),"Audit64 kind/initial/global parameter/optional/work");zeros(p,62,64);}
    for(unsigned j=0;j<r.certified_leaves.size();++j){const auto& l=r.certified_leaves[j];Packet p(6,0.);put_cell(p,0,l.cell);put(p,3,l.lower_gap_certificate);p[5]=double(l.audit_index);equal(record(3,j),p,"All certified islands/certificate links");}
    for(unsigned j=0;j<r.partition.size();++j){const auto& l=r.partition[j];Packet p(8,0.);p[0]=j;put_cell(p,1,l.cell);p[4]=unsigned(l.state);p[5]=bool(l.audit_index);if(l.audit_index){p[6]=double(*l.audit_index);}p[7]=unsigned(l.blocked_reason);equal(record(4,j),p,"Full sorted partition8 state/index/blocked reason");}
    for(unsigned j=0;j<r.frontier.size();++j){Packet p(4,0.);p[0]=j;put_cell(p,1,r.frontier[j]);equal(record(5,j),p,"Every breadth frontier/tail cell");}
    if(r.current){Packet p(4,0.);put_cell(p,1,*r.current);equal(record(6,0),p,"Current4 can be initial point outside partition");}
    if(r.initial){const auto& i=*r.initial;Packet p(6,0.);put(p,1,i.lower_gap_certificate);put(p,3,i.upper_gap_certificate);p[5]=double(i.audit_index);equal(record(7,0),p,"Initial6 both expressions and audit0");}
    if(r.best_witness){const auto& w=*r.best_witness;Packet p(18,0.);put_cell(p,1,w.cell);p[4]=w.parameter;put(p,5,w.exact_path_bounds);put(p,11,w.anchor);p[14]=w.error_upper;put(p,15,w.upper_gap_certificate);p[17]=double(w.audit_index);equal(record(8,0),p,"Best witness18 strict E/path/audit relation");}
    if(r.window){const auto& w=*r.window;Packet p(6,0.);p[1]=w.parameter[0];p[2]=w.parameter[1];put(p,3,w.width);p[5]=double(w.witness_audit_index);equal(record(9,0),p,"Window6 outward width and witness link");}
    for(unsigned j=0;j<r.candidate_surface_ids.size();++j){equal(record(10,j),Packet{double(j),double(r.candidate_surface_ids[j])},"All conservative ID records2");}
    if(r.last_mesh){
        equal(last_mesh(0,0),mesh_header(*r.last_mesh,triangles.size()),"Last mesh summary24");
        for(unsigned j=0;j<r.last_mesh->rows.size();++j){if(r.last_mesh->rows[j].query){const auto& row=r.last_mesh->rows[j];equal(last_mesh(1,j),row_packet(*row.query,row.triangle.id),"Last mesh row58 own failure/success");for(unsigned k=0;k<row.query->candidates.size();++k){equal(candidate(j,k),candidate_packet(row.query->candidates[k]),"Last candidate13 exact KKT signs");}}}
    }
}
void verify_case(const std::vector<Triangle>& triangles,Query q=query()){const auto actual=run(triangles,q);const auto reference=pure(triangles,q);verify_packets(triangles,q,actual,reference);}
Query crossing(){auto q=query();q[1]=2;q[4]=-4;q[6]=.5;return q;}
void single_snapshot(){auto* p=pp_sim_input_f64_ptr();const auto q=query();std::fill_n(p,24,0.);std::copy_n(q.begin(),3,p);p[3]=q[6];const auto t=triangle(999);std::copy(t.begin(),t.end(),p+4);std::copy_n(q.begin()+8,6,p+14);ok(pp_sim_sphere_triangle(24));}
void mesh_snapshot(){auto* p=pp_sim_input_f64_ptr();ok(pp_sim_sphere_triangle_mesh_begin(1));const auto t=triangle(511);std::copy(t.begin(),t.end(),p);ok(pp_sim_sphere_triangle_mesh_append(10));const auto q=query();std::array<double,14> m{};std::copy_n(q.begin(),3,m.begin());m[3]=q[6];m[4]=q[7];std::copy_n(q.begin()+8,6,m.begin()+5);std::copy(m.begin(),m.end(),p);ok(pp_sim_sphere_triangle_mesh(14));}
void trajectory_snapshot(){const auto t=triangle(311);ok(pp_sim_sphere_triangle_mesh_trajectory_begin(1));std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());ok(pp_sim_sphere_triangle_mesh_trajectory_append(10));auto q=query();q[19]=0;input(q);ok(pp_sim_sphere_triangle_mesh_trajectory(24));}
}

int main(){try{
test("ABI1 and existing capacities unchanged new explicit record constants",[]{
    need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64&&pp_sim_input_f64_capacity()==49152&&pp_sim_input_u32_capacity()==98304,"Existing ABI capacities");
    need(PP_SIM_SPHERE_TRIANGLE_MESH_ENTRY_OUTPUT_COUNT==40&&PP_SIM_SPHERE_TRIANGLE_MESH_ENTRY_MAX_AUDITS==256&&PP_SIM_SPHERE_TRIANGLE_MESH_ENTRY_MAX_FRONTIER==128,"Entry wire constants");
});
test("unbegun stage and absent all eleven getters reject without changing output",[]{
    input(query());rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(10);});rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});
    for(unsigned kind=0;kind<11;++kind){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,0);});}
    rejected([]{return pp_sim_sphere_triangle_mesh_entry_last_mesh(0,0);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(0,0);});
});
test("all chunks1through6 preserve initial point flags signed zero and full layout",[]{
    for(unsigned n=1;n<=6;++n){std::vector<Triangle> source;for(unsigned j=0;j<n;++j){source.push_back(triangle(20+j));}verify_case(source);const auto s=record(1,n-1);need(std::signbit(s[2])&&std::signbit(s[4]),"Source signed zero lost");}
});
test("actual entry has initial safe prefix best witness outward window and later islands",[]{
    const auto q=crossing();const std::vector<Triangle> source{triangle(37),triangle(5,-2)};const auto h=run(source,q);
    need(h[0]==0&&h[6]==1&&h[7]==1&&h[12]==1&&h[15]==1&&h[16]==1&&h[17]==2,"Complete entry proof absent");verify_packets(source,q,h,pure(source,q));
    const auto w=record(9,0),b=record(8,0),initial=record(7,0);need(w[1]<.25&&w[2]>.25&&w[4]<=q[19]&&b[16]<0&&initial[1]>0&&initial[5]==0,"Quarter window/strict sign fields");
    need(record(10,0)[1]==5&&record(10,1)[1]==37,"All IDs must remain conservative");
    // Frozen pure cases distinguish these sources: the second plane leaves
    // the later domain unqueried (no certified island). The single-plane
    // analytic quarter case has an actual certified island beyond its prefix.
    const std::vector<Triangle> single_source{triangle(37)};const auto island_header=run(single_source,q);
    verify_packets(single_source,q,island_header,pure(single_source,q));
    bool island=false;for(unsigned j=0;j<island_header[8];++j){if(record(3,j)[0]>island_header[14]){island=true;}}need(island,"Later certified island disappeared into prefix");
});
test("actual64 entry sources conservative IDs final row and seventh candidate preserved",[]{
    std::vector<Triangle> source;for(unsigned j=0;j<64;++j){source.push_back(triangle(64-j));}const auto q=crossing();const auto h=run(source,q);
    need(h[0]==0&&h[2]==64&&h[17]==64,"64-source entry failed");verify_packets(source,q,h,pure(source,q));
    need(record(1,63)[1]==1&&record(10,63)[1]==64&&candidate(63,6)[0]==6,"Last source/ID/candidate missing");
    rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(1,64);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(10,64);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(63,7);});
});
test("actual256 audits128 proof leaves partition tails include the initial query",[]{
    auto q=query();q[3]=129;const std::vector<Triangle> source{big_triangle(37)};const auto h=run(source,q);
    need(h[0]==1&&h[8]==128&&h[9]==128&&h[11]==256&&h[22]==128&&h[24]==256,"Hard capacity not reached");verify_packets(source,q,h,pure(source,q));
    need(record(2,255)[0]==255&&record(3,127)[1]==1&&record(4,127)[2]==1,"Final audit/leaf/partition truncated");
    rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(2,256);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(3,128);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(4,128);});
});
test("BFS frontier127 exceeds legacy33 and initial-only budget keeps a distinct current",[]{
    auto q=query();q[3]=129;q[14]=128;const std::vector<Triangle> source{big_triangle(37)};const auto h=run(source,q);
    need(h[0]==3&&h[1]==9&&h[9]==128&&h[10]==127&&h[11]==128&&h[18]==1&&h[14]==0,"Breadth capacity/zero-prefix altered");verify_packets(source,q,h,pure(source,q));
    need(record(5,126)[0]==126,"Final frontier lost");rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(5,127);});
    q=query();q[14]=1;verify_case({triangle(37)},q);need(record(6,0)[1]==0&&record(7,0)[1]>0,"Initial-only proof/current not distinct");
});
test("127partition stop keeps126 certified leaves and never calls it a window",[]{
    auto q=query();q[3]=129;q[15]=127;const std::vector<Triangle> source{big_triangle(37)};const auto h=run(source,q);
    need(h[0]==3&&h[1]==10&&h[8]==126&&h[9]==127&&h[11]==254&&h[12]==1&&h[14]>0&&h[14]<1&&h[16]==0,"Partial prefix hidden or accepted");verify_packets(source,q,h,pure(source,q));
});
test("initial strict negative boundary and normal failure keep their actual diagnostics",[]{
    auto q=query();q[1]=q[4]=.125;const auto h=run({triangle(37)},q);need(h[0]==2&&h[6]==1&&h[7]==0&&h[15]==0&&h[16]==0&&record(7,0)[4]<0,"Initial penetration became window/witness");verify_packets({triangle(37)},q,h,pure({triangle(37)},q));
    q=query();q[1]=q[4]=.5;q[6]=.5;verify_case({triangle(37)},q);need(record(2,0)[6]==3,"Initial boundary lost uncertainty");
    q[1]=q[4]=0;verify_case({triangle(37)},q);need(record(2,0)[27]==3,"Initial zero-distance failed mesh not retained");
});
test("rowfailure ancestor splits and exact child proofs may recover without borrowing geometry",[]{
    auto q=crossing();q[4]=-2;const std::vector<Triangle> source{triangle(37)};const auto h=run(source,q);need(h[0]==0,"Symmetric child recovery failed");verify_packets(source,q,h,pure(source,q));
    const auto a=record(2,1);need(a[1]==1&&a[27]==3&&a[6]==5&&record(8,0)[17]>1,"Failed ancestor promoted or stopped later children");
});
test("begin append and overwritten scratch cannot mutate old committed records",[]{
    run({triangle(37)},crossing());const auto echo=record(0,0),source=record(1,0),a=record(2,1),window=record(9,0);
    ok(pp_sim_sphere_triangle_mesh_entry_begin(2));equal(output(),window,"Valid begin changed output");append({triangle(51)},0,1);equal(output(),window,"Valid append changed output");
    std::fill_n(pp_sim_input_f64_ptr(),64,123.);equal(record(0,0),echo,"Echo aliases scratch");equal(record(1,0),source,"Original source aliases stage");equal(record(2,1),a,"Audit aliases caller");equal(record(9,0),window,"Window aliases scratch");
    append({triangle(52)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));need(record(1,0)[1]==51&&source[1]==37,"New commit mutated old copied source");
});
test("bad begin and complete invalid append chunks are atomic and reusable",[]{
    run({triangle(37)});const auto old=record(1,0);for(auto n:{65u,std::numeric_limits<uint32_t>::max()}){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_begin(n);});}
    input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));equal(record(1,0),old,"Invalid begin erased existing stage");
    for(double bad:{0.,9007199254740992.,1.5,-1.,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){
        ok(pp_sim_sphere_triangle_mesh_entry_begin(3));append({triangle(1)},0,1);const auto a=triangle(2),b=triangle(bad);std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());std::copy(b.begin(),b.end(),pp_sim_input_f64_ptr()+10);
        rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(20);});append({triangle(2),triangle(3)},0,2);input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));need(output()[2]==3,"Bad final member partially committed");
    }
});
test("nonfinite last coordinates and incomplete overrun wrong lengths preserve all state",[]{
    for(double bad:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){
        run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_entry_begin(2));const auto a=triangle(1);auto b=triangle(2);b[9]=bad;std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());std::copy(b.begin(),b.end(),pp_sim_input_f64_ptr()+10);
        rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(20);});append({triangle(1),triangle(2)},0,2);input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));need(output()[0]==1,"Bad coordinate poisoned stage");
    }
    ok(pp_sim_sphere_triangle_mesh_entry_begin(2));for(auto n:{0u,1u,9u,11u,59u,61u,70u,std::numeric_limits<uint32_t>::max()}){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_append(n);});}
    input(query());rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});append({triangle(1)},0,1);input(query());rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});
    const auto t=triangle(2);std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(20);});append({triangle(2)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(10);});
});
test("all query shape finite integer failures reject and keep original echo and staged source",[]{
    run({triangle(37)});const auto old=record(0,0);
    for(auto n:{0u,19u,23u,25u,std::numeric_limits<uint32_t>::max()}){input(query());rejected([&]{return pp_sim_sphere_triangle_mesh_entry(n);});}
    for(unsigned at=0;at<20;++at){auto q=query();q[at]=std::numeric_limits<double>::infinity();input(q);rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});}
    for(unsigned at:{7u,8u,9u,10u,14u,15u,16u,17u,18u}){for(double value:{-1.,.5,4294967296.}){auto q=query();q[at]=value;input(q);rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});}}
    for(unsigned at=20;at<24;++at){for(double value:{1.,-0.}){auto q=query();q[at]=value;input(q);rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});}}
    equal(record(0,0),old,"Exchange failure replaced echo");input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));need(output()[0]==1,"Valid stage did not recover");
});
test("finite model-invalid settings and negativezero originals reach the actual kernel",[]{
    for(unsigned at:{7u,8u,9u,10u,14u,15u,17u,18u}){for(double value:{0.,4294967295.}){auto q=query();q[at]=value;const auto h=run({triangle(37)},q);need(h[0]==4&&h[1]==1&&h[3]==0&&h[11]==0,"Model setting became host failure/success");equal(record(0,0),Packet(q.begin(),q.end()),"Invalid original echo lost");}}
    for(double value:{0.,-0.,-1.,2.}){auto q=query();q[19]=value;verify_case({triangle(37)},q);need(record(0,0)[19]==value,"Tolerance source changed");}
    auto q=query();q[16]=-0.;const auto h=run({triangle(37)},q);need(h[0]==1&&std::signbit(record(0,0)[16]),"Valid depth0/source negativezero not preserved");verify_packets({triangle(37)},q,h,pure({triangle(37)},q));
});
test("accepted preflight and surface budget replace old proof but keep original source without snapshot",[]{
    run({triangle(37)},crossing());auto h=run({});need(h[0]==4&&h[1]==2&&h[3]==0&&h[6]==0&&h[16]==0,"Empty retained old proof");rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(1,0);});
    h=run({triangle(37),triangle(37)});need(h[0]==4&&h[1]==4&&h[4]==1&&h[5]==1&&h[3]==0,"Duplicate source index wrong");const auto s=record(1,1);zeros(s,11,14);need(s[1]==37,"Preflight lost source");
    auto t=triangle(9);t[1]=1e13;verify_case({t});need(record(1,0)[2]==1e13,"Finite out-of-domain source was erased");
    auto q=query();q[7]=1;const std::vector<Triangle> source{triangle(1),triangle(2)};h=run(source,q);need(h[0]==3&&h[1]==6&&h[3]==1&&h[11]==0&&h[10]==1&&h[19]==0,"Surface budget borrowed query/proof");verify_packets(source,q,h,pure(source,q));
});
test("far failed row later successful row and candidate-prefix failure are all retained",[]{
    const Triangle bad{99,1000,0,0,1004,0,0,1008,0,0};const std::vector<Triangle> source{triangle(37),bad,triangle(5,-4)};const auto h=run(source);
    need(h[0]==3&&h[1]==7&&h[6]==0&&h[19]==1,"Initial failed mesh hidden");verify_packets(source,query(),h,pure(source,query()));need(last_mesh(1,1)[0]==2&&last_mesh(1,2)[0]==0,"Failed/later row changed");
    auto q=query();q[8]=3;verify_case({triangle(37),triangle(5,-4)},q);need(candidate(1,2)[0]==2,"Candidate prefix missing");rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(1,3);});
});
test("unresolved earlier leaf and later negative witness do not accept a too-wide window",[]{
    auto q=crossing();q[19]=0x1p-32;q[16]=10;const std::vector<Triangle> source{triangle(37)};const auto h=run(source,q);
    need(h[0]==3&&h[1]==11&&h[15]==1&&h[16]==0&&h[12]==1&&h[14]<.25,"Unknown cell width became window");verify_packets(source,q,h,pure(source,q));rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(9,0);});
});
test("sqrt budgets current initial point and unqueried lastmesh absence preserve exact work",[]{
    auto q=query();q[18]=511;const std::vector<Triangle> source{triangle(37)};const auto h=run(source,q);need(h[0]==3&&h[1]==12&&h[19]==0&&h[24]==0,"Before-mesh reservation made a query");verify_packets(source,q,h,pure(source,q));
    const auto a=record(2,0);need(a[1]==0&&a[25]==0,"Initial unqueried audit reused old mesh");zeros(a,26,51);rejected([]{return pp_sim_sphere_triangle_mesh_entry_last_mesh(0,0);});
    q[18]=512;verify_case(source,q);
});
test("all getter tails absent optionals and null geometry preserve outputcount and committed snapshots",[]{
    run({triangle(37)});const auto old=record(1,0);
    for(auto kind:{11u,std::numeric_limits<uint32_t>::max()}){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,0);});}
    for(unsigned kind=0;kind<11;++kind){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,std::numeric_limits<uint32_t>::max());});}
    for(unsigned kind:{0u,6u,7u,8u,9u}){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,1);});}
    for(unsigned kind:{5u,6u,8u,9u,10u}){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,0);});}
    rejected([]{return pp_sim_sphere_triangle_mesh_entry_last_mesh(0,1);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_last_mesh(2,0);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(1,0);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(0,7);});equal(record(1,0),old,"Rejected getter changed committed source");
});
test("old single mesh and trajectory stages and owned snapshots remain independent",[]{
    single_snapshot();ok(pp_sim_sphere_triangle_candidate(0));const auto single=output();mesh_snapshot();ok(pp_sim_sphere_triangle_mesh_source(0));const auto mesh=output();trajectory_snapshot();ok(pp_sim_sphere_triangle_mesh_trajectory_record(1,0));const auto trajectory=output();
    run({triangle(37)},crossing());const auto entry=record(1,0);need(std::signbit(candidate(0,0)[9]),"Unused KKT negativezero lost");
    ok(pp_sim_sphere_triangle_candidate(0));equal(output(),single,"Entry overwrote single snapshot");ok(pp_sim_sphere_triangle_mesh_source(0));equal(output(),mesh,"Entry overwrote mesh snapshot");ok(pp_sim_sphere_triangle_mesh_trajectory_record(1,0));equal(output(),trajectory,"Entry overwrote trajectory snapshot");
    ok(pp_sim_sphere_triangle_mesh_begin(1));const auto mesh_staged=triangle(611);std::copy(mesh_staged.begin(),mesh_staged.end(),pp_sim_input_f64_ptr());ok(pp_sim_sphere_triangle_mesh_append(10));
    ok(pp_sim_sphere_triangle_mesh_trajectory_begin(1));const auto t=triangle(711);std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());ok(pp_sim_sphere_triangle_mesh_trajectory_append(10));
    ok(pp_sim_sphere_triangle_mesh_entry_begin(1));append({triangle(811)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_entry(24));need(record(1,0)[1]==811,"Entry dedicated stage missing");
    const std::array<double,14> mesh_query{1,1,1,.25,64,7,128,1024,1e-7,1e-8,1e-12,0,0,0};std::copy(mesh_query.begin(),mesh_query.end(),pp_sim_input_f64_ptr());ok(pp_sim_sphere_triangle_mesh(14));ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[1]==611,"Entry overwrote ordinary mesh staging");
    auto q=query();q[19]=0;input(q);ok(pp_sim_sphere_triangle_mesh_trajectory(24));ok(pp_sim_sphere_triangle_mesh_trajectory_record(1,0));need(output()[1]==711,"Entry overwrote trajectory staging");need(record(1,0)[1]==811&&entry[1]==37,"Later query mutated copied old entry");
});
test("World clock reset destruction and model failures do not share entry record lifetime",[]{
    const auto world=pp_sim_world_create();need(world!=0,"World create");ok(pp_sim_world_info(world));const auto info=output();run({triangle(37)},crossing());const auto echo=record(0,0),source=record(1,0);
    ok(pp_sim_world_info(world));equal(output(),info,"Entry advanced World/time");ok(pp_sim_world_reset(world));equal(record(1,0),source,"World reset erased entry");ok(pp_sim_world_destroy(world));equal(record(0,0),echo,"World destroy erased entry");
    auto q=query();q[6]=-1;run({triangle(37)},q);need(record(0,0)[6]==-1,"New model failure retained old input");rejected([]{return pp_sim_sphere_triangle_mesh_entry_record(9,0);});need(run({triangle(37)})[0]==1,"Recovery after model failure failed");
});
test("unsupported rounding remains a real Native model with original echo and caller mode intact",[]{
    const auto q=query();stage({triangle(37)});input(q);const auto before=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Set upward");const auto code=pp_sim_sphere_triangle_mesh_entry(24);const auto h=output();const auto after=std::fegetround();std::fesetround(before);ok(code);
    need(h.size()==40&&h[0]==5&&h[1]==16&&h[2]==1&&h[3]==0&&h[11]==0&&after==FE_UPWARD,"Environment model/priority/mode changed");equal(record(0,0),Packet(q.begin(),q.end()),"Unsupported environment echo lost");input(q);ok(pp_sim_sphere_triangle_mesh_entry(24));need(output()[0]==1,"Environment recovery failed");
});
test("global reset clears all entry stages records and optionals then accepts a new query",[]{
    run({triangle(37)},crossing());single_snapshot();mesh_snapshot();trajectory_snapshot();ok(pp_sim_reset());need(pp_sim_output_count()==0,"Global reset left output");
    for(unsigned kind=0;kind<11;++kind){rejected([&]{return pp_sim_sphere_triangle_mesh_entry_record(kind,0);});}
    rejected([]{return pp_sim_sphere_triangle_mesh_entry_last_mesh(0,0);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_candidate(0,0);});input(query());rejected([]{return pp_sim_sphere_triangle_mesh_entry(24);});rejected([]{return pp_sim_sphere_triangle_mesh_entry_append(10);});
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(0,0);});rejected([]{return pp_sim_sphere_triangle_mesh_source(0);});rejected([]{return pp_sim_sphere_triangle_candidate(0);});need(run({triangle(5)})[0]==1,"Global reset recovery failed");
});
std::cout<<groups<<" sphere triangle mesh entry C ABI groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
