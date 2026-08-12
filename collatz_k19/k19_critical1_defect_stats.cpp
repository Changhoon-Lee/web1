#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

using i128 = __int128_t;
using u128 = __uint128_t;
static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;

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
static std::string ustr(u128 x){if(!x)return"0";std::string s;while(x){s.push_back(char('0'+x%10));x/=10;}std::reverse(s.begin(),s.end());return s;}
static std::string istr(i128 x){if(x<0)return"-"+ustr(u128(-x));return ustr(u128(x));}

int main(int argc,char**argv){
 if(argc!=2){std::cerr<<"usage: stats WEIGHTS\n";return 2;}
 Mapping m(argv[1]);if(m.bytes!=4ULL*N){std::cerr<<"bad size\n";return 3;}
 std::array<u128,3> lhs{},rhs{},positive{},negative{},sumw{},sumwf{},sumwa{};
 std::array<uint64_t,3> pass{},fail{},equal{};
 std::array<int64_t,3> minDef{INT64_MAX,INT64_MAX,INT64_MAX};
 std::array<int64_t,3> maxDef{INT64_MIN,INT64_MIN,INT64_MIN};
 std::array<uint64_t,3> minIdx{},maxIdx{};
 for(uint64_t i=0;i<N;++i){
   uint64_t wi=rd(m.data+4*i),wf=rd(m.data+4ULL*four_index(i));
   unsigned k=unsigned(i%3);uint64_t wa=0,c=0;
   if(k==0||k==2){uint32_t q=k==0?l1_aux(i):l3_aux(i);wa=std::min<uint64_t>(rd(m.data+4ULL*q),std::min<uint64_t>(rd(m.data+4ULL*(q+AUX)),rd(m.data+4ULL*(q+2*AUX))));c=k==0?3:6;}
   uint64_t L=4*wi,R=wf+c*wa;
   int64_t d=int64_t(R)-int64_t(L);
   lhs[k]+=L;rhs[k]+=R;sumw[k]+=wi;sumwf[k]+=wf;sumwa[k]+=wa;
   if(d>0){++pass[k];positive[k]+=uint64_t(d);}else if(d<0){++fail[k];negative[k]+=uint64_t(-d);}else ++equal[k];
   if(d<minDef[k]){minDef[k]=d;minIdx[k]=i;}
   if(d>maxDef[k]){maxDef[k]=d;maxIdx[k]=i;}
 }
 u128 TL=0,TR=0,TP=0,TN=0;
 for(unsigned k=0;k<3;++k){TL+=lhs[k];TR+=rhs[k];TP+=positive[k];TN+=negative[k];
   std::cout<<"K="<<k<<"\nCOUNT="<<(N/3)<<"\nPASS="<<pass[k]<<"\nFAIL="<<fail[k]<<"\nEQUAL="<<equal[k]
    <<"\nSUM_W="<<ustr(sumw[k])<<"\nSUM_WF="<<ustr(sumwf[k])<<"\nSUM_WA="<<ustr(sumwa[k])
    <<"\nSUM_LHS="<<ustr(lhs[k])<<"\nSUM_RHS="<<ustr(rhs[k])
    <<"\nNET_DEFECT="<<istr(i128(rhs[k])-i128(lhs[k]))
    <<"\nPOSITIVE_SURPLUS="<<ustr(positive[k])<<"\nNEGATIVE_DEFICIT="<<ustr(negative[k])
    <<"\nMIN_DEFECT="<<minDef[k]<<"\nMIN_INDEX="<<minIdx[k]
    <<"\nMAX_DEFECT="<<maxDef[k]<<"\nMAX_INDEX="<<maxIdx[k]<<"\n";
 }
 std::cout<<"ROWS="<<N<<"\nTOTAL_LHS="<<ustr(TL)<<"\nTOTAL_RHS="<<ustr(TR)
  <<"\nTOTAL_NET_DEFECT="<<istr(i128(TR)-i128(TL))
  <<"\nTOTAL_POSITIVE_SURPLUS="<<ustr(TP)<<"\nTOTAL_NEGATIVE_DEFICIT="<<ustr(TN)<<"\n";
 return 0;
}
