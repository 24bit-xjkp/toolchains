# 构建GCC工具链

1. 安装系统包
```shell
sudo apt install bison flex texinfo make automake autoconf git gcc g++ gcc-multilib g++-multilib cmake ninja-build
```
2. 下载源代码
```shell
git clone https://github.com/gcc-mirror/gcc.git --depth=1 gcc
git clone https://github.com/bminor/binutils-gdb.git --depth=1 binutils
git clone https://github.com/mirror/mingw-w64.git --depth=1 mingw
git clone https://github.com/libexpat/libexpat.git --depth=1 expat
git clone https://github.com/torvalds/linux.git --depth=1 linux
# glibc版本要与目标系统使用的版本对应
git clone https://github.com/bminor/glibc.git -b release/2.38/master --depth=1 glibc
```
3. 安装依赖库
```shell
cd gcc
contrib/download_prerequisites
cp -rfL gmp mpfr ..
```
4. 构建本地gcc工具链
|build|host|target|
```
export PREFIX=~/x86_64-linux-gnu-native-gcc14
mkdir build
cd build
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix=$PREFIX
make -j 18
make install-strip -j 18
```