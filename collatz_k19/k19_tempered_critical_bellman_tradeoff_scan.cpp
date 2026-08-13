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
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;
static constexpr unsigned ITER_MAX=384;
static constexpr uint32_t WMIN=1497192U;
static constexpr uint32_t WMAX=4166117961U;

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
struct Minimum{long double ratio=std::numeric_limits<long double>::infinity();uint64_t index=0;};

int main(int argc,char**argv){if(argc!=2)return 2;Mapping w(argv[1]);if(w.bytes!=4ULL*N)return 3;
 const std::array<unsigned,9> Qs={1,2,4,8,16,32,64,128,256};
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\n";
 for(unsigned Q:Qs){
  const long double q=1.0L/Q;
  const long double range=std::pow((long double)WMIN/WMAX,q);
  const long double sideFactor=(8.0L/7.0L)*range;
  std::vector<float> base(N),value(N),fresh(N);
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i){float x=(float)std::pow((long double)rd(w.data+4ULL*i),q);base[i]=x;value[i]=x;}
  unsigned fixed=0;Minimum finalMin;uint64_t finalBelow=0;
  for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
   for(uint64_t i=0;i<N;++i){long double v=0.25L*value[four_index(i)];unsigned k=i%3;if(k==0||k==2){uint32_t a=k==0?l1_aux(i):l3_aux(i);long double mn=std::min<long double>(value[a],std::min<long double>(value[a+AUX],value[a+2*AUX]));v+=(k==0?0.75L:1.5L)*mn;}fresh[i]=(float)v;}
   uint64_t changed=0,below=0;Minimum minimum;
#pragma omp parallel
   {uint64_t ch=0,bl=0;Minimum local;
#pragma omp for schedule(static)
    for(uint64_t i=0;i<N;++i){long double r=(long double)fresh[i]/base[i];if(r<1)++bl;if(fresh[i]>value[i])++ch;if(r<local.ratio)local={r,i};value[i]=std::max(value[i],fresh[i]);}
#pragma omp critical
    {changed+=ch;below+=bl;if(local.ratio<minimum.ratio)minimum=local;}}
   finalMin=minimum;finalBelow=below;
   if(changed==0){fixed=iter;break;}
  }
  const long double product=sideFactor*finalMin.ratio;
  std::cout<<"Q="<<Q
    <<" RANGE_FACTOR="<<range
    <<" SIDE_FACTOR="<<sideFactor
    <<" FIXED_ITER="<<fixed
    <<" FRESH_MIN_RETENTION="<<finalMin.ratio
    <<" MIN_INDEX="<<finalMin.index
    <<" BELOW_ONE="<<finalBelow
    <<" CONSERVATIVE_PRODUCT="<<product
    <<" PRODUCT_GT_ONE="<<(product>1?"YES":"NO")<<"\n";
 }
 return 0;}
