#include "pikapika/simulation_api.h"
#include "pikapika/sphere_triangle_mesh_trajectory.hpp"
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
namespace guard=pikapika::sphere_triangle_mesh_trajectory;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using Packet=std::vector<double>;
using Triangle=std::array<double,10>;
using Query=std::array<double,24>;
unsigned groups{};
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void ok(int32_t status){if(status!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
Packet output(){const auto n=pp_sim_output_count();need(n<=64,"Output capacity");const auto* p=pp_sim_output_f64_ptr();return {p,p+n};}
bool same(const Packet& a,const Packet& b){if(a.size()!=b.size())return false;for(std::size_t i=0;i<a.size();++i)if(std::bit_cast<uint64_t>(a[i])!=std::bit_cast<uint64_t>(b[i]))return false;return true;}
void equal(const Packet& a,const Packet& b,const char* message){need(same(a,b),message);}
template<class F>void rejected(F f){const auto before=output();need(f()==PP_SIM_INVALID_ARGUMENT,"Expected host/getter rejection");equal(before,output(),"Rejected operation changed old output bits/count");}
template<class F>void test(const char* name,F f){ok(pp_sim_reset());f();++groups;std::cout<<"PASS "<<name<<'\n';}
Triangle triangle(double id,double y=0){return {id,-0.,y,-0.,4,y,0,0,y,4};}
Triangle big_triangle(double id){return {id,-0.,0,-0.,1024,0,0,0,0,1024};}
Query query(){return {1,1,1,1,1,1,.25,64,7,128,1024,1e-7,1e-8,1e-12,256,128,16,128,1000000,0,0,0,0,0};}
void input(const Query& q){std::copy(q.begin(),q.end(),pp_sim_input_f64_ptr());}
void append(const std::vector<Triangle>& triangles,std::size_t first,std::size_t count){
    for(std::size_t j=0;j<count;++j)std::copy(triangles[first+j].begin(),triangles[first+j].end(),pp_sim_input_f64_ptr()+10*j);
    ok(pp_sim_sphere_triangle_mesh_trajectory_append(uint32_t(10*count)));
}
void stage(const std::vector<Triangle>& triangles){ok(pp_sim_sphere_triangle_mesh_trajectory_begin(uint32_t(triangles.size())));for(std::size_t i=0;i<triangles.size();i+=6)append(triangles,i,std::min<std::size_t>(6,triangles.size()-i));}
Packet run(const std::vector<Triangle>& triangles,Query q=query()){stage(triangles);input(q);ok(pp_sim_sphere_triangle_mesh_trajectory(24));return output();}
Packet record(unsigned kind,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_trajectory_record(kind,ordinal));return output();}
Packet last_mesh(unsigned part,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_trajectory_last_mesh(part,ordinal));return output();}
Packet candidate(unsigned row,unsigned ordinal){ok(pp_sim_sphere_triangle_mesh_trajectory_candidate(row,ordinal));return output();}
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
    return guard::audit({q[0],q[1],q[2]},{q[3],q[4],q[5]},q[6],source,s);
}
Packet header(const guard::Result& r,std::size_t count){
    Packet p(32,0.);p[0]=unsigned(r.status);p[1]=unsigned(r.reason);p[2]=double(count);p[3]=bool(r.snapshot);p[4]=bool(r.failed_index);if(r.failed_index)p[5]=double(*r.failed_index);
    p[6]=double(r.certified_leaves.size());p[7]=double(r.frontier.size());p[8]=double(r.audits.size());p[9]=bool(r.safe_prefix);if(r.safe_prefix){p[10]=(*r.safe_prefix)[0];p[11]=(*r.safe_prefix)[1];}
    p[12]=bool(r.witness);p[13]=bool(r.current);p[14]=bool(r.last_mesh);p[15]=bool(r.last_mesh_audit_index);if(r.last_mesh_audit_index)p[16]=double(*r.last_mesh_audit_index);
    p[17]=double(r.partition_leaves);p[18]=r.maximum_depth;put_work(p,19,r.work);return p;
}
Packet audit_packet(const guard::CellAudit& a,std::size_t ordinal){
    Packet p(64,0.);p[0]=double(ordinal);put_cell(p,1,a.cell);p[4]=a.midpoint;p[5]=unsigned(a.outcome);
    if(a.path_bounds){p[6]=1;put(p,7,*a.path_bounds);}if(a.point_bounds){p[13]=1;put(p,14,*a.point_bounds);}if(a.anchor){p[20]=1;put(p,21,*a.anchor);}
    p[24]=a.mesh_queried;if(a.mesh_status){p[25]=1;p[26]=unsigned(*a.mesh_status);}if(a.mesh_reason){p[27]=1;p[28]=unsigned(*a.mesh_reason);}
    const std::array<const std::optional<pikapika::interval::Interval>*,7> fields{&a.distance,&a.displacement_squared_bound,&a.error_squared_bound,&a.displacement_root,&a.error_root,&a.clearance_certificate,&a.penetration_certificate};
    for(unsigned j=0;j<fields.size();++j)if(*fields[j]){p[29+3*j]=1;put(p,30+3*j,**fields[j]);}put_work(p,50,a.work);return p;
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
void verify_packets(const std::vector<Triangle>& triangles,const Query& q,const Packet& actual,const guard::Result& r){
    equal(actual,header(r,triangles.size()),"Full header32 differs from pure result");zeros(actual,30,32);
    equal(record(0,0),Packet(q.begin(),q.end()),"Echo24 lost original input bits");
    for(unsigned j=0;j<triangles.size();++j){
        Packet expected(14,0.);expected[0]=j;std::copy(triangles[j].begin(),triangles[j].end(),expected.begin()+1);
        if(r.last_mesh&&j<r.last_mesh->rows.size()){expected[11]=1;expected[12]=bool(r.last_mesh->rows[j].query);if(r.last_mesh->nearest)expected[13]=std::find(r.last_mesh->nearest->possible_surface_ids.begin(),r.last_mesh->nearest->possible_surface_ids.end(),uint64_t(triangles[j][0]))!=r.last_mesh->nearest->possible_surface_ids.end();}
        equal(record(1,j),expected,"Source14 original bits/lastMesh flags");
    }
    for(unsigned j=0;j<r.audits.size();++j){const auto p=record(2,j);equal(p,audit_packet(r.audits[j],j),"Audit64 optional/work/ordinal layout");zeros(p,61,64);}
    for(unsigned j=0;j<r.certified_leaves.size();++j){const auto& leaf=r.certified_leaves[j];Packet p(6,0.);put_cell(p,0,leaf.cell);put(p,3,leaf.lower_gap_certificate);p[5]=double(leaf.audit_index);equal(record(3,j),p,"Leaf6 full certificate/auditIndex");}
    for(unsigned j=0;j<r.frontier.size();++j){Packet p(4,0.);p[0]=j;put_cell(p,1,r.frontier[j]);equal(record(4,j),p,"Frontier4 all unexamined cells");}
    if(r.current){Packet p(4,0.);put_cell(p,1,*r.current);equal(record(5,0),p,"Current4 distinct from old mesh query");}
    if(r.witness){const auto& w=*r.witness;Packet p(18,0.);put_cell(p,1,w.cell);p[4]=w.parameter;put(p,5,w.exact_path_bounds);put(p,11,w.anchor);p[14]=w.error_upper;put(p,15,w.upper_gap_certificate);p[17]=double(w.audit_index);equal(record(6,0),p,"Witness18 E/strict expression/path bounds");}
    if(r.last_mesh){
        equal(last_mesh(0,0),mesh_header(*r.last_mesh,triangles.size()),"Last mesh summary24");
        for(unsigned j=0;j<r.last_mesh->rows.size();++j)if(r.last_mesh->rows[j].query){const auto& row=r.last_mesh->rows[j];equal(last_mesh(1,j),row_packet(*row.query,row.triangle.id),"Last mesh row58 geometry/failure");for(unsigned k=0;k<row.query->candidates.size();++k)equal(candidate(j,k),candidate_packet(row.query->candidates[k]),"Last mesh candidate13 full KKT bits");}
    }
}
void verify_case(const std::vector<Triangle>& triangles,Query q=query()){const auto actual=run(triangles,q);const auto reference=pure(triangles,q);verify_packets(triangles,q,actual,reference);}
void single_snapshot(){auto* p=pp_sim_input_f64_ptr();const auto q=query();std::fill_n(p,24,0.);std::copy_n(q.begin(),3,p);p[3]=q[6];const auto t=triangle(999);std::copy(t.begin(),t.end(),p+4);std::copy_n(q.begin()+8,6,p+14);ok(pp_sim_sphere_triangle(24));}
void mesh_snapshot(){auto* p=pp_sim_input_f64_ptr();ok(pp_sim_sphere_triangle_mesh_begin(1));const auto t=triangle(511);std::copy(t.begin(),t.end(),p);ok(pp_sim_sphere_triangle_mesh_append(10));const auto q=query();std::array<double,14> m{};std::copy_n(q.begin(),3,m.begin());m[3]=q[6];m[4]=q[7];std::copy_n(q.begin()+8,6,m.begin()+5);std::copy(m.begin(),m.end(),p);ok(pp_sim_sphere_triangle_mesh(14));}
}

int main(){try{
test("ABI1 and all exchange capacities remain unchanged",[]{need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64&&pp_sim_input_f64_capacity()==49152&&pp_sim_input_u32_capacity()==98304,"Existing ABI capacities");});
test("unbegun trajectory stages and absent getters reject preserving output",[]{
    input(query());rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(10);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});
    for(unsigned kind=0;kind<7;++kind)rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_record(kind,0);});
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(0,0);});
});
test("all complete append chunks one through six preserve original signed zeros and packet layout",[]{
    for(unsigned n=1;n<=6;++n){std::vector<Triangle> source;for(unsigned j=0;j<n;++j)source.push_back(triangle(20+j));verify_case(source);const auto s=record(1,n-1);need(std::signbit(s[2])&&std::signbit(s[4]),"Source -0 lost");}
});
test("actual64 sources all lastMesh rows and final candidate remain owned",[]{
    std::vector<Triangle> source;for(unsigned j=0;j<64;++j)source.push_back(triangle(64-j));const auto h=run(source);need(h[0]==0&&h[2]==64&&h[8]==1&&h[14]==1,"64-source guard failed");verify_packets(source,query(),h,pure(source,query()));
    const auto s=record(1,63);need(s[1]==1&&s[11]==1&&s[12]==1&&s[13]==1,"Last source/query/possible flag missing");need(candidate(63,6)[0]==6,"Last row's last KKT candidate missing");
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(1,64);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(1,64);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(63,7);});
});
test("actual255 audits128 certified leaves and last record are not truncated",[]{
    auto q=query();q[3]=129;const std::vector<Triangle> source{big_triangle(37)};const auto h=run(source,q);
    need(h[0]==0&&h[6]==128&&h[8]==255&&h[17]==128&&h[19]==255&&h[10]==0&&h[11]==1,"Actual 128-leaf capacity not exercised");verify_packets(source,q,h,pure(source,q));
    const auto leaf=record(3,127);need(leaf[1]==1&&leaf[5]==254,"Final leaf missing");need(record(2,254)[0]==254,"Final audit missing");
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(2,255);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(3,128);});
});
test("127-leaf failure retains actual positive prefix and all frontier current work",[]{
    auto q=query();q[3]=129;q[15]=127;const std::vector<Triangle> source{big_triangle(37)};const auto h=run(source,q);
    need(h[0]==2&&h[1]==9&&h[9]==1&&h[11]>0&&h[11]<1&&h[13]==1&&h[17]==127,"Leaf-budget partial prefix hidden or globally certified");verify_packets(source,q,h,pure(source,q));
});
test("valid begin append and caller scratch never mutate old committed echo source and audits",[]{
    run({triangle(37)});const auto echo=record(0,0),source=record(1,0),audit=record(2,0);ok(pp_sim_sphere_triangle_mesh_trajectory_begin(2));equal(output(),audit,"Begin changed old output");append({triangle(51)},0,1);equal(output(),audit,"Append changed old output");
    std::fill_n(pp_sim_input_f64_ptr(),64,123.);equal(record(0,0),echo,"Echo aliases staging/caller scratch");equal(record(1,0),source,"Source aliases staging");equal(record(2,0),audit,"Audit aliases staging");append({triangle(52)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(record(1,0)[1]==51&&source[1]==37&&echo.size()==24,"New commit or copied old source lost");
});
test("invalid begin counts preserve a complete reusable stage and prior snapshot",[]{
    run({triangle(37)});const auto old=record(1,0);for(auto n:{65u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_begin(n);});input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));equal(record(1,0),old,"Rejected begin destroyed old stage/source");
});
test("a bad last source in append never commits the preceding valid member",[]{
    for(double bad:{0.,9007199254740992.,1.5,-1.,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){
        run({triangle(37)});const auto old=record(1,0);ok(pp_sim_sphere_triangle_mesh_trajectory_begin(3));append({triangle(1)},0,1);
        const auto a=triangle(2),b=triangle(bad);std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());std::copy(b.begin(),b.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(20);});equal(record(1,0),old,"Rejected append changed old source record");
        append({triangle(2),triangle(3)},0,2);input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(output()[2]==3&&output()[0]==0,"Invalid chunk partially committed");
    }
});
test("nonfinite appended coordinate rejects whole chunk and same stage recovers",[]{
    for(double bad:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){
        run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_trajectory_begin(2));auto a=triangle(1),b=triangle(2);b[9]=bad;std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());std::copy(b.begin(),b.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(20);});append({triangle(1),triangle(2)},0,2);input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(output()[0]==0,"Coordinate rejection poisoned staging");
    }
});
test("wrong append lengths incomplete stages and declared overruns are atomic",[]{
    ok(pp_sim_sphere_triangle_mesh_trajectory_begin(2));for(auto n:{0u,1u,9u,11u,59u,61u,70u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_append(n);});input(query());rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});append({triangle(1)},0,1);input(query());rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});
    const auto t=triangle(2);std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(20);});append({triangle(2)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(output()[2]==2,"Incomplete/overrun retry");rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(10);});
});
test("query24 length finite and uint32 exchange failures retain echo record output and stage",[]{
    run({triangle(37)});const auto old=record(0,0);
    for(auto n:{0u,19u,23u,25u,std::numeric_limits<uint32_t>::max()}){input(query());rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory(n);});}
    for(unsigned field=0;field<19;++field){auto q=query();q[field]=std::numeric_limits<double>::infinity();input(q);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});}
    for(unsigned field:{7u,8u,9u,10u,14u,15u,16u,17u,18u})for(double value:{-1.,.5,4294967296.}){auto q=query();q[field]=value;input(q);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});}
    equal(record(0,0),old,"Exchange failure changed old echo");input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(output()[0]==0,"Stage not reusable after exchange failure");
});
test("all five reserved fields require positive zero not negative zero",[]{
    run({triangle(37)});const auto old=record(0,0);for(unsigned at=19;at<24;++at)for(double value:{1.,-0.}){auto q=query();q[at]=value;input(q);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});}
    equal(record(0,0),old,"Reserved rejection changed echo");
});
test("uint32 model-invalid settings reach Native and maxDepth zero remains valid",[]{
    for(unsigned at:{7u,8u,9u,10u,14u,15u,17u,18u})for(double value:{0.,4294967295.}){auto q=query();q[at]=value;const auto h=run({triangle(37)},q);need(h[0]==3&&h[1]==1&&h[3]==0&&h[8]==0,"Model-invalid setting became host failure/success");equal(record(0,0),Packet(q.begin(),q.end()),"Invalid model input echo not preserved");}
    auto q=query();q[16]=0;need(run({triangle(37)},q)[0]==0,"Depth zero is a valid evaluated root domain");q[16]=33;need(run({triangle(37)},q)[0]==3,"Depth33 did not reach invalid model");
});
test("accepted empty duplicate domain and surface-budget failures replace old proof and preserve original source",[]{
    run({triangle(37)});auto h=run({});need(h[0]==3&&h[1]==2&&h[2]==0&&h[3]==0&&h[9]==0,"Empty did not commit invalid model");rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(1,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(3,0);});
    h=run({triangle(37),triangle(37)});need(h[0]==3&&h[1]==4&&h[4]==1&&h[5]==1&&h[3]==0,"Duplicate ID failure index");const auto s=record(1,1);need(s[1]==37&&s[11]==0&&s[12]==0&&s[13]==0,"Preflight original source/absent lastMesh flags");
    auto t=triangle(7);t[1]=1e13;verify_case({t});h=run({t});need(h[0]==3&&h[1]==5&&h[4]==1&&h[5]==0,"Finite coordinate domain failure");need(record(1,0)[2]==1e13,"Rejected model lost original coordinate");
    auto q=query();q[7]=1;h=run({triangle(1),triangle(2)},q);need(h[0]==2&&h[1]==6&&h[3]==1&&h[7]==1&&h[8]==0&&h[14]==0,"Surface budget must keep owned snapshot and unqueried whole frontier");verify_packets({triangle(1),triangle(2)},q,h,pure({triangle(1),triangle(2)},q));
});
test("row failure preserves far degenerate and later row without partial trajectory success",[]{
    Triangle bad{99,1000,0,0,1004,0,0,1008,0,0};const std::vector<Triangle> source{triangle(37),bad,triangle(5,-4)};const auto h=run(source);need(h[0]==2&&h[1]==7&&h[14]==1&&h[6]==0&&h[9]==0,"Failed mesh was hidden by trajectory");verify_packets(source,query(),h,pure(source,query()));need(last_mesh(1,1)[0]==2&&last_mesh(1,2)[0]==0,"Far failed row or later query lost");
});
test("candidate budget failure retains actual KKT diagnostic prefix and rejects its tail",[]{
    auto q=query();q[8]=3;const std::vector<Triangle> source{triangle(37),triangle(5,-4)};const auto h=run(source,q);need(h[0]==2&&h[1]==7,"Primitive candidate budget hidden");verify_packets(source,q,h,pure(source,q));need(candidate(1,2)[0]==2,"Actual failed-row prefix lost");rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(1,3);});
});
test("strict penetration witness includes actual path bounds error and audit link",[]{
    auto q=query();q[1]=2;q[4]=-4;q[6]=1.5;const std::vector<Triangle> source{triangle(37)};const auto h=run(source,q);need(h[0]==1&&h[12]==1&&h[13]==1&&h[6]==0,"Interior penetration witness missing");verify_packets(source,q,h,pure(source,q));const auto w=record(6,0);need(w.size()==18&&w[16]<0&&w[17]==0,"Witness strict upper/auditIndex layout");
});
test("inside rounded anchor does not become a false strict midpoint witness",[]{
    constexpr double base=0x1p39,h=0x1p-13;auto q=query();q[0]=base;q[1]=q[2]=q[4]=q[5]=0;q[3]=base+h;q[6]=1-3*0x1p-15;q[16]=0;
    const std::vector<Triangle> source{{37,base+1,-4,-4,base+1,4,-4,base+1,0,4}};const auto result=run(source,q);need(result[0]==2&&result[12]==0,"Anchor pointification manufactured witness");verify_packets(source,q,result,pure(source,q));const auto a=record(2,0);need(a[41]==1&&a[43]>0&&a[47]==1&&a[49]>0,"E bound/positive upper expression missing");
});
test("evaluation leaf depth and each sqrt reservation retain current frontier and exact work",[]{
    auto q=query();q[0]=.5;q[2]=.5;q[3]=2.5;q[5]=.5;q[6]=.5;const std::vector<Triangle> source{triangle(37)};
    for(unsigned at:{14u,15u,16u}){auto p=q;p[at]=at==16?0:1;const auto h=run(source,p);need(h[0]==2&&h[13]==1&&h[3]==1,"Subdivision/evaluation budget became success");verify_packets(source,p,h,pure(source,p));}
    q=query();q[18]=511;verify_case(source,q);const auto h=run(source,q);need(h[1]==11&&h[14]==0&&h[19]==0,"Before-mesh reservation executed query");const auto a=record(2,0);need(a[24]==0,"Unqueried audit borrowed mesh result");zeros(a,25,50);rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0);});
    q[18]=512;q[2]=-1;q[5]=-1;q[3]=3;verify_case(source,q);q[0]=.5;q[2]=.5;q[3]=2.5;q[5]=2.5;verify_case(source,q);
});
test("getter kinds ordinals absence and unsigned tails preserve output and committed data",[]{
    run({triangle(37)});const auto old=record(1,0);for(auto kind:{7u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_record(kind,0);});
    for(unsigned kind=0;kind<7;++kind)rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_record(kind,std::numeric_limits<uint32_t>::max());});
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(0,1);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(4,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(5,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(6,0);});
    rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,1);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(2,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(1,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(0,7);});equal(record(1,0),old,"Invalid getters changed snapshot");
});
test("single mesh dedicated staging and independent records cannot overwrite each other",[]{
    single_snapshot();ok(pp_sim_sphere_triangle_candidate(0));const auto single=output();mesh_snapshot();ok(pp_sim_sphere_triangle_mesh_source(0));const auto mesh_source=output();
    run({triangle(37)});const auto trajectory=record(1,0);need(std::signbit(candidate(0,0)[9]),"Trajectory unused KKT -0 lost");ok(pp_sim_sphere_triangle_candidate(0));equal(output(),single,"Trajectory changed single snapshot");ok(pp_sim_sphere_triangle_mesh_source(0));equal(output(),mesh_source,"Trajectory changed mesh snapshot");
    ok(pp_sim_sphere_triangle_mesh_begin(1));const auto m=triangle(711);std::copy(m.begin(),m.end(),pp_sim_input_f64_ptr());ok(pp_sim_sphere_triangle_mesh_append(10));
    ok(pp_sim_sphere_triangle_mesh_trajectory_begin(1));append({triangle(811)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(record(1,0)[1]==811,"Dedicated trajectory staging missing");
    auto* p=pp_sim_input_f64_ptr();const std::array<double,14> q{1,1,1,.25,64,7,128,1024,1e-7,1e-8,1e-12,0,0,0};std::copy(q.begin(),q.end(),p);ok(pp_sim_sphere_triangle_mesh(14));ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[1]==711,"Trajectory overwrote ordinary mesh stage");need(record(1,0)[1]==811&&trajectory[1]==37,"Other stage/old copied source changed trajectory record");
});
test("query failures reset and World operations do not advance or borrow trajectory state",[]{
    const auto world=pp_sim_world_create();need(world!=0,"World create");ok(pp_sim_world_info(world));const auto info=output();run({triangle(37)});const auto echo=record(0,0),source=record(1,0);ok(pp_sim_world_info(world));equal(output(),info,"Guard advanced World/time");ok(pp_sim_world_reset(world));equal(record(1,0),source,"World reset erased unrelated trajectory record");ok(pp_sim_world_destroy(world));equal(record(0,0),echo,"World destruction erased trajectory echo");
    auto q=query();q[6]=-1;run({triangle(37)},q);need(record(0,0)[6]==-1,"Accepted invalid model retained old echo");rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_record(3,0);});need(run({triangle(37)})[0]==0,"Model failure retry");
});
test("unsupported Native rounding returns real environment model and preserves caller mode",[]{
    const auto q=query();stage({triangle(37)});input(q);const auto before=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Set upward rounding");const auto code=pp_sim_sphere_triangle_mesh_trajectory(24);const auto h=output();const auto after=std::fegetround();std::fesetround(before);ok(code);need(h.size()==32&&h[0]==4&&h[1]==15&&h[2]==1&&h[3]==0&&h[8]==0&&after==FE_UPWARD,"Environment priority/result/mode changed");equal(record(0,0),Packet(q.begin(),q.end()),"Environment query lost echo");input(q);ok(pp_sim_sphere_triangle_mesh_trajectory(24));need(output()[0]==0,"Environment retry did not recover");
});
test("global reset clears both staging and record while allowing fresh recovery",[]{
    run({triangle(37)});single_snapshot();mesh_snapshot();ok(pp_sim_reset());need(pp_sim_output_count()==0,"Global reset retained output");
    for(unsigned kind=0;kind<7;++kind)rejected([&]{return pp_sim_sphere_triangle_mesh_trajectory_record(kind,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_candidate(0,0);});
    input(query());rejected([]{return pp_sim_sphere_triangle_mesh_trajectory(24);});rejected([]{return pp_sim_sphere_triangle_mesh_trajectory_append(10);});rejected([]{return pp_sim_sphere_triangle_mesh_source(0);});rejected([]{return pp_sim_sphere_triangle_candidate(0);});need(run({triangle(5)})[0]==0,"Global reset recovery");
});
std::cout<<groups<<" sphere triangle mesh trajectory C ABI groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
