#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

using u128 = unsigned __int128;
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
static u128 sq(uint64_t x) { return u128(x)*x; }
static u128 cu(uint64_t x) { return u128(x)*x*x; }
static std::string s128(u128 x) {
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

  uint64_t fail2=0, fail3=0, fail2_kind[3]={0,0,0}, fail3_kind[3]={0,0,0};
  uint64_t min2i=0,min3i=0;
  u128 min2n=0,min2d=1,min3n=0,min3d=1;
  const std::array<long double,9> exps =
    {1.0L,1.05L,1.10L,1.20L,1.30L,1.50L,1.75L,2.0L,3.0L};
  std::array<long double,9> sampleMin;
  sampleMin.fill(std::numeric_limits<long double>::infinity());
  std::array<uint64_t,9> sampleIndex{};

  for (uint64_t i=0;i<N;++i) {
    const uint64_t wi=rd(m.data+4*i);
    const uint64_t wf=rd(m.data+4ULL*four_index(i));
    const unsigned kind=unsigned(i%3);
    uint64_t wa=0;
    if (kind==0 || kind==2) {
      const uint32_t q = kind==0 ? l1_aux(i) : l3_aux(i);
      wa=std::min<uint64_t>(rd(m.data+4ULL*q),
        std::min<uint64_t>(rd(m.data+4ULL*(q+AUX)),
                           rd(m.data+4ULL*(q+2*AUX))));
    }
    const uint64_t c = kind==0 ? 3 : (kind==2 ? 6 : 0);

    const u128 lhs2=4*sq(wi), rhs2=sq(wf)+u128(c)*sq(wa);
    const u128 lhs3=4*cu(wi), rhs3=cu(wf)+u128(c)*cu(wa);
    if (rhs2<lhs2) { ++fail2; ++fail2_kind[kind]; }
    if (rhs3<lhs3) { ++fail3; ++fail3_kind[kind]; }
    if (i==0 || rhs2*min2d < min2n*lhs2) {
      min2n=rhs2; min2d=lhs2; min2i=i;
    }
    if (i==0 || rhs3*min3d < min3n*lhs3) {
      min3n=rhs3; min3d=lhs3; min3i=i;
    }

    if (i%10000==0) {
      for (size_t j=0;j<exps.size();++j) {
        const long double a=exps[j];
        const long double num=std::pow((long double)wf,a)
          + (long double)c*std::pow((long double)wa,a);
        const long double den=4.0L*std::pow((long double)wi,a);
        const long double ratio=num/den;
        if (ratio<sampleMin[j]) { sampleMin[j]=ratio; sampleIndex[j]=i; }
      }
    }
  }

  const u128 g2=std::gcd((uint64_t)min2n,(uint64_t)min2d);
  std::cout << "ROWS=" << N << "\n";
  std::cout << "A2_FAIL=" << fail2 << "\n";
  std::cout << "A2_FAIL_K0=" << fail2_kind[0] << "\n";
  std::cout << "A2_FAIL_K1=" << fail2_kind[1] << "\n";
  std::cout << "A2_FAIL_K2=" << fail2_kind[2] << "\n";
  std::cout << "A2_MIN_INDEX=" << min2i << "\n";
  std::cout << "A2_MIN_NUM=" << s128(min2n) << "\n";
  std::cout << "A2_MIN_DEN=" << s128(min2d) << "\n";
  std::cout << "A3_FAIL=" << fail3 << "\n";
  std::cout << "A3_FAIL_K0=" << fail3_kind[0] << "\n";
  std::cout << "A3_FAIL_K1=" << fail3_kind[1] << "\n";
  std::cout << "A3_FAIL_K2=" << fail3_kind[2] << "\n";
  std::cout << "A3_MIN_INDEX=" << min3i << "\n";
  std::cout << "A3_MIN_NUM=" << s128(min3n) << "\n";
  std::cout << "A3_MIN_DEN=" << s128(min3d) << "\n";
  std::cout << std::setprecision(20);
  for (size_t j=0;j<exps.size();++j)
    std::cout << "SAMPLE_A=" << exps[j] << " MIN=" << sampleMin[j]
              << " INDEX=" << sampleIndex[j] << "\n";
  std::cout << "A2_EXACT_GATE=" << (fail2==0 ? "PASS" : "FAIL") << "\n";
  std::cout << "A3_EXACT_GATE=" << (fail3==0 ? "PASS" : "FAIL") << "\n";
  return 0;
}
