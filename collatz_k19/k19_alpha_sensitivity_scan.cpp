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
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static constexpr uint64_t N=387420489ULL,AUX=129140163ULL,MOD=1162261467ULL;
struct Mapping{int fd=-1;size_t bytes=0;const unsigned char*data=nullptr;explicit Mapping(const char*p){fd=open(p,O_RDONLY);if(fd<0)throw std::runtime_error("open");struct stat st{};if(fstat(fd,&st))throw std::runtime_error("stat");bytes=st.st_size;data=(const unsigned char*)mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,fd,0);if(data==MAP_FAILED)throw std::runtime_error("mmap");}~Mapping(){if(data&&data!=MAP_FAILED)munmap((void*)data,bytes);if(fd>=0)close(fd);}};
static uint32_t rd(const unsigned char*p){uint32_t v;memcpy(&v,p,4);return v;}
static uint64_t residue(uint64_t i){return 3*i+2;}
static uint32_t four_index(uint64_t i){return uint32_t(((4*residue(i)%MOD)-2)/3);}
static uint32_t l1_aux(uint64_t i){return uint32_t(((((4*residue(i)-2)/3)%N)-2)/3);}
static uint32_t l3_aux(uint64_t i){return uint32_t(((((2*residue(i)-1)/3)%N)-2)/3);}
int main(int argc,char**argv){if(argc!=2){std::cerr<<"usage WEIGHTS\n";return 2;}Mapping m(argv[1]);if(m.bytes!=4*N)return 3;
 const long double g=14551.0L/16000.0L;
 const long double c0=powl(4.0L,-g),c1=powl(0.75L,g),c3=powl(1.5L,g);
 const long double l4=logl(4.0L), l075=logl(0.75L), l15=logl(1.5L);
 std::array<long double,3> minlin;minlin.fill(std::numeric_limits<long double>::infinity());
 std::array<uint64_t,3> idx{};std::array<long double,3> fval{},dval{};
 const std::array<long double,9> eps={1e-16L,1e-15L,5e-15L,1e-14L,1e-13L,1e-12L,1e-11L,1e-10L,1e-9L};
 std::array<uint64_t,eps.size()> fails{};std::array<long double,eps.size()> minmargin;minmargin.fill(std::numeric_limits<long double>::infinity());std::array<uint64_t,eps.size()> minidx{};
 for(uint64_t i=0;i<N;++i){long double w=rd(m.data+4*i),wf=rd(m.data+4ULL*four_index(i));unsigned k=i%3;long double wa=0;if(k!=1){uint32_t ai=k==0?l1_aux(i):l3_aux(i);wa=std::min<long double>(rd(m.data+4ULL*ai),std::min<long double>(rd(m.data+4ULL*(ai+AUX)),rd(m.data+4ULL*(ai+2*AUX))));}
  long double rhs=(k==0?c0*wf+c1*wa:k==1?c0*wf:c0*wf+c3*wa); long double f=rhs-w;
  long double der=(k==0?-l4*c0*wf+l075*c1*wa:k==1?-l4*c0*wf:-l4*c0*wf+l15*c3*wa);
  if(der<0 && f>=0){long double e=f/(-der);if(e<minlin[k]){minlin[k]=e;idx[k]=i;fval[k]=f;dval[k]=der;}}
  for(size_t j=0;j<eps.size();++j){long double gg=g+eps[j];long double r=(k==0?powl(4.0L,-gg)*wf+powl(0.75L,gg)*wa:k==1?powl(4.0L,-gg)*wf:powl(4.0L,-gg)*wf+powl(1.5L,gg)*wa);long double mar=r-w;if(mar<0)fails[j]++;if(mar<minmargin[j]){minmargin[j]=mar;minidx[j]=i;}}
 }
 std::cout<<std::setprecision(24);
 for(int k=0;k<3;++k)std::cout<<"KIND="<<k<<" LINEAR_EPS="<<minlin[k]<<" INDEX="<<idx[k]<<" F="<<fval[k]<<" DER="<<dval[k]<<"\n";
 for(size_t j=0;j<eps.size();++j)std::cout<<"EPS="<<eps[j]<<" FAILURES="<<fails[j]<<" MIN_MARGIN="<<minmargin[j]<<" MIN_INDEX="<<minidx[j]<<"\n";
}
