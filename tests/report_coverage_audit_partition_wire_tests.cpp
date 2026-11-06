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
void need(bool b) {if(!b) throw std::runtime_error("report coverage Audit/Partition assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_pair_coverage;
struct AuditPartitionSources {
    std::array<p::Audit,20> audits{};
    std::array<p::PartitionLeaf,12> leaves{};
    AuditPartitionSources() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        auto reason=[](std::size_t n) {const auto k=n%17;return static_cast<p::Reason>(k<15?static_cast<unsigned>(k):(k==15?0x80000000u:UINT32_MAX));};
        for(std::size_t i=0;i<audits.size();++i) {
            auto& value=audits[i];value.cell.time_bounds={std::bit_cast<double>(bits[2*i%16]),std::bit_cast<double>(bits[(2*i+1)%16])};value.cell.depth=depths[i%4];
            if(i&4) value.cell.parent_audit=static_cast<std::size_t>(counts[i%4]);
            value.call_attempted=(i&8)!=0;
            if(i&1) {
                switch((i/2)%5) {
                case 0:value.value=interval::Interval::point(0);break;
                case 1:value.value=interval::Interval::whole();break;
                case 2:value.value=interval::Interval(std::bit_cast<double>(bits[9]),std::bit_cast<double>(bits[8]));break;
                case 3:value.value=interval::Interval(std::bit_cast<double>(bits[2]),std::bit_cast<double>(bits[5]));break;
                default:value.value=interval::Interval(-1,std::bit_cast<double>(bits[3]));break;
                }
            }
            value.outcome=static_cast<p::Outcome>(kinds[i%6]);value.blocked_reason=reason(i);
            if(i&2) value.split_time=std::bit_cast<double>(bits[(i+3)%16]);
        }
        for(std::size_t i=0;i<leaves.size();++i) {
            auto& value=leaves[i];value.cell.time_bounds={std::bit_cast<double>(bits[(2*i+3)%16]),std::bit_cast<double>(bits[(2*i+4)%16])};value.cell.depth=depths[(i+1)%4];
            if(i&2) value.cell.parent_audit=static_cast<std::size_t>(counts[(i/4+i)%4]);
            value.state=static_cast<p::LeafState>(kinds[i%6]);
            if(i&1) value.audit_index=static_cast<std::size_t>(counts[(i/2)%4]);
            value.blocked_reason=reason(i+7);
        }
    }
};
void fixture(d::Writer& w,const AuditPartitionSources& v) {
    ok(w.begin(0x52434131));ok(w.array());
    for(const auto& value:v.audits) {ok(r::write(w,value));}
    for(const auto& value:v.leaves) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const AuditPartitionSources* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.audits[c.calls%20])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.leaves[c.calls%12])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    AuditPartitionSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":10,\"fixtureRecords\":32,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":32,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            AuditPartitionSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
