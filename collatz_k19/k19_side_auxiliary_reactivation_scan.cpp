#include <algorithm>
#include <array>
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
#ifdef _OPENMP
#include <omp.h>
#endif

static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;
static constexpr uint64_t INV2_N=(N+1)/2;
static constexpr uint64_t SCALE=281474976710656ULL;
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr long double GAMMA=14551.0L/16000.0L;
static constexpr unsigned SIDE_COUNT=16;

struct Mapping{int fd=-1;size_t bytes=0;const unsigned char*data=nullptr;
 explicit Mapping(const char*p){fd=open(p,O_RDONLY);if(fd<0)throw std::runtime_error("open");struct stat st{};if(fstat(fd,&st))throw std::runtime_error("stat");bytes=size_t(st.st_size);data=(const unsigned char*)mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,fd,0);if(data==MAP_FAILED)throw std::runtime_error("mmap");}
 ~Mapping(){if(data&&data!=MAP_FAILED)munmap((void*)data,bytes);if(fd>=0)close(fd);}};
static inline uint32_t rd(const unsigned char*p){uint32_t v;std::memcpy(&v,p,4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
 v=__builtin_bswap32(v);
#endif
 return v;}
static inline uint64_t residue(uint64_t i){return 3*i+2;}
static inline uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static inline uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static inline uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
static inline uint64_t next_q(uint64_t q){const uint64_t a=(__uint128_t(q)*INV2_N)%N;return(3*a+1)%N;}
struct Min{long double ratio=std::numeric_limits<long double>::infinity();uint64_t parent=0;};

int main(int argc,char**argv){if(argc!=2)return 2;Mapping w(argv[1]);if(w.bytes!=4ULL*N)return 3;
 std::array<long double,SIDE_COUNT> factor{};for(unsigned j=0;j<SIDE_COUNT;++j)factor[j]=std::pow(std::ldexp(1.0L,int(j))/std::pow(3.0L,int(j+1)),GAMMA);
 const long double c0=(long double)C0/SCALE,c1=(long double)C1/SCALE,c3=(long double)C3/SCALE;
 uint64_t activeBelowOne=0,totalBelowOne=0;Min activeMin,totalMin;
#pragma omp parallel
 {
  uint64_t lab=0,ltb=0;Min lam,ltm;
#pragma omp for schedule(static)
  for(uint64_t parent=0;parent<N;++parent){long double active=0,total=0;uint64_t q=(3*parent+2)%N;
   for(unsigned j=0;j<SIDE_COUNT;++j){const unsigned kind=q%3;const long double principal=c0*rd(w.data+4ULL*four_index(q));long double auxiliary=0;
    if(kind==0||kind==2){const uint32_t a=kind==0?l1_aux(q):l3_aux(q);const uint64_t wa=std::min<uint64_t>(rd(w.data+4ULL*a),std::min<uint64_t>(rd(w.data+4ULL*(a+AUX)),rd(w.data+4ULL*(a+2*AUX))));auxiliary=(kind==0?c1:c3)*wa;}
    active+=factor[j]*auxiliary;total+=factor[j]*(principal+auxiliary);q=next_q(q);}
   const long double den=rd(w.data+4ULL*parent);const long double ar=active/den,tr=total/den;if(ar<1)++lab;if(tr<1)++ltb;if(ar<lam.ratio){lam={ar,parent};}if(tr<ltm.ratio){ltm={tr,parent};}}
#pragma omp critical
  {activeBelowOne+=lab;totalBelowOne+=ltb;if(lam.ratio<activeMin.ratio)activeMin=lam;if(ltm.ratio<totalMin.ratio)totalMin=ltm;}
 }
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\nACTIVE_AUX_BELOW_ONE="<<activeBelowOne<<"\nACTIVE_AUX_MIN_RATIO="<<activeMin.ratio<<"\nACTIVE_AUX_MIN_PARENT="<<activeMin.parent<<"\nTOTAL_K19_AFTER_SIDE_BELOW_ONE="<<totalBelowOne<<"\nTOTAL_K19_AFTER_SIDE_MIN_RATIO="<<totalMin.ratio<<"\nTOTAL_K19_AFTER_SIDE_MIN_PARENT="<<totalMin.parent<<"\nAUXILIARY_ACTIVE_UNIVERSAL="<<(activeBelowOne==0?"PASS_DIAGNOSTIC":"FAIL_DIAGNOSTIC")<<"\nTOTAL_COMPOSITE_UNIVERSAL="<<(totalBelowOne==0?"PASS_DIAGNOSTIC":"FAIL_DIAGNOSTIC")<<"\n";
 return 0;}
