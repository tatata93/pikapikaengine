#include "pikapika/derived_mesh.hpp"
#include "pikapika/skinning_io.hpp"
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

namespace dm=pikapika::derived_mesh;
namespace io=pikapika::skinning_io;
namespace skin=pikapika::skinning;
using pikapika::Vec3;
struct Case {
    std::string name;io::Source source;double seconds{};bool loop{};dm::Settings settings;
    Case(std::string label,io::Source value,double time,bool looping=false,dm::Settings limits={})
        :name(std::move(label)),source(std::move(value)),seconds(time),loop(looping),settings(limits){}
};
struct Record {
    std::string name,portable;double seconds{};bool loop{};dm::Settings settings;
    bool source_unchanged{};std::optional<std::string> source_error;
    std::optional<skin::DeformResult> deformation;std::optional<dm::Result> derived;
    std::vector<dm::Triangle> triangles;
};
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
std::string saved(const io::Source&s){std::ostringstream out;out.imbue(std::locale::classic());s.save(out);return out.str();}
void number(double x){require(std::isfinite(x),"Nonfinite probe JSON value");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
void quoted(const std::string&s){
    constexpr char hex[]="0123456789abcdef";std::cout<<'"';
    for(unsigned char c:s){if(c=='"')std::cout<<"\\\"";else if(c=='\\')std::cout<<"\\\\";
        else if(c<0x20)std::cout<<"\\u00"<<hex[c>>4]<<hex[c&15];else std::cout<<char(c);}
    std::cout<<'"';
}
void settings_json(const dm::Settings&s){std::cout<<'['<<s.max_vertices<<','<<s.max_triangles<<','<<s.sqrt_refinements<<']';}
void positions_json(const std::vector<Vec3>&p){std::cout<<'[';for(std::size_t i=0;i<p.size();++i){if(i)std::cout<<',';std::cout<<'[';number(p[i].x);std::cout<<',';number(p[i].y);std::cout<<',';number(p[i].z);std::cout<<']';}std::cout<<']';}
void triangles_json(const std::vector<dm::Triangle>&t){std::cout<<'[';for(std::size_t i=0;i<t.size();++i){if(i)std::cout<<',';std::cout<<'['<<t[i][0]<<','<<t[i][1]<<','<<t[i][2]<<']';}std::cout<<']';}
void float_bits(const auto&values){std::cout<<'[';bool first=true;for(float x:values){if(!first)std::cout<<',';first=false;std::cout<<std::bit_cast<std::uint32_t>(x);}std::cout<<']';}
void interval_json(const pikapika::interval::Interval&i){std::cout<<'[';number(i.lower());std::cout<<',';number(i.upper());std::cout<<']';}
void bounds_json(const dm::Bounds3&b){std::cout<<'[';for(unsigned i=0;i<3;++i){if(i)std::cout<<',';interval_json(b[i]);}std::cout<<']';}
void derived_json(const dm::Result&r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"failedVertex\":";
    if(r.failed_vertex)std::cout<<*r.failed_vertex;else std::cout<<"null";
    std::cout<<",\"failedFace\":";if(r.failed_face)std::cout<<*r.failed_face;else std::cout<<"null";
    std::cout<<",\"positionsBits\":";if(r.geometry){std::cout<<'[';for(std::size_t i=0;i<r.geometry->positions.size();++i){if(i)std::cout<<',';float_bits(r.geometry->positions[i]);}std::cout<<']';}else std::cout<<"null";
    std::cout<<",\"triangles\":";if(r.geometry)triangles_json(r.geometry->triangles);else std::cout<<"null";
    std::cout<<",\"interleavedBits\":";if(r.geometry)float_bits(r.geometry->interleaved);else std::cout<<"null";
    std::cout<<",\"minimumBits\":";if(r.geometry)float_bits(r.geometry->minimum);else std::cout<<"null";
    std::cout<<",\"maximumBits\":";if(r.geometry)float_bits(r.geometry->maximum);else std::cout<<"null";
    std::cout<<",\"audits\":[";
    for(std::size_t i=0;i<r.audits.size();++i){if(i)std::cout<<',';const auto&a=r.audits[i];std::cout<<"{\"face\":"<<a.face<<",\"cross\":";bounds_json(a.cross);std::cout<<",\"squaredCross\":";interval_json(a.squared_cross);
        std::cout<<",\"normalized\":";if(a.normalized)bounds_json(*a.normalized);else std::cout<<"null";
        std::cout<<",\"normalBits\":";if(a.normal)float_bits(*a.normal);else std::cout<<"null";
        std::cout<<",\"normalError\":";if(a.normal_error){std::cout<<'[';for(unsigned axis=0;axis<3;++axis){if(axis)std::cout<<',';number((*a.normal_error)[axis]);}std::cout<<']';}else std::cout<<"null";
        std::cout<<",\"sqrtRefinements\":"<<a.sqrt_refinements<<",\"sqrtRefinementLimited\":"<<(a.sqrt_refinement_limited?"true":"false")<<'}';}
    std::cout<<"],\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtLimitedFaces\":"<<r.sqrt_limited_faces<<'}';
}
void deformation_json(const skin::DeformResult&r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"positions\":";if(r.positions)positions_json(*r.positions);else std::cout<<"null";
    std::cout<<",\"diagnostics\":[";for(std::size_t i=0;i<r.inverse_diagnostics.size();++i){if(i)std::cout<<',';const auto&d=r.inverse_diagnostics[i];std::cout<<"{\"id\":"<<d.bone_id<<",\"condition\":";if(d.linear_condition)number(*d.linear_condition);else std::cout<<"null";std::cout<<",\"residual\":";if(d.inverse_residual)number(*d.inverse_residual);else std::cout<<"null";std::cout<<",\"pivotFailure\":"<<(d.pivot_failure?"true":"false")<<'}';}
    std::cout<<"],\"weightResiduals\":[";for(std::size_t i=0;i<r.weight_residuals.size();++i){if(i)std::cout<<',';number(r.weight_residuals[i]);}std::cout<<"]}";
}
Record evaluate(const Case&c){
    Record r;r.name=c.name;r.portable=saved(c.source);r.seconds=c.seconds;r.loop=c.loop;r.settings=c.settings;r.triangles=c.source.mesh.triangles;
    try {r.deformation=c.source.sample(c.seconds,c.loop?pikapika::motion::Playback::loop:pikapika::motion::Playback::clamp);}
    catch(const std::exception&e){r.source_error=e.what();}
    if(r.deformation&&r.deformation->status==skin::Status::completed&&r.deformation->positions)
        r.derived=dm::prepare(*r.deformation->positions,c.source.mesh.triangles,c.settings);
    r.source_unchanged=r.portable==saved(c.source);require(r.source_unchanged,"Source saved bytes changed during sample/prepare");return r;
}
void record_json(const Record&r){
    std::cout<<"{\"name\":";quoted(r.name);std::cout<<",\"input\":{\"portable\":";quoted(r.portable);std::cout<<",\"seconds\":";number(r.seconds);std::cout<<",\"loop\":"<<(r.loop?"true":"false")<<",\"settings\":";settings_json(r.settings);
    std::cout<<"},\"sourceSavedUnchanged\":"<<(r.source_unchanged?"true":"false")<<",\"sourceError\":";if(r.source_error)quoted(*r.source_error);else std::cout<<"null";
    std::cout<<",\"deformation\":";if(r.deformation)deformation_json(*r.deformation);else std::cout<<"null";
    std::cout<<",\"derivedInput\":";if(r.derived){std::cout<<"{\"positions\":";positions_json(*r.deformation->positions);std::cout<<",\"triangles\":";triangles_json(r.triangles);std::cout<<",\"settings\":";settings_json(r.settings);std::cout<<'}';}else std::cout<<"null";
    std::cout<<",\"derived\":";if(r.derived)derived_json(*r.derived);else std::cout<<"null";std::cout<<'}';
}
std::vector<Case> fixtures(){
    std::vector<Case> out;const auto source=io::example();
    out.push_back({"default-t0",source,0});out.push_back({"default-t0.5",source,.5});out.push_back({"default-t1",source,1});out.push_back({"default-t2",source,2});out.push_back({"default-loop-t3",source,3,true});
    auto collapse=source;for(auto&w:collapse.influences)w={{7,1},{19,1}};collapse.motion.tracks[0].keys[1].pose.rotation={0,0,1,0};collapse.validate();out.push_back({"actual-lbs-half-turn-collapse",std::move(collapse),1});
    Case budget{"derived-face-budget",source,1};budget.settings.max_triangles=3;out.push_back(std::move(budget));
    budget={"derived-normal-budget",source,0};budget.settings.sqrt_refinements=1;out.push_back(std::move(budget));
    auto underflow=source;underflow.influences[0]={{7,std::numeric_limits<double>::denorm_min()},{19,std::numeric_limits<double>::max()}};underflow.validate();out.push_back({"source-weight-underflow",std::move(underflow),1});
    auto inverse=source;inverse.joints[0].inverse_bind[0]+=1e-4;inverse.validate();out.push_back({"source-inverse-quality",std::move(inverse),1});
    auto stale=source;stale.joints[0].rest_world[12]+=1e-12;stale.validate();out.push_back({"source-stale-rest",std::move(stale),1});return out;
}
void check_fixtures(const std::vector<Record>&r){
    require(r.size()==11,"Probe fixture count changed");
    for(unsigned i=0;i<5;++i)require(!r[i].source_error&&r[i].deformation&&r[i].deformation->status==skin::Status::completed&&r[i].derived&&r[i].derived->status==dm::Status::completed,"Default source through actual LBS/derived failed");
    const auto&collapse=r[5];require(collapse.deformation&&collapse.deformation->status==skin::Status::completed&&collapse.deformation->positions,"Actual LBS collapse did not complete deformation");
    for(const auto&p:*collapse.deformation->positions)require(p.x==1&&p.y==0&&p.z==0,"Independent half-turn LBS position mismatch");
    require(collapse.derived&&collapse.derived->status==dm::Status::degenerate&&!collapse.derived->geometry,"Actual LBS collapse not rejected by derived");
    require(r[6].derived&&r[6].derived->status==dm::Status::budget_exceeded,"Derived face budget fixture mismatch");
    require(r[7].derived&&r[7].derived->status==dm::Status::quality_unresolved,"Derived normal budget fixture mismatch");
    require(r[8].deformation&&r[8].deformation->status==skin::Status::numerical_failure&&!r[8].derived,"Normalization failure incorrectly reached derived");
    require(r[9].deformation&&r[9].deformation->status==skin::Status::ill_conditioned&&!r[9].derived,"Inverse quality failure incorrectly reached derived");
    require(r[10].source_error&&!r[10].deformation&&!r[10].derived,"Stale rest source incorrectly reached derived");
}
double seconds(const std::string&text){double out{};const auto parsed=std::from_chars(text.data(),text.data()+text.size(),out);require(parsed.ec==std::errc{}&&parsed.ptr==text.data()+text.size()&&std::isfinite(out)&&out>=0,"Seconds must be finite nonnegative numeric text");return out;}
int main(int argc,char**argv){
    try {std::cout.imbue(std::locale::classic());std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);std::vector<Record> out;
        if(argc==2&&std::string(argv[1])=="--fixtures"){for(const auto&c:fixtures())out.push_back(evaluate(c));check_fixtures(out);}
        else if((argc==4||argc==5)&&std::string(argv[1])=="sample"){
            require(argc!=5||std::string(argv[4])=="loop","Optional playback must be loop");std::ifstream file(std::filesystem::path(argv[2]),std::ios::binary);require(bool(file),"Cannot open binding source");
            out.push_back(evaluate({"file-sample",io::Source::load(file),seconds(argv[3]),argc==5}));
        }else throw std::invalid_argument("Usage: pikapika-derived-probe --fixtures | sample FILE SECONDS [loop]");
        std::cout<<"{\"schema\":1,\"fixtures\":[";for(std::size_t i=0;i<out.size();++i){if(i)std::cout<<',';record_json(out[i]);}std::cout<<"]}\n";return 0;
    }catch(const std::exception&e){std::cerr<<"ERROR "<<e.what()<<'\n';return 1;}
}
