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
static constexpr unsigned ITER_MAX=32;

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
struct Min{long double ratio=std::numeric_limits<long double>::infinity();uint64_t index=0;};

static void scan_ratio(const std::vector<float>&value,const Mapping&w,unsigned iter){uint64_t below=0;Min global;
#pragma omp parallel
 {uint64_t lb=0;Min local;
#pragma omp for schedule(static)
  for(uint64_t i=0;i<N;++i){const long double r=(long double)value[i]/rd(w.data+4ULL*i);if(r<1)++lb;if(r<local.ratio)local={r,i};}
#pragma omp critical
  {below+=lb;if(local.ratio<global.ratio)global=local;}}
 std::cout<<std::setprecision(30)<<"RESOLVENT_ITER="<<iter<<" BELOW_ONE="<<below<<" MIN_RATIO="<<global.ratio<<" MIN_INDEX="<<global.index<<" MIN_WEIGHT="<<rd(w.data+4ULL*global.index)<<"\n";}

int main(int argc,char**argv){if(argc!=2)return 2;Mapping w(argv[1]);if(w.bytes!=4ULL*N)return 3;
 std::array<long double,SIDE_COUNT> factor{};for(unsigned j=0;j<SIDE_COUNT;++j)factor[j]=std::pow(std::ldexp(1.0L,int(j))/std::pow(3.0L,int(j+1)),GAMMA);
 std::vector<float> side(N);
#pragma omp parallel for schedule(static)
 for(uint64_t i=0;i<N;++i){uint64_t q=(3*i+2)%N;long double s=0;for(unsigned j=0;j<SIDE_COUNT;++j){s+=factor[j]*rd(w.data+4ULL*q);q=next_q(q);}side[i]=(float)s;}
 uint64_t sideBelow=0;Min sideMin;
#pragma omp parallel
 {uint64_t lb=0;Min lm;
#pragma omp for schedule(static)
  for(uint64_t i=0;i<N;++i){long double r=(long double)side[i]/rd(w.data+4ULL*i);if(r<1)++lb;if(r<lm.ratio)lm={r,i};}
#pragma omp critical
  {sideBelow+=lb;if(lm.ratio<sideMin.ratio)sideMin=lm;}}
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\nSIDE_BELOW_ONE="<<sideBelow<<"\nSIDE_MIN_RATIO="<<sideMin.ratio<<"\nSIDE_MIN_INDEX="<<sideMin.index<<"\n";
 const long double c0=(long double)C0/SCALE,c1=(long double)C1/SCALE,c3=(long double)C3/SCALE;
 std::vector<float> emission(N);
#pragma omp parallel for schedule(static)
 for(uint64_t i=0;i<N;++i){const unsigned kind=i%3;long double e=0;if(kind==0||kind==2){const uint32_t a=kind==0?l1_aux(i):l3_aux(i);const long double mn=std::min<long double>(side[a],std::min<long double>(side[a+AUX],side[a+2*AUX]));e=(kind==0?c1:c3)*mn;}emission[i]=(float)e;}
 side.clear();side.shrink_to_fit();
 std::vector<float> current(N,0.0f),next(N,0.0f);
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i)next[i]=(float)((long double)emission[i]+c0*(long double)current[four_index(i)]);
  current.swap(next);
  if(iter<=4||iter==8||iter==12||iter==16||iter==20||iter==24||iter==28||iter==32)scan_ratio(current,w,iter);
 }
 return 0;}
