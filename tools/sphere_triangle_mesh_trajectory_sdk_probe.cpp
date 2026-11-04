#include "pikapika/simulation_api.h"
#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

// Only bounded transport is implemented here. Geometric recipes and expected
// statuses come from the frozen pure fixture corpus in the independent runner.
namespace {
void need(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
using Query=std::array<double,24>;
using Triangle=std::array<double,10>;
using Packet=std::vector<double>;
struct Input{std::string name;Query query{};std::vector<Triangle> triangles;};
struct Row{unsigned row_ordinal{};std::optional<Packet> packet;std::vector<Packet> candidates;};
struct Record{
    Input input;int32_t begin_status{},exchange_status{};std::vector<int32_t> append_statuses;
    std::optional<std::string> failed_phase;
    std::optional<Packet> summary,echo,current,witness,last_mesh_summary;
    std::vector<Packet> sources,audits,leaves,frontier;
    std::vector<Row> last_mesh_rows;
    Packet output_before,output_after;std::optional<bool> host_failure_preserved;
};
std::optional<std::string> line(std::istream& in){
    std::string text;char c{};
    while(in.get(c)){
        if(c=='\n'){if(!text.empty()&&text.back()=='\r')text.pop_back();return text;}
        need(text.size()<4096,"Probe line exceeds 4096 bytes");
        need(static_cast<unsigned char>(c)<128,"Probe rows require ASCII tokens");text.push_back(c);
    }
    need(!in.bad(),"Probe read failed");if(text.empty())return std::nullopt;
    if(text.back()=='\r'){
        text.pop_back();
    }
    return text;
}
unsigned integer(const std::string& token,unsigned maximum){
    unsigned value{};const auto parsed=std::from_chars(token.data(),token.data()+token.size(),value);
    need(parsed.ec==std::errc{}&&parsed.ptr==token.data()+token.size()&&value<=maximum,"Invalid bounded unsigned probe token");return value;
}
template<class Values>void values(std::istringstream& in,Values& out){
    for(auto& value:out){std::string token;need(bool(in>>token)&&token.size()<=64,"Missing or oversized probe F64");
        const auto parsed=std::from_chars(token.data(),token.data()+token.size(),value,std::chars_format::general);
        need(parsed.ec==std::errc{}&&parsed.ptr==token.data()+token.size()&&std::isfinite(value),"Probe F64 must be finite roundtrip decimal");}
    std::string extra;need(!(in>>extra),"Trailing probe tokens");
}
std::vector<Input> read(std::istream& in){
    need(line(in)==std::optional<std::string>("pikapika_sphere_triangle_mesh_trajectory_sdk 1"),"Expected trajectory probe header");
    auto raw=line(in);need(raw.has_value(),"Missing cases count");std::istringstream count_fields(*raw);std::string keyword,token,extra;
    need(bool(count_fields>>keyword>>token)&&keyword=="cases"&&!(count_fields>>extra),"Expected cases N");
    const auto count=integer(token,256);need(count>=1,"Probe cases must be 1..256");std::vector<Input> inputs;inputs.reserve(count);std::set<std::string> names;
    for(unsigned i=0;i<count;++i){
        raw=line(in);need(raw.has_value(),"Truncated probe case");std::istringstream f(*raw);f.imbue(std::locale::classic());f>>std::ws;
        need(f.peek()=='"',"Quoted fixture identity required");Input input;need(bool(f>>std::quoted(input.name)),"Malformed fixture identity");
        need(f.peek()==' '||f.peek()=='\t',"Fixture identity delimiter required");
        need(!input.name.empty()&&input.name.size()<=96&&std::all_of(input.name.begin(),input.name.end(),[](unsigned char c){
            return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_';}),"Invalid fixture identity");
        need(names.insert(input.name).second,"Duplicate fixture identity");need(bool(f>>token),"Missing source count");
        const auto n=integer(token,65);values(f,input.query);input.triangles.resize(n);
        for(auto& triangle:input.triangles){raw=line(in);need(raw.has_value(),"Truncated triangle sources");std::istringstream source(*raw);source.imbue(std::locale::classic());values(source,triangle);}
        inputs.push_back(std::move(input));
    }
    need(!line(in).has_value(),"Trailing probe corpus bytes");return inputs;
}
Packet output(){
    const auto count=pp_sim_output_count();need(count<=64,"Invalid Native output capacity");const auto* p=pp_sim_output_f64_ptr();
    Packet result(p,p+count);need(std::all_of(result.begin(),result.end(),[](double x){return std::isfinite(x);}),"Nonfinite Native packet");return result;
}
bool same(const Packet& a,const Packet& b){
    if(a.size()!=b.size()){
        return false;
    }
    for(std::size_t i=0;i<a.size();++i){
        if(std::bit_cast<uint64_t>(a[i])!=std::bit_cast<uint64_t>(b[i])){
            return false;
        }
    }
    return true;
}
void number(double value){need(std::isfinite(value),"Nonfinite probe JSON");if(value==0&&std::signbit(value))std::cout<<"-0";else std::cout<<value;}
template<class Values>void numbers(const Values& values){std::cout<<'[';bool first=true;for(double value:values){if(!first)std::cout<<',';first=false;number(value);}std::cout<<']';}
template<class Values>void bits(const Values& values){
    std::cout<<'[';bool first=true;for(double value:values){if(!first)std::cout<<',';first=false;std::ostringstream s;
        s<<std::hex<<std::nouppercase<<std::setfill('0')<<std::setw(16)<<std::bit_cast<uint64_t>(value);std::cout<<'"'<<s.str()<<'"';}std::cout<<']';
}
template<class Rows,class Writer>void matrix(const Rows& rows,Writer writer){std::cout<<'[';for(std::size_t i=0;i<rows.size();++i){if(i)std::cout<<',';writer(rows[i]);}std::cout<<']';}
void optional_numbers(const std::optional<Packet>& p){if(p)numbers(*p);else std::cout<<"null";}
void optional_bits(const std::optional<Packet>& p){if(p)bits(*p);else std::cout<<"null";}
void packet_field(const char* key,const std::optional<Packet>& value){std::cout<<",\""<<key<<"\":";optional_numbers(value);std::cout<<",\""<<key<<"Bits\":";optional_bits(value);}
void packets_field(const char* key,const char* bit_key,const std::vector<Packet>& value){std::cout<<",\""<<key<<"\":";matrix(value,[](const auto& p){numbers(p);});std::cout<<",\""<<bit_key<<"\":";matrix(value,[](const auto& p){bits(p);});}
void dump(const Record& r){
    std::cout<<"{\"name\":"<<std::quoted(r.input.name)<<",\"input\":";numbers(r.input.query);std::cout<<",\"inputBits\":";bits(r.input.query);
    std::cout<<",\"triangles\":";matrix(r.input.triangles,[](const auto& t){numbers(t);});std::cout<<",\"triangleBits\":";matrix(r.input.triangles,[](const auto& t){bits(t);});
    std::cout<<",\"beginStatus\":"<<r.begin_status<<",\"appendStatuses\":";numbers(r.append_statuses);std::cout<<",\"exchangeStatus\":"<<r.exchange_status<<",\"failedPhase\":";
    if(r.failed_phase)std::cout<<std::quoted(*r.failed_phase);else std::cout<<"null";
    packet_field("summary",r.summary);packet_field("echo",r.echo);
    packets_field("sources","sourceBits",r.sources);packets_field("audits","auditBits",r.audits);packets_field("leaves","leafBits",r.leaves);packets_field("frontier","frontierBits",r.frontier);
    packet_field("current",r.current);packet_field("witness",r.witness);packet_field("lastMeshSummary",r.last_mesh_summary);
    std::cout<<",\"lastMeshRows\":[";for(std::size_t i=0;i<r.last_mesh_rows.size();++i){if(i)std::cout<<',';const auto& row=r.last_mesh_rows[i];
        std::cout<<"{\"rowOrdinal\":"<<row.row_ordinal<<",\"packet\":";optional_numbers(row.packet);std::cout<<",\"bits\":";optional_bits(row.packet);
        std::cout<<",\"candidates\":";matrix(row.candidates,[](const auto& p){numbers(p);});std::cout<<",\"candidateBits\":";matrix(row.candidates,[](const auto& p){bits(p);});std::cout<<'}';}
    std::cout<<"],\"outputBefore\":";numbers(r.output_before);std::cout<<",\"outputBeforeBits\":";bits(r.output_before);
    std::cout<<",\"outputAfter\":";numbers(r.output_after);std::cout<<",\"outputAfterBits\":";bits(r.output_after);std::cout<<",\"hostFailurePreserved\":";
    if(r.host_failure_preserved)std::cout<<(*r.host_failure_preserved?"true":"false");else std::cout<<"null";std::cout<<'}';
}
}

int main(int argc,char** argv){try{
    std::cout.imbue(std::locale::classic());std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);
    std::vector<Input> inputs;
    if(argc==1)inputs=read(std::cin);
    else if(argc==3&&std::string(argv[1])=="--rows"){
        std::ifstream in(argv[2],std::ios::binary);need(bool(in),"Cannot open probe input");inputs=read(in);
    }else throw std::runtime_error("Usage: sphere_triangle_mesh_trajectory_sdk_probe [--rows file]; header pikapika_sphere_triangle_mesh_trajectory_sdk 1; cases N; then quoted-name triangleCount query24 followed by triangleCount ID+ABC9 lines");
    need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64,"Unexpected Native ABI");
    need(pp_sim_reset()==PP_SIM_OK,"Native reset failed");std::vector<Record> records;records.reserve(inputs.size());unsigned accepted{},rejected{};
    for(auto& input:inputs){
        Record r;r.input=std::move(input);r.output_before=output();
        r.begin_status=pp_sim_sphere_triangle_mesh_trajectory_begin(uint32_t(r.input.triangles.size()));r.exchange_status=r.begin_status;
        if(r.begin_status!=PP_SIM_OK)r.failed_phase="begin";
        for(std::size_t first=0;!r.failed_phase&&first<r.input.triangles.size();first+=6){
            const auto count=std::min<std::size_t>(6,r.input.triangles.size()-first);
            for(std::size_t j=0;j<count;++j)std::copy(r.input.triangles[first+j].begin(),r.input.triangles[first+j].end(),pp_sim_input_f64_ptr()+10*j);
            r.exchange_status=pp_sim_sphere_triangle_mesh_trajectory_append(uint32_t(10*count));r.append_statuses.push_back(r.exchange_status);
            if(r.exchange_status!=PP_SIM_OK)r.failed_phase="append";
        }
        if(!r.failed_phase){
            std::copy(r.input.query.begin(),r.input.query.end(),pp_sim_input_f64_ptr());
            r.exchange_status=pp_sim_sphere_triangle_mesh_trajectory(24);if(r.exchange_status!=PP_SIM_OK)r.failed_phase="query";
        }
        if(!r.failed_phase){
            ++accepted;r.summary=output();need(r.summary->size()==32,"Native trajectory header length");const auto& h=*r.summary;
            const auto n=r.input.triangles.size();need(h[2]==double(n),"Native original source count");
            auto count_at=[&](unsigned at,unsigned maximum){need(h[at]>=0&&h[at]<=maximum&&std::floor(h[at])==h[at],"Bounded Native header count");return unsigned(h[at]);};
            for(unsigned at:{3u,4u,9u,12u,13u,14u,15u})need(h[at]==0||h[at]==1,"Native header flag");
            const auto leaf_count=count_at(6,128),frontier_count=count_at(7,33),audit_count=count_at(8,255);
            auto get=[&](unsigned kind,unsigned index,unsigned length){
                need(pp_sim_sphere_triangle_mesh_trajectory_record(kind,index)==PP_SIM_OK,"Native trajectory record getter failed");
                auto p=output();need(p.size()==length,"Native trajectory record length");return p;
            };
            r.echo=get(0,0,24);need(same(*r.echo,Packet(r.input.query.begin(),r.input.query.end())),"Original input echo bits changed");
            for(unsigned j=0;j<n;++j){auto p=get(1,j,14);need(p[0]==j,"Source ordinal");r.sources.push_back(std::move(p));}
            for(unsigned j=0;j<audit_count;++j){auto p=get(2,j,64);need(p[0]==j,"Audit ordinal");r.audits.push_back(std::move(p));}
            for(unsigned j=0;j<leaf_count;++j)r.leaves.push_back(get(3,j,6));
            for(unsigned j=0;j<frontier_count;++j){auto p=get(4,j,4);need(p[0]==j,"Frontier ordinal");r.frontier.push_back(std::move(p));}
            if(h[13]){r.current=get(5,0,4);need((*r.current)[0]==0,"Current ordinal");}
            if(h[12]){r.witness=get(6,0,18);need((*r.witness)[0]==0,"Witness ordinal");}
            if(h[14]){
                need(pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0)==PP_SIM_OK,"Last mesh summary getter failed");
                r.last_mesh_summary=output();need(r.last_mesh_summary->size()==24,"Last mesh summary length");
                for(unsigned j=0;j<n;++j)if(r.sources[j][11]==1){
                    Row row;row.row_ordinal=j;
                    if(r.sources[j][12]==1){
                        need(pp_sim_sphere_triangle_mesh_trajectory_last_mesh(1,j)==PP_SIM_OK,"Last mesh row getter failed");
                        row.packet=output();need(row.packet->size()==58,"Last mesh row length");const auto count=(*row.packet)[6];
                        need(count>=0&&count<=7&&std::floor(count)==count,"Last mesh candidate count");
                        for(unsigned k=0;k<unsigned(count);++k){
                            need(pp_sim_sphere_triangle_mesh_trajectory_candidate(j,k)==PP_SIM_OK,"Last mesh candidate getter failed");
                            auto p=output();need(p.size()==13&&p[0]==k,"Last mesh candidate packet");row.candidates.push_back(std::move(p));
                        }
                    }
                    r.last_mesh_rows.push_back(std::move(row));
                }
            }
        }else{
            ++rejected;r.host_failure_preserved=same(r.output_before,output());need(*r.host_failure_preserved,"Host rejection changed old output bits/count");
        }
        r.output_after=output();records.push_back(std::move(r));
    }
    std::cout<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-trajectory-sdk-packets\",\"fixtureCount\":"<<records.size()
             <<",\"accepted\":"<<accepted<<",\"hostRejected\":"<<rejected<<",\"fixtures\":[";
    for(std::size_t i=0;i<records.size();++i){if(i)std::cout<<',';dump(records[i]);}
    std::cout<<"]}\n";need(pp_sim_reset()==PP_SIM_OK,"Final Native reset failed");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
