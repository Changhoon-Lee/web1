#include <cassert>
#include <cstdint>
#include <iostream>
#include <random>
#include <tuple>
#include <vector>

using i128 = __int128_t;

static i128 powi(i128 a, int e) {
  i128 z = 1;
  while (e-- > 0) z *= a;
  return z;
}

static bool backward_ok(i128 A, const std::vector<i128>& a,
                        const std::vector<int>& r, i128& delta0) {
  i128 d = 0;
  for (int i = static_cast<int>(a.size()) - 1; i >= 0; --i) {
    i128 den = powi(3, r[i]);
    if (d % den != 0) return false;
    d = a[i] + A * (d / den);
  }
  delta0 = d;
  return true;
}

static void numerator(i128 A, const std::vector<i128>& a,
                      const std::vector<int>& r, i128& C, i128& D) {
  const int n = static_cast<int>(a.size());
  std::vector<int> R(n, 0);
  for (int j = 1; j < n; ++j) R[j] = R[j - 1] + r[j - 1];
  const int total = R.back();
  C = 0;
  for (int j = 0; j < n; ++j)
    C += powi(A, j) * a[j] * powi(3, total - R[j]);
  D = powi(3, total);
}

static std::uint64_t mod_inverse(std::uint64_t a, std::uint64_t m) {
  std::int64_t t = 0, nt = 1;
  std::int64_t r = static_cast<std::int64_t>(m);
  std::int64_t nr = static_cast<std::int64_t>(a % m);
  while (nr != 0) {
    std::int64_t q = r / nr;
    std::tie(t, nt) = std::make_pair(nt, t - q * nt);
    std::tie(r, nr) = std::make_pair(nr, r - q * nr);
  }
  if (t < 0) t += static_cast<std::int64_t>(m);
  return static_cast<std::uint64_t>(t);
}

static std::uint64_t forward_mod(std::uint64_t A,
                                 const std::vector<i128>& a,
                                 const std::vector<int>& rs, int K,
                                 std::uint64_t x) {
  std::uint64_t m = 1;
  for (int i = 0; i < K; ++i) m *= 3;
  const std::uint64_t inv = mod_inverse(A, m);
  for (std::size_t i = 0; i < a.size(); ++i) {
    std::int64_t ai = static_cast<std::int64_t>(a[i] % static_cast<i128>(m));
    std::int64_t z = static_cast<std::int64_t>(x) - ai;
    z %= static_cast<std::int64_t>(m);
    if (z < 0) z += static_cast<std::int64_t>(m);
    std::uint64_t p = 1;
    for (int j = 0; j < rs[i]; ++j) p = (p * 3) % m;
    x = static_cast<std::uint64_t>((static_cast<__uint128_t>(p) * inv % m) *
                                   static_cast<std::uint64_t>(z) % m);
  }
  return x;
}

int main() {
  const i128 A = 16;
  std::uint64_t integer_cases = 0;
  for (int n = 1; n <= 5; ++n) {
    std::uint64_t r_count = 1, a_count = 1;
    for (int i = 0; i < n; ++i) { r_count *= 3; a_count *= 7; }
    for (std::uint64_t rc = 0; rc < r_count; ++rc) {
      std::uint64_t z = rc;
      std::vector<int> rs(n);
      for (int i = 0; i < n; ++i) { rs[i] = z % 3; z /= 3; }
      for (std::uint64_t ac = 0; ac < a_count; ++ac) {
        z = ac;
        std::vector<i128> a(n);
        for (int i = 0; i < n; ++i) { a[i] = static_cast<int>(z % 7) - 3; z /= 7; }
        i128 d0 = 0, C = 0, D = 0;
        bool ok = backward_ok(A, a, rs, d0);
        numerator(A, a, rs, C, D);
        assert(ok == (C % D == 0));
        if (ok) assert(d0 == C / D);
        ++integer_cases;
      }
    }
  }

  std::uint64_t fiber_cases = 0;
  for (int K = 1; K <= 6; ++K) {
    std::uint64_t mod = 1;
    for (int i = 0; i < K; ++i) mod *= 3;
    for (int n = 1; n <= 3; ++n) {
      std::uint64_t r_count = 1, a_count = 1;
      for (int i = 0; i < n; ++i) { r_count *= 3; a_count *= 5; }
      for (std::uint64_t rc = 0; rc < r_count; ++rc) {
        std::uint64_t z = rc;
        std::vector<int> rs(n);
        int S = 0;
        for (int i = 0; i < n; ++i) { rs[i] = z % 3; S += rs[i]; z /= 3; }
        for (std::uint64_t ac = 0; ac < a_count; ++ac) {
          z = ac;
          std::vector<i128> a(n);
          for (int i = 0; i < n; ++i) { a[i] = static_cast<int>(z % 5) - 2; z /= 5; }
          std::vector<std::uint64_t> pre;
          for (std::uint64_t x = 0; x < mod; ++x)
            if (forward_mod(16, a, rs, K, x) == 0) pre.push_back(x);
          std::uint64_t expected_nonzero = 1;
          for (int i = 0; i < std::min(S, K); ++i) expected_nonzero *= 3;
          assert(pre.empty() || pre.size() == expected_nonzero);
          if (K >= S) {
            i128 C = 0, D = 0;
            numerator(A, a, rs, C, D);
            bool compatible = (C % D == 0);
            assert((!pre.empty()) == compatible);
            if (compatible) {
              std::uint64_t aliases = 1;
              for (int i = 0; i < S; ++i) aliases *= 3;
              assert(pre.size() == aliases);
            }
          }
          ++fiber_cases;
        }
      }
    }
  }

  std::mt19937_64 rng(20260808);
  constexpr std::uint64_t random_cases = 100000;
  for (std::uint64_t t = 0; t < random_cases; ++t) {
    int n = 1 + rng() % 6;
    std::vector<i128> a(n);
    std::vector<int> rs(n);
    for (int i = 0; i < n; ++i) {
      a[i] = static_cast<std::int64_t>(rng() % 2000001) - 1000000;
      rs[i] = rng() % 4;
    }
    i128 d0 = 0, C = 0, D = 0;
    bool ok = backward_ok(1 << 14, a, rs, d0);
    numerator(1 << 14, a, rs, C, D);
    assert(ok == (C % D == 0));
    if (ok) assert(d0 == C / D);
  }

  std::cout << "T089_GLOBAL_COMPATIBILITY_COLLAPSE_CPP=PASS\n";
  std::cout << "INTEGER_EXHAUSTIVE_CASES=" << integer_cases << "\n";
  std::cout << "MODULAR_FIBER_EXHAUSTIVE_CASES=" << fiber_cases << "\n";
  std::cout << "RANDOM_CASES=" << random_cases << "\n";
}
