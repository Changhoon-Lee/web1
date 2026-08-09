#include <algorithm>
#include <array>
#include <boost/multiprecision/cpp_int.hpp>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

using boost::multiprecision::cpp_int;
static constexpr uint64_t N = 387420489ULL;
static constexpr uint64_t A = 129140163ULL;
static constexpr uint32_t COUNT_CAP = 1000000U;
static constexpr uint64_t STATE_CAP = 100000000ULL;

struct Mapping {
  int fd = -1;
  size_t bytes = 0;
  const unsigned char* data = nullptr;
  explicit Mapping(const char* path) {
    fd = open(path, O_RDONLY);
    if (fd < 0) throw std::runtime_error("open failed");
    struct stat st {};
    if (fstat(fd, &st) != 0) throw std::runtime_error("fstat failed");
    bytes = static_cast<size_t>(st.st_size);
    data = static_cast<const unsigned char*>(
      mmap(nullptr, bytes, PROT_READ, MAP_PRIVATE, fd, 0));
    if (data == MAP_FAILED) throw std::runtime_error("mmap failed");
  }
  Mapping(const Mapping&) = delete;
  Mapping& operator=(const Mapping&) = delete;
  ~Mapping() {
    if (data && data != MAP_FAILED) munmap((void*)data, bytes);
    if (fd >= 0) close(fd);
  }
};

struct Shift { uint16_t a; uint16_t b; };
struct Label { uint32_t index; Shift s; };

static cpp_int ipow(unsigned base, unsigned exp) {
  cpp_int out = 1, b = base;
  while (exp) {
    if (exp & 1u) out *= b;
    b *= b;
    exp >>= 1u;
  }
  return out;
}

static bool value_nonnegative(Shift s) {
  return ipow(3, s.a) >= ipow(2, s.b);
}

static bool value_less(Shift x, Shift y) {
  const int da = int(x.a) - int(y.a);
  const int db = int(x.b) - int(y.b);
  if (da == 0) return db > 0;
  if (db == 0) return da < 0;
  if (da > 0 && db < 0) return false;
  if (da < 0 && db > 0) return true;
  if (da > 0) return ipow(3, unsigned(da)) < ipow(2, unsigned(db));
  return ipow(3, unsigned(-da)) > ipow(2, unsigned(-db));
}

static uint32_t read_u32(const unsigned char* p) {
  uint32_t v;
  std::memcpy(&v, p, sizeof(v));
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  v = __builtin_bswap32(v);
#endif
  return v;
}

struct Engine {
  const unsigned char* weights;
  const unsigned char* potential;
  uint64_t states = 0;
  uint64_t terminals = 0;
  uint32_t max_depth = 0;
  bool capped = false;

  uint32_t w(uint32_t i) const { return read_u32(weights + 4ULL * i); }
  uint8_t pot(uint32_t i) const { return potential[i]; }
  static uint32_t principal(uint32_t i) {
    return uint32_t((4ULL * i + 2ULL) % N);
  }
  static std::array<uint32_t, 3> d1(uint32_t i) {
    const uint64_t base = (4ULL * i + 2ULL) % N;
    const uint64_t q = (base - 2ULL) / 3ULL;
    return {uint32_t(q), uint32_t(q + A), uint32_t(q + 2 * A)};
  }
  static std::array<uint32_t, 3> d3(uint32_t i) {
    const uint64_t base = (2ULL * i + 1ULL) % N;
    const uint64_t q = (base - 2ULL) / 3ULL;
    return {uint32_t(q), uint32_t(q + A), uint32_t(q + 2 * A)};
  }
  int fallback(const std::array<uint32_t, 3>& c) const {
    const uint8_t v0 = pot(c[0]), v1 = pot(c[1]), v2 = pot(c[2]);
    if (v0 <= v1 && v0 <= v2) return 0;
    if (v1 <= v2) return 1;
    return 2;
  }
  static bool dominated(const Label& child, const std::vector<Label>& path) {
    if (!value_nonnegative(child.s)) return false;
    for (const auto& prior : path) {
      if (prior.index == child.index && value_less(prior.s, child.s)) return true;
    }
    return false;
  }
  static uint32_t capped_add(uint32_t x, uint32_t y) {
    if (x >= COUNT_CAP || y >= COUNT_CAP || x > COUNT_CAP - y) return COUNT_CAP;
    return x + y;
  }

  uint32_t count_dfs(Label current, std::vector<Label>& path, uint32_t depth) {
    if (++states > STATE_CAP) {
      capped = true;
      return 0;
    }
    max_depth = std::max(max_depth, depth);
    if (!value_nonnegative(current.s)) {
      ++terminals;
      return 1;
    }
    path.push_back(current);
    const Label pchild{principal(current.index),
      Shift{current.s.a, uint16_t(current.s.b + 2)}};
    const uint32_t pcount = count_dfs(pchild, path, depth + 1);
    if (capped || pcount >= COUNT_CAP) {
      path.pop_back();
      return pcount;
    }
    const unsigned row = current.index % 3U;
    if (row == 1U) {
      path.pop_back();
      return pcount;
    }
    const auto indices = row == 0U ? d1(current.index) : d3(current.index);
    std::array<Label, 3> children;
    std::array<bool, 3> keep{};
    int kept = 0;
    for (int q = 0; q < 3; ++q) {
      children[q] = Label{indices[q],
        row == 0U
          ? Shift{uint16_t(current.s.a + 1), uint16_t(current.s.b + 2)}
          : Shift{uint16_t(current.s.a + 1), uint16_t(current.s.b + 1)}};
      keep[q] = !dominated(children[q], path);
      kept += keep[q] ? 1 : 0;
    }
    if (kept == 0) keep[fallback(indices)] = true;
    uint32_t amin = COUNT_CAP;
    for (int q = 0; q < 3; ++q) {
      if (!keep[q]) continue;
      const uint32_t value = count_dfs(children[q], path, depth + 1);
      if (capped) {
        path.pop_back();
        return 0;
      }
      amin = std::min(amin, value);
      if (amin == 1) break;
    }
    path.pop_back();
    return capped_add(pcount, amin);
  }

  uint32_t root_count(uint32_t root) {
    states = terminals = 0;
    max_depth = 0;
    capped = false;
    std::vector<Label> path;
    path.reserve(128);
    return count_dfs(Label{root, Shift{0, 0}}, path, 0);
  }
};

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: probe WEIGHTS POTENTIAL\n";
    return 2;
  }
  Mapping wm(argv[1]), pm(argv[2]);
  if (wm.bytes != 4ULL * N || pm.bytes != N) {
    std::cerr << "bad payload sizes\n";
    return 3;
  }
  Engine e{wm.data, pm.data};
  using Pair = std::pair<uint32_t, uint32_t>;
  std::priority_queue<Pair, std::vector<Pair>, std::greater<Pair>> top;
  uint32_t global_max = 0, global_max_index = 0;
  unsigned __int128 sum_weight = 0;
  for (uint32_t i = 0; i < N; ++i) {
    const uint32_t wi = e.w(i);
    sum_weight += wi;
    if (wi > global_max) {
      global_max = wi;
      global_max_index = i;
    }
    if (top.size() < 512) top.push({wi, i});
    else if (wi > top.top().first) {
      top.pop();
      top.push({wi, i});
    }
  }
  std::vector<Pair> ranked;
  while (!top.empty()) {
    ranked.push_back(top.top());
    top.pop();
  }
  std::sort(ranked.rbegin(), ranked.rend());
  std::set<uint32_t> roots;
  for (const auto& [wi, i] : ranked) roots.insert(i);
  for (uint32_t i : {0U, 1U, 2U, 3U, 4U, 5U, 13U, 37U,
                     uint32_t(N / 4), uint32_t(N / 2),
                     uint32_t(3 * N / 4), uint32_t(N - 1)}) roots.insert(i);
  std::mt19937_64 rng(0x424f554e44415259ULL);
  for (int q = 0; q < 128; ++q) roots.insert(uint32_t(rng() % N));

  const long double mean_weight = (long double)sum_weight / (long double)N;
  std::cout << std::setprecision(22)
            << "N=" << N << "\n"
            << "COUNT_CAP=" << COUNT_CAP << "\n"
            << "STATE_CAP=" << STATE_CAP << "\n"
            << "GLOBAL_MAX_WEIGHT=" << global_max << "\n"
            << "GLOBAL_MAX_INDEX=" << global_max_index << "\n"
            << "MEAN_WEIGHT=" << mean_weight << "\n";
  long double min_top_factor = std::numeric_limits<long double>::infinity();
  uint64_t complete = 0, state_capped = 0, count_capped = 0;
  for (uint32_t root : roots) {
    const uint32_t count = e.root_count(root);
    const uint32_t wi = e.w(root);
    const long double factor = e.capped ? 0.0L :
      (long double)count * (long double)global_max / (long double)wi;
    const bool is_top = std::binary_search(ranked.begin(), ranked.end(),
      Pair{wi, root}, std::greater<Pair>());
    if (!e.capped) {
      ++complete;
      if (count >= COUNT_CAP) ++count_capped;
      if (is_top) min_top_factor = std::min(min_top_factor, factor);
    } else {
      ++state_capped;
    }
    std::cout << "ROOT=" << root
              << " WEIGHT=" << wi
              << " ROW=" << (root % 3U)
              << " BOUNDARY_COUNT=" << count
              << " COUNT_TIMES_MAX_OVER_WEIGHT=" << factor
              << " TOP512=" << (is_top ? 1 : 0)
              << " STATES=" << e.states
              << " TERMINALS=" << e.terminals
              << " MAX_DEPTH=" << e.max_depth
              << " STATE_CAPPED=" << (e.capped ? 1 : 0)
              << " COUNT_CAPPED=" << (count >= COUNT_CAP ? 1 : 0)
              << "\n";
  }
  std::cout << "ROOTS=" << roots.size() << "\n"
            << "COMPLETE_ROOTS=" << complete << "\n"
            << "STATE_CAPPED_ROOTS=" << state_capped << "\n"
            << "COUNT_CAPPED_ROOTS=" << count_capped << "\n"
            << "MIN_TOP512_FACTOR=" << min_top_factor << "\n";
  return 0;
}
