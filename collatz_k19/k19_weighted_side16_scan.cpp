#include <algorithm>
#include <array>
#include <atomic>
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

static constexpr uint64_t N = 387420489ULL;      // 3^18
static constexpr uint64_t MOD = 1162261467ULL;   // 3^19
static constexpr uint64_t INV2_N = (N + 1) / 2;
static constexpr uint64_t INV2_MOD = (MOD + 1) / 2;
static constexpr long double GAMMA = 14551.0L / 16000.0L;
static constexpr unsigned SIDE_COUNT = 16;

struct Mapping {
  int fd = -1;
  size_t bytes = 0;
  const unsigned char* data = nullptr;
  explicit Mapping(const char* path) {
    fd = open(path, O_RDONLY);
    if (fd < 0) throw std::runtime_error("open");
    struct stat st{};
    if (fstat(fd, &st)) throw std::runtime_error("stat");
    bytes = size_t(st.st_size);
    data = static_cast<const unsigned char*>(
      mmap(nullptr, bytes, PROT_READ, MAP_PRIVATE, fd, 0));
    if (data == MAP_FAILED) throw std::runtime_error("mmap");
  }
  ~Mapping() {
    if (data && data != MAP_FAILED) munmap((void*)data, bytes);
    if (fd >= 0) close(fd);
  }
};

static inline uint32_t rd(const unsigned char* p) {
  uint32_t v;
  std::memcpy(&v, p, 4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  v = __builtin_bswap32(v);
#endif
  return v;
}

struct Minimum {
  long double ratio = std::numeric_limits<long double>::infinity();
  uint64_t parent = 0;
};

static inline uint64_t next_q(uint64_t q) {
  // q_j = 2 a_j (mod 3^18).  Under a_{j+1}=(3a_j+1)/2,
  // q_{j+1}=3 a_j+1=3*(q_j/2)+1 modulo 3^18.
  const uint64_t a = (__uint128_t(q) * INV2_N) % N;
  return (3 * a + 1) % N;
}

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: weighted-side16 WEIGHTS\n";
    return 2;
  }
  Mapping weights(argv[1]);
  if (weights.bytes != 4ULL * N) {
    std::cerr << "bad weight size\n";
    return 3;
  }

  std::array<long double, SIDE_COUNT> factor{};
  for (unsigned j = 0; j < SIDE_COUNT; ++j) {
    // Exact asymptotic upper factor for an r=1 odd block:
    // m / b_j < 2^j / 3^(j+1).
    factor[j] = std::pow(
      std::ldexp(1.0L, static_cast<int>(j)) /
        std::pow(3.0L, static_cast<int>(j + 1)),
      GAMMA);
  }

  uint64_t belowOne = 0;
  uint64_t belowSevenEighths = 0;
  uint64_t belowHalf = 0;
  Minimum global;

#pragma omp parallel
  {
    Minimum local;
    uint64_t localBelowOne = 0;
    uint64_t localBelowSevenEighths = 0;
    uint64_t localBelowHalf = 0;

#pragma omp for schedule(static)
    for (uint64_t parent = 0; parent < N; ++parent) {
      const uint32_t parentWeight = rd(weights.data + 4ULL * parent);
      uint64_t q = (3 * parent + 2) % N; // q_0=2m mod 3^18.
      long double numerator = 0.0L;
      for (unsigned j = 0; j < SIDE_COUNT; ++j) {
        numerator += static_cast<long double>(
          rd(weights.data + 4ULL * q)) * factor[j];
        q = next_q(q);
      }
      const long double ratio = numerator /
        static_cast<long double>(parentWeight);
      if (ratio < 1.0L) ++localBelowOne;
      if (ratio < 0.875L) ++localBelowSevenEighths;
      if (ratio < 0.5L) ++localBelowHalf;
      if (ratio < local.ratio) {
        local.ratio = ratio;
        local.parent = parent;
      }
    }

#pragma omp critical
    {
      belowOne += localBelowOne;
      belowSevenEighths += localBelowSevenEighths;
      belowHalf += localBelowHalf;
      if (local.ratio < global.ratio) global = local;
    }
  }

  const uint64_t sourceResidue = 3 * global.parent + 2;
  const uint64_t mResidue = (__uint128_t(sourceResidue) * INV2_MOD) % MOD;
  const uint32_t parentWeight = rd(weights.data + 4ULL * global.parent);

  std::cout << std::setprecision(30);
  std::cout << "ROWS=" << N << "\n";
  std::cout << "SIDE_COUNT=" << SIDE_COUNT << "\n";
  std::cout << "GAMMA=" << GAMMA << "\n";
  for (unsigned j = 0; j < SIDE_COUNT; ++j)
    std::cout << "FACTOR_" << j << "=" << factor[j] << "\n";
  std::cout << "BELOW_ONE=" << belowOne << "\n";
  std::cout << "BELOW_SEVEN_EIGHTHS=" << belowSevenEighths << "\n";
  std::cout << "BELOW_HALF=" << belowHalf << "\n";
  std::cout << "MIN_RATIO=" << global.ratio << "\n";
  std::cout << "MIN_PARENT_INDEX=" << global.parent << "\n";
  std::cout << "MIN_PARENT_WEIGHT=" << parentWeight << "\n";
  std::cout << "MIN_SOURCE_RESIDUE_MOD_3_19=" << sourceResidue << "\n";
  std::cout << "MIN_M_RESIDUE_MOD_3_19=" << mResidue << "\n";

  uint64_t q = (3 * global.parent + 2) % N;
  long double numerator = 0.0L;
  for (unsigned j = 0; j < SIDE_COUNT; ++j) {
    const uint32_t w = rd(weights.data + 4ULL * q);
    const long double term = static_cast<long double>(w) * factor[j];
    numerator += term;
    std::cout << "J=" << j
      << " Q=" << q
      << " W=" << w
      << " FACTOR=" << factor[j]
      << " TERM=" << term << "\n";
    q = next_q(q);
  }
  std::cout << "MIN_NUMERATOR_APPROX=" << numerator << "\n";
  std::cout << "WEIGHTED_SIDE16_NAIVE_BRIDGE="
    << (global.ratio > 1.0L ? "PASS_DIAGNOSTIC" : "FAIL_DIAGNOSTIC")
    << "\n";
  return 0;
}
