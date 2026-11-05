#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace r=pikapika::report_values_wire;
namespace d=pikapika::diagnostic_wire;
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8 && sizeof(unsigned)==4);
void need(bool b) {if(!b) throw std::runtime_error("report interval assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace i=pikapika::interval;
struct IntervalValues {
    static constexpr double inf=std::numeric_limits<double>::infinity();
    static constexpr double tiny=std::numeric_limits<double>::denorm_min();
    static constexpr double maximum=std::numeric_limits<double>::max();
    std::array<i::Interval,9> intervals{
        i::Interval::point(0),i::Interval(-tiny,tiny),i::Interval::point(tiny),i::Interval(-maximum,maximum),
        i::Interval::whole(),i::Interval(-inf,-1),i::Interval(1,inf),i::Interval(-0.0,1),i::Interval(-1,0.0)};
    std::array<i::SqrtResult,5> roots{
        i::sqrt_enclosure(i::Interval::point(4)),i::sqrt_enclosure(i::Interval::point(2),1),
        i::sqrt_enclosure(i::Interval(1,4)),i::sqrt_enclosure(i::Interval::point(0)),
        i::SqrtResult{i::Interval::whole(),UINT32_MAX,true}};
};
void fixture(d::Writer& w,const IntervalValues& v) {
    ok(w.begin(0x52495631));ok(w.array());
    for(const auto& value:v.intervals) {ok(r::write(w,value));}
    for(const auto& value:v.roots) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const IntervalValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.intervals[0])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.roots[0])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);i::require_environment();
    unsigned invalid=0;
    const auto rejects=[&](auto call) {bool threw=false;try {call();} catch(const std::invalid_argument&) {threw=true;}need(threw);++invalid;};
    const auto nan=std::numeric_limits<double>::quiet_NaN();const auto inf=IntervalValues::inf;
    rejects([&]{(void)i::Interval(nan,1);});rejects([&]{(void)i::Interval(0,nan);});rejects([]{(void)i::Interval(1,-1);});
    rejects([&]{(void)i::Interval(inf,inf);});rejects([&]{(void)i::Interval(-inf,-inf);});
    rejects([&]{(void)i::Interval::point(inf);});rejects([&]{(void)i::Interval::point(nan);});need(invalid==7);
    IntervalValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
        if(mode!=FE_TONEAREST) {bool refused=false;try {(void)i::Interval::point(1);} catch(const std::runtime_error&) {refused=true;}need(refused && std::fegetround()==mode);}

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":5,\"fixtureRecords\":14,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"invalidConstructionRejections\":7,\"nonNearestConstructionRejections\":3,\"actualSqrtRecords\":4,\"syntheticSqrtRecords\":1,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            IntervalValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
