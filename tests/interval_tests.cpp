#include "pikapika/interval.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

using namespace pikapika::interval;
namespace {
constexpr double inf=std::numeric_limits<double>::infinity();
constexpr double tiny=std::numeric_limits<double>::denorm_min();
constexpr double maximum=std::numeric_limits<double>::max();
unsigned passed=0;
void check(bool yes,const char* message) { if(!yes)throw std::runtime_error(message); }
void test(const char* name,const std::function<void()>& body) { body();++passed;std::cout<<"PASS "<<name<<'\n'; }
template<class Error=std::exception> void rejects(const std::function<void()>& body) {
    bool threw=false;try{body();}catch(const Error&){threw=true;}check(threw,"expected exception");
}
Interval p(double value) { return Interval::point(value); }
bool same(const Interval& a,const Interval& b) { return a.lower()==b.lower() && a.upper()==b.upper(); }
void encloses(const Interval& a,double lo,double hi) { check(a.lower()<=lo && a.upper()>=hi,"known exact range enclosure"); }
void valid(const Interval& a) { check(!std::isnan(a.lower())&&!std::isnan(a.upper())&&a.lower()<=a.upper(),"valid ordered non-NaN bounds"); }
std::uint64_t bits(double value) { return std::bit_cast<std::uint64_t>(value); }
void row(char op,const Interval& a,const Interval& b,const Interval& result) {
    valid(result);
    std::cout<<op<<','<<std::hex<<bits(a.lower())<<','<<bits(a.upper())<<','<<bits(b.lower())<<','<<bits(b.upper())
        <<','<<bits(result.lower())<<','<<bits(result.upper())<<std::dec<<'\n';
}
// Exact-oracle mode deliberately performs NO reference floating-point arithmetic.
// Each line encodes source/output IEEE bits for a separate Python Fraction check.
void oracle_pair(const Interval& a,const Interval& b) {
    row('+',a,b,add(a,b));row('-',a,b,sub(a,b));row('*',a,b,mul(a,b));
    if(!b.contains_zero())row('/',a,b,divide(a,b));
}
int oracle() {
    require_environment();
    const std::array<double,25> edge{0.0,-0.0,tiny,-tiny,2*tiny,-2*tiny,
        0x1p-1022,-0x1p-1022,0x1.fffffffffffffp-1023,-0x1.fffffffffffffp-1023,
        0x1p-511,-0x1p-511,0x1p-53,-0x1p-53,1,-1,
        0x1.0000000000001p0,0x1.fffffffffffffp-1,3,-3,0x1p511,-0x1p511,
        maximum,-maximum,0x1p-537};
    for(double a:edge) {
        row('s',p(a),p(0),square(p(a)));
        for(double b:edge)oracle_pair(p(a),p(b));
    }
    // xorshift corpus, finite bit patterns spanning all exponent scales.
    std::uint64_t state=0x50696b6170696b61ULL;
    auto next=[&]() { state^=state<<13;state^=state>>7;state^=state<<17;
        std::uint64_t value=state;if((value&0x7ff0000000000000ULL)==0x7ff0000000000000ULL)value^=0x0010000000000000ULL;
        return std::bit_cast<double>(value); };
    for(unsigned i=0;i<512;++i) {
        const double a=next(),b=next(),c=next(),d=next();
        oracle_pair(p(a),p(b));
        const Interval x{std::min(a,b),std::max(a,b)},y{std::min(c,d),std::max(c,d)};
        oracle_pair(x,y);row('s',x,p(0),square(x));
    }
    return 0;
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--oracle")return oracle();
        test("supported binary64 environment",[]{require_environment();check(environment_issue()==nullptr,"environment issue");});
        test("finite point and invalid bounds",[]{
            check(same(p(3),{3,3}),"point3");
            rejects<std::invalid_argument>([]{Interval{2,1};});
            rejects<std::invalid_argument>([]{Interval{NAN,1};});
            rejects<std::invalid_argument>([]{Interval{0,NAN};});
            rejects<std::invalid_argument>([]{p(inf);});rejects<std::invalid_argument>([]{p(-inf);});
            rejects<std::invalid_argument>([]{Interval{inf,inf};});rejects<std::invalid_argument>([]{Interval{-inf,-inf};});
        });
        test("infinities are bounds not finite-real members",[]{
            const auto all=Interval::whole();check(all.contains(maximum)&&all.contains(-maximum)&&all.contains(0),"whole");
            check(!all.contains(inf)&&!all.contains(-inf)&&!all.contains(NAN),"nonfinite is not member");
            check(all.contains(Interval{-inf,2}),"interval subset");
        });
        test("sign distinguishes strict exclusion from zero boundary",[]{
            check(sign({-2,-1})==Sign::negative&&sign({-2,0})==Sign::nonpositive,"negative signs");
            check(sign(p(0))==Sign::zero&&sign({0,2})==Sign::nonnegative,"zero signs");
            check(sign({1,2})==Sign::positive&&sign({-2,2})==Sign::mixed,"remaining signs");
            check(!Interval{0,2}.strictly_positive()&&Interval{tiny,2}.strictly_positive(),"CCD strict positive");
        });
        test("intersection hull and touching point",[]{
            check(!intersection({-2,-1},{0,3}),"empty intersection");
            check(same(*intersection({-2,1},{1,3}),p(1)),"point intersection");
            check(same(*intersection(Interval::whole(),{-1,3}),{-1,3}),"whole intersection");
            check(same(hull({-2,-1},{1,3}),{-2,3}),"hull");
        });
        test("signed zero and exact zero identities",[]{
            check(std::signbit(p(-0.0).lower())&&!std::signbit(p(-0.0).upper()),"canonical signedzero");
            check(same(add(p(0),{-2,3}),{-2,3})&&same(sub({-2,3},p(0)),{-2,3}),"zero identity");
            check(same(mul(p(-0.0),Interval::whole()),p(0)),"zero times unbounded");
            check(same(negate({-inf,2}),{-2,inf}),"negate unbounded");
        });
        test("addition midpoint exact binary rational enclosure",[]{
            // 1+2^-53 is strictly between 1 and 1+2^-52. nearest-even gives 1.
            const auto r=add(p(1),p(0x1p-53));
            check(r.lower()<=1&&r.upper()>=0x1.0000000000001p0,"halfway addition");
            const auto n=add(p(-1),p(-0x1p-53));
            check(n.lower()<=-0x1.0000000000001p0&&n.upper()>=-1,"negative halfway");
        });
        test("subtraction midpoint cancellation and lost low terms",[]{
            // 1-2^-54 lies strictly between 1-2^-53 and 1.
            const auto r=sub(p(1),p(0x1p-54));
            check(r.lower()<=0x1.fffffffffffffp-1&&r.upper()>=1,"halfway subtraction");
            encloses(sub(p(1),p(1)),0,0);
            // ((2^53+1)-2^53) is exactly 1 over reals. Final-only expansion of
            // rounded result0 would miss it; primitive enclosures retain it.
            check(sub(add(p(0x1p53),p(1)),p(0x1p53)).contains(1),"composition lost term");
        });
        test("product nonrepresentable 106-bit rational",[]{
            // (1+2^-52)^2=1+2^-51+2^-104 lies strictly between these bounds.
            const auto r=mul(p(0x1.0000000000001p0),p(0x1.0000000000001p0));
            check(r.lower()<=0x1.0000000000002p0&&r.upper()>=0x1.0000000000003p0,"product fine remainder");
            encloses(mul({-2,3},{-4,5}),-12,15);
        });
        test("division one-third rational and sign reversal",[]{
            // Binary expansions bracket exact 1/3; no double 1/3 oracle.
            const auto r=divide(p(1),p(3));
            check(r.lower()<=0x1.5555555555555p-2&&r.upper()>=0x1.5555555555556p-2,"one third");
            encloses(divide({2,4},{-4,-2}),-2,-0.5);
            check(same(divide(p(0),{tiny,inf}),p(0)),"zero quotient");
        });
        test("zero denominator is explicitly unresolved by exception",[]{
            for(const Interval b:std::array<Interval,4>{p(0),Interval{-1,1},Interval{0,1},Interval{-1,0}})
                rejects<std::domain_error>([&]{divide(p(0),b);});
        });
        test("overflow produces enclosure not infinity singleton",[]{
            const auto a=add(p(maximum),p(maximum)),m=mul(p(maximum),p(2));
            check(a.lower()==maximum&&a.upper()==inf&&m.lower()==maximum&&m.upper()==inf,"positive overflow");
            const auto n=sub(p(-maximum),p(maximum));
            check(n.lower()==-inf&&n.upper()==-maximum,"negative overflow");
            const auto q=divide(p(1),p(tiny));check(q.upper()==inf&&q.lower()<=maximum,"reciprocal overflow");
        });
        test("gradual and below-subnormal underflow enclose real results",[]{
            const auto half=mul(p(tiny),p(0.5));
            // Exact2^-1075 is positive strictly between 0 and tiny.
            check(half.lower()<=0&&half.upper()>=tiny,"positive half subnormal");
            const auto neg=mul(p(-tiny),p(0.5));check(neg.lower()<=-tiny&&neg.upper()>=0,"negative half subnormal");
            const auto q=divide(p(tiny),p(2));check(q.lower()<=0&&q.upper()>=tiny,"division underflow");
            encloses(add(p(tiny),p(tiny)),2*tiny,2*tiny);
        });
        test("unbounded arithmetic avoids infinity NaNs",[]{
            check(same(add({-inf,2},{3,inf}),Interval::whole()),"unbounded add");
            check(same(sub({-inf,2},{3,inf}),{-inf,std::nextafter(-1,inf)}),"unbounded subtract");
            check(same(mul({0,inf},{-inf,0}),{-inf,0}),"unbounded product");
            check(same(mul(Interval::whole(),Interval::whole()),Interval::whole()),"whole product");
            const auto r=divide({1,inf},{1,inf});check(r.lower()<=0&&r.upper()==inf,"unbounded quotient");
            const auto n=divide(p(1),{-inf,-1});encloses(n,-1,0);
        });
        test("square knows correlation and nonnegative lower bound",[]{
            encloses(square({-2,3}),0,9);check(square({-2,3}).lower()==0,"square crosses zero");
            encloses(square({-3,-2}),4,9);check(square(p(tiny)).lower()==0,"tiny square lower");
            check(same(square(Interval::whole()),{0,inf}),"whole square");
            check(same(square(p(0)),p(0)),"zero square");
        });
        test("Horner quadratic and quartic every operation enclosed",[]{
            const std::array<Interval,3> quadratic{p(1),p(-3),p(2)};
            check(polynomial(quadratic,p(1)).contains(0),"quadratic known root1");
            check(polynomial(quadratic,p(2)).contains(0),"quadratic known root2");
            check(polynomial(quadratic,{-1,0}).strictly_positive(),"quadratic interval exclusion");
            const std::array<Interval,5> quartic{p(1),p(0),p(-2),p(0),p(1)};
            check(polynomial(quartic,p(1)).contains(0),"quartic double root");
            check(polynomial(quartic,p(2)).contains(9),"quartic exact value");
            rejects<std::invalid_argument>([]{polynomial({},p(1));});
            check(same(polynomial(std::array<Interval,1>{p(4)},Interval::whole()),p(4)),"constant");
        });
        test("changed rounding rejects or WASM remains fixed nearest",[]{
            const Interval one=p(1);
            const int original=std::fegetround();
            const int status=std::fesetround(FE_UPWARD);
            if(status==0 && std::fegetround()!=FE_TONEAREST) {
                const bool rejected=environment_issue()!=nullptr;
                bool threw=false;try{add(one,one);}catch(const std::runtime_error&){threw=true;}
                std::fesetround(original);check(rejected&&threw,"nonnearest must reject");
            } else {
                std::fesetround(original);
                check(std::fegetround()==FE_TONEAREST,"fixed nearest target");
#if !defined(__wasm__)
                check(status!=0,"native rounding setter must not silently ignore requested mode");
#endif
                // Wasm has no dynamic rounding instruction. Emscripten's libc
                // fesetround can acknowledge a call without changing f64 ops.
            }
            require_environment();
        });
#if defined(_M_X64) || defined(__x86_64__)
        test("runtime rejects FTZ DAZ and exception unmask before arithmetic",[]{
            const Interval before=p(tiny);
            const unsigned original=_mm_getcsr();
            for(const unsigned setting:std::array<unsigned,3>{original|0x8000u,original|0x40u,original&~0x80u}) {
                _mm_setcsr(setting);const bool rejected=environment_issue()!=nullptr;
                bool threw=false,construction_threw=false;
                try{square(before);}catch(const std::runtime_error&){threw=true;}
                try{p(tiny);}catch(const std::runtime_error&){construction_threw=true;}
                _mm_setcsr(original);check(rejected&&threw&&construction_threw,"unsupported MXCSR must reject");
            }
            require_environment();
        });
#endif
        std::cout<<"INTERVAL PASS "<<passed<<" groups\n";
        return 0;
    } catch(const std::exception& error) { std::cerr<<"INTERVAL FAIL: "<<error.what()<<'\n';return 1; }
}
