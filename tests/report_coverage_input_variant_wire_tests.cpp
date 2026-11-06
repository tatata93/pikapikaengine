#include "pikapika/report_values_wire.hpp"
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
void need(bool b) {if(!b) throw std::runtime_error("report coverage Input variant assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace a=pikapika::accelerated;
struct Numbers {
    std::size_t n=0;
    double next() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        return std::bit_cast<double>(bits[n++%bits.size()]);
    }
    Vec3 vec() {return {next(),next(),next()};}
};
struct OriginalCoefficients {
    std::array<a::Sphere,2> spheres{};
    std::array<a::StaticPlane,2> planes{};
    OriginalCoefficients() {
        Numbers values;
        for(auto& v:spheres) {v.center=values.vec();v.velocity=values.vec();v.acceleration=values.vec();v.radius=values.next();}
        for(auto& v:planes) {v.normal=values.vec();v.offset=values.next();}
        need(values.n==28);
    }
};
namespace p=pikapika::accelerated_pair_coverage;
struct PairSources {
    std::array<p::SpherePair,2> pairs{};
    std::array<p::SpherePlane,2> planes{};
    PairSources() {
        OriginalCoefficients original;
        pairs[0]={original.spheres[0],original.spheres[1]};
        pairs[1]={original.spheres[1],original.spheres[0]};
        planes[0]={original.spheres[0],original.planes[0]};
        planes[1]={original.spheres[1],original.planes[1]};
    }
};
struct InputSources {
    std::array<p::Input,4> values;
    InputSources() {PairSources v;values={p::Input{v.pairs[0]},p::Input{v.pairs[1]},p::Input{v.planes[0]},p::Input{v.planes[1]}};}
};
void fixture(d::Writer& w,const InputSources& v) {
    ok(w.begin(0x52434931));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const InputSources* source=nullptr;
    const p::Input* empty=nullptr;
    std::size_t empty_reentries=0;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%2])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[2+c.calls%2])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
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
struct Reachability {std::size_t empty=0,retained=0,phases=0,reentries=0;};
Reachability valueless_checks(const InputSources& original,std::size_t callback_count) {
    Reachability result;
    for(unsigned old=0;old<2;++old) for(unsigned target=0;target<2;++target) {
        p::Input value=original.values[old==0?0:2];
        Capture before;d::Writer bw(Capture::sink,&before);ok(bw.begin(1));ok(r::write(bw,value));ok(bw.finish());
        bool caught=false;
        try {if(target==0) value.emplace<0>(ThrowPair{});else value.emplace<1>(ThrowPlane{});}
        catch(const ConversionFailure&) {caught=true;}
        need(caught);
        if(!value.valueless_by_exception()) {
            Capture after;d::Writer aw(Capture::sink,&after);ok(aw.begin(1));ok(r::write(aw,value));ok(aw.finish());
            need(value.index()==old && before.data==after.data);++result.retained;continue;
        }
        need(value.index()==std::variant_npos);++result.empty;
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
            need(c.data==data && c.calls==calls && w.complete()==complete && complete==(phase==5));
            need(w.finish()==d::Status::invalid_state && c.data==data && c.calls==calls);++result.phases;
        }
        Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&original;re.empty=&value;fixture(rw,original);
        need(re.empty_reentries==callback_count && value.valueless_by_exception());result.reentries+=re.empty_reentries;
    }
    need(result.empty+result.retained==4);return result;
}
void run() {
    need(std::fegetround()==FE_TONEAREST);
    InputSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"common\":{\"status\":\"PASS\",\"mappedRecordTypes\":0,\"mappedFields\":0,\"mappedVariants\":1,\"fixtureRecords\":4,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":4,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true},\"reachability\":{\"attempts\":4,\"valuelessCases\":"<<reach.empty<<",\"retainedCases\":"<<reach.retained<<",\"byteFreePhaseCases\":"<<reach.phases<<",\"valuelessReentryRefusals\":"<<reach.reentries<<",\"privateBytesModified\":false}}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            InputSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
