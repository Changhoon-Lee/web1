#include <algorithm>
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
static constexpr uint64_t SCALE=281474976710656ULL;
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr unsigned Q=256;
static constexpr unsigned ITER_MAX=64;

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
 const long double c0=(long double)C0/SCALE,c1=(long double)C1/SCALE,c3=(long double)C3/SCALE;
 std::vector<float> base(N),value(N),fresh(N);
#pragma omp parallel for schedule(static)
 for(uint64_t i=0;i<N;++i){float u=(float)std::pow((long double)rd(w.data+4ULL*i),1.0L/Q);base[i]=u;value[i]=u;}
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\nQ="<<Q<<"\n";
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i){long double v=c0*value[four_index(i)];unsigned k=i%3;if(k==0||k==2){uint32_t a=k==0?l1_aux(i):l3_aux(i);long double mn=std::min<long double>(value[a],std::min<long double>(value[a+AUX],value[a+2*AUX]));v+=(k==0?c1:c3)*mn;}fresh[i]=(float)v;}
  uint64_t belowFiveNinths=0,belowSevenEighths=0,belowOne=0,changed=0;Minimum minimum;
#pragma omp parallel
  {uint64_t b5=0,b7=0,b1=0,ch=0;Minimum local;
#pragma omp for schedule(static)
   for(uint64_t i=0;i<N;++i){long double r=(long double)fresh[i]/base[i];if(r<5.0L/9.0L)++b5;if(r<7.0L/8.0L)++b7;if(r<1.0L)++b1;if(fresh[i]>value[i])++ch;if(r<local.ratio)local={r,i};value[i]=std::max(value[i],fresh[i]);}
#pragma omp critical
   {belowFiveNinths+=b5;belowSevenEighths+=b7;belowOne+=b1;changed+=ch;if(local.ratio<minimum.ratio)minimum=local;}}
  std::cout<<"ITER="<<iter<<" FRESH_MIN_RATIO="<<minimum.ratio<<" MIN_INDEX="<<minimum.index<<" BELOW_5_OVER_9="<<belowFiveNinths<<" BELOW_7_OVER_8="<<belowSevenEighths<<" BELOW_ONE="<<belowOne<<" VALUE_CHANGED="<<changed<<"\n";
  if(changed==0)break;
 }
 return 0;}
