#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
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
static constexpr unsigned ITER_MAX=512;
static constexpr long double THRESHOLD=7.0L/8.0L;

static inline uint64_t residue(uint64_t i){return 3*i+2;}
static inline uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static inline uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static inline uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
struct Minimum{long double value=std::numeric_limits<long double>::infinity();uint64_t index=0;};

int main(){
 const long double c0=(long double)C0/SCALE,c1=(long double)C1/SCALE,c3=(long double)C3/SCALE;
 std::vector<float> value(N,1.0f),fresh(N);
 std::cout<<std::setprecision(30)<<"ROWS="<<N<<"\nBASE=ONE\nTHRESHOLD="<<THRESHOLD<<"\n";
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i){long double v=c0*value[four_index(i)];unsigned k=i%3;if(k==0||k==2){uint32_t a=k==0?l1_aux(i):l3_aux(i);long double mn=std::min<long double>(value[a],std::min<long double>(value[a+AUX],value[a+2*AUX]));v+=(k==0?c1:c3)*mn;}fresh[i]=(float)v;}
  uint64_t below=0,belowOne=0,changed=0;Minimum minimum;
#pragma omp parallel
  {uint64_t b=0,b1=0,ch=0;Minimum local;
#pragma omp for schedule(static)
   for(uint64_t i=0;i<N;++i){long double r=fresh[i];if(r<THRESHOLD)++b;if(r<1.0L)++b1;if(fresh[i]>value[i])++ch;if(r<local.value)local={r,i};value[i]=std::max(value[i],fresh[i]);}
#pragma omp critical
   {below+=b;belowOne+=b1;changed+=ch;if(local.value<minimum.value)minimum=local;}}
  if(iter<=16||iter%16==0||below==0||changed==0){std::cout<<"ITER="<<iter<<" FRESH_MIN="<<minimum.value<<" MIN_INDEX="<<minimum.index<<" BELOW_7_OVER_8="<<below<<" BELOW_ONE="<<belowOne<<" VALUE_CHANGED="<<changed<<"\n";}
  if(below==0){std::cout<<"UNWEIGHTED_BELLMAN_FIRST_PASS="<<iter<<"\n";break;}
  if(changed==0){std::cout<<"UNWEIGHTED_BELLMAN_FIXED_POINT_BELOW_THRESHOLD="<<below<<"\n";break;}
 }
 return 0;
}
