#include <algorithm>
#include <array>
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

using u128 = __uint128_t;
using i128 = __int128_t;
static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t AUX = 129140163ULL;
static constexpr uint64_t MOD = 1162261467ULL;

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

static uint32_t rd(const unsigned char* p) {
  uint32_t v;
  std::memcpy(&v, p, 4);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  v = __builtin_bswap32(v);
#endif
  return v;
}
static uint64_t residue(uint64_t i) { return 3*i + 2; }
static uint32_t four_index(uint64_t i) {
  return uint32_t(((4*residue(i) % MOD)-2)/3);
}
static uint32_t l1_aux(uint64_t i) {
  return uint32_t(((((4*residue(i)-2)/3) % N)-2)/3);
}
static uint32_t l3_aux(uint64_t i) {
  return uint32_t(((((2*residue(i)-1)/3) % N)-2)/3);
}
static std::string ustr(u128 x) {
  if (!x) return "0";
  std::string s;
  while (x) { s.push_back(char('0' + x%10)); x/=10; }
  std::reverse(s.begin(), s.end());
  return s;
}
static std::string istr(i128 x) {
  return x < 0 ? "-" + ustr(u128(-x)) : ustr(u128(x));
}

int main(int argc, char** argv) {
  if (argc != 2) { std::cerr << "usage: scan WEIGHTS\n"; return 2; }
  Mapping m(argv[1]);
  if (m.bytes != 4ULL*N) { std::cerr << "bad size\n"; return 3; }

  constexpr unsigned LMAX = 36;
  std::array<uint64_t, LMAX+1> pass{}, equal{}, fail{}, firstStrict{};
  std::array<i128, LMAX+1> net{};
  std::array<uint64_t,3> neverKind{};
  uint64_t neverStrict = 0;
  uint64_t oneStepPassKind[3] = {0,0,0};
  uint64_t oneStepEqualKind[3] = {0,0,0};
  uint64_t oneStepFailKind[3] = {0,0,0};
  i128 oneStepNetKind[3] = {0,0,0};

  for (uint64_t root=0; root<N; ++root) {
    const uint64_t rootWeight = rd(m.data + 4*root);
    u128 auxiliaryAccumulator = 0;
    u128 powerFour = 1;
    uint64_t state = root;
    bool seenStrict = false;

    for (unsigned length=1; length<=LMAX; ++length) {
      const unsigned kind = unsigned(state % 3);
      u128 fullAux = 0;
      if (kind == 0 || kind == 2) {
        const uint32_t q = kind == 0 ? l1_aux(state) : l3_aux(state);
        const u128 sum = u128(rd(m.data + 4ULL*q))
          + rd(m.data + 4ULL*(q+AUX))
          + rd(m.data + 4ULL*(q+2*AUX));
        fullAux = kind == 0 ? sum : 2*sum;
      }

      auxiliaryAccumulator = 4*auxiliaryAccumulator + fullAux;
      state = four_index(state);
      powerFour *= 4;

      const u128 rhs = rd(m.data + 4ULL*state) + auxiliaryAccumulator;
      const u128 lhs = powerFour * rootWeight;
      const i128 defect = i128(rhs) - i128(lhs);
      net[length] += defect;

      if (defect > 0) {
        ++pass[length];
        if (!seenStrict) { ++firstStrict[length]; seenStrict = true; }
      } else if (defect < 0) {
        ++fail[length];
      } else {
        ++equal[length];
      }

      if (length == 1) {
        const unsigned rootKind = unsigned(root % 3);
        oneStepNetKind[rootKind] += defect;
        if (defect > 0) ++oneStepPassKind[rootKind];
        else if (defect < 0) ++oneStepFailKind[rootKind];
        else ++oneStepEqualKind[rootKind];
      }
    }

    if (!seenStrict) {
      ++neverStrict;
      ++neverKind[root % 3];
    }
  }

  std::cout << "ROWS=" << N << "\nLMAX=" << LMAX << "\n";
  for (unsigned kind=0; kind<3; ++kind) {
    std::cout << "ONE_STEP_KIND=" << kind
      << " PASS=" << oneStepPassKind[kind]
      << " EQUAL=" << oneStepEqualKind[kind]
      << " FAIL=" << oneStepFailKind[kind]
      << " NET_DEFECT=" << istr(oneStepNetKind[kind]) << "\n";
  }
  for (unsigned length=1; length<=LMAX; ++length) {
    std::cout << "L=" << length
      << " PASS=" << pass[length]
      << " EQUAL=" << equal[length]
      << " FAIL=" << fail[length]
      << " FIRST_STRICT=" << firstStrict[length]
      << " NET_DEFECT=" << istr(net[length]) << "\n";
  }
  std::cout << "NEVER_STRICT=" << neverStrict
    << "\nNEVER_KIND0=" << neverKind[0]
    << "\nNEVER_KIND1=" << neverKind[1]
    << "\nNEVER_KIND2=" << neverKind[2] << "\n";
  std::cout << "FULL_LIFT_ONE_STEP_UNIVERSAL="
    << (fail[1] == 0 && equal[1] == 0 ? "PASS" : "FAIL") << "\n";
  std::cout << "FULL_LIFT_ADAPTIVE_L36_UNIVERSAL="
    << (neverStrict == 0 ? "PASS" : "FAIL") << "\n";
  return 0;
}
