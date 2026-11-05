#include "pikapika/world_static_mesh_session_wire.hpp"
#include <array>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace {
namespace w=pikapika::world_static_mesh_session_wire;
constexpr std::array<std::uint64_t,6> generations{1,4294967295ULL,4294967296ULL,4294967297ULL,4503599627370496ULL,9007199254740991ULL};
constexpr std::array<std::array<std::uint32_t,2>,6> known_words{{{1,0},{4294967295U,0},{0,1},{1,1},{0,1048576},{4294967295U,2097151}}};
constexpr w::TokenWords prior_words{0xdeadbeefU,0x12345678U,0xfedcba98U};
constexpr w::Token prior_token{3,42};
void need(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
void token_json(w::Token t) {std::cout<<"{\"slot\":"<<t.slot<<",\"generation\":"<<t.generation<<'}';}
template<class Values> void words_json(const Values& values) {std::cout<<'[';bool comma=false;for(auto value:values) {if(comma)std::cout<<',';comma=true;std::cout<<value;}std::cout<<']';}
std::vector<std::vector<std::uint32_t>> bad_words() {
    return {{},{0},{0,1},{0,1,0,0},{0,1,0,0,0},{0,1,0,0,0,0},
            {4,1,0},{std::numeric_limits<std::uint32_t>::max(),1,0},
            {0,0,0},{3,0,0},{0,1,2097152},{1,42,std::numeric_limits<std::uint32_t>::max()},
            {99,0,2097152}};
}
void directed() {
    unsigned pairs=0;
    for(std::uint32_t slot=0;slot<4;++slot)for(std::size_t i=0;i<generations.size();++i) {
        auto encoded=prior_words;const w::Token input{slot,generations[i]};
        need(w::encode_token(input,encoded)==w::TokenStatus::ok,"Known encode refused");
        need(encoded==w::TokenWords{slot,known_words[i][0],known_words[i][1]},"Known integer word vector differs");
        auto decoded=prior_token;need(w::decode_token(encoded,decoded)==w::TokenStatus::ok&&decoded==input,"Known decode differs");++pairs;
    }
    for(auto generation:{std::uint64_t{0},std::uint64_t{9007199254740992ULL},std::numeric_limits<std::uint64_t>::max()}) {
        auto output=prior_words;need(w::encode_token({0,generation},output)!=w::TokenStatus::ok&&output==prior_words,"Invalid generation altered output");
    }
    auto output=prior_words;need(w::encode_token({4,1},output)==w::TokenStatus::slot_range&&output==prior_words,"Invalid slot altered output");
    for(const auto& words:bad_words()) {auto output_token=prior_token;need(w::decode_token(words,output_token)!=w::TokenStatus::ok&&output_token==prior_token,"Invalid wire altered token");}
    auto precedence=prior_token;
    need(w::decode_token(std::array<std::uint32_t,3>{99,0,2097152},precedence)==w::TokenStatus::slot_range&&precedence==prior_token,"Invalid-field precedence changed");
    std::cout<<"Token wire: "<<pairs<<" known integer vectors and invalid-output retention PASS. Syntax only; no Registry, C ABI, JS or WASM acceptance.\n";
}
void fixtures() {
    std::cout<<"{\"schema\":1,\"kind\":\"world-static-mesh-session-token-wire-fixtures\",\"tokenVersion\":"<<w::token_version<<",\"rows\":[";unsigned rows=0;
    auto comma=[&] {if(rows++)std::cout<<',';};
    auto encode=[&](w::Token token) {
        comma();auto output=prior_words;const auto status=w::encode_token(token,output);std::cout<<"{\"kind\":\"encode\",\"input\":";token_json(token);std::cout<<",\"prior\":";words_json(prior_words);std::cout<<",\"status\":"<<static_cast<unsigned>(status)<<",\"output\":";words_json(output);std::cout<<'}';
    };
    auto decode=[&](const auto& words) {
        comma();auto output=prior_token;const auto status=w::decode_token(words,output);std::cout<<"{\"kind\":\"decode\",\"input\":";words_json(words);std::cout<<",\"prior\":";token_json(prior_token);std::cout<<",\"status\":"<<static_cast<unsigned>(status)<<",\"output\":";token_json(output);std::cout<<'}';
    };
    for(std::uint32_t slot=0;slot<4;++slot)for(std::size_t i=0;i<generations.size();++i) {
        encode({slot,generations[i]});decode(w::TokenWords{slot,known_words[i][0],known_words[i][1]});
    }
    for(std::uint32_t slot:{0U,3U,4U,std::numeric_limits<std::uint32_t>::max()})for(auto generation:{std::uint64_t{0},std::uint64_t{1},std::uint64_t{9007199254740992ULL},std::numeric_limits<std::uint64_t>::max()})encode({slot,generation});
    for(const auto& words:bad_words())decode(words);
    std::cout<<"],\"actualRows\":"<<rows<<"}\n";
}
}
int main(int argc,char** argv) {
    try {const std::string_view mode=argc==2?argv[1]:"--run";if(mode=="--fixtures")fixtures();else {need(mode=="--run","Unknown mode");directed();}return 0;}
    catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
