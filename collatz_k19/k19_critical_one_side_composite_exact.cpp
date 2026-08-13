#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

using u128 = __uint128_t;
static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;
static constexpr uint64_t INV2_N = (N + 1) / 2;
static constexpr uint32_t SCALE = 1U << 24;
static constexpr unsigned ITER_MAX = 512;
static constexpr unsigned SIDE_COUNT = 16;

static inline uint64_t residue(uint64_t i) { return 3*i + 2; }
static inline uint32_t four_index(uint64_t i) {
  return uint32_t(((4*residue(i) % MOD)-2)/3);
}
static inline uint32_t l1_aux(uint64_t i) {
  return uint32_t(((((4*residue(i)-2)/3) % N)-2)/3);
}
static inline uint32_t l3_aux(uint64_t i) {
  return uint32_t(((((2*residue(i)-1)/3) % N)-2)/3);
}
static inline uint64_t next_q(uint64_t q) {
  const uint64_t a = (u128(q) * INV2_N) % N;
  return (3*a + 1) % N;
}
static std::string ustr(u128 x) {
  if (!x) return "0";
  std::string s;
  while (x) { s.push_back(char('0' + x%10)); x/=10; }
  std::reverse(s.begin(),s.end());
  return s;
}

int main() {
  std::vector<uint32_t> value(N,SCALE), fresh(N);
  unsigned fixedIteration=0;
  for (unsigned iter=1; iter<=ITER_MAX; ++iter) {
    uint64_t saturated=0;
#pragma omp parallel for schedule(static) reduction(+:saturated)
    for (uint64_t i=0;i<N;++i) {
      uint64_t numerator=value[four_index(i)];
      const unsigned kind=unsigned(i%3);
      if (kind==0 || kind==2) {
        const uint32_t a=kind==0?l1_aux(i):l3_aux(i);
        const uint32_t mn=std::min<uint32_t>(
          value[a],std::min<uint32_t>(value[a+AUX],value[a+2*AUX]));
        numerator += uint64_t(kind==0?3:6)*mn;
      }
      const uint64_t q=numerator/4;
      if (q>std::numeric_limits<uint32_t>::max()) {
        ++saturated; fresh[i]=std::numeric_limits<uint32_t>::max();
      } else fresh[i]=uint32_t(q);
    }
    uint64_t changed=0;
#pragma omp parallel for schedule(static) reduction(+:changed)
    for (uint64_t i=0;i<N;++i) {
      if (fresh[i]>value[i]) { value[i]=fresh[i]; ++changed; }
    }
    if (iter<=16 || iter%16==0 || changed==0)
      std::cout << "BELLMAN_ITER=" << iter
        << " VALUE_CHANGED=" << changed
        << " SATURATED=" << saturated << "\n";
    if (changed==0) { fixedIteration=iter; break; }
  }
  if (!fixedIteration) {
    std::cout << "BELLMAN_FIXED_POINT=OPEN\n";
    return 3;
  }

  std::array<uint64_t,SIDE_COUNT> coefficient{};
  uint64_t pow2=1;
  std::array<uint64_t,16> pow3{};
  pow3[0]=1;
  for (unsigned j=1;j<16;++j) pow3[j]=pow3[j-1]*3;
  for (unsigned j=0;j<SIDE_COUNT;++j) {
    coefficient[j]=pow2*pow3[15-j];
    pow2*=2;
  }
  const uint64_t commonDenominator=2*pow3[15]*3; // 2*3^16
  const u128 threshold=u128(SCALE)*commonDenominator;

  uint64_t belowOne=0, equalOne=0;
  u128 minNumerator=0;
  uint64_t minParent=0;
#pragma omp parallel
  {
    uint64_t localBelow=0,localEqual=0,localParent=0;
    u128 localMin=0;
#pragma omp for schedule(static)
    for (uint64_t parent=0; parent<N; ++parent) {
      uint64_t q=(3*parent+2)%N;
      u128 numerator=0;
      for (unsigned j=0;j<SIDE_COUNT;++j) {
        numerator += u128(value[q])*coefficient[j];
        q=next_q(q);
      }
      if (numerator<threshold) ++localBelow;
      else if (numerator==threshold) ++localEqual;
      if (localMin==0 || numerator<localMin) {
        localMin=numerator; localParent=parent;
      }
    }
#pragma omp critical
    {
      belowOne+=localBelow; equalOne+=localEqual;
      if (minNumerator==0 || localMin<minNumerator) {
        minNumerator=localMin; minParent=localParent;
      }
    }
  }

  std::cout << "ROWS=" << N
    << "\nBELLMAN_FIXED_POINT_ITER=" << fixedIteration
    << "\nSIDE_SOURCE_NORMALIZATION=ONE_HALF_INCLUDED"
    << "\nCOMPOSITE_COMMON_DENOMINATOR=" << commonDenominator
    << "\nCOMPOSITE_THRESHOLD=" << ustr(threshold)
    << "\nCOMPOSITE_MIN_NUMERATOR=" << ustr(minNumerator)
    << "\nCOMPOSITE_MIN_PARENT=" << minParent
    << "\nCOMPOSITE_BELOW_ONE=" << belowOne
    << "\nCOMPOSITE_EQUAL_ONE=" << equalOne
    << "\nCOMPOSITE_UNIVERSAL="
    << (belowOne==0 && equalOne==0 ? "PASS_DIAGNOSTIC" : "FAIL_DIAGNOSTIC")
    << "\n";
  return 0;
}
