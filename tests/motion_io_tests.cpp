#include "pikapika/motion_io.hpp"
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace pikapika;
namespace {
unsigned passed{};
void require(bool v,const char* s){if(!v)throw std::runtime_error(s);}
void test(const char* name,const std::function<void()>& fn){fn();++passed;std::cout<<"PASS "<<name<<'\n';}
void reject(const std::function<void()>& fn){bool rejected=false;try{fn();}catch(const std::invalid_argument&){rejected=true;}require(rejected,"Expected source rejection");}
motion_io::Source source(){motion_io::Source s;s.name="Original \"motion\" \\ data";s.clip_name="Reach";s.duration=2;s.bones={{30,20,{{1,0,0},{},{1,1,1}}},{10,0,{}},{20,10,{{0,1,0},{},{1,1,1}}}};s.bone_names={"Tip",std::string("Root ")+"\xe8\x85\x95","Arm"};s.tracks={{20,motion::Interpolation::linear,{{0,{{0,1,0},{},{1,1,1}}},{1,{{0,1,0},{0,0,1,1},{1,1,1}}},{2,{{0,1,0},{},{1,1,1}}}}}};return s;}
std::string text(const motion_io::Source& s){std::ostringstream out;s.save(out);return out.str();}
motion_io::Source load(const std::string& s){std::istringstream in(s);return motion_io::Source::load(in);}
}
int main(){try{
 test("portable roundtrip retains names IDs ordering keys and binary64 source values",[]{const auto s=source();const auto a=text(s),b=text(load(a));require(a==b,"Canonical portable bytes changed");const auto t=load(a);require(t.bones[0].id==30&&t.bone_names==s.bone_names&&t.name==s.name&&t.tracks[0].keys[1].pose.rotation.z==1,"Source metadata lost");});
 test("portable source samples parent-first FK without reordering author bones",[]{const auto r=load(text(source())).sample(1);require(r.status==motion::Status::completed&&r.pose.has_value(),"FK failed");require(r.pose->evaluation_order==std::vector<std::uint64_t>({10,20,30}),"Wrong evaluation order");require(r.pose->bones[0].id==30,"Original source order lost");const auto& m=r.pose->bones[0].world_matrix;require(std::abs(m[12])<1e-12&&std::abs(m[13]-2)<1e-12,"Known two-link position");});
 test("source quaternion magnitudes are retained while sampled quaternions normalize",[]{auto s=source();s.bones[0].rest.rotation={0,0,0,1e300};s.tracks[0].keys[0].pose.rotation={0,0,0,std::numeric_limits<double>::denorm_min()};const auto t=load(text(s));require(t.bones[0].rest.rotation.w==1e300&&t.tracks[0].keys[0].pose.rotation.w==std::numeric_limits<double>::denorm_min(),"Quaternion source magnitude changed");require(t.sample(0).status==motion::Status::completed,"Extreme quaternion sample failed");});
 test("portable rejects trailing input unsupported versions and truncated source",[]{auto a=text(source());reject([&]{load(a+"junk\n");});a.replace(a.find("motion 1"),8,"motion 2");reject([&]{load(a);});reject([&]{load("pikapika_motion 1\nname \"x\"\nbones 1\nbone");});});
 test("portable admits no excessive declared count or key allocation",[]{reject([]{load("pikapika_motion 1 name \"x\" bones 129");});reject([]{load("pikapika_motion 1 name \"x\" bones 1 bone 1 0 \"r\" 0 0 0 0 0 0 1 1 1 1 clip \"c\" 1 129");});reject([]{load("pikapika_motion 1 name \"x\" bones 1 bone 1 0 \"r\" 0 0 0 0 0 0 1 1 1 1 clip \"c\" 1 1 track 1 linear 4097");});});
 test("invalid graph and later invalid key fail before changing output stream",[]{auto s=source();s.bones[0].parent_id=999;std::ostringstream out;out<<"sentinel";reject([&]{s.save(out);});require(out.str()=="sentinel","Invalid save changed output");s=source();s.tracks[0].keys.back().pose.scale.x=0;reject([&]{text(s);});});
 test("portable decimal grammar rejects overflow underflow and nonfinite values",[]{const auto valid=text(source());for(const auto& value:{"nan","inf","1e9999","1e-9999"}){auto a=valid;const auto offset=a.find("clip \"Reach\" 2 ")+13;a.replace(offset,1,value);reject([&]{load(a);});}});
 test("portable source names reject invalid UTF8 controls and unsupported escapes",[]{for(const auto& bad:{std::string(1,char(0xff)),std::string("\xc0\x80"),std::string("\xed\xa0\x80"),std::string("bad\nname")}){auto s=source();s.name=bad;reject([&]{text(s);});}reject([]{load("pikapika_motion 1 name \"bad\\q\" bones 0");});});
 test("owned tracks remain independent after copy mutation save and reload",[]{auto a=source(),b=a;b.tracks[0].keys[1].pose.position.x=3;const auto c=load(text(b));require(a.tracks[0].keys[1].pose.position.x==0&&c.tracks[0].keys[1].pose.position.x==3,"Owned source alias");});
 test("sample failures retain editable structurally valid source and publish no pose",[]{auto s=source();const auto original=text(s);const auto r=s.sample(-1);require(r.status==motion::Status::invalid_input&&!r.pose&&text(s)==original,"Failed sample mutated source or returned pose");});
 test("empty tracks return rest pose and codec keeps the empty clip",[]{auto s=source();s.tracks.clear();const auto t=load(text(s));require(t.tracks.empty(),"Empty clip changed");const auto r=t.sample(1);require(r.status==motion::Status::completed&&r.pose->bones[0].world_matrix[12]==1,"Rest FK changed");});
 test("positive nonuniform scale is saved without decomposing world shear",[]{auto s=source();s.bones[1].rest.scale={2,1,1};s.tracks.clear();s.bones[2].rest.rotation={0,0,1,2};const auto r=load(text(s)).sample(0);require(r.status==motion::Status::completed,"Shear sample failed");const auto& m=r.pose->bones[2].world_matrix;const double cross=m[0]*m[4]+m[1]*m[5]+m[2]*m[6];require(std::abs(cross+36./25)<1e-12,"Shear was discarded");});
 std::cout<<"Motion IO: "<<passed<<" groups\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
