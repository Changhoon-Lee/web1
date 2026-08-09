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
#include <unordered_set>
#include <utility>
#include <vector>
#include <unistd.h>

using boost::multiprecision::cpp_int;
static constexpr uint64_t N = 387420489ULL;       // 3^18
static constexpr uint64_t A = 129140163ULL;       // 3^17
static constexpr uint64_t TREE_STATE_CAP = 2000000ULL;
static constexpr uint64_t CLOSURE_CAP = 250000ULL;

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
  cpp_int out = 1;
  cpp_int b = base;
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
  // x.a*alpha-x.b < y.a*alpha-y.b iff da*alpha < db.
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
  uint32_t global_max = 0;
  uint32_t global_max_index = 0;
  uint64_t tree_states = 0;
  bool tree_capped = false;

  uint32_t w(uint32_t i) const { return read_u32(weights + 4ULL * i); }
  uint8_t pot(uint32_t i) const { return potential[i]; }

  static uint32_t principal(uint32_t i) {
    return uint32_t((4ULL * i + 2ULL) % N);
  }

  static std::array<uint32_t, 3> d1(uint32_t i) {
    const uint64_t base = (4ULL * i + 2ULL) % N;
    const uint64_t aux = (base - 2ULL) / 3ULL;
    return {uint32_t(aux), uint32_t(aux + A), uint32_t(aux + 2 * A)};
  }

  static std::array<uint32_t, 3> d3(uint32_t i) {
    const uint64_t base = (2ULL * i + 1ULL) % N;
    const uint64_t aux = (base - 2ULL) / 3ULL;
    return {uint32_t(aux), uint32_t(aux + A), uint32_t(aux + 2 * A)};
  }

  int fallback(const std::array<uint32_t, 3>& c) const {
    const uint8_t v0 = pot(c[0]), v1 = pot(c[1]), v2 = pot(c[2]);
    if (v0 <= v1 && v0 <= v2) return 0;
    if (v1 <= v2) return 1;
    return 2;
  }

  static bool dominated(const Label& child, const std::vector<Label>& path) {
    if (!value_nonnegative(child.s)) return false;
    for (const auto& e : path) {
      if (e.index == child.index && value_less(e.s, child.s)) return true;
    }
    return false;
  }

  void leaves_dfs(Label current, std::vector<Label>& path,
                  std::unordered_set<uint32_t>& leaves) {
    if (++tree_states > TREE_STATE_CAP) {
      tree_capped = true;
      return;
    }
    if (!value_nonnegative(current.s)) {
      leaves.insert(current.index);
      return;
    }
    path.push_back(current);
    Label pc{principal(current.index), Shift{current.s.a,
      uint16_t(current.s.b + 2)}};
    leaves_dfs(pc, path, leaves);
    if (tree_capped) {
      path.pop_back();
      return;
    }
    const unsigned row = current.index % 3U;
    if (row == 0U || row == 2U) {
      const auto child_indices = row == 0U ? d1(current.index) : d3(current.index);
      std::array<Label, 3> children;
      for (int q = 0; q < 3; ++q) {
        children[q] = Label{child_indices[q],
          row == 0U
            ? Shift{uint16_t(current.s.a + 1), uint16_t(current.s.b + 2)}
            : Shift{uint16_t(current.s.a + 1), uint16_t(current.s.b + 1)}};
      }
      std::array<bool, 3> keep{};
      int kept = 0;
      for (int q = 0; q < 3; ++q) {
        keep[q] = !dominated(children[q], path);
        kept += keep[q] ? 1 : 0;
      }
      if (kept == 0) keep[fallback(child_indices)] = true;
      for (int q = 0; q < 3 && !tree_capped; ++q) {
        if (keep[q]) leaves_dfs(children[q], path, leaves);
      }
    }
    path.pop_back();
  }

  std::vector<uint32_t> root_leaves(uint32_t root, uint64_t& states,
                                    bool& capped) {
    tree_states = 0;
    tree_capped = false;
    std::unordered_set<uint32_t> set;
    set.reserve(1024);
    std::vector<Label> path;
    path.reserve(128);
    leaves_dfs(Label{root, Shift{0, 0}}, path, set);
    states = tree_states;
    capped = tree_capped;
    std::vector<uint32_t> out(set.begin(), set.end());
    std::sort(out.begin(), out.end());
    return out;
  }

  struct ClosureResult {
    uint64_t size = 0, expanded = 0, tree_states = 0, edge_count = 0;
    uint32_t max_weight = 0, max_index = 0;
    bool closure_capped = false, tree_capped = false, hit_global = false;
  };

  ClosureResult closure(uint32_t root) {
    ClosureResult r;
    std::unordered_set<uint32_t> seen;
    seen.reserve(CLOSURE_CAP * 2);
    std::queue<uint32_t> q;
    seen.insert(root);
    q.push(root);
    while (!q.empty()) {
      if (seen.size() >= CLOSURE_CAP) {
        r.closure_capped = true;
        break;
      }
      const uint32_t i = q.front();
      q.pop();
      ++r.expanded;
      uint64_t states = 0;
      bool capped = false;
      auto ls = root_leaves(i, states, capped);
      r.tree_states += states;
      r.edge_count += ls.size();
      if (capped) {
        r.tree_capped = true;
        break;
      }
      for (uint32_t j : ls) {
        if (seen.insert(j).second) q.push(j);
      }
    }
    r.size = seen.size();
    for (uint32_t i : seen) {
      const uint32_t wi = w(i);
      if (wi > r.max_weight) {
        r.max_weight = wi;
        r.max_index = i;
      }
      if (i == global_max_index) r.hit_global = true;
    }
    return r;
  }
};

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: probe WEIGHTS POTENTIAL\n";
    return 2;
  }
  Mapping wm(argv[1]), pm(argv[2]);
  if (wm.bytes != 4ULL * N || pm.bytes != N) {
    std::cerr << "bad sizes\n";
    return 3;
  }
  Engine e{wm.data, pm.data};
  std::vector<std::pair<uint32_t, uint32_t>> top;
  top.reserve(64);
  uint32_t minw = std::numeric_limits<uint32_t>::max(), mini = 0;
  for (uint32_t i = 0; i < N; ++i) {
    const uint32_t wi = e.w(i);
    if (wi > e.global_max) {
      e.global_max = wi;
      e.global_max_index = i;
    }
    if (wi < minw) {
      minw = wi;
      mini = i;
    }
    if (top.size() < 64) {
      top.push_back({wi, i});
      if (top.size() == 64) std::sort(top.begin(), top.end());
    } else if (wi > top.front().first) {
      top.front() = {wi, i};
      std::sort(top.begin(), top.end());
    }
  }
  std::reverse(top.begin(), top.end());
  std::set<uint32_t> roots;
  roots.insert(e.global_max_index);
  roots.insert(mini);
  for (size_t k = 0; k < 16 && k < top.size(); ++k) roots.insert(top[k].second);
  for (uint32_t x : {0U, 1U, 2U, 3U, 4U, 5U, 13U, 37U, 1000U,
                     1000000U, uint32_t(N / 4), uint32_t(N / 2),
                     uint32_t(3 * N / 4), uint32_t(N - 1)}) {
    roots.insert(x);
  }
  std::mt19937_64 rng(0x4b31394c4f43414cULL);
  for (int k = 0; k < 32; ++k) roots.insert(uint32_t(rng() % N));
  std::cout << "N=" << N
            << "\nGLOBAL_MAX_WEIGHT=" << e.global_max
            << "\nGLOBAL_MAX_INDEX=" << e.global_max_index
            << "\nMIN_WEIGHT=" << minw
            << "\nMIN_INDEX=" << mini << "\n";
  std::cout << std::setprecision(18);
  for (uint32_t root : roots) {
    const auto r = e.closure(root);
    const long double ratio = static_cast<long double>(e.w(root)) /
                              static_cast<long double>(r.max_weight);
    std::cout << "ROOT=" << root
              << " WEIGHT=" << e.w(root)
              << " CLOSURE_SIZE=" << r.size
              << " EXPANDED=" << r.expanded
              << " EDGE_COUNT=" << r.edge_count
              << " TREE_STATES=" << r.tree_states
              << " LOCAL_MAX=" << r.max_weight
              << " LOCAL_MAX_INDEX=" << r.max_index
              << " ROOT_OVER_LOCAL_MAX=" << ratio
              << " HIT_GLOBAL_MAX=" << (r.hit_global ? 1 : 0)
              << " CLOSURE_CAPPED=" << (r.closure_capped ? 1 : 0)
              << " TREE_CAPPED=" << (r.tree_capped ? 1 : 0)
              << "\n";
  }
  return 0;
}
