#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;
static constexpr uint32_t SCALE = 1U << 24;
static constexpr unsigned ITER_MAX = 1024;

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

int main() {
  std::vector<uint32_t> value(N, SCALE), fresh(N);
  std::cout << "ROWS=" << N
            << "\nSCALE=" << SCALE
            << "\nOPERATOR=CRITICAL_ONE_BELLMAN"
            << "\nTHRESHOLD_NUM=30"
            << "\nTHRESHOLD_DEN=31"
            << "\nROUNDING=EXACT_FLOOR"
            << "\nSATURATION=MONOTONE_DOWNWARD_LOWER_BOUND\n";

  for (unsigned iter=1; iter<=ITER_MAX; ++iter) {
    uint64_t saturated = 0;
#pragma omp parallel for schedule(static) reduction(+:saturated)
    for (uint64_t i=0; i<N; ++i) {
      uint64_t numerator = value[four_index(i)];
      const unsigned kind = unsigned(i % 3);
      if (kind == 0 || kind == 2) {
        const uint32_t a = kind == 0 ? l1_aux(i) : l3_aux(i);
        const uint32_t mn = std::min<uint32_t>(
          value[a], std::min<uint32_t>(value[a+AUX], value[a+2*AUX]));
        numerator += uint64_t(kind == 0 ? 3 : 6) * mn;
      }
      const uint64_t quotient = numerator / 4;
      if (quotient > std::numeric_limits<uint32_t>::max()) {
        ++saturated;
        fresh[i] = std::numeric_limits<uint32_t>::max();
      } else {
        fresh[i] = uint32_t(quotient);
      }
    }

    uint64_t belowThreshold=0, belowOne=0, changed=0;
    uint32_t minValue=std::numeric_limits<uint32_t>::max(), maxValue=0;
    uint64_t minIndex=0;
#pragma omp parallel
    {
      uint64_t bt=0, b1=0, ch=0;
      uint32_t localMin=std::numeric_limits<uint32_t>::max(), localMax=0;
      uint64_t localIndex=0;
#pragma omp for schedule(static)
      for (uint64_t i=0; i<N; ++i) {
        const uint32_t x=fresh[i];
        if (uint64_t(31)*x <= uint64_t(30)*SCALE) ++bt;
        if (x < SCALE) ++b1;
        if (x > value[i]) ++ch;
        if (x < localMin) { localMin=x; localIndex=i; }
        if (x > localMax) localMax=x;
        value[i]=std::max(value[i],x);
      }
#pragma omp critical
      {
        belowThreshold += bt; belowOne += b1; changed += ch;
        if (localMin < minValue) { minValue=localMin; minIndex=localIndex; }
        if (localMax > maxValue) maxValue=localMax;
      }
    }

    if (iter<=32 || iter%16==0 || belowThreshold==0 || changed==0) {
      std::cout << "ITER=" << iter
        << " MIN_VALUE=" << minValue
        << " MIN_INDEX=" << minIndex
        << " MIN_RATIO_NUM=" << minValue
        << " MIN_RATIO_DEN=" << SCALE
        << " BELOW_OR_EQUAL_30_OVER_31=" << belowThreshold
        << " BELOW_ONE=" << belowOne
        << " VALUE_CHANGED=" << changed
        << " SATURATED=" << saturated
        << " MAX_VALUE=" << maxValue << "\n";
    }

    if (belowThreshold==0) {
      std::cout << "CRITICAL_ONE_BELLMAN_FIRST_PASS=" << iter
        << "\nEXACT_CERTIFICATE=PASS\n";
      return 0;
    }
    if (changed==0) {
      std::cout << "CRITICAL_ONE_FIXED_POINT_BELOW_THRESHOLD="
        << belowThreshold << "\nEXACT_CERTIFICATE=FAIL\n";
      return 4;
    }
  }
  std::cout << "DEPTH_LIMIT_REACHED=" << ITER_MAX
    << "\nEXACT_CERTIFICATE=OPEN\n";
  return 0;
}
