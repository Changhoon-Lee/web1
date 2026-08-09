#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;

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

struct Candidate {
  long double gamma=0,c0=0,c1=0,c3=0,maxq=0;
  uint64_t index=0; int row=-1;
  long double wf=0,wa=0,w=0;
};

int main(int argc,char**argv){
  if(argc!=2){std::cerr<<"usage: scan WEIGHTS\n";return 2;}
  Mapping m(argv[1]); if(m.bytes!=4ULL*N){std::cerr<<"bad size\n";return 3;}
  const std::array<long double,6> gs={
    14551.0L/16000.0L,0.907L,0.905L,0.903L,0.902L,0.9011L};
  std::array<Candidate,gs.size()> cs{};
  for(size_t j=0;j<gs.size();++j){
    cs[j].gamma=gs[j];
    cs[j].c0=std::pow(2.0L,-2.0L*gs[j]);
    cs[j].c1=std::pow(3.0L/4.0L,gs[j]);
    cs[j].c3=std::pow(3.0L/2.0L,gs[j]);
  }
  for(uint64_t i=0;i<N;++i){
    const long double w=rd(m.data+4*i);
    const long double wf=rd(m.data+4ULL*four_index(i));
    const unsigned kind=unsigned(i%3);
    long double wa=0;
    if(kind==0 || kind==2){
      const uint32_t ai=kind==0?l1_aux(i):l3_aux(i);
      wa=std::min<long double>(rd(m.data+4ULL*ai),
        std::min<long double>(rd(m.data+4ULL*(ai+AUX)),
          rd(m.data+4ULL*(ai+2*AUX))));
    }
    for(auto& c:cs){
      long double req=0;
      if(kind==0){
        req=std::sqrt(w/(c.c0*wf+c.c1*wa));
      } else if(kind==1){
        req=std::sqrt(w/(c.c0*wf));
      } else {
        const long double A=c.c0*wf, B=c.c3*wa;
        req=(-B+std::sqrt(B*B+4*A*w))/(2*A);
      }
      if(req>c.maxq){c.maxq=req;c.index=i;c.row=int(kind);c.wf=wf;c.wa=wa;c.w=w;}
    }
  }
  std::cout<<std::setprecision(22);
  const long double h=25.0L/8.0L;
  for(const auto& c:cs){
    const long double kappa=std::pow(h,-(1-c.gamma))+8.0L/75.0L;
    std::cout<<"GAMMA="<<c.gamma
             <<" REQUIRED_Q="<<c.maxq
             <<" FEASIBLE_Q_LT_ONE="<<(c.maxq<1?1:0)
             <<" CRITICAL_INDEX="<<c.index
             <<" ROW="<<c.row
             <<" W="<<c.w<<" WF="<<c.wf<<" WA="<<c.wa
             <<" KAPPA_WORST="<<kappa
             <<" LOCAL_GAIN_POSITIVE="<<(kappa>1?1:0)<<"\n";
  }
  return 0;
}
