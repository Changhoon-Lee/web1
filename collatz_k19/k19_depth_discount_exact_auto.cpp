#include <algorithm>
#include <array>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/multiprecision/cpp_int.hpp>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

using boost::multiprecision::cpp_dec_float_100;
using boost::multiprecision::cpp_int;

static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;
static constexpr uint64_t SCALE = 1ULL << 48;
static constexpr uint64_t QDEN = 1000000000ULL;

struct Mapping {
  int fd=-1; size_t bytes=0; const unsigned char* data=nullptr;
  explicit Mapping(const char* path) {
    fd=open(path,O_RDONLY); if(fd<0) throw std::runtime_error("open");
    struct stat st{}; if(fstat(fd,&st)!=0) throw std::runtime_error("stat");
    bytes=size_t(st.st_size);
    data=static_cast<const unsigned char*>(
      mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,fd,0));
    if(data==MAP_FAILED) throw std::runtime_error("mmap");
  }
  ~Mapping(){if(data&&data!=MAP_FAILED)munmap((void*)data,bytes);if(fd>=0)close(fd);}
};
static uint32_t rd(const unsigned char* p){uint32_t v;std::memcpy(&v,p,4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  v=__builtin_bswap32(v);
#endif
  return v;}
static uint64_t residue(uint64_t i){return 3*i+2;}
static uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
static cpp_int ipow(cpp_int b,uint64_t e){cpp_int r=1;while(e){if(e&1)r*=b;b*=b;e>>=1;}return r;}
static std::string u128str(unsigned __int128 x){if(!x)return"0";std::string s;while(x){s.push_back(char('0'+x%10));x/=10;}std::reverse(s.begin(),s.end());return s;}

struct Candidate {
  uint64_t p=0,d=1;
  long double gamma=0,c0=0,c1=0,c3=0,maxq=0;
  uint64_t criticalIndex=0;
  int criticalRow=-1;
  uint64_t qnum=0,C0=0,C1=0,C3=0;
  bool qFeasible=false,powerPass=false;
  uint64_t failures=0,minIndex=0;
  unsigned __int128 minSlack=~(unsigned __int128)0;
};

static bool c0bound(uint64_t C,const Candidate& c){
  return ipow(cpp_int(C),c.d)*ipow(cpp_int(QDEN),2*c.d)*ipow(cpp_int(2),2*c.p)
    <= ipow(cpp_int(SCALE),c.d)*ipow(cpp_int(c.qnum),2*c.d);
}
static bool c1bound(uint64_t C,const Candidate& c){
  return ipow(cpp_int(C),c.d)*ipow(cpp_int(QDEN),2*c.d)*ipow(cpp_int(2),2*c.p)
    <= ipow(cpp_int(SCALE),c.d)*ipow(cpp_int(c.qnum),2*c.d)*ipow(cpp_int(3),c.p);
}
static bool c3bound(uint64_t C,const Candidate& c){
  return ipow(cpp_int(C),c.d)*ipow(cpp_int(QDEN),c.d)*ipow(cpp_int(2),c.p)
    <= ipow(cpp_int(SCALE),c.d)*ipow(cpp_int(c.qnum),c.d)*ipow(cpp_int(3),c.p);
}

int main(int argc,char**argv){
  if(argc!=2){std::cerr<<"usage: cert WEIGHTS\n";return 2;}
  Mapping m(argv[1]); if(m.bytes!=4ULL*N){std::cerr<<"bad size\n";return 3;}
  std::array<Candidate,4> cs{{
    {181,200},{903,1000},{451,500},{9011,10000}
  }};
  for(auto& c:cs){
    c.gamma=(long double)c.p/(long double)c.d;
    c.c0=std::pow(2.0L,-2.0L*c.gamma);
    c.c1=std::pow(3.0L/4.0L,c.gamma);
    c.c3=std::pow(3.0L/2.0L,c.gamma);
  }
  // Pass 1: determine the real-coefficient q threshold for the fixed K19 vector.
  for(uint64_t i=0;i<N;++i){
    const long double w=rd(m.data+4*i);
    const long double wf=rd(m.data+4ULL*four_index(i));
    const unsigned kind=unsigned(i%3);
    long double wa=0;
    if(kind==0 || kind==2){
      const uint32_t ai=kind==0?l1_aux(i):l3_aux(i);
      wa=std::min<long double>(rd(m.data+4ULL*ai),
        std::min<long double>(rd(m.data+4ULL*(ai+AUX)),rd(m.data+4ULL*(ai+2*AUX))));
    }
    for(auto& c:cs){
      long double req;
      if(kind==0) req=std::sqrt(w/(c.c0*wf+c.c1*wa));
      else if(kind==1) req=std::sqrt(w/(c.c0*wf));
      else {
        const long double A=c.c0*wf,B=c.c3*wa;
        req=(-B+std::sqrt(B*B+4*A*w))/(2*A);
      }
      if(req>c.maxq){c.maxq=req;c.criticalIndex=i;c.criticalRow=int(kind);}
    }
  }
  // Rational q and exact dyadic coefficient lower bounds.
  for(auto& c:cs){
    const long double padded=c.maxq+5e-8L;
    c.qnum=(uint64_t)std::ceil(padded*(long double)QDEN);
    c.qFeasible=c.qnum<QDEN;
    if(!c.qFeasible) continue;
    const cpp_dec_float_100 g=cpp_dec_float_100(c.p)/c.d;
    const cpp_dec_float_100 q=cpp_dec_float_100(c.qnum)/QDEN;
    auto floorSafe=[](const cpp_dec_float_100& x)->uint64_t{
      uint64_t v=floor(x).convert_to<uint64_t>();
      return v>16?v-16:0;
    };
    c.C0=floorSafe(cpp_dec_float_100(SCALE)*q*q*pow(cpp_dec_float_100(2),-2*g));
    c.C1=floorSafe(cpp_dec_float_100(SCALE)*q*q*pow(cpp_dec_float_100(3)/4,g));
    c.C3=floorSafe(cpp_dec_float_100(SCALE)*q*pow(cpp_dec_float_100(3)/2,g));
    while(c.C0 && !c0bound(c.C0,c)) --c.C0;
    while(c.C1 && !c1bound(c.C1,c)) --c.C1;
    while(c.C3 && !c3bound(c.C3,c)) --c.C3;
    c.powerPass=c0bound(c.C0,c)&&c1bound(c.C1,c)&&c3bound(c.C3,c);
  }
  // Pass 2: exact 128-bit row verification.
  for(uint64_t i=0;i<N;++i){
    const uint64_t w=rd(m.data+4*i);
    const uint64_t wf=rd(m.data+4ULL*four_index(i));
    const unsigned kind=unsigned(i%3);
    uint64_t wa=0;
    if(kind==0 || kind==2){
      const uint32_t ai=kind==0?l1_aux(i):l3_aux(i);
      wa=std::min<uint64_t>(rd(m.data+4ULL*ai),
        std::min<uint64_t>(rd(m.data+4ULL*(ai+AUX)),rd(m.data+4ULL*(ai+2*AUX))));
    }
    for(auto& c:cs){
      if(!c.qFeasible||!c.powerPass) continue;
      const unsigned __int128 lhs=(unsigned __int128)SCALE*w;
      unsigned __int128 rhs=(unsigned __int128)c.C0*wf;
      if(kind==0) rhs+=(unsigned __int128)c.C1*wa;
      else if(kind==2) rhs+=(unsigned __int128)c.C3*wa;
      if(rhs<lhs) ++c.failures;
      else if(rhs-lhs<c.minSlack){c.minSlack=rhs-lhs;c.minIndex=i;}
    }
  }
  std::cout<<std::setprecision(22);
  const long double h=25.0L/8.0L;
  for(const auto& c:cs){
    const long double kappa=std::pow(h,-(1-c.gamma))+8.0L/75.0L;
    std::cout<<"GAMMA_NUM="<<c.p<<" GAMMA_DEN="<<c.d
      <<" GAMMA="<<c.gamma
      <<" REQUIRED_Q="<<c.maxq
      <<" Q_NUM="<<c.qnum<<" Q_DEN="<<QDEN
      <<" Q_LT_ONE="<<(c.qFeasible?1:0)
      <<" C0="<<c.C0<<" C1="<<c.C1<<" C3="<<c.C3
      <<" POWER_BOUNDS="<<(c.powerPass?"PASS":"FAIL")
      <<" ROW_FAILURES="<<c.failures
      <<" MIN_SLACK="<<(c.minSlack==~(unsigned __int128)0?"NA":u128str(c.minSlack))
      <<" MIN_INDEX="<<c.minIndex
      <<" CRITICAL_SCAN_INDEX="<<c.criticalIndex
      <<" CRITICAL_SCAN_ROW="<<c.criticalRow
      <<" KAPPA_WORST="<<kappa
      <<" LOCAL_GAIN_POSITIVE="<<(kappa>1?1:0)
      <<" EXACT_CERTIFICATE="<<((c.qFeasible&&c.powerPass&&c.failures==0)?"PASS":"FAIL")
      <<"\n";
  }
  return 0;
}
