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
using u128=__uint128_t; using i128=__int128_t;
static constexpr uint64_t N=387420489ULL,AUX=129140163ULL,MOD=1162261467ULL;
struct M{int f=-1;size_t n=0;const unsigned char*p=nullptr;explicit M(const char*x){f=open(x,O_RDONLY);if(f<0)throw std::runtime_error("open");struct stat s{};if(fstat(f,&s))throw std::runtime_error("stat");n=s.st_size;p=(const unsigned char*)mmap(nullptr,n,PROT_READ,MAP_PRIVATE,f,0);if(p==MAP_FAILED)throw std::runtime_error("mmap");}~M(){if(p&&p!=MAP_FAILED)munmap((void*)p,n);if(f>=0)close(f);}};
static uint32_t rd(const unsigned char*p){uint32_t v;memcpy(&v,p,4);return v;}
static uint64_t r(uint64_t i){return 3*i+2;} static uint32_t fidx(uint64_t i){return ((4*r(i)%MOD)-2)/3;}
static uint32_t aidx(uint64_t i){unsigned k=i%3;return k==0?(((((4*r(i)-2)/3)%N)-2)/3):(((((2*r(i)-1)/3)%N)-2)/3);}
static uint64_t cval(uint64_t i){return i%3==0?3:(i%3==2?6:0);} static std::string us(u128 x){if(!x)return"0";std::string s;while(x){s.push_back('0'+x%10);x/=10;}reverse(s.begin(),s.end());return s;} static std::string is(i128 x){return x<0?"-"+us(-x):us(x);}
int main(int ac,char**av){if(ac!=2)return 2;M m(av[1]);if(m.n!=4ULL*N)return 3;constexpr unsigned LMAX=18;std::array<uint64_t,LMAX+1> fail{},eq{},pass{},firstPass{};std::array<i128,LMAX+1> net{};std::array<uint64_t,3> neverKind{};uint64_t never=0;
 for(uint64_t i=0;i<N;++i){u128 lhs=rd(m.p+4*i),rhs=0,pow4=1;uint64_t j=i;bool seen=false;for(unsigned L=1;L<=LMAX;++L){uint64_t c=cval(j),wa=0;if(c){uint32_t q=aidx(j);wa=std::min<uint64_t>(rd(m.p+4ULL*q),std::min<uint64_t>(rd(m.p+4ULL*(q+AUX)),rd(m.p+4ULL*(q+2*AUX))));}rhs=4*rhs+u128(4*c)*wa;j=fidx(j);rhs+=rd(m.p+4ULL*j); /* correction below by direct recompute recurrence */
   /* The previous update double-counts old principal. Recompute exact macro incrementally:
      R_L = w(f^L i) + sum_{t=0}^{L-1}4^(L-1-t)c_t a_t.
      Maintain aux accumulator A_L=4*A_{L-1}+c_{L-1}a_{L-1}. */
 }
 /* redo cleanly */
 u128 auxacc=0; j=i; pow4=1; seen=false;
 for(unsigned L=1;L<=LMAX;++L){uint64_t c=cval(j),wa=0;if(c){uint32_t q=aidx(j);wa=std::min<uint64_t>(rd(m.p+4ULL*q),std::min<uint64_t>(rd(m.p+4ULL*(q+AUX)),rd(m.p+4ULL*(q+2*AUX))));}auxacc=4*auxacc+u128(c)*wa;j=fidx(j);pow4*=4;u128 R=rd(m.p+4ULL*j)+auxacc,LH=pow4*rd(m.p+4*i);i128 d=i128(R)-i128(LH);net[L]+=d;if(d>0){pass[L]++;if(!seen){firstPass[L]++;seen=true;}}else if(d<0)fail[L]++;else {eq[L]++;if(!seen){firstPass[L]++;seen=true;}}}
 if(!seen){never++;neverKind[i%3]++;}}
 std::cout<<"ROWS="<<N<<"\nLMAX="<<LMAX<<"\n";for(unsigned L=1;L<=LMAX;++L)std::cout<<"L="<<L<<" PASS="<<pass[L]<<" EQUAL="<<eq[L]<<" FAIL="<<fail[L]<<" FIRST_NONFAIL="<<firstPass[L]<<" NET_DEFECT="<<is(net[L])<<"\n";std::cout<<"NEVER_NONFAIL="<<never<<"\nNEVER_K0="<<neverKind[0]<<"\nNEVER_K1="<<neverKind[1]<<"\nNEVER_K2="<<neverKind[2]<<"\n";return 0;}
