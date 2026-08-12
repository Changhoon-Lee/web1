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

static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;
static constexpr uint64_t INV2_N = (N + 1) / 2;
static constexpr uint64_t SCALE = 281474976710656ULL;
static constexpr uint64_t C0 = 79781805157054ULL;
static constexpr uint64_t C1 = 216678499581515ULL;
static constexpr uint64_t C3 = 406990044804623ULL;
static constexpr long double GAMMA = 14551.0L / 16000.0L;
static constexpr unsigned SIDE_COUNT = 16;
static constexpr unsigned ITER_MAX = 8;

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
  const uint64_t a = (__uint128_t(q) * INV2_N) % N;
  return (3*a + 1) % N;
}

struct Minimum {
  long double ratio = std::numeric_limits<long double>::infinity();
  uint64_t parent = 0;
};

static void scan_side(const std::vector<float>& values,
                      const Mapping& weights,
                      unsigned iteration,
                      const std::array<long double,SIDE_COUNT>& factor) {
  uint64_t belowOne = 0;
  uint64_t belowEightSevenths = 0;
  Minimum global;

#pragma omp parallel
  {
    uint64_t localBelowOne = 0;
    uint64_t localBelowEightSevenths = 0;
    Minimum local;
#pragma omp for schedule(static)
    for (uint64_t parent=0; parent<N; ++parent) {
      const long double parentWeight = rd(weights.data + 4ULL*parent);
      uint64_t q = (3*parent + 2) % N;
      long double numerator = 0;
      for (unsigned j=0; j<SIDE_COUNT; ++j) {
        numerator += static_cast<long double>(values[q]) * factor[j];
        q = next_q(q);
      }
      const long double ratio = numerator / parentWeight;
      if (ratio < 1.0L) ++localBelowOne;
      if (ratio < 8.0L/7.0L) ++localBelowEightSevenths;
      if (ratio < local.ratio) { local.ratio=ratio; local.parent=parent; }
    }
#pragma omp critical
    {
      belowOne += localBelowOne;
      belowEightSevenths += localBelowEightSevenths;
      if (local.ratio < global.ratio) global = local;
    }
  }

  std::cout << std::setprecision(30)
    << "ITERATION=" << iteration
    << " BELOW_ONE=" << belowOne
    << " BELOW_EIGHT_SEVENTHS=" << belowEightSevenths
    << " MIN_RATIO=" << global.ratio
    << " MIN_PARENT_INDEX=" << global.parent
    << " MIN_PARENT_WEIGHT=" << rd(weights.data + 4ULL*global.parent)
    << "\n";
}

int main(int argc, char** argv) {
  if (argc != 2) { std::cerr << "usage: scan WEIGHTS\n"; return 2; }
  Mapping weights(argv[1]);
  if (weights.bytes != 4ULL*N) { std::cerr << "bad weight size\n"; return 3; }

  std::array<long double,SIDE_COUNT> factor{};
  for (unsigned j=0; j<SIDE_COUNT; ++j) {
    factor[j] = std::pow(
      std::ldexp(1.0L, int(j)) /
        std::pow(3.0L, int(j+1)), GAMMA);
  }

  std::vector<float> current(N), next(N);
#pragma omp parallel for schedule(static)
  for (uint64_t i=0; i<N; ++i)
    current[i] = static_cast<float>(rd(weights.data + 4ULL*i));

  std::cout << "ROWS=" << N << "\nITER_MAX=" << ITER_MAX << "\n";
  scan_side(current, weights, 0, factor);

  const long double c0 = static_cast<long double>(C0)/SCALE;
  const long double c1 = static_cast<long double>(C1)/SCALE;
  const long double c3 = static_cast<long double>(C3)/SCALE;

  for (unsigned iteration=1; iteration<=ITER_MAX; ++iteration) {
#pragma omp parallel for schedule(static)
    for (uint64_t i=0; i<N; ++i) {
      const uint32_t f = four_index(i);
      long double value = c0 * static_cast<long double>(current[f]);
      const unsigned kind = unsigned(i % 3);
      if (kind == 0 || kind == 2) {
        const uint32_t q = kind == 0 ? l1_aux(i) : l3_aux(i);
        const long double a = std::min<long double>(
          current[q], std::min<long double>(current[q+AUX], current[q+2*AUX]));
        value += (kind == 0 ? c1 : c3) * a;
      }
      next[i] = static_cast<float>(value);
    }
    current.swap(next);
    scan_side(current, weights, iteration, factor);
  }
  return 0;
}
