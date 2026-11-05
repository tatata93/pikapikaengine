#include "sphere_triangle_mesh_flight_sdk_support.hpp"
#include <charconv>
#include <fstream>
#include <iomanip>
#include <locale>
#include <set>
#include <sstream>
#include <system_error>

// Bounded transport only: input recipes use original fixture FACTORIES; packets
// below are exclusively obtained from the real public C ABI and never filled
// from a pure result after a host rejection.
namespace {
using namespace flight_sdk;
struct Row{unsigned ordinal{};std::optional<Packet> packet;std::vector<Packet> candidates;};
struct Record{
    Input input;int32_t begin_status{},exchange_status{};std::vector<int32_t> append_statuses;
    std::optional<std::string> failed_phase;std::optional<bool> host_failure_preserved;
    Packet before,after;std::optional<Packet> summary,last_mesh_summary;
    std::vector<EncodedRecord> packets;std::vector<Row> last_mesh_rows;
};
std::optional<std::string> line(std::istream& in){std::string value;char c{};while(in.get(c)){if(c=='\n'){if(!value.empty()&&value.back()=='\r'){value.pop_back();}return value;}need(value.size()<4096&&static_cast<unsigned char>(c)<128,"Probe line exceeds bounded ASCII contract");value.push_back(c);}need(!in.bad(),"Probe stream error");if(value.empty()){return std::nullopt;}if(value.back()=='\r'){value.pop_back();}return value;}
unsigned integer(const std::string& token,unsigned maximum){unsigned value{};const auto r=std::from_chars(token.data(),token.data()+token.size(),value);need(r.ec==std::errc{}&&r.ptr==token.data()+token.size()&&value<=maximum,"Invalid probe integer token");return value;}
bool identity(const std::string& value){return !value.empty()&&value.size()<=96&&std::all_of(value.begin(),value.end(),[](unsigned char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_';});}
template<class Values>void values(std::istringstream& stream,Values& destination){for(auto& value:destination){std::string token;need(bool(stream>>token)&&token.size()<=64,"Missing bounded F64 token");const auto r=std::from_chars(token.data(),token.data()+token.size(),value,std::chars_format::general);need(r.ec==std::errc{}&&r.ptr==token.data()+token.size()&&std::isfinite(value),"Probe F64 is not finite roundtrip decimal");}std::string extra;need(!(stream>>extra),"Trailing probe values");}
std::vector<Input> read(std::istream& in){
    need(line(in)==std::optional<std::string>("pikapika_sphere_triangle_mesh_flight_sdk 1"),"Expected flight probe magic");auto raw=line(in);need(raw.has_value(),"Missing case count");std::istringstream count(*raw);std::string keyword,token,extra;need(bool(count>>keyword>>token)&&keyword=="cases"&&!(count>>extra),"Expected cases N");const unsigned n=integer(token,256);need(n>0,"Probe case count must be1..256");
    std::vector<Input> result;result.reserve(n);std::set<std::string> names;
    for(unsigned j=0;j<n;++j){raw=line(in);need(raw.has_value(),"Truncated case row");std::istringstream stream(*raw);stream.imbue(std::locale::classic());Input i;stream>>std::ws;need(stream.peek()=='"'&&bool(stream>>std::quoted(i.cohort)),"Quoted cohort required");stream>>std::ws;need(stream.peek()=='"'&&bool(stream>>std::quoted(i.name)),"Quoted name required");need(identity(i.cohort)&&identity(i.name)&&names.insert(i.cohort+"/"+i.name).second,"Invalid or duplicate fixture identity");need(bool(stream>>token),"Missing mode");i.mode=integer(token,1);need(bool(stream>>token),"Missing triangle count");const auto triangles=integer(token,65);i.query.resize(i.mode==0?32:48);values(stream,i.query);i.triangles.resize(triangles);
        for(auto& triangle:i.triangles){raw=line(in);need(raw.has_value(),"Truncated source row");std::istringstream source(*raw);values(source,triangle);}result.push_back(std::move(i));
    }
    need(!line(in).has_value(),"Trailing probe line");return result;
}
unsigned count(const Packet& p,unsigned at,unsigned maximum){const double v=p.at(at);need(std::isfinite(v)&&v>=0&&!std::signbit(v)&&v<=maximum&&std::floor(v)==v,"Invalid bounded packet metadata");return unsigned(v);}
Record execute(Input i){
    Record r;r.input=std::move(i);r.before=output();const auto mode=r.input.mode;r.begin_status=pp_sim_sphere_triangle_mesh_flight_begin(mode,uint32_t(r.input.triangles.size()));r.exchange_status=r.begin_status;if(r.begin_status!=PP_SIM_OK){r.failed_phase="begin";}
    for(std::size_t first=0;!r.failed_phase&&first<r.input.triangles.size();first+=6){const auto n=std::min<std::size_t>(6,r.input.triangles.size()-first);for(std::size_t j=0;j<n;++j){std::copy(r.input.triangles[first+j].begin(),r.input.triangles[first+j].end(),pp_sim_input_f64_ptr()+10*j);}r.exchange_status=pp_sim_sphere_triangle_mesh_flight_append(mode,uint32_t(10*n));r.append_statuses.push_back(r.exchange_status);if(r.exchange_status!=PP_SIM_OK){r.failed_phase="append";}}
    if(!r.failed_phase){write_input(r.input.query);r.exchange_status=pp_sim_sphere_triangle_mesh_flight_query(mode,uint32_t(r.input.query.size()));if(r.exchange_status!=PP_SIM_OK){r.failed_phase="query";}}
    if(r.failed_phase){r.host_failure_preserved=same(r.before,output());need(*r.host_failure_preserved,"Host refusal changed prior output/count");r.after=output();return r;}
    r.summary=output();need(r.summary->size()==24,"Family summary24 length");const auto& s=*r.summary;need(s[0]==mode&&s[3]==double(r.input.triangles.size()),"Family mode/source metadata");for(unsigned j:{4u,5u,7u,8u,9u,11u,12u,13u,14u,15u}){count(s,j,1);}zeros(s,16,24);
    auto get=[&](unsigned kind,unsigned index,unsigned length){auto packet=record(mode,kind,index);need(packet.size()==length,"Record length mismatch");r.packets.push_back({kind,index,packet});return packet;};
    get(0,0,mode==0?32:48);std::vector<Packet> sources;
    for(unsigned j=0;j<r.input.triangles.size();++j){sources.push_back(get(1,j,14));}
    if(s[4]){get(2,0,mode==0?32:48);}std::optional<Packet> h;
    if(s[15]){h=get(3,0,48);}if(h&&(*h)[3]){get(4,0,32);}if(s[7]){get(5,0,32);}if(s[8]){get(6,0,24);}if(s[12]){get(7,0,40);}if(s[14]){get(8,0,32);}
    if(h){
        for(unsigned j=0;j<3;++j){if(count(*h,7+j,1)){get(9+j,0,8);}}
        for(unsigned j=0;j<count(*h,15,256);++j){get(12,j,64);}for(unsigned j=0;j<count(*h,12,128);++j){get(13,j,6);}for(unsigned j=0;j<count(*h,13,128);++j){get(14,j,8);}for(unsigned j=0;j<count(*h,14,128);++j){get(15,j,4);}
        if(count(*h,22,1)){get(16,0,4);}if(count(*h,10,1)){get(17,0,6);}if(count(*h,19,1)){get(18,0,18);}if(count(*h,20,1)){get(19,0,14);}for(unsigned j=0;j<count(*h,21,64);++j){get(20,j,2);}
        if(count(*h,23,1)){r.last_mesh_summary=last_mesh(mode,0);need(r.last_mesh_summary->size()==24,"Last mesh24 length");for(unsigned j=0;j<sources.size();++j){if(sources[j][11]){Row row;row.ordinal=j;if(sources[j][12]){row.packet=last_mesh(mode,1,j);need(row.packet->size()==58,"Row58 length");for(unsigned k=0;k<count(*row.packet,6,7);++k){auto p=candidate(mode,j,k);need(p.size()==13,"Candidate13 length");row.candidates.push_back(std::move(p));}}r.last_mesh_rows.push_back(std::move(row));}}}
    }
    r.after=output();return r;
}
void number(double v){need(std::isfinite(v),"Nonfinite output");if(v==0&&std::signbit(v)){std::cout<<"-0";}else{std::cout<<v;}}
void packet(const Packet& p){std::cout<<'[';for(std::size_t j=0;j<p.size();++j){if(j){std::cout<<',';}number(p[j]);}std::cout<<']';}
void bits(const Packet& p){std::cout<<'[';for(std::size_t j=0;j<p.size();++j){if(j){std::cout<<',';}std::ostringstream stream;stream<<std::hex<<std::setfill('0')<<std::setw(16)<<std::bit_cast<std::uint64_t>(p[j]);std::cout<<'"'<<stream.str()<<'"';}std::cout<<']';}
void optional_packet(const std::optional<Packet>& p,bool binary=false){if(p){if(binary){bits(*p);}else{packet(*p);}}else{std::cout<<"null";}}
void dump(const Record& r){
    std::cout<<"{\"cohort\":\""<<r.input.cohort<<"\",\"name\":\""<<r.input.name<<"\",\"mode\":"<<r.input.mode<<",\"input\":";packet(r.input.query);std::cout<<",\"inputBits\":";bits(r.input.query);std::cout<<",\"triangles\":[";for(std::size_t j=0;j<r.input.triangles.size();++j){if(j){std::cout<<',';}packet(Packet(r.input.triangles[j].begin(),r.input.triangles[j].end()));}std::cout<<"],\"triangleBits\":[";for(std::size_t j=0;j<r.input.triangles.size();++j){if(j){std::cout<<',';}bits(Packet(r.input.triangles[j].begin(),r.input.triangles[j].end()));}
    std::cout<<"],\"beginStatus\":"<<r.begin_status<<",\"appendStatuses\":[";for(std::size_t j=0;j<r.append_statuses.size();++j){if(j){std::cout<<',';}std::cout<<r.append_statuses[j];}std::cout<<"],\"exchangeStatus\":"<<r.exchange_status<<",\"failedPhase\":";if(r.failed_phase){std::cout<<'"'<<*r.failed_phase<<'"';}else{std::cout<<"null";}std::cout<<",\"hostFailurePreserved\":";if(r.host_failure_preserved){std::cout<<(*r.host_failure_preserved?"true":"false");}else{std::cout<<"null";}
    std::cout<<",\"summary\":";optional_packet(r.summary);std::cout<<",\"summaryBits\":";optional_packet(r.summary,true);std::cout<<",\"packets\":[";
    for(std::size_t j=0;j<r.packets.size();++j){if(j){std::cout<<',';}const auto& p=r.packets[j];std::cout<<"{\"kind\":"<<p.kind<<",\"index\":"<<p.index<<",\"values\":";packet(p.values);std::cout<<",\"bits\":";bits(p.values);std::cout<<'}';}
    std::cout<<"],\"lastMeshSummary\":";optional_packet(r.last_mesh_summary);std::cout<<",\"lastMeshSummaryBits\":";optional_packet(r.last_mesh_summary,true);std::cout<<",\"lastMeshRows\":[";
    for(std::size_t j=0;j<r.last_mesh_rows.size();++j){if(j){std::cout<<',';}const auto& row=r.last_mesh_rows[j];std::cout<<"{\"rowOrdinal\":"<<row.ordinal<<",\"packet\":";optional_packet(row.packet);std::cout<<",\"bits\":";optional_packet(row.packet,true);std::cout<<",\"candidates\":[";for(std::size_t k=0;k<row.candidates.size();++k){if(k){std::cout<<',';}packet(row.candidates[k]);}std::cout<<"],\"candidateBits\":[";for(std::size_t k=0;k<row.candidates.size();++k){if(k){std::cout<<',';}bits(row.candidates[k]);}std::cout<<"]}";}
    std::cout<<"],\"outputBefore\":";packet(r.before);std::cout<<",\"outputBeforeBits\":";bits(r.before);std::cout<<",\"outputAfter\":";packet(r.after);std::cout<<",\"outputAfterBits\":";bits(r.after);std::cout<<'}';
}
}
int main(int argc,char** argv){try{
    std::vector<Input> inputs;if(argc==2&&std::string(argv[1])=="--corpus"){inputs=corpus();}else{need(argc==1,"Usage: flight-sdk-probe [--corpus] < bounded-ascii");inputs=read(std::cin);}ok(pp_sim_reset());std::vector<Record> records;records.reserve(inputs.size());unsigned accepted=0,rejected=0;
    for(auto& input:inputs){auto r=execute(std::move(input));if(r.failed_phase){++rejected;}else{++accepted;}records.push_back(std::move(r));}
    std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-flight-sdk-packets\",\"fixtureCount\":"<<records.size()<<",\"accepted\":"<<accepted<<",\"hostRejected\":"<<rejected<<",\"fixtures\":[";for(std::size_t j=0;j<records.size();++j){if(j){std::cout<<',';}dump(records[j]);}std::cout<<"]}\n";ok(pp_sim_reset());return 0;
}catch(const std::exception& e){std::cerr<<"FAIL flight SDK probe: "<<e.what()<<'\n';return 1;}}
