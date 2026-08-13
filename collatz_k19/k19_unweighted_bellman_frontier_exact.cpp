#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

using u128 = __uint128_t;
static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;
static constexpr uint64_t COEFFICIENT_SCALE=281474976710656ULL; // 2^48
static constexpr uint32_t VALUE_SCALE=16777216U;                // 2^24
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr unsigned ITER_MAX=512;

static inline uint64_t residue(uint64_t i){return 3*i+2;}
static inline uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static inline uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static inline uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}

int main(){
 std::vector<uint32_t> value(N,VALUE_SCALE),fresh(N);
 std::cout<<"ROWS="<<N<<"\nCOEFFICIENT_SCALE="<<COEFFICIENT_SCALE<<"\nVALUE_SCALE="<<VALUE_SCALE<<"\nSATURATION_VALUE="<<std::numeric_limits<uint32_t>::max()<<"\nTHRESHOLD_NUM=7\nTHRESHOLD_DEN=8\nROUNDING=DOWNWARD_EXACT\nSATURATION=DOWNWARD_MONOTONE_LOWER_BOUND\n";
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
  uint64_t saturated=0;
#pragma omp parallel for schedule(static) reduction(+:saturated)
  for(uint64_t i=0;i<N;++i){
    u128 numerator=u128(C0)*value[four_index(i)];
    unsigned k=i%3;
    if(k==0||k==2){
      uint32_t a=k==0?l1_aux(i):l3_aux(i);
      uint32_t mn=std::min<uint32_t>(value[a],std::min<uint32_t>(value[a+AUX],value[a+2*AUX]));
      numerator+=u128(k==0?C1:C3)*mn;
    }
    u128 quotient=numerator/COEFFICIENT_SCALE;
    if(quotient>std::numeric_limits<uint32_t>::max()){
      ++saturated;
      fresh[i]=std::numeric_limits<uint32_t>::max();
    }else fresh[i]=uint32_t(quotient);
  }
  uint64_t below=0,belowOne=0,changed=0;
  uint32_t minValue=std::numeric_limits<uint32_t>::max(),maxValue=0;
  uint64_t minIndex=0;
#pragma omp parallel
  {
    uint64_t b=0,b1=0,ch=0;
    uint32_t lmin=std::numeric_limits<uint32_t>::max(),lmax=0;
    uint64_t lidx=0;
#pragma omp for schedule(static)
    for(uint64_t i=0;i<N;++i){
      uint32_t x=fresh[i];
      if(uint64_t(8)*x<=uint64_t(7)*VALUE_SCALE)++b;
      if(x<VALUE_SCALE)++b1;
      if(x>value[i])++ch;
      if(x<lmin){lmin=x;lidx=i;}
      if(x>lmax)lmax=x;
      value[i]=std::max(value[i],x);
    }
#pragma omp critical
    {
      below+=b;belowOne+=b1;changed+=ch;
      if(lmin<minValue){minValue=lmin;minIndex=lidx;}
      if(lmax>maxValue)maxValue=lmax;
    }
  }
  if(iter<=16||iter%16==0||below==0||changed==0){
    std::cout<<"ITER="<<iter
      <<" MIN_VALUE="<<minValue
      <<" MIN_INDEX="<<minIndex
      <<" MIN_RATIO_NUM="<<minValue
      <<" MIN_RATIO_DEN="<<VALUE_SCALE
      <<" BELOW_OR_EQUAL_7_OVER_8="<<below
      <<" BELOW_ONE="<<belowOne
      <<" VALUE_CHANGED="<<changed
      <<" SATURATED="<<saturated
      <<" MAX_VALUE="<<maxValue<<"\n";
  }
  if(below==0){
    std::cout<<"EXACT_UNWEIGHTED_BELLMAN_FIRST_PASS="<<iter
      <<"\nSATURATION_SOUNDNESS=MONOTONE_DOWNWARD_LOWER_BOUND"
      <<"\nEXACT_CERTIFICATE=PASS\n";
    return 0;
  }
  if(changed==0){
    std::cout<<"EXACT_FIXED_POINT_BELOW_THRESHOLD="<<below
      <<"\nSATURATION_SOUNDNESS=MONOTONE_DOWNWARD_LOWER_BOUND"
      <<"\nEXACT_CERTIFICATE=FAIL\n";
    return 4;
  }
 }
 std::cout<<"EXACT_DEPTH_LIMIT_REACHED=512"
   <<"\nSATURATION_SOUNDNESS=MONOTONE_DOWNWARD_LOWER_BOUND"
   <<"\nEXACT_CERTIFICATE=OPEN\n";
 return 0;
}
