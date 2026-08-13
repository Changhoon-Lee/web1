#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

using u128 = __uint128_t;
static constexpr uint64_t N=387420489ULL;
static constexpr uint64_t AUX=129140163ULL;
static constexpr uint64_t MOD=1162261467ULL;
static constexpr uint64_t SCALE=281474976710656ULL; // 2^48
static constexpr uint64_t C0=79781805157054ULL;
static constexpr uint64_t C1=216678499581515ULL;
static constexpr uint64_t C3=406990044804623ULL;
static constexpr unsigned ITER_MAX=512;

static inline uint64_t residue(uint64_t i){return 3*i+2;}
static inline uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static inline uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static inline uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
static std::string ustr(u128 x){if(!x)return"0";std::string s;while(x){s.push_back(char('0'+x%10));x/=10;}std::reverse(s.begin(),s.end());return s;}

int main(){
 std::vector<uint64_t> value(N,SCALE),fresh(N);
 std::cout<<"ROWS="<<N<<"\nSCALE="<<SCALE<<"\nTHRESHOLD_NUM=7\nTHRESHOLD_DEN=8\nROUNDING=DOWNWARD_EXACT\n";
 for(unsigned iter=1;iter<=ITER_MAX;++iter){
#pragma omp parallel for schedule(static)
  for(uint64_t i=0;i<N;++i){u128 numerator=u128(C0)*value[four_index(i)];unsigned k=i%3;if(k==0||k==2){uint32_t a=k==0?l1_aux(i):l3_aux(i);uint64_t mn=std::min<uint64_t>(value[a],std::min<uint64_t>(value[a+AUX],value[a+2*AUX]));numerator+=u128(k==0?C1:C3)*mn;}fresh[i]=uint64_t(numerator/SCALE);}
  uint64_t below=0,belowOne=0,changed=0,minValue=std::numeric_limits<uint64_t>::max(),minIndex=0,maxValue=0;
#pragma omp parallel
  {uint64_t b=0,b1=0,ch=0,lmin=std::numeric_limits<uint64_t>::max(),lidx=0,lmax=0;
#pragma omp for schedule(static)
   for(uint64_t i=0;i<N;++i){uint64_t x=fresh[i];if(u128(8)*x<=u128(7)*SCALE)++b;if(x<SCALE)++b1;if(x>value[i])++ch;if(x<lmin){lmin=x;lidx=i;}if(x>lmax)lmax=x;value[i]=std::max(value[i],x);}
#pragma omp critical
   {below+=b;belowOne+=b1;changed+=ch;if(lmin<minValue){minValue=lmin;minIndex=lidx;}if(lmax>maxValue)maxValue=lmax;}}
  if(iter<=16||iter%16==0||below==0||changed==0){std::cout<<"ITER="<<iter<<" MIN_VALUE="<<minValue<<" MIN_INDEX="<<minIndex<<" MIN_RATIO_NUM="<<minValue<<" MIN_RATIO_DEN="<<SCALE<<" BELOW_OR_EQUAL_7_OVER_8="<<below<<" BELOW_ONE="<<belowOne<<" VALUE_CHANGED="<<changed<<" MAX_VALUE="<<maxValue<<"\n";}
  if(below==0){std::cout<<"EXACT_UNWEIGHTED_BELLMAN_FIRST_PASS="<<iter<<"\nEXACT_CERTIFICATE=PASS\n";return 0;}
  if(changed==0){std::cout<<"EXACT_FIXED_POINT_BELOW_THRESHOLD="<<below<<"\nEXACT_CERTIFICATE=FAIL\n";return 4;}
 }
 std::cout<<"EXACT_DEPTH_LIMIT_REACHED=512\nEXACT_CERTIFICATE=OPEN\n";
 return 0;
}
