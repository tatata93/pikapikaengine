#include "pikapika/simulation_api.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Triangle=std::array<double,10>;
using Query=std::array<double,14>;
unsigned groups{};
void need(bool b,const char* text){if(!b)throw std::runtime_error(text);}
void ok(int32_t code){if(code!=PP_SIM_OK)throw std::runtime_error(pp_sim_error_ptr());}
std::vector<double> output(){const auto* p=pp_sim_output_f64_ptr();return {p,p+pp_sim_output_count()};}
bool same(const std::vector<double>& a,const std::vector<double>& b){if(a.size()!=b.size())return false;for(std::size_t i=0;i<a.size();++i)if(std::bit_cast<uint64_t>(a[i])!=std::bit_cast<uint64_t>(b[i]))return false;return true;}
template<class F>void rejected(F f){const auto before=output();need(f()==PP_SIM_INVALID_ARGUMENT,"Expected exchange/getter rejection");need(same(before,output()),"Rejected operation changed prior output bits/count");}
template<class F>void test(const char* name,F f){ok(pp_sim_reset());f();++groups;std::cout<<"PASS "<<name<<'\n';}
Triangle triangle(double id,double y=0){return {id,-0.,y,-0.,4,y,0,0,y,4};}
Query query(){return {1,1,1,.5,64,7,128,1024,1e-7,1e-8,1e-12,0,0,0};}
void input(const Query& q){std::copy(q.begin(),q.end(),pp_sim_input_f64_ptr());}
void append(const std::vector<Triangle>& t,std::size_t first,std::size_t count){for(std::size_t i=0;i<count;++i)std::copy(t[first+i].begin(),t[first+i].end(),pp_sim_input_f64_ptr()+10*i);ok(pp_sim_sphere_triangle_mesh_append(uint32_t(10*count)));}
void stage(const std::vector<Triangle>& t){ok(pp_sim_sphere_triangle_mesh_begin(uint32_t(t.size())));for(std::size_t i=0;i<t.size();i+=6)append(t,i,std::min<std::size_t>(6,t.size()-i));}
std::vector<double> run(const std::vector<Triangle>& t,Query q=query()){stage(t);input(q);ok(pp_sim_sphere_triangle_mesh(14));return output();}
void single(){const auto q=query();auto* p=pp_sim_input_f64_ptr();std::fill_n(p,24,0.);std::copy_n(q.begin(),4,p);const auto t=triangle(999);std::copy(t.begin(),t.end(),p+4);std::copy_n(q.begin()+5,6,p+14);ok(pp_sim_sphere_triangle(24));}
}
int main(){try{
test("existing ABI1 and F64/U32 capacities remain unchanged",[]{need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64&&pp_sim_input_f64_capacity()==49152&&pp_sim_input_u32_capacity()==98304,"Existing exchange contract changed");});
test("unbegun staging and missing snapshots reject atomically",[]{input(query());rejected([]{return pp_sim_sphere_triangle_mesh_append(10);});rejected([]{return pp_sim_sphere_triangle_mesh(14);});rejected([]{return pp_sim_sphere_triangle_mesh_source(0);});rejected([]{return pp_sim_sphere_triangle_mesh_row(0);});rejected([]{return pp_sim_sphere_triangle_mesh_candidate(0,0);});});
test("every complete chunk length one through six preserves signed-zero source and full rows",[]{
    for(unsigned count=1;count<=6;++count){std::vector<Triangle> t;for(unsigned j=0;j<count;++j)t.push_back(triangle(j+1));const auto h=run(t);need(h.size()==24&&h[0]==0&&h[3]==count&&h[4]==count&&h[9]==count&&h[14]==count,"Chunk sources lost");
        for(unsigned j=0;j<count;++j){ok(pp_sim_sphere_triangle_mesh_source(j));auto s=output();need(s.size()==14&&s[0]==j&&s[1]==j+1&&s[11]==1&&s[12]==1&&s[13]==1&&std::signbit(s[2])&&std::signbit(s[4]),"Source flags or signed-zero bits");ok(pp_sim_sphere_triangle_mesh_row(j));need(output().size()==58&&output()[3]==j+1,"Row/source stable-ID mismatch");}
    }
});
test("actual 64-source staging retains last source last candidate and all possible IDs",[]{std::vector<Triangle> t;for(unsigned j=0;j<64;++j)t.push_back(triangle(64-j));const auto h=run(t);need(h[0]==0&&h[3]==64&&h[4]==64&&h[9]==64&&h[10]==448&&h[14]==64,"Capacity truncated");ok(pp_sim_sphere_triangle_mesh_source(63));need(output()[1]==1&&output()[13]==1,"Last source missing");ok(pp_sim_sphere_triangle_mesh_candidate(63,6));need(output().size()==13&&output()[0]==6,"Last actual candidate missing");rejected([]{return pp_sim_sphere_triangle_mesh_source(64);});rejected([]{return pp_sim_sphere_triangle_mesh_row(64);});rejected([]{return pp_sim_sphere_triangle_mesh_candidate(63,7);});});
test("valid begin and append leave old output and snapshot independently owned",[]{run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_source(0));const auto source=output();ok(pp_sim_sphere_triangle_mesh_begin(2));need(same(source,output()),"Begin changed output");append({triangle(51)},0,1);need(same(source,output()),"Append changed output");ok(pp_sim_sphere_triangle_mesh_source(0));need(same(source,output()),"Staging overwrote old source snapshot");append({triangle(52)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh(14));ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[1]==51,"New query did not consume new owned staging");});
test("invalid begin counts retain complete staging snapshot and old output",[]{run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_source(0));const auto source=output();for(auto n:{65u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_begin(n);});input(query());ok(pp_sim_sphere_triangle_mesh(14));ok(pp_sim_sphere_triangle_mesh_source(0));need(same(source,output()),"Bad begin destroyed reusable old stage");});
test("bad final ID and nonfinite member never partially append a chunk",[]{
    const std::array<double,6> bad{0,9007199254740992.,1.5,-1,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()};
    for(double id:bad){run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_source(0));const auto snapshot=output();ok(pp_sim_sphere_triangle_mesh_begin(3));append({triangle(1)},0,1);const auto a=triangle(2),b=triangle(id);std::copy(a.begin(),a.end(),pp_sim_input_f64_ptr());std::copy(b.begin(),b.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_append(20);});ok(pp_sim_sphere_triangle_mesh_source(0));need(same(snapshot,output()),"Rejected append changed old model snapshot");append({triangle(2),triangle(3)},0,2);input(query());ok(pp_sim_sphere_triangle_mesh(14));need(output()[3]==3&&output()[0]==0,"Failed chunk retained partial additions");}
});
test("wrong append counts incomplete queries and declared overrun recover without silent sources",[]{
    ok(pp_sim_sphere_triangle_mesh_begin(2));for(auto count:{0u,1u,9u,11u,59u,61u,70u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_append(count);});input(query());rejected([]{return pp_sim_sphere_triangle_mesh(14);});append({triangle(1)},0,1);const auto t=triangle(2);std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr()+10);rejected([]{return pp_sim_sphere_triangle_mesh_append(20);});append({triangle(2)},0,1);input(query());ok(pp_sim_sphere_triangle_mesh(14));need(output()[3]==2&&output()[0]==0,"Stage retry after count errors");std::copy(t.begin(),t.end(),pp_sim_input_f64_ptr());rejected([]{return pp_sim_sphere_triangle_mesh_append(10);});
});
test("query length reserved finite and uint32 exchange errors retain old snapshot and reusable stage",[]{
    run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_source(0));const auto before=output();
    for(auto count:{0u,13u,15u,std::numeric_limits<uint32_t>::max()}){input(query());rejected([&]{return pp_sim_sphere_triangle_mesh(count);});}
    for(unsigned field:{0u,3u,8u}){auto q=query();q[field]=std::numeric_limits<double>::infinity();input(q);rejected([]{return pp_sim_sphere_triangle_mesh(14);});}
    for(unsigned field:{4u,5u,6u,7u})for(double bad:{-1.,.5,4294967296.}){auto q=query();q[field]=bad;input(q);rejected([]{return pp_sim_sphere_triangle_mesh(14);});}
    for(unsigned field=11;field<14;++field){auto q=query();q[field]=1;input(q);rejected([]{return pp_sim_sphere_triangle_mesh(14);});}
    ok(pp_sim_sphere_triangle_mesh_source(0));need(same(before,output()),"Host query failure changed source");input(query());ok(pp_sim_sphere_triangle_mesh(14));need(output()[0]==0,"Host query retry failed");
});
test("all uint32 settings including zero and max reach actual core model failure",[]{
    for(unsigned field:{4u,5u,6u,7u})for(double bad:{0.,4294967295.}){auto q=query();q[field]=bad;auto h=run({triangle(37)},q);need(h[0]==1&&h[1]==1&&h[2]==0&&h[3]==1&&h[4]==0,"Model-invalid setting became host rejection");for(unsigned i=14;i<24;++i)need(h[i]==0&&!std::signbit(h[i]),"Absent aggregate/padding not positive zero");ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[11]==0&&output()[12]==0,"Structural failure manufactured queried row");}
});
test("empty duplicate and finite out-of-domain source update model but preserve source diagnostics",[]{
    auto h=run({});need(h[0]==1&&h[1]==2&&h[3]==0&&h[4]==0,"Empty stage did not reach model");rejected([]{return pp_sim_sphere_triangle_mesh_source(0);});
    h=run({triangle(37),triangle(37,-4)});need(h[0]==1&&h[1]==5&&h[5]==1&&h[6]==1&&h[4]==0&&h[9]==0,"Duplicate preflight model diagnostics");ok(pp_sim_sphere_triangle_mesh_source(1));need(output()[1]==37&&output()[11]==0&&output()[12]==0&&output()[13]==0,"Rejected model lost original source");rejected([]{return pp_sim_sphere_triangle_mesh_row(0);});
    auto t=triangle(55);t[1]=1e151;h=run({t});need(h[0]==1&&h[1]==6&&h[5]==1&&h[6]==0,"Finite source domain classified at host");ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[2]==1e151,"Original domain-invalid source not preserved");
});
test("surface budget and failed primitive row retain complete row diagnostics without partial nearest",[]{
    auto q=query();q[4]=1;auto h=run({triangle(1),triangle(2)},q);need(h[0]==2&&h[1]==3&&h[4]==0,"Surface caller budget not model failure");
    Triangle degenerate{99,0,0,0,4,0,0,8,0,0};h=run({triangle(37),degenerate,triangle(5,-4)});need(h[0]==3&&h[1]==7&&h[2]==0&&h[4]==3&&h[7]==1&&h[8]==1&&h[9]==3&&h[13]==1&&h[14]==0,"Row failure truncated diagnostics");ok(pp_sim_sphere_triangle_mesh_row(1));need(output()[0]==2&&output()[2]==0,"Degenerate row misrepresented");ok(pp_sim_sphere_triangle_mesh_row(2));need(output()[0]==0&&output()[3]==5,"Later row unexamined");
    q=query();q[5]=3;h=run({triangle(37),triangle(5,-4)},q);need(h[0]==3&&h[9]==2&&h[10]==6&&h[13]==2,"Candidate budget work lost");ok(pp_sim_sphere_triangle_mesh_candidate(1,2));rejected([]{return pp_sim_sphere_triangle_mesh_candidate(1,3);});
});
test("single snapshot and unused KKT negative zero remain independent of mesh getters",[]{
    single();ok(pp_sim_sphere_triangle_candidate(0));const auto old=output();need(std::signbit(old[9])&&!std::signbit(old[10]),"Single unused KKT bits changed");run({triangle(37),triangle(5,-4)});ok(pp_sim_sphere_triangle_mesh_candidate(0,0));need(same(old,output()),"Mesh candidate differs from same single source KKT layout");ok(pp_sim_sphere_triangle_candidate(0));need(same(old,output()),"Mesh call changed single snapshot");single();ok(pp_sim_sphere_triangle_mesh_row(0));need(output()[3]==37,"Single query changed mesh snapshot");
});
test("old copied packets caller scratch and World clock stay independent",[]{
    const auto world=pp_sim_world_create();need(world!=0,"World create");ok(pp_sim_world_info(world));const auto info=output();const auto h=run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_source(0));const auto s=output();std::fill_n(pp_sim_input_f64_ptr(),64,123.);need(h[0]==0&&s[1]==37&&std::signbit(s[2]),"Owned packet changed");ok(pp_sim_sphere_triangle_mesh_source(0));need(same(s,output()),"Source aliases caller scratch");ok(pp_sim_world_info(world));need(same(info,output()),"Read-only mesh changed World/time");ok(pp_sim_world_destroy(world));
});
test("mesh staging queries and failures preserve derived skin and motion snapshots",[]{
    auto* p=pp_sim_input_f64_ptr();std::fill_n(p,25,0.);p[0]=1;p[1]=128;p[2]=65536;p[3]=262144;p[4]=1e12;p[5]=1e-10;p[8]=7;for(unsigned j=0;j<4;++j)p[9+5*j]=1;ok(pp_sim_skin_bind(25));ok(pp_sim_skin_bind_record(0,0));const auto skin=output();
    std::fill_n(p,22,0.);p[0]=1;p[3]=2;p[6]=128;p[7]=128;p[8]=4096;p[10]=7;p[18]=p[19]=p[20]=p[21]=1;ok(pp_sim_motion(22));ok(pp_sim_motion_bone(0));const auto motion=output();
    const double derived[17]={3,1,2048,32768,128,0,0,0,0,0,0,1,0,0,0,1,0};std::copy_n(derived,17,p);auto* u=pp_sim_input_u32_ptr();u[0]=0;u[1]=1;u[2]=2;ok(pp_sim_derived_mesh(17,3));ok(pp_sim_derived_mesh_record(0,1));const auto buffer=output();
    run({triangle(37),triangle(5,-4)});run({triangle(37),triangle(37)});ok(pp_sim_sphere_triangle_mesh_begin(2));rejected([]{return pp_sim_sphere_triangle_mesh_begin(65);});
    ok(pp_sim_skin_bind_record(0,0));need(same(skin,output()),"Mesh changed skin snapshot");ok(pp_sim_motion_bone(0));need(same(motion,output()),"Mesh changed motion snapshot");ok(pp_sim_derived_mesh_record(0,1));need(same(buffer,output()),"Mesh changed derived snapshot");
});
test("unsupported Native rounding is a real empty-row model result and valid retry recovers",[]{
    stage({triangle(37)});input(query());const auto mode=std::fegetround();need(std::fesetround(FE_UPWARD)==0,"Set Native rounding");const auto code=pp_sim_sphere_triangle_mesh(14);const auto h=output();const auto after=std::fegetround();std::fesetround(mode);ok(code);need(h[0]==5&&h[1]==11&&h[2]==0&&h[3]==1&&h[4]==0&&after==FE_UPWARD,"Environment rejection escaped model contract or mutated mode");input(query());ok(pp_sim_sphere_triangle_mesh(14));need(output()[0]==0,"Native rounding recovery");
});
test("getter ordinals and unsigned tails reject retaining preceding output and snapshot",[]{
    run({triangle(37)});ok(pp_sim_sphere_triangle_mesh_candidate(0,6));for(auto index:{1u,64u,std::numeric_limits<uint32_t>::max()}){rejected([&]{return pp_sim_sphere_triangle_mesh_source(index);});rejected([&]{return pp_sim_sphere_triangle_mesh_row(index);});rejected([&]{return pp_sim_sphere_triangle_mesh_candidate(index,0);});}for(auto index:{7u,std::numeric_limits<uint32_t>::max()})rejected([&]{return pp_sim_sphere_triangle_mesh_candidate(0,index);});ok(pp_sim_sphere_triangle_mesh_source(0));need(output()[1]==37,"Getter rejection changed model snapshot");
});
test("global reset clears staging mesh and single snapshots and allows new retry",[]{
    run({triangle(37)});single();ok(pp_sim_reset());need(pp_sim_output_count()==0,"Reset retained output");rejected([]{return pp_sim_sphere_triangle_mesh_source(0);});rejected([]{return pp_sim_sphere_triangle_mesh_row(0);});rejected([]{return pp_sim_sphere_triangle_mesh_candidate(0,0);});rejected([]{return pp_sim_sphere_triangle_candidate(0);});input(query());rejected([]{return pp_sim_sphere_triangle_mesh(14);});rejected([]{return pp_sim_sphere_triangle_mesh_append(10);});need(run({triangle(5)})[0]==0,"Reset recovery");
});
std::cout<<groups<<" sphere triangle mesh C ABI test groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
