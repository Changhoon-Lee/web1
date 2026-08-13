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
static constexpr uint64_t INV2_N=(N+1)/2;
static constexpr uint64_t SCALE=281474976710656ULL;
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr long double GAMMA=14551.0L/16000.0L;
static constexpr unsigned SIDE_COUNT=16;
static constexpr unsigned ITER_MAX=20;
static constexpr unsigned Q=256;

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
struct Minimum{long double ratio=std::numeric_limits<long double>::infinity();uint64_t index=0;};
static Minimum scan(const std::vector<float>&v,const std::vector<float>&base,uint64_t&belowOne,uint64_t&belowFiveNinths){Minimum g;belowOne=belowFiveNinths=0;
#pragma omp parallel
 {Minimum l;uint64_t b1=0,b5=0;
#pragma omp for schedule(static)
  for(uint64_t i=0;i<N;++i){long double r=(long double)v[i]/base[i];if(r<1)++b1;if(r<5.0L/9.0L)++b5;if(r<l.ratio)l={r,i};}
#pragma omp critical
  {belowOne+=b1;belowFiveNinths+=b5;if(l.ratio<g.ratio)g=l;}}
 return g;}

int main(int argc,char**argv){if(argc!=2)return 2;Mapping w(argv[1]);if(w.bytes!=4ULL*N)return 3;
 const long double c0=(long double)C0/SCALE,c1=(long double)C1/SCALE,c3=(long double)C3/SCALE;
 std::array<long double,SIDE_COUNT> factor{};for(unsigned j=0;j<SIDE_COUNT;++j)factor[j]=std::pow(std::ldexp(1.0L,int(j))/std::pow(3.0L,int(j+1)),GAMMA);
 std::vector<float> base(N),cur(N),next(N);
#pragma omp parallel for schedule(static)
 for(uint64_t i=0;i<N;++i)base[i]=(float)std::pow((long double)rd(w.data+4ULL*i),1.0L/Q);
#pragma omp parallel for schedule(static)
 for(uint64_t i=0;i<N;++i){uint64_t q=(3*i+2)%N;long double s=0;for(unsigned j=0;j<SIDE_COUNT;++j){s+=factor[j]*(long double)base[q];q=next_q(q);}cur[i]=(float)s;}
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\nQ="<<Q<<"\n";uint64_t b1,b5;Minimum m=scan(cur,base,b1,b5);std::cout<<"ITER=0 MIN_RATIO="<<m.ratio<<" MIN_INDEX="<<m.index<<" BELOW_ONE="<<b1<<" BELOW_5_OVER_9="<<b5<<"\n";
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i){long double v=c0*cur[four_index(i)];unsigned k=i%3;if(k==0||k==2){uint32_t a=k==0?l1_aux(i):l3_aux(i);long double mn=std::min<long double>(cur[a],std::min<long double>(cur[a+AUX],cur[a+2*AUX]));v+=(k==0?c1:c3)*mn;}next[i]=(float)v;}
  cur.swap(next);m=scan(cur,base,b1,b5);std::cout<<"ITER="<<iter<<" MIN_RATIO="<<m.ratio<<" MIN_INDEX="<<m.index<<" BELOW_ONE="<<b1<<" BELOW_5_OVER_9="<<b5<<"\n";}
 return 0;}
