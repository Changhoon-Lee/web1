#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <boost/multiprecision/cpp_int.hpp>

using boost::multiprecision::uint256_t;

static constexpr uint64_t N = 387420489ULL;    // 3^18
static constexpr uint64_t AUX = 129140163ULL;  // 3^17
static constexpr uint64_t MOD = 1162261467ULL; // 3^19
static constexpr uint64_t SCALE = 281474976710656ULL; // 2^48
static constexpr uint64_t C0 = 79781805157054ULL;
static constexpr uint64_t C1 = 216678499581515ULL;
static constexpr uint64_t C3 = 406990044804623ULL;
static constexpr uint64_t B = 10000000000000000ULL;
static constexpr uint64_t A = B - 1;

struct Mapping {
  int fd = -1;
  size_t bytes = 0;
  const unsigned char* data = nullptr;
  explicit Mapping(const char* path) {
    fd = open(path, O_RDONLY);
    if (fd < 0) throw std::runtime_error("open");
    struct stat st{};
    if (fstat(fd, &st) != 0) throw std::runtime_error("stat");
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

static uint32_t rd(const unsigned char* p) {
  uint32_t v;
  std::memcpy(&v, p, 4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  v = __builtin_bswap32(v);
#endif
  return v;
}

static uint64_t residue(uint64_t i) { return 3 * i + 2; }
static uint32_t four_index(uint64_t i) {
  return uint32_t((((4 * residue(i)) % MOD) - 2) / 3);
}
static uint32_t l1_aux(uint64_t i) {
  const uint64_t rr = ((4 * residue(i) - 2) / 3) % N;
  return uint32_t((rr - 2) / 3);
}
static uint32_t l3_aux(uint64_t i) {
  const uint64_t rr = ((2 * residue(i) - 1) / 3) % N;
  return uint32_t((rr - 2) / 3);
}

static std::string u256s(const uint256_t& x) { return x.convert_to<std::string>(); }

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: k19_q1e16_exact_check WEIGHTS\n";
    return 2;
  }
  Mapping m(argv[1]);
  if (m.bytes != 4ULL * N) {
    std::cerr << "bad payload size\n";
    return 3;
  }

  const uint256_t b = B;
  const uint256_t b2 = b * b;
  const uint256_t two_b_minus_one = uint256_t(2) * b - 1;

  uint64_t failures = 0;
  uint64_t original_failures = 0;
  uint64_t min_slack_index = 0;
  unsigned __int128 min_slack = ~static_cast<unsigned __int128>(0);
  uint64_t min_margin_index = 0;
  uint256_t min_margin = ~uint256_t(0);
  int min_margin_kind = -1;

  for (uint64_t i = 0; i < N; ++i) {
    const uint64_t w = rd(m.data + 4 * i);
    const uint64_t wf = rd(m.data + 4ULL * four_index(i));
    const unsigned kind = unsigned(i % 3);

    const unsigned __int128 L = static_cast<unsigned __int128>(SCALE) * w;
    const unsigned __int128 principal = static_cast<unsigned __int128>(C0) * wf;
    unsigned __int128 auxiliary = 0;
    if (kind == 0 || kind == 2) {
      const uint32_t ai = kind == 0 ? l1_aux(i) : l3_aux(i);
      const uint64_t wa = std::min<uint64_t>(
          rd(m.data + 4ULL * ai),
          std::min<uint64_t>(rd(m.data + 4ULL * (ai + AUX)),
                             rd(m.data + 4ULL * (ai + 2 * AUX))));
      auxiliary = static_cast<unsigned __int128>(kind == 0 ? C1 : C3) * wa;
    }
    const unsigned __int128 R = principal + auxiliary;
    if (R < L) {
      ++original_failures;
      ++failures;
      continue;
    }
    const unsigned __int128 slack = R - L;
    if (slack < min_slack) {
      min_slack = slack;
      min_slack_index = i;
    }

    // Exact q-weighted margin after multiplying by B^2.
    // D1/D2: B^2*slack - (2B-1)*(principal+auxiliary).
    // D3:    B^2*slack - (2B-1)*principal - B*auxiliary.
    const uint256_t lhs = b2 * uint256_t(slack);
    uint256_t loss = two_b_minus_one * uint256_t(principal);
    if (kind == 0) {
      loss += two_b_minus_one * uint256_t(auxiliary);
    } else if (kind == 2) {
      loss += b * uint256_t(auxiliary);
    }

    if (lhs < loss) {
      ++failures;
      if (failures <= 10) {
        std::cerr << "FAIL index=" << i << " kind=" << kind
                  << " deficit=" << u256s(loss - lhs) << "\n";
      }
    } else {
      const uint256_t margin = lhs - loss;
      if (margin < min_margin) {
        min_margin = margin;
        min_margin_index = i;
        min_margin_kind = int(kind);
      }
    }
  }

  auto u128s = [](unsigned __int128 x) {
    if (x == 0) return std::string("0");
    std::string s;
    while (x) {
      s.push_back(char('0' + x % 10));
      x /= 10;
    }
    std::reverse(s.begin(), s.end());
    return s;
  };

  std::cout << "GAMMA_NUM=14551\n";
  std::cout << "GAMMA_DEN=16000\n";
  std::cout << "Q_NUM=" << A << "\n";
  std::cout << "Q_DEN=" << B << "\n";
  std::cout << "ROWS=" << N << "\n";
  std::cout << "ORIGINAL_ROW_FAILURES=" << original_failures << "\n";
  std::cout << "Q_WEIGHTED_ROW_FAILURES=" << failures << "\n";
  std::cout << "MIN_ORIGINAL_SLACK=" << u128s(min_slack) << "\n";
  std::cout << "MIN_ORIGINAL_SLACK_INDEX=" << min_slack_index << "\n";
  if (failures == 0) {
    std::cout << "MIN_Q_MARGIN=" << u256s(min_margin) << "\n";
    std::cout << "MIN_Q_MARGIN_INDEX=" << min_margin_index << "\n";
    std::cout << "MIN_Q_MARGIN_KIND=" << min_margin_kind << "\n";
    std::cout << "Q1E16_EXACT_CERTIFICATE=PASS\n";
    return 0;
  }
  std::cout << "Q1E16_EXACT_CERTIFICATE=FAIL\n";
  return 1;
}
