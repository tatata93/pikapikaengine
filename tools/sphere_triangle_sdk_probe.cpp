#include "pikapika/simulation_api.h"
#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
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

// This probe consumes the one frozen pure-kernel corpus, rather than maintaining
// a second copy of its 113 recipes. See --rows format in usage below. The caller
// converts the pure --fixtures JSON input values to max_digits10/roundtrip tokens.
namespace {
void need(bool b,const char* text){if(!b)throw std::runtime_error(text);}
using Input=std::array<double,PP_SIM_SPHERE_TRIANGLE_INPUT_COUNT>;
struct Row {std::string name;Input input{};};
struct Record {
    Row row;int32_t exchange_status{};
    std::optional<std::vector<double>> summary;
    std::vector<std::vector<double>> candidates;
    std::vector<double> output_before,output_after;
    std::optional<bool> host_failure_preserved;
};
std::optional<std::string> line(std::istream& in){
    std::string text;char c{};
    while(in.get(c)){if(c=='\n'){if(!text.empty()&&text.back()=='\r')text.pop_back();return text;}
        need(text.size()<4096,"Probe input line exceeds 4096 bytes");need(static_cast<unsigned char>(c)<128,"Probe rows require ASCII tokens");text.push_back(c);}
    need(!in.bad(),"Probe input read failed");if(text.empty())return std::nullopt;
    if(text.back()=='\r')text.pop_back();return text;
}
std::vector<Row> read(std::istream& in){
    need(line(in)==std::optional<std::string>("pikapika_sphere_triangle_sdk 1"),"Expected pikapika_sphere_triangle_sdk 1 header");
    need(line(in)==std::optional<std::string>("cases 113"),"Expected fixed 113-case corpus");
    std::vector<Row> rows;rows.reserve(113);std::set<std::string> names;
    for(unsigned i=0;i<113;++i){const auto raw=line(in);need(raw.has_value(),"Truncated probe corpus");std::istringstream fields(*raw);fields.imbue(std::locale::classic());fields>>std::ws;
        need(fields.peek()=='"',"Probe fixture name must be a quoted token");Row row;need(bool(fields>>std::quoted(row.name)),"Malformed probe fixture name");
        need(fields.peek()==' '||fields.peek()=='\t',"Probe name must be followed by a token delimiter");
        need(!row.name.empty()&&row.name.size()<=96&&std::all_of(row.name.begin(),row.name.end(),[](unsigned char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_';}),"Invalid probe fixture identity");
        need(names.insert(row.name).second,"Duplicate probe fixture identity");
        for(auto& value:row.input){std::string token;need(bool(fields>>token)&&token.size()<=64,"Missing/oversized probe F64 token");
            const auto parsed=std::from_chars(token.data(),token.data()+token.size(),value,std::chars_format::general);
            need(parsed.ec==std::errc{}&&parsed.ptr==token.data()+token.size()&&std::isfinite(value),"Probe F64 token must be finite roundtrip decimal");}
        std::string extra;need(!(fields>>extra),"Extra probe row values");rows.push_back(std::move(row));
    }
    need(!line(in).has_value(),"Trailing probe input after 113 rows");return rows;
}
std::vector<double> output(){const auto count=pp_sim_output_count();need(count<=64,"Invalid Native output capacity");const auto* p=pp_sim_output_f64_ptr();std::vector<double> values(p,p+count);need(std::all_of(values.begin(),values.end(),[](double x){return std::isfinite(x);}),"Nonfinite Native packet");return values;}
bool same(const std::vector<double>& a,const std::vector<double>& b){if(a.size()!=b.size())return false;for(std::size_t i=0;i<a.size();++i)if(std::bit_cast<uint64_t>(a[i])!=std::bit_cast<uint64_t>(b[i]))return false;return true;}
void number(double x){need(std::isfinite(x),"Nonfinite probe output");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
template<class Values>void numbers(const Values& values){std::cout<<'[';bool first=true;for(double x:values){if(!first)std::cout<<',';first=false;number(x);}std::cout<<']';}
template<class Values>void bit_array(const Values& values){std::cout<<'[';bool first=true;for(double x:values){if(!first)std::cout<<',';first=false;std::ostringstream bits;bits<<std::hex<<std::nouppercase<<std::setfill('0')<<std::setw(16)<<std::bit_cast<uint64_t>(x);std::cout<<'"'<<bits.str()<<'"';}std::cout<<']';}
void dump(const Record& r){
    std::cout<<"{\"name\":"<<std::quoted(r.row.name)<<",\"input\":";numbers(r.row.input);std::cout<<",\"inputBits\":";bit_array(r.row.input);std::cout<<",\"exchangeStatus\":"<<r.exchange_status<<",\"summary\":";
    if(r.summary)numbers(*r.summary);else std::cout<<"null";std::cout<<",\"summaryBits\":";if(r.summary)bit_array(*r.summary);else std::cout<<"null";
    std::cout<<",\"candidates\":[";for(std::size_t i=0;i<r.candidates.size();++i){if(i)std::cout<<',';numbers(r.candidates[i]);}std::cout<<"],\"candidateBits\":[";for(std::size_t i=0;i<r.candidates.size();++i){if(i)std::cout<<',';bit_array(r.candidates[i]);}
    std::cout<<"],\"outputBefore\":";numbers(r.output_before);std::cout<<",\"outputBeforeBits\":";bit_array(r.output_before);std::cout<<",\"outputAfter\":";numbers(r.output_after);std::cout<<",\"outputAfterBits\":";bit_array(r.output_after);
    std::cout<<",\"hostFailurePreserved\":";if(r.host_failure_preserved)std::cout<<(*r.host_failure_preserved?"true":"false");else std::cout<<"null";std::cout<<'}';
}
}
int main(int argc,char**argv){try{
    std::cout.imbue(std::locale::classic());std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);
    std::vector<Row> rows;
    if(argc==1)rows=read(std::cin);
    else if(argc==3&&std::string(argv[1])=="--rows"){std::ifstream in(argv[2],std::ios::binary);need(bool(in),"Cannot read probe rows file");rows=read(in);}
    else throw std::runtime_error("Usage: sphere_triangle_sdk_probe [--rows input.rows]; stdin: pikapika_sphere_triangle_sdk 1, cases 113, then quoted-name + 24 finite F64 tokens per row");
    need(pp_sim_api_version()==1&&pp_sim_output_f64_capacity()==64,"Unexpected Native ABI/capacity");need(pp_sim_reset()==PP_SIM_OK,"Native reset failed");std::vector<Record> records;records.reserve(rows.size());unsigned accepted=0,rejected=0;
    for(auto& row:rows){Record r;r.row=std::move(row);r.output_before=output();std::copy(r.row.input.begin(),r.row.input.end(),pp_sim_input_f64_ptr());r.exchange_status=pp_sim_sphere_triangle(24);
        if(r.exchange_status==PP_SIM_OK){++accepted;r.summary=output();need(r.summary->size()==58,"Native summary length mismatch");const double count=(*r.summary)[6];need(count>=0&&count<=7&&std::floor(count)==count,"Invalid Native candidate count");
            for(unsigned j=0;j<unsigned(count);++j){need(pp_sim_sphere_triangle_candidate(j)==PP_SIM_OK,"Native prefix getter failed");auto candidate=output();need(candidate.size()==13&&candidate[0]==j,"Native candidate packet/ordinal mismatch");r.candidates.push_back(std::move(candidate));}
            r.output_after=output();
        }else{++rejected;need(r.exchange_status==PP_SIM_INVALID_ARGUMENT,"Unexpected Native exchange failure class");r.output_after=output();r.host_failure_preserved=same(r.output_before,r.output_after);need(*r.host_failure_preserved,"Rejected exchange changed preceding output bits");}
        records.push_back(std::move(r));
    }
    need(accepted==111&&rejected==2,"Expected 111 actual core attempts and 2 explicit ID exchange rejections");
    std::cout<<"{\"schema\":1,\"kind\":\"sphere-triangle-sdk-packets\",\"fixtureCount\":"<<records.size()<<",\"accepted\":"<<accepted<<",\"hostRejected\":"<<rejected<<",\"fixtures\":[";
    for(std::size_t i=0;i<records.size();++i){if(i)std::cout<<',';dump(records[i]);}std::cout<<"]}\n";need(pp_sim_reset()==PP_SIM_OK,"Final Native reset failed");return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
