#include "pikapika/report_values_wire.hpp"
#include "report_coverage_pair_result_wire_sources.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>
#include <type_traits>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace r=pikapika::report_values_wire;
namespace d=pikapika::diagnostic_wire;
namespace c=pikapika::world_static_mesh_flight_controlled_tick;
namespace s=pikapika::world_static_mesh_flight_scheduler;
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report coverage pair Result assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_pair_coverage;
using ResultSources=pikapika_report_pair_result_sources::ResultSources;
void fixture(d::Writer& w,const ResultSources& v) {
    ok(w.begin(0x52435231));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const ResultSources* source=nullptr;
    const p::Result* empty=nullptr;
    std::size_t empty_reentries=0;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%17])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[(c.calls+2)%17])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
            if(c.empty) {need(r::write(w,*c.empty)==d::Status::reentrant);need(w.status()==d::Status::ok);++c.empty_reentries;}
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
struct ConversionFailure {};
struct ThrowPair {operator p::SpherePair() const {throw ConversionFailure{};}};
struct ThrowPlane {operator p::SpherePlane() const {throw ConversionFailure{};}};
struct Reachability {std::size_t empty=0,retained=0,phases=0,reentries=0,prefix_cases=0,sticky_cases=0;};
Reachability valueless_checks(const ResultSources& original,std::size_t callback_count) {
    Reachability result;
    for(unsigned old=0;old<2;++old) for(unsigned target=0;target<2;++target) {
        p::Result value=original.values[1];
        pikapika_report_pair_result_sources::SnapshotSources snapshots;value.snapshot=snapshots.values[old==0?0:2];
        value.status=p::Status::invalid_input;value.reason=p::Reason::input_domain;
        Capture before;d::Writer bw(Capture::sink,&before);ok(bw.begin(1));ok(r::write(bw,value));ok(bw.finish());
        bool caught=false;
        try {if(target==0) value.snapshot->input.emplace<0>(ThrowPair{});else value.snapshot->input.emplace<1>(ThrowPlane{});}
        catch(const ConversionFailure&) {caught=true;}
        need(caught);
        if(!value.snapshot->input.valueless_by_exception()) {
            Capture after;d::Writer aw(Capture::sink,&after);ok(aw.begin(1));ok(r::write(aw,value));ok(aw.finish());
            need(value.snapshot->input.index()==old && before.data==after.data);++result.retained;continue;
        }
        need(value.snapshot->input.index()==std::variant_npos);++result.empty;
        for(unsigned phase=0;phase<6;++phase) {
            Capture c;d::Writer w(Capture::sink,&c);
            if(phase) ok(w.begin(1));
            if(phase==1) ok(w.array());
            if(phase==2) {ok(w.object());ok(w.key({}));}
            if(phase==3) ok(w.present());
            if(phase==4) ok(w.variant(0));
            if(phase==5) {ok(w.null_value());ok(w.finish());}
            const auto data=c.data;const auto calls=c.calls;const auto complete=w.complete();
            need(r::write(w,value)==d::Status::invalid_state && w.status()==d::Status::invalid_state);
            auto expected=data;std::size_t expected_calls=calls;
            if(phase>=1 && phase<=4) {
                // Independent v1 prefix: outer object,2 enum fields,optional Snapshot,
                // then its object/input key. No Writer/getter calls build this expectation.
                std::vector<std::byte> prefix{std::byte{9}};
                auto key=[&prefix](std::string_view name) {
                    prefix.push_back(std::byte{15});for(unsigned n=0;n<8;++n) prefix.push_back(static_cast<std::byte>((static_cast<std::uint64_t>(name.size())>>(8*n))&255));
                    for(const unsigned char ch:name) prefix.push_back(static_cast<std::byte>(ch));
                };
                key("status");prefix.insert(prefix.end(),{std::byte{8},std::byte{2},std::byte{0},std::byte{0},std::byte{0}});
                key("reason");prefix.insert(prefix.end(),{std::byte{8},std::byte{3},std::byte{0},std::byte{0},std::byte{0}});
                key("snapshot");prefix.push_back(std::byte{12});prefix.push_back(std::byte{9});key("input");need(prefix.size()==74);
                expected.insert(expected.end(),prefix.begin(),prefix.end());expected_calls+=13;++result.prefix_cases;
            }
            need(c.data==expected && c.calls==expected_calls && w.complete()==complete && complete==(phase==5));
            need(w.finish()==d::Status::invalid_state && c.data==expected && c.calls==expected_calls);++result.phases;
        }
        for(unsigned prior=0;prior<5;++prior) {
            Capture c;d::Writer w(prior==2?nullptr:Capture::sink,&c);d::Status expected=d::Status::invalid_state;
            if(prior==0) need(w.finish()==expected);
            if(prior==1) {ok(w.begin(1));for(std::size_t i=0;i<64;++i) ok(w.array());expected=d::Status::depth_limit;need(w.array()==expected);}
            if(prior==2) {expected=d::Status::missing_sink;need(w.begin(1)==expected);}
            if(prior==3) {c.fail_at=1;expected=d::Status::sink_stopped;need(w.begin(1)==expected);}
            if(prior==4) {c.throw_at=1;expected=d::Status::sink_exception;need(w.begin(1)==expected);}
            const auto data=c.data;const auto calls=c.calls;
            need(r::write(w,value)==expected && w.status()==expected && c.calls==calls && c.data==data);++result.sticky_cases;
        }
        Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&original;re.empty=&value;fixture(rw,original);
        need(re.empty_reentries==callback_count && value.snapshot->input.valueless_by_exception());result.reentries+=re.empty_reentries;
    }
    need(result.empty+result.retained==4);return result;
}
void run() {
    need(std::fegetround()==FE_TONEAREST);
    ResultSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==2*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    const auto reach=valueless_checks(v,base.calls);
    std::cout<<"{\"common\":{\"status\":\"PASS\",\"mappedRecordTypes\":1,\"mappedFields\":12,\"mappedVariants\":0,\"fixtureRecords\":17,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":17,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true},\"reachability\":{\"attempts\":4,\"valuelessCases\":"<<reach.empty<<",\"retainedCases\":"<<reach.retained<<",\"resultRejectionPhaseCases\":"<<reach.phases<<",\"exactPartialPrefixCases\":"<<reach.prefix_cases<<",\"existingStickyFailureCases\":"<<reach.sticky_cases<<",\"valuelessReentryRefusals\":"<<reach.reentries<<",\"privateBytesModified\":false}}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            ResultSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
