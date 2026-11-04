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

// ASCII input is bounded and parsed completely before any Native exchange.
// The root runner converts the frozen pure fixture inputs into these tokens;
// this probe contains no duplicate geometric recipes or expected classifications.
namespace {
void need(bool b,const char* text){if(!b)throw std::runtime_error(text);}
using Query=std::array<double,14>;
using Triangle=std::array<double,10>;
struct Input {std::string name;Query query{};std::vector<Triangle> triangles;};
struct Row {unsigned row_ordinal{};std::optional<std::vector<double>> packet;std::vector<std::vector<double>> candidates;};
struct Record {
    Input input;int32_t begin_status{},exchange_status{};std::vector<int32_t> append_statuses;
    std::optional<std::string> failed_phase;std::optional<std::vector<double>> summary;
    std::vector<std::vector<double>> sources;std::vector<Row> rows;
    std::vector<double> output_before,output_after;std::optional<bool> host_failure_preserved;
};
std::optional<std::string> line(std::istream& in){std::string text;char c{};
    while(in.get(c)){if(c=='\n'){if(!text.empty()&&text.back()=='\r')text.pop_back();return text;}
        need(text.size()<4096,"Probe line exceeds 4096 bytes");need(static_cast<unsigned char>(c)<128,"Probe rows require ASCII tokens");text.push_back(c);}
    need(!in.bad(),"Probe read failed");if(text.empty())return std::nullopt;if(text.back()=='\r')text.pop_back();return text;
}
unsigned integer(const std::string& token,unsigned maximum){unsigned result{};const auto p=std::from_chars(token.data(),token.data()+token.size(),result);need(p.ec==std::errc{}&&p.ptr==token.data()+token.size()&&result<=maximum,"Invalid bounded unsigned probe token");return result;}
template<class Values>void values(std::istringstream& in,Values& out){for(auto& value:out){std::string token;need(bool(in>>token)&&token.size()<=64,"Missing or oversized probe F64");const auto p=std::from_chars(token.data(),token.data()+token.size(),value,std::chars_format::general);need(p.ec==std::errc{}&&p.ptr==token.data()+token.size()&&std::isfinite(value),"Probe F64 must be finite roundtrip decimal");}std::string extra;need(!(in>>extra),"Trailing probe tokens");}
std::vector<Input> read(std::istream& in){
    need(line(in)==std::optional<std::string>("pikapika_sphere_triangle_mesh_sdk 1"),"Expected mesh probe header");
    const auto raw_count=line(in);need(raw_count.has_value(),"Missing cases count");std::istringstream count_fields(*raw_count);std::string keyword,token,extra;need(bool(count_fields>>keyword>>token)&&keyword=="cases"&&!(count_fields>>extra),"Expected cases N");const auto count=integer(token,256);need(count>=1,"Probe cases must be 1..256");
    std::vector<Input> result;result.reserve(count);std::set<std::string> names;
    for(unsigned i=0;i<count;++i){const auto raw=line(in);need(raw.has_value(),"Truncated probe case");std::istringstream fields(*raw);fields.imbue(std::locale::classic());fields>>std::ws;need(fields.peek()=='"',"Quoted fixture identity required");Input c;need(bool(fields>>std::quoted(c.name)),"Malformed fixture identity");need(fields.peek()==' '||fields.peek()=='\t',"Fixture identity delimiter required");
        need(!c.name.empty()&&c.name.size()<=96&&std::all_of(c.name.begin(),c.name.end(),[](unsigned char x){return (x>='a'&&x<='z')||(x>='A'&&x<='Z')||(x>='0'&&x<='9')||x=='-'||x=='_';}),"Invalid probe fixture identity");need(names.insert(c.name).second,"Duplicate probe identity");
        need(bool(fields>>token),"Missing source count");const auto n=integer(token,65);values(fields,c.query);c.triangles.resize(n);
        for(auto& t:c.triangles){const auto source=line(in);need(source.has_value(),"Truncated triangle sources");std::istringstream f(*source);f.imbue(std::locale::classic());values(f,t);}result.push_back(std::move(c));
    }
    need(!line(in).has_value(),"Trailing probe corpus bytes");return result;
}
std::vector<double> output(){const auto n=pp_sim_output_count();need(n<=64,"Invalid Native output capacity");const auto* p=pp_sim_output_f64_ptr();std::vector<double> a(p,p+n);need(std::all_of(a.begin(),a.end(),[](double x){return std::isfinite(x);}),"Nonfinite Native packet");return a;}
bool same(const std::vector<double>& a,const std::vector<double>& b){if(a.size()!=b.size())return false;for(std::size_t i=0;i<a.size();++i)if(std::bit_cast<uint64_t>(a[i])!=std::bit_cast<uint64_t>(b[i]))return false;return true;}
void number(double x){need(std::isfinite(x),"Nonfinite probe JSON");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
template<class Values>void numbers(const Values& a){std::cout<<'[';bool first=true;for(double x:a){if(!first)std::cout<<',';first=false;number(x);}std::cout<<']';}
template<class Values>void bits(const Values& a){std::cout<<'[';bool first=true;for(double x:a){if(!first)std::cout<<',';first=false;std::ostringstream s;s<<std::hex<<std::nouppercase<<std::setfill('0')<<std::setw(16)<<std::bit_cast<uint64_t>(x);std::cout<<'"'<<s.str()<<'"';}std::cout<<']';}
template<class Rows,class Writer>void matrix(const Rows& rows,Writer write){std::cout<<'[';for(std::size_t i=0;i<rows.size();++i){if(i)std::cout<<',';write(rows[i]);}std::cout<<']';}
void optional_numbers(const std::optional<std::vector<double>>& a){if(a)numbers(*a);else std::cout<<"null";}
void optional_bits(const std::optional<std::vector<double>>& a){if(a)bits(*a);else std::cout<<"null";}
void dump(const Record& r){
    std::cout<<"{\"name\":"<<std::quoted(r.input.name)<<",\"input\":";numbers(r.input.query);std::cout<<",\"inputBits\":";bits(r.input.query);
    std::cout<<",\"triangles\":";matrix(r.input.triangles,[](const auto& a){numbers(a);});std::cout<<",\"triangleBits\":";matrix(r.input.triangles,[](const auto& a){bits(a);});
    std::cout<<",\"beginStatus\":"<<r.begin_status<<",\"appendStatuses\":";numbers(r.append_statuses);std::cout<<",\"exchangeStatus\":"<<r.exchange_status<<",\"failedPhase\":";if(r.failed_phase)std::cout<<std::quoted(*r.failed_phase);else std::cout<<"null";
    std::cout<<",\"summary\":";optional_numbers(r.summary);std::cout<<",\"summaryBits\":";optional_bits(r.summary);
    std::cout<<",\"sources\":";matrix(r.sources,[](const auto& a){numbers(a);});std::cout<<",\"sourceBits\":";matrix(r.sources,[](const auto& a){bits(a);});
    std::cout<<",\"rows\":[";for(std::size_t i=0;i<r.rows.size();++i){if(i)std::cout<<',';const auto& row=r.rows[i];std::cout<<"{\"rowOrdinal\":"<<row.row_ordinal<<",\"packet\":";optional_numbers(row.packet);std::cout<<",\"bits\":";optional_bits(row.packet);std::cout<<",\"candidates\":";matrix(row.candidates,[](const auto& a){numbers(a);});std::cout<<",\"candidateBits\":";matrix(row.candidates,[](const auto& a){bits(a);});std::cout<<'}';}
    std::cout<<"],\"outputBefore\":";numbers(r.output_before);std::cout<<",\"outputBeforeBits\":";bits(r.output_before);std::cout<<",\"outputAfter\":";numbers(r.output_after);std::cout<<",\"outputAfterBits\":";bits(r.output_after);std::cout<<",\"hostFailurePreserved\":";if(r.host_failure_preserved)std::cout<<(*r.host_failure_preserved?"true":"false");else std::cout<<"null";std::cout<<'}';
}
}
int main(int argc,char** argv){try{
    std::cout.imbue(std::locale::classic());std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);std::vector<Input> inputs;
    if(argc==1)inputs=read(std::cin);else if(argc==3&&std::string(argv[1])=="--rows"){std::ifstream in(argv[2],std::ios::binary);need(bool(in),"Cannot open probe input");inputs=read(in);}else throw std::runtime_error("Usage: sphere_triangle_mesh_sdk_probe [--rows file]; header pikapika_sphere_triangle_mesh_sdk 1; cases N; then quoted-name triangleCount query14, followed by triangleCount lines of ID ABC9");
    need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64,"Unexpected Native ABI");need(pp_sim_reset()==PP_SIM_OK,"Native reset failed");std::vector<Record> records;records.reserve(inputs.size());unsigned accepted=0,rejected=0;
    for(auto& input:inputs){Record r;r.input=std::move(input);r.output_before=output();r.begin_status=pp_sim_sphere_triangle_mesh_begin(uint32_t(r.input.triangles.size()));r.exchange_status=r.begin_status;
        if(r.begin_status!=PP_SIM_OK)r.failed_phase="begin";
        for(std::size_t first=0;!r.failed_phase&&first<r.input.triangles.size();first+=6){const auto count=std::min<std::size_t>(6,r.input.triangles.size()-first);for(std::size_t j=0;j<count;++j)std::copy(r.input.triangles[first+j].begin(),r.input.triangles[first+j].end(),pp_sim_input_f64_ptr()+10*j);r.exchange_status=pp_sim_sphere_triangle_mesh_append(uint32_t(count*10));r.append_statuses.push_back(r.exchange_status);if(r.exchange_status!=PP_SIM_OK)r.failed_phase="append";}
        if(!r.failed_phase){std::copy(r.input.query.begin(),r.input.query.end(),pp_sim_input_f64_ptr());r.exchange_status=pp_sim_sphere_triangle_mesh(14);if(r.exchange_status!=PP_SIM_OK)r.failed_phase="query";}
        if(!r.failed_phase){++accepted;r.summary=output();need(r.summary->size()==24,"Native mesh header length");const auto n=r.input.triangles.size();need((*r.summary)[3]==double(n),"Native mesh source count");
            for(unsigned j=0;j<n;++j){need(pp_sim_sphere_triangle_mesh_source(j)==PP_SIM_OK,"Native mesh source getter failed");auto source=output();need(source.size()==14&&source[0]==j,"Native mesh source packet");r.sources.push_back(std::move(source));}
            for(unsigned j=0;j<n;++j)if(r.sources[j][11]==1){Row row;row.row_ordinal=j;if(r.sources[j][12]==1){need(pp_sim_sphere_triangle_mesh_row(j)==PP_SIM_OK,"Native mesh row getter failed");row.packet=output();need(row.packet->size()==58,"Native mesh row packet length");const auto c=(*row.packet)[6];need(c>=0&&c<=7&&std::floor(c)==c,"Native mesh candidate count");for(unsigned k=0;k<unsigned(c);++k){need(pp_sim_sphere_triangle_mesh_candidate(j,k)==PP_SIM_OK,"Native mesh candidate getter failed");auto candidate=output();need(candidate.size()==13&&candidate[0]==k,"Native mesh candidate packet");row.candidates.push_back(std::move(candidate));}}r.rows.push_back(std::move(row));}
        }else{++rejected;r.host_failure_preserved=same(r.output_before,output());need(*r.host_failure_preserved,"Rejected exchange changed prior output");}
        r.output_after=output();records.push_back(std::move(r));
    }
    std::cout<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-sdk-packets\",\"fixtureCount\":"<<records.size()<<",\"accepted\":"<<accepted<<",\"hostRejected\":"<<rejected<<",\"fixtures\":[";for(std::size_t i=0;i<records.size();++i){if(i)std::cout<<',';dump(records[i]);}std::cout<<"]}\n";need(pp_sim_reset()==PP_SIM_OK,"Final Native reset failed");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
