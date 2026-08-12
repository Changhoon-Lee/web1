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
static uint64_t numerator(const Mapping& m, uint64_t i) {
  const uint64_t wf = rd(m.data + 4ULL*four_index(i));
  const unsigned kind = unsigned(i % 3);
  if (kind == 1) return wf;
  const uint32_t q = kind == 0 ? l1_aux(i) : l3_aux(i);
  const uint64_t wa = std::min<uint64_t>(
    rd(m.data + 4ULL*q),
    std::min<uint64_t>(
      rd(m.data + 4ULL*(q+AUX)),
      rd(m.data + 4ULL*(q+2*AUX))));
  return wf + (kind == 0 ? 3ULL : 6ULL) * wa;
}
static uint64_t denominator(const Mapping& m, uint64_t i) {
  return 4ULL * rd(m.data + 4ULL*i);
}
static bool gt_threshold(const Mapping& m, uint64_t i,
                         uint64_t num, uint64_t den) {
  return u128(numerator(m,i))*den > u128(denominator(m,i))*num;
}
static bool ge_threshold(const Mapping& m, uint64_t i,
                         uint64_t num, uint64_t den) {
  return u128(numerator(m,i))*den >= u128(denominator(m,i))*num;
}
static std::string ustr(u128 x) {
  if (!x) return "0";
  std::string s;
  while (x) { s.push_back(char('0' + x%10)); x/=10; }
  std::reverse(s.begin(), s.end());
  return s;
}

int main(int argc, char** argv) {
  if (argc != 2) { std::cerr << "usage: scan WEIGHTS\n"; return 2; }
  Mapping m(argv[1]);
  if (m.bytes != 4ULL*N) { std::cerr << "bad size\n"; return 3; }

  constexpr unsigned KMAX = 64;
  std::array<uint64_t,KMAX+1> fail30{}, fail1{};
  uint64_t firstK30 = 0, firstK1 = 0;
  uint64_t worstStart30 = 0, worstStart1 = 0;
  unsigned maxWait30 = 0, maxWait1 = 0;
  uint64_t kind2Below30 = 0, kind2Below1 = 0;
  u128 minKind2Num = 0, minKind2Den = 1;
  uint64_t minKind2Index = 0;

  for (uint64_t i=0; i<N; ++i) {
    if (i % 3 == 2) {
      const u128 n = numerator(m,i), d = denominator(m,i);
      if (n*31 <= d*30) ++kind2Below30;
      if (n < d) ++kind2Below1;
      if (minKind2Num == 0 || n*minKind2Den < minKind2Num*d) {
        minKind2Num=n; minKind2Den=d; minKind2Index=i;
      }
    }

    uint64_t state = i;
    bool seen30 = false, seen1 = false;
    unsigned wait30 = KMAX+1, wait1 = KMAX+1;
    for (unsigned k=0; k<=KMAX; ++k) {
      if (!seen30 && gt_threshold(m,state,30,31)) {
        seen30=true; wait30=k;
      }
      if (!seen1 && gt_threshold(m,state,1,1)) {
        seen1=true; wait1=k;
      }
      state = four_index(state);
    }
    if (!seen30) wait30=KMAX+1;
    if (!seen1) wait1=KMAX+1;
    if (wait30 > maxWait30) { maxWait30=wait30; worstStart30=i; }
    if (wait1 > maxWait1) { maxWait1=wait1; worstStart1=i; }
    for (unsigned k=0; k<=KMAX; ++k) {
      if (wait30 > k) ++fail30[k];
      if (wait1 > k) ++fail1[k];
    }
  }

  for (unsigned k=0;k<=KMAX;++k) {
    if (fail30[k]==0 && firstK30==0) firstK30=k+1;
    if (fail1[k]==0 && firstK1==0) firstK1=k+1;
  }

  std::cout << "ROWS=" << N << "\n";
  std::cout << "KMAX=" << KMAX << "\n";
  std::cout << "KIND2_BELOW_OR_EQUAL_30_OVER_31=" << kind2Below30 << "\n";
  std::cout << "KIND2_BELOW_ONE=" << kind2Below1 << "\n";
  std::cout << "KIND2_MIN_INDEX=" << minKind2Index << "\n";
  std::cout << "KIND2_MIN_NUM=" << ustr(minKind2Num) << "\n";
  std::cout << "KIND2_MIN_DEN=" << ustr(minKind2Den) << "\n";
  for (unsigned k=0; k<=KMAX; ++k) {
    std::cout << "WINDOW=" << (k+1)
      << " FAIL_30_OVER_31=" << fail30[k]
      << " FAIL_ONE=" << fail1[k] << "\n";
  }
  std::cout << "MAX_WAIT_30_OVER_31=" << maxWait30 << "\n";
  std::cout << "WORST_START_30_OVER_31=" << worstStart30 << "\n";
  std::cout << "MAX_WAIT_ONE=" << maxWait1 << "\n";
  std::cout << "WORST_START_ONE=" << worstStart1 << "\n";
  std::cout << "FIRST_UNIVERSAL_WINDOW_30_OVER_31="
    << (firstK30 ? firstK30 : 0) << "\n";
  std::cout << "FIRST_UNIVERSAL_WINDOW_ONE="
    << (firstK1 ? firstK1 : 0) << "\n";
  return 0;
}
