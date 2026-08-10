#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <boost/multiprecision/cpp_int.hpp>

using boost::multiprecision::uint256_t;
using u128 = unsigned __int128;

static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;
static constexpr uint64_t SCALE = 281474976710656ULL;
static constexpr uint64_t C0 = 79781805157054ULL;
static constexpr uint64_t C1 = 216678499581515ULL;
static constexpr uint64_t C3 = 406990044804623ULL;

struct Mapping {
  int fd=-1; size_t bytes=0; const unsigned char* data=nullptr;
  explicit Mapping(const char* path) {
    fd=open(path,O_RDONLY); if(fd<0) throw std::runtime_error("open");
    struct stat st{}; if(fstat(fd,&st)!=0) throw std::runtime_error("stat");
    bytes=size_t(st.st_size);
    data=static_cast<const unsigned char*>(mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,fd,0));
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

static std::string u128s(u128 x){if(!x)return"0";std::string s;while(x){s.push_back(char('0'+x%10));x/=10;}std::reverse(s.begin(),s.end());return s;}
static uint256_t to256(u128 x){return (uint256_t(uint64_t(x>>64))<<64)|uint64_t(x);}
static std::string u256s(const uint256_t& x){return x.convert_to<std::string>();}
static u128 ceil_div(u128 n,u128 d){return n/d+(n%d!=0);}

struct Row {u128 L,P,A,R,slack,T,constant; unsigned kind;};
static Row row_at(const Mapping& m,uint64_t i){
  const uint64_t w=rd(m.data+4*i);
  const uint64_t wf=rd(m.data+4ULL*four_index(i));
  const unsigned kind=unsigned(i%3);
  Row z{}; z.kind=kind;
  z.L=u128(SCALE)*w;
  z.P=u128(C0)*wf;
  z.A=0;
  if(kind==0||kind==2){
    const uint32_t ai=kind==0?l1_aux(i):l3_aux(i);
    const uint64_t wa=std::min<uint64_t>(rd(m.data+4ULL*ai),
      std::min<uint64_t>(rd(m.data+4ULL*(ai+AUX)),rd(m.data+4ULL*(ai+2*AUX))));
    z.A=u128(kind==0?C1:C3)*wa;
  }
  z.R=z.P+z.A;
  z.slack=z.R-z.L;
  if(kind==2){z.T=2*z.P+z.A;z.constant=z.P;}
  else {z.T=2*z.R;z.constant=z.R;}
  return z;
}

int main(int argc,char**argv){
  if(argc!=2){std::cerr<<"usage: checker WEIGHTS\n";return 2;}
  Mapping m(argv[1]); if(m.bytes!=4ULL*N){std::cerr<<"bad size\n";return 3;}
  uint64_t original_failures=0;
  u128 maxB=2; uint64_t maxBidx=0; unsigned maxBkind=0;
  u128 minSlack=~u128(0);uint64_t minSlackIdx=0;
  for(uint64_t i=0;i<N;++i){
    Row z=row_at(m,i);
    if(z.R<z.L){++original_failures;continue;}
    if(z.slack<minSlack){minSlack=z.slack;minSlackIdx=i;}
    u128 req=ceil_div(z.T,z.slack);
    if(req>maxB){maxB=req;maxBidx=i;maxBkind=z.kind;}
  }
  if(original_failures){std::cout<<"ORIGINAL_FAILURES="<<original_failures<<"\n";return 4;}
  const u128 B=maxB,A=B-1;
  const uint256_t b=to256(B),a=to256(A),b2=b*b,a2=a*a,ab=a*b;
  uint64_t failures=0,minMarginIdx=0;unsigned minMarginKind=0;
  uint256_t minMargin=~uint256_t(0);
  for(uint64_t i=0;i<N;++i){
    Row z=row_at(m,i);
    uint256_t lhs=b2*to256(z.L);
    uint256_t rhs=(z.kind==2)?a2*to256(z.P)+ab*to256(z.A):a2*to256(z.R);
    if(lhs>rhs){
      ++failures;
      if(failures<=10)std::cerr<<"FAIL index="<<i<<" deficit="<<u256s(lhs-rhs)<<"\n";
    }else{
      uint256_t margin=rhs-lhs;
      if(margin<minMargin){minMargin=margin;minMarginIdx=i;minMarginKind=z.kind;}
    }
  }
  std::cout<<"GAMMA_NUM=14551\nGAMMA_DEN=16000\n";
  std::cout<<"ROWS="<<N<<"\nORIGINAL_FAILURES="<<original_failures<<"\n";
  std::cout<<"MIN_ORIGINAL_SLACK="<<u128s(minSlack)<<"\nMIN_ORIGINAL_SLACK_INDEX="<<minSlackIdx<<"\n";
  std::cout<<"SAFE_Q_DEN="<<u128s(B)<<"\nSAFE_Q_NUM="<<u128s(A)<<"\n";
  std::cout<<"SAFE_DEN_CRITICAL_INDEX="<<maxBidx<<"\nSAFE_DEN_CRITICAL_KIND="<<maxBkind<<"\n";
  std::cout<<"Q_WEIGHTED_FAILURES="<<failures<<"\n";
  if(!failures){
    std::cout<<"MIN_Q_MARGIN="<<u256s(minMargin)<<"\nMIN_Q_MARGIN_INDEX="<<minMarginIdx<<"\nMIN_Q_MARGIN_KIND="<<minMarginKind<<"\n";
    std::cout<<"AUTO_SAFE_Q_EXACT_CERTIFICATE=PASS\n";return 0;
  }
  std::cout<<"AUTO_SAFE_Q_EXACT_CERTIFICATE=FAIL\n";return 1;
}
