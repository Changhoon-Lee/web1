#include <algorithm>
#include <array>
#include <boost/multiprecision/cpp_int.hpp>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

using boost::multiprecision::cpp_int;
static constexpr uint64_t N = 387420489ULL; // 3^18
static constexpr uint64_t A = 129140163ULL; // 3^17
static constexpr uint64_t DEFAULT_STATE_CAP = 20000000ULL;
static const long double F0 = std::ldexp(79781805157054.0L, -48);
static const long double F1 = std::ldexp(216678499581515.0L, -48);
static const long double F3 = std::ldexp(406990044804623.0L, -48);
static constexpr long double SAT = 1.0L;
static long double down_mul(long double x, long double y) {
  return std::nextafterl(x * y, -std::numeric_limits<long double>::infinity());
}
static long double down_add(long double x, long double y) {
  return std::nextafterl(x + y, -std::numeric_limits<long double>::infinity());
}

struct Mapping {
  int fd = -1;
  size_t bytes = 0;
  const unsigned char* data = nullptr;
  explicit Mapping(const char* path) {
    fd = open(path, O_RDONLY);
    if (fd < 0) throw std::runtime_error("open failed");
    struct stat st{};
    if (fstat(fd, &st) != 0) throw std::runtime_error("fstat failed");
    bytes = static_cast<size_t>(st.st_size);
    data = static_cast<const unsigned char*>(
      mmap(nullptr, bytes, PROT_READ, MAP_PRIVATE, fd, 0));
    if (data == MAP_FAILED) throw std::runtime_error("mmap failed");
  }
  Mapping(const Mapping&) = delete;
  Mapping& operator=(const Mapping&) = delete;
  ~Mapping() {
    if (data && data != MAP_FAILED) munmap((void*)data, bytes);
    if (fd >= 0) close(fd);
  }
};

struct Shift { uint16_t a; uint16_t b; };
struct Label { uint32_t index; Shift s; long double multiplier; };

static cpp_int ipow(unsigned base, unsigned exp) {
  cpp_int out = 1, b = base;
  while (exp) {
    if (exp & 1u) out *= b;
    b *= b;
    exp >>= 1u;
  }
  return out;
}

static bool value_nonnegative(Shift s) {
  return ipow(3, s.a) >= ipow(2, s.b);
}

static bool value_less(Shift x, Shift y) {
  const int da = int(x.a) - int(y.a);
  const int db = int(x.b) - int(y.b);
  if (da == 0) return db > 0;
  if (db == 0) return da < 0;
  if (da > 0 && db < 0) return false;
  if (da < 0 && db > 0) return true;
  if (da > 0) return ipow(3, unsigned(da)) < ipow(2, unsigned(db));
  return ipow(3, unsigned(-da)) > ipow(2, unsigned(-db));
}

struct Engine {
  const unsigned char* potential;
  uint64_t state_cap = DEFAULT_STATE_CAP;
  uint64_t states = 0;
  uint64_t terminals = 0;
  uint64_t early_saturated = 0;
  uint32_t max_depth = 0;
  bool capped = false;

  uint8_t pot(uint32_t i) const { return potential[i]; }
  static uint32_t principal(uint32_t i) {
    return uint32_t((4ULL * i + 2ULL) % N);
  }
  static std::array<uint32_t, 3> d1(uint32_t i) {
    const uint64_t base = (4ULL * i + 2ULL) % N;
    const uint64_t aux = (base - 2ULL) / 3ULL;
    return {uint32_t(aux), uint32_t(aux + A), uint32_t(aux + 2 * A)};
  }
  static std::array<uint32_t, 3> d3(uint32_t i) {
    const uint64_t base = (2ULL * i + 1ULL) % N;
    const uint64_t aux = (base - 2ULL) / 3ULL;
    return {uint32_t(aux), uint32_t(aux + A), uint32_t(aux + 2 * A)};
  }
  int fallback(const std::array<uint32_t,3>& c) const {
    const uint8_t v0=pot(c[0]),v1=pot(c[1]),v2=pot(c[2]);
    if(v0<=v1 && v0<=v2) return 0;
    if(v1<=v2) return 1;
    return 2;
  }
  static bool dominated(const Label& child,const std::vector<Label>& path) {
    if(!value_nonnegative(child.s)) return false;
    for(const auto& e:path) {
      if(e.index==child.index && value_less(e.s,child.s)) return true;
    }
    return false;
  }

  long double coeff_dfs(Label cur,std::vector<Label>& path,uint32_t depth) {
    if (++states > state_cap) { capped=true; return 0.0L; }
    max_depth=std::max(max_depth,depth);
    if(!value_nonnegative(cur.s)) { ++terminals; return cur.multiplier; }
    path.push_back(cur);
    Label pc{principal(cur.index),Shift{cur.s.a,uint16_t(cur.s.b+2)},down_mul(cur.multiplier,F0)};
    long double principal_value=coeff_dfs(pc,path,depth+1);
    if(capped){path.pop_back();return 0.0L;}
    if(principal_value>=SAT){++early_saturated;path.pop_back();return SAT;}
    const unsigned row=cur.index%3U;
    if(row==1U){path.pop_back();return principal_value;}
    const auto ci = row==0U?d1(cur.index):d3(cur.index);
    const long double factor=row==0U?F1:F3;
    std::array<Label,3> children;
    std::array<bool,3> keep{};
    int kept=0;
    for(int q=0;q<3;q++){
      children[q]=Label{ci[q],row==0U?Shift{uint16_t(cur.s.a+1),uint16_t(cur.s.b+2)}:Shift{uint16_t(cur.s.a+1),uint16_t(cur.s.b+1)},down_mul(cur.multiplier,factor)};
      keep[q]=!dominated(children[q],path);
      kept+=keep[q]?1:0;
    }
    if(kept==0) keep[fallback(ci)]=true;
    long double aux=std::numeric_limits<long double>::infinity();
    for(int q=0;q<3;q++) if(keep[q]) {
      long double v=coeff_dfs(children[q],path,depth+1);
      if(capped){path.pop_back();return 0.0L;}
      aux=std::min(aux,v);
    }
    path.pop_back();
    long double out=down_add(principal_value,aux);
    return out>=SAT?SAT:out;
  }

  long double root_coeff(uint32_t root) {
    states=terminals=early_saturated=0;max_depth=0;capped=false;
    std::vector<Label> path;path.reserve(128);
    return coeff_dfs(Label{root,Shift{0,0},1.0L},path,0);
  }
};

int main(int argc,char**argv){
  if(argc<2||argc>4){std::cerr<<"usage: probe POTENTIAL [STATE_CAP] [SAMPLE_COUNT]\n";return 2;}
  Mapping pm(argv[1]); if(pm.bytes!=N){std::cerr<<"bad potential size\n";return 3;}
  Engine e{pm.data};
  if(argc>=3)e.state_cap=std::stoull(argv[2]);
  const int sample_count=argc>=4?std::stoi(argv[3]):128;
  std::set<uint32_t> roots={0U,1U,2U,3U,4U,5U,13U,37U,1000U,1000000U,uint32_t(N/4),uint32_t(N/2),uint32_t(3*N/4),uint32_t(N-1)};
  std::mt19937_64 rng(0x554e574549474854ULL);
  for(int k=0;k<sample_count;k++)roots.insert(uint32_t(rng()%N));
  uint64_t pass=0,fail=0,capped=0;long double minv=2.0L,sum=0.0L;
  std::cout<<std::setprecision(21)<<"F0="<<F0<<"\nF1="<<F1<<"\nF3="<<F3<<"\nSTATE_CAP="<<e.state_cap<<"\n";
  for(uint32_t root:roots){
    long double v=e.root_coeff(root);
    if(e.capped)++capped;else if(v>=1.0L)++pass;else ++fail;
    if(!e.capped){minv=std::min(minv,v);sum+=v;}
    std::cout<<"ROOT="<<root<<" COEFF_LOWER_DIAGNOSTIC="<<v<<" PASS="<<(!e.capped&&v>=1.0L?1:0)<<" STATES="<<e.states<<" TERMINALS="<<e.terminals<<" MAX_DEPTH="<<e.max_depth<<" EARLY_SATURATED="<<e.early_saturated<<" CAPPED="<<(e.capped?1:0)<<"\n";
  }
  std::cout<<"ROOTS="<<roots.size()<<"\nPASS_COUNT="<<pass<<"\nFAIL_COUNT="<<fail<<"\nCAPPED_COUNT="<<capped<<"\nMIN_COMPLETE_COEFF="<<minv<<"\nMEAN_COMPLETE_COEFF="<<(pass+fail?sum/(pass+fail):0.0L)<<"\n";
  return 0;
}
