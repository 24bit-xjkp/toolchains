# 构建GCC工具链

## 基本信息

| 项目      | 版本         |
| :-------- | :----------- |
| OS        | Ubuntu 23.10 |
| GCC       | 14.0.1       |
| GDB       | 15.0.50      |
| Binutils  | 2.42.50      |
| Python    | 3.11.6       |
| Glibc     | 2.38         |
| Mingw-w64 | 10.0.0       |

## 准备工作

### 1.安装系统包

```shell
sudo apt install bison flex texinfo make automake autoconf git gcc g++ gcc-multilib g++-multilib cmake ninja-build
```

### 2.下载源代码

```shell
git clone https://github.com/gcc-mirror/gcc.git --depth=1 gcc
git clone https://github.com/bminor/binutils-gdb.git --depth=1 binutils
git clone https://github.com/mirror/mingw-w64.git --depth=1 mingw
git clone https://github.com/libexpat/libexpat.git --depth=1 expat
git clone https://github.com/torvalds/linux.git --depth=1 linux
# glibc版本要与目标系统使用的版本对应
git clone https://github.com/bminor/glibc.git -b release/2.38/master --depth=1 glibc
git clone https://github.com/bocke/pexports.git --depth=1 pexports
```

### 3.安装依赖库

```shell
cd ~/gcc
contrib/download_prerequisites
cp -rfL gmp mpfr ..
```

## 构建gcc本地工具链

| build            | host             | target           |
| :--------------- | :--------------- | :--------------- |
| x86_64-linux-gnu | x86_64-linux-gnu | x86_64-linux-gnu |

### 1.编译安装gcc

```shell
export PREFIX=~/x86_64-linux-gnu-native-gcc14
cd ~/gcc
mkdir build
cd build
sh ../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix=$PREFIX
make -j 20
make install-strip -j 20
echo "export PATH=$PREFIX/bin:"'$PATH' >> ~/.bashrc
source ~/.bashrc
```

参阅[gcc配置选项](https://gcc.gnu.org/install/configure.html)。

### 2.编译安装binutils和gdb

```shell
cd ~/binutils
mkdir build
cd build
export ORIGIN='$$ORIGIN'
sh ../configure --prefix=$PREFIX --disable-werror --enable-nls --with-system-gdbinit=$PREFIX/share/.gdbinit LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64"
make -j 20
make install-strip -j 20
```

`--with-system-gdbinit=$PREFIX/share/.gdbinit`选项是用于设置默认的.gdbinit，而我们可以在默认的.gdbinit中配置好pretty-printer模块，
这样就可以实现开箱即用的pretty-printer。参见[GDB系统设置](https://sourceware.org/gdb/current/onlinedocs/gdb.html/System_002dwide-configuration.html#System_002dwide-configuration)。

`export ORIGIN='$$ORIGIN'`和`LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64"`选项是用于设置gdb的rpath。由于编译时使用的gcc版本比系统自带的更高，故链接的libstdc++版本也更高。
因而需要将rpath设置到编译出来的libstdc++所在的目录。

### 3.创建.gdbinit

```python
# share/.gdbinit
python
import os
import gdb
import sys
# gdb启动时会将sys.path[0]设置为share/gdb/python
scriptPath = os.path.join(sys.path[0], "../../../lib64/libstdc++.so.6.0.33-gdb.py")
gdb.execute(f"source {scriptPath}")
end
```

### 4.修改libstdc++的Python支持

```python
# lib64/libstdc++.so.6.0.33-gdb.py
import sys
import gdb
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# pretty-printer所需的python脚本位于share/gcc-14.0.1/python下
# 故使用哪个libstdc++.so.6.0.33-gdb.py都不影响结果，此处选择lib64下的
# 同理，可以直接在.gdbinit中配置好pretty-printer
python_dir  = os.path.normpath(os.path.join(current_dir, "../share/gcc-14.0.1/python"))
if not python_dir in sys.path:
    sys.path.insert(0, python_dir)
# 注册pretty-printer
from libstdcxx.v6 import register_libstdcxx_printers
register_libstdcxx_printers(gdb.current_objfile())
```

同理，修改`lib32/libstdc++.so.6.0.33-gdb.py`，尽管在默认配置中该文件不会被加载。

### 5.打包工具链

```shell
cd ~
export MEMORY=$(cat /proc/meminfo | awk '/MemTotal/ {printf "%dGiB\n", int($2/1024/1024)}')
tar -cf $PREFIX.tar $PREFIX
xz -ev9 -T 0 --memlimit=$MEMORY $PREFIX.tar
```

## 构建mingw[交叉工具链](https://en.wikipedia.org/wiki/Cross_compiler)

| build            | host             | target             |
| :--------------- | :--------------- | :----------------- |
| x86_64-linux-gnu | x86_64-linux-gnu | x86_64-w64-mingw32 |

### 1.设置环境变量

```shell
export TARGET=x86_64-w64-mingw32
export HOST=x86_64-linux-gnu
export PREFIX=~/$HOST-host-$TARGET-cross-gcc14
```

### 2.编译安装binutils

```shell
cd binutils/build
rm -rf *
# Linux下不便于调试Windows,故不编译gdb
sh ../configure --disable-werror --enable-nls --disable-gdb --prefix=$PREFIX --target=$TARGET
make -j 20
make install-strip -j 20
echo "export PATH=$PREFIX/bin:"'$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 3.安装mingw-w64头文件

```shell
cd ~/mingw
mkdir build
cd build
# 这是交叉编译器，故目标平台的头文件需要装在$TARGET目录下
sh ../configure --prefix=$PREFIX/$TARGET --with-default-msvcrt=ucrt --host=$TARGET --without-crt
make install
```

### 4.修改libgcc以支持win32线程模型下的条件变量

```c
// libgcc/config/i386/gthr-win32.h
/* Condition variables are supported on Vista and Server 2008 or later.  */
#if _WIN32_WINNT >= 0x0600
#define __GTHREAD_HAS_COND 1
#define __GTHREADS_CXX0X 1
#endif
```

修改为：

```c
// libgcc/config/i386/gthr-win32.h
/* Condition variables are supported on Vista and Server 2008 or later.  */
#define __GTHREAD_HAS_COND 1
#define __GTHREADS_CXX0X 1
```

### 5.编译安装gcc和libgcc

```shell
cd ~/gcc/build
rm -rf *
sh ../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET
make all-gcc all-target-libgcc -j 20
make install-strip-gcc install-strip-target-libgcc -j 20
```

遇到如下情况：

```log
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 dllcrt2.o: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lmingwthrd: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lmingw32: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lmingwex: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lmoldname: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lmsvcrt: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -ladvapi32: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lshell32: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -luser32: 没有那个文件或目录
/home/luo/x86_64-linux-gnu-host-x86_64-w64-mingw32-cross-gcc14/x86_64-w64-mingw32/bin/ld: 找不到 -lkernel32: 没有那个文件或目录
```

尝试禁用动态库编译出gcc和libgcc

```shell
cd ~/gcc/build
rm -rf *
sh ../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET --disable-shared
make all-gcc all-target-libgcc -j 20
make install-strip-gcc install-strip-target-libgcc -j 20
```

### 6.编译安装mingw-w64运行时

```shell
cd ~/mingw/build
rm -rf *
sh ../configure --prefix=$PREFIX/$TARGET --with-default-msvcrt=ucrt --host=$TARGET
make -j 24
make install-strip -j 24
# 构建交叉工具链时multilib在$TARGET/lib/32而不是$TARGET/lib32下
cd $PREFIX/$TARGET/lib
ln -s ../lib32 32
```

### 7.编译安装完整gcc

```shell
cd ~/gcc/build
rm -rf *
sh ../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET
make -j 20
make install-strip -j 20
```

## 构建mingw[加拿大工具链](https://en.wikipedia.org/wiki/Cross_compiler#Canadian_Cross)
