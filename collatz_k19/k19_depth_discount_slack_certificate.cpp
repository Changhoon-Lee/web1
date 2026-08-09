#include <algorithm>
#include <array>
#include <boost/multiprecision/cpp_int.hpp>
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

using boost::multiprecision::cpp_int;
static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;
static constexpr uint64_t S=281474976710656ULL;
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr uint64_t EXPECTED_MIN_SLACK=1488314ULL;
static constexpr uint64_t EXPECTED_MAX_WEIGHT=4166117961ULL;

struct Mapping{int fd=-1;size_t bytes=0;const unsigned char*data=nullptr;
 explicit Mapping(const char*p){fd=open(p,O_RDONLY);if(fd<0)throw std::runtime_error("open");struct stat st{};if(fstat(fd,&st))throw std::runtime_error("stat");bytes=size_t(st.st_size);data=(const unsigned char*)mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,fd,0);if(data==MAP_FAILED)throw std::runtime_error("mmap");}
 ~Mapping(){if(data&&data!=MAP_FAILED)munmap((void*)data,bytes);if(fd>=0)close(fd);}};
static uint32_t rd(const unsigned char*p){uint32_t v;std::memcpy(&v,p,4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
 v=__builtin_bswap32(v);
#endif
 return v;}
static uint64_t residue(uint64_t i){return 3*i+2;}
static uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
static std::string u128(unsigned __int128 x){if(!x)return"0";std::string s;while(x){s.push_back(char('0'+x%10));x/=10;}std::reverse(s.begin(),s.end());return s;}

int main(int argc,char**argv){
 if(argc!=2){std::cerr<<"usage: cert WEIGHTS\n";return 2;}
 Mapping m(argv[1]);if(m.bytes!=4ULL*N){std::cerr<<"bad size\n";return 3;}
 uint64_t maxw=0,maxwi=0,minidx=0,fail=0;
 unsigned __int128 minslack=~(unsigned __int128)0,maxrhs=0;
 for(uint64_t i=0;i<N;++i){
  uint64_t w=rd(m.data+4*i);if(w>maxw){maxw=w;maxwi=i;}
  uint64_t wf=rd(m.data+4ULL*four_index(i));
  unsigned kind=unsigned(i%3);uint64_t wa=0;
  if(kind==0||kind==2){uint32_t ai=kind==0?l1_aux(i):l3_aux(i);wa=std::min<uint64_t>(rd(m.data+4ULL*ai),std::min<uint64_t>(rd(m.data+4ULL*(ai+AUX)),rd(m.data+4ULL*(ai+2*AUX))));}
  unsigned __int128 lhs=(unsigned __int128)S*w;
  unsigned __int128 rhs=(unsigned __int128)C0*wf;
  if(kind==0)rhs+=(unsigned __int128)C1*wa;else if(kind==2)rhs+=(unsigned __int128)C3*wa;
  if(rhs<lhs)++fail;else if(rhs-lhs<minslack){minslack=rhs-lhs;minidx=i;}
  maxrhs=std::max(maxrhs,rhs);
 }
 cpp_int b("100000000000000000000");
 cpp_int a=b-1;
 cpp_int rmax=cpp_int(C0+C3)*EXPECTED_MAX_WEIGHT;
 cpp_int left=(b*b-a*a)*rmax;
 cpp_int right=cpp_int(EXPECTED_MIN_SLACK)*b*b;
 bool scalar=left<=right;
 bool pass=fail==0&&minslack>=EXPECTED_MIN_SLACK&&maxw<=EXPECTED_MAX_WEIGHT&&maxrhs<=rmax.convert_to<unsigned __int128>()&&scalar;
 std::cout<<"ROWS="<<N<<"\nROW_FAILURES="<<fail
  <<"\nMIN_SLACK="<<u128(minslack)<<"\nMIN_SLACK_INDEX="<<minidx
  <<"\nMAX_WEIGHT="<<maxw<<"\nMAX_WEIGHT_INDEX="<<maxwi
  <<"\nMAX_RHS="<<u128(maxrhs)
  <<"\nQ_NUM="<<a<<"\nQ_DEN="<<b
  <<"\nRMAX_BOUND="<<rmax
  <<"\nSCALAR_LEFT="<<left<<"\nSCALAR_RIGHT="<<right
  <<"\nSCALAR_SLACK="<<(right-left)
  <<"\nSCALAR_INEQUALITY="<<(scalar?"PASS":"FAIL")
  <<"\nDEPTH_DISCOUNT_Q_LT_ONE=PASS"
  <<"\nEXACT_DEPTH_DISCOUNT_CERTIFICATE="<<(pass?"PASS":"FAIL")<<"\n";
 return pass?0:4;
}
