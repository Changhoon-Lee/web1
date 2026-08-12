#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
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
  return v;
}
static uint64_t residue(uint64_t i) { return 3*i + 2; }
static uint32_t four_index(uint64_t i) {
  return uint32_t(((4*residue(i) % MOD)-2)/3);
}
static uint32_t aux_index(uint64_t i) {
  const unsigned kind = unsigned(i % 3);
  return kind == 0
    ? uint32_t(((((4*residue(i)-2)/3) % N)-2)/3)
    : uint32_t(((((2*residue(i)-1)/3) % N)-2)/3);
}
static uint64_t multiplicity(uint64_t i) {
  return i % 3 == 0 ? 3 : (i % 3 == 2 ? 6 : 0);
}
static std::string unsigned_string(u128 x) {
  if (!x) return "0";
  std::string s;
  while (x) { s.push_back(char('0' + x%10)); x/=10; }
  std::reverse(s.begin(), s.end());
  return s;
}
static std::string signed_string(i128 x) {
  return x < 0 ? "-" + unsigned_string(u128(-x)) : unsigned_string(u128(x));
}

int main(int argc, char** argv) {
  if (argc != 2) { std::cerr << "usage: scan WEIGHTS\n"; return 2; }
  Mapping m(argv[1]);
  if (m.bytes != 4ULL*N) { std::cerr << "bad size\n"; return 3; }

  constexpr unsigned LMAX = 18;
  std::array<uint64_t, LMAX+1> fail{}, equal{}, pass{}, firstNonfail{};
  std::array<i128, LMAX+1> net{};
  std::array<uint64_t,3> neverKind{};
  uint64_t never = 0;

  for (uint64_t i=0; i<N; ++i) {
    u128 auxiliaryAccumulator = 0;
    u128 powerFour = 1;
    uint64_t state = i;
    bool alreadyNonfail = false;
    const uint64_t rootWeight = rd(m.data + 4*i);

    for (unsigned length=1; length<=LMAX; ++length) {
      const uint64_t c = multiplicity(state);
      uint64_t auxiliaryWeight = 0;
      if (c) {
        const uint32_t q = aux_index(state);
        auxiliaryWeight = std::min<uint64_t>(
          rd(m.data + 4ULL*q),
          std::min<uint64_t>(
            rd(m.data + 4ULL*(q+AUX)),
            rd(m.data + 4ULL*(q+2*AUX))));
      }

      auxiliaryAccumulator = 4*auxiliaryAccumulator + u128(c)*auxiliaryWeight;
      state = four_index(state);
      powerFour *= 4;

      const u128 rhs = rd(m.data + 4ULL*state) + auxiliaryAccumulator;
      const u128 lhs = powerFour * rootWeight;
      const i128 defect = i128(rhs) - i128(lhs);
      net[length] += defect;

      if (defect > 0) {
        ++pass[length];
        if (!alreadyNonfail) { ++firstNonfail[length]; alreadyNonfail = true; }
      } else if (defect < 0) {
        ++fail[length];
      } else {
        ++equal[length];
        if (!alreadyNonfail) { ++firstNonfail[length]; alreadyNonfail = true; }
      }
    }

    if (!alreadyNonfail) {
      ++never;
      ++neverKind[i % 3];
    }
  }

  std::cout << "ROWS=" << N << "\nLMAX=" << LMAX << "\n";
  for (unsigned length=1; length<=LMAX; ++length) {
    std::cout << "L=" << length
      << " PASS=" << pass[length]
      << " EQUAL=" << equal[length]
      << " FAIL=" << fail[length]
      << " FIRST_NONFAIL=" << firstNonfail[length]
      << " NET_DEFECT=" << signed_string(net[length]) << "\n";
  }
  std::cout << "NEVER_NONFAIL=" << never
    << "\nNEVER_K0=" << neverKind[0]
    << "\nNEVER_K1=" << neverKind[1]
    << "\nNEVER_K2=" << neverKind[2] << "\n";
  return 0;
}
