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
| PExports  | 0.47         |
| Iconv     | 1.17         |
| Gmp       | 6.2.1        |
| Mpfr      | 4.1.0        |
| Expat     | 2.5.0        |

## 准备工作

### 1安装系统包

```shell
sudo apt install bison flex texinfo make automake autoconf libtool git gcc g++ gcc-multilib g++-multilib cmake ninja-build python3 tar xz-utils unzip libgmp-dev libmpfr-dev zlib1g-dev libexpat1-dev gawk
```

### 2下载源代码

```shell
git clone https://github.com/gcc-mirror/gcc.git --depth=1 gcc
git clone https://github.com/bminor/binutils-gdb.git --depth=1 binutils
git clone https://github.com/mirror/mingw-w64.git --depth=1 mingw
git clone https://github.com/libexpat/libexpat.git --depth=1 expat
cd ~/pexports
autoreconf -if
cd ~
git clone https://github.com/torvalds/linux.git --depth=1 linux
# glibc版本要与目标系统使用的版本对应
git clone https://github.com/bminor/glibc.git -b release/2.38/master --depth=1 glibc
git clone https://github.com/bocke/pexports.git --depth=1 pexports
cd ~/pexports
autoreconf -if
cd ~
# 编译Windows下带有Python支持的gdb需要嵌入式Python3环境
wget https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip -O python-embed.zip
unzip -o python-embed.zip  python3*.dll python3*.zip *._pth -d python-embed -x python3.dll
rm python-embed.zip
# 下载Python源代码以提取include目录
wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tar.xz -O Python.tar.xz
tar -xaf Python.tar.xz
rm Python.tar.xz
cd Python-3.11.6/Include
mkdir ~/python-embed/include
cp -r * ~/python-embed/include
cd ../PC
cp pyconfig.h ~/python-embed/include
cd ~
rm -rf Python-3.11.6
wget https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.17.tar.gz -O iconv.tar.gz
tar -axf iconv.tar.gz
rm iconv.tar.gz
mv libiconv-1.17/ iconv
```

### 3安装依赖库

```shell
cd ~/gcc
contrib/download_prerequisites
cp -rfL gmp mpfr ..
cd ~
```

## 构建gcc本地工具链

| build            | host             | target           |
| :--------------- | :--------------- | :--------------- |
| x86_64-linux-gnu | x86_64-linux-gnu | x86_64-linux-gnu |

### 4编译安装gcc

```shell
export PREFIX=~/x86_64-linux-gnu-native-gcc14
cd ~/gcc
mkdir build
cd build
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix=$PREFIX
make -j 20
make install-strip -j 20
# 单独安装带调试符号的库文件
make install-target-libgcc install-target-libstdc++-v3 install-target-libatomic install-target-libquadmath install-target-libgomp -j 20
echo "export PATH=$PREFIX/bin:"'$PATH' >> ~/.bashrc
source ~/.bashrc
```

参阅[gcc配置选项](https://gcc.gnu.org/install/configure.html)。

### 5编译安装binutils和gdb

```shell
cd ~/binutils
mkdir build
cd build
export ORIGIN='$$ORIGIN'
../configure --prefix=$PREFIX --disable-werror --enable-nls --with-system-gdbinit=$PREFIX/share/.gdbinit LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64" --enable-gold
make -j 20
make install-strip -j 20
```

`--with-system-gdbinit=$PREFIX/share/.gdbinit`选项是用于设置默认的.gdbinit，而我们可以在默认的.gdbinit中配置好pretty-printer模块，
这样就可以实现开箱即用的pretty-printer。参见[GDB系统设置](https://sourceware.org/gdb/current/onlinedocs/gdb.html/System_002dwide-configuration.html#System_002dwide-configuration)。

`export ORIGIN='$$ORIGIN'`和`LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64"`选项是用于设置gdb的rpath。由于编译时使用的gcc版本比系统自带的更高，故链接的libstdc++版本也更高。
因而需要将rpath设置到编译出来的libstdc++所在的目录。

### 6创建.gdbinit

由`libstdc++.so.6.0.33-gdb.py`配置pretty-printer：

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

由`share/.gdbinit`直接配置pretty-printer，完成后直接跳转至[第9步](#9打包工具链)：

```python
# share/.gdbinit
python
import os
import gdb
import sys

# gdb启动时会将sys.path[0]设置为share/gdb/python
share_dir = os.path.abspath(os.path.join(sys.path[0], "../../"))
# 在share目录下搜索gcc的python支持
python_dir = ""
for dir in os.listdir(share_dir):
    current_dir = os.path.join(share_dir, dir, "python")
    if dir[0:3] == "gcc" and os.path.isdir(current_dir):
        python_dir = current_dir
        break
if python_dir != "":
    sys.path.insert(0, python_dir)
    from libstdcxx.v6 import register_libstdcxx_printers
    register_libstdcxx_printers(gdb.current_objfile())
else:
    print("Cannot find gcc python support because share/gcc*/python directory does not exist.")
end
```

### 7修改libstdc++的python支持

```python
# lib64/libstdc++.so.6.0.33-gdb.py
import sys
import gdb
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# pretty-printer所需的python脚本位于share/gcc-14.0.1/python下
# 故使用哪个libstdc++.so.6.0.33-gdb.py都不影响结果，此处选择lib64下的
python_dir  = os.path.normpath(os.path.join(current_dir, "../share/gcc-14.0.1/python"))
if not python_dir in sys.path:
    sys.path.insert(0, python_dir)
# 注册pretty-printer
from libstdcxx.v6 import register_libstdcxx_printers
register_libstdcxx_printers(gdb.current_objfile())
```

同理，修改`lib32/libstdc++.so.6.0.33-gdb.py`，尽管在默认配置中该文件不会被加载。

### 8剥离调试符号到独立符号文件

通过`make install-target`命令可以安装未strip的运行库，但这样的运行库体积过大，不利于部署。因此需要剥离调试符号到独立的符号文件中。

在[第4步](#4编译安装gcc)中我们保留了以下库的调试符号：libgcc libstdc++ libatomic libquadmath libgomp

接下来逐个完成剥离操作：

```shell
# 生成独立的调试符号文件
objcopy --only-keep-debug $PREFIX/lib64/libgcc_s.so.1 $PREFIX/lib64/libgcc_so.1.debug
# 剥离动态库的调试符号
strip $PREFIX/lib64/libgcc_s.so.1
# 关联调试符号和动态库
objcopy --add-gnu-debuglink=$PREFIX/lib64/libgcc_s.so.1.debug $PREFIX/lib64/libgcc_s.so.1
# 重复上述操作直到处理完所有动态库
```

### 9打包工具链

```shell
cd ~
export MEMORY=$(cat /proc/meminfo | awk '/MemTotal/ {printf "%dGiB\n", int($2/1024/1024)}')
tar -cf x86_64-linux-gnu-native-gcc14.tar x86_64-linux-gnu-native-gcc14/
xz -ev9 -T 0 --memlimit=$MEMORY x86_64-linux-gnu-native-gcc14.tar
```

## 构建mingw[交叉工具链](https://en.wikipedia.org/wiki/Cross_compiler)

| build            | host             | target             |
| :--------------- | :--------------- | :----------------- |
| x86_64-linux-gnu | x86_64-linux-gnu | x86_64-w64-mingw32 |

### 10设置环境变量

```shell
export TARGET=x86_64-w64-mingw32
export HOST=x86_64-linux-gnu
export PREFIX=~/$HOST-host-$TARGET-target-gcc14
```

### 11编译安装binutils

```shell
cd binutils/build
rm -rf *
# Linux下不便于调试Windows,故不编译gdb
../configure --disable-werror --enable-nls --disable-gdb --prefix=$PREFIX --target=$TARGET
make -j 20
make install-strip -j 20
echo "export PATH=$PREFIX/bin:"'$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 12安装mingw-w64头文件

```shell
cd ~/mingw
mkdir build
cd build
# 这是交叉编译器，故目标平台的头文件需要装在$TARGET目录下
../configure --prefix=$PREFIX/$TARGET --with-default-msvcrt=ucrt --host=$TARGET --without-crt
make install
```

### 13编译安装gcc和libgcc

```shell
cd ~/gcc/build
rm -rf *
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET
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
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET --disable-shared
make all-gcc all-target-libgcc -j 20
make install-strip-gcc install-strip-target-libgcc -j 20
```

### 14编译安装完整mingw-w64

```shell
cd ~/mingw/build
rm -rf *
../configure --prefix=$PREFIX/$TARGET --with-default-msvcrt=ucrt --host=$TARGET
make -j 24
make install-strip -j 24
# 构建交叉工具链时multilib在$TARGET/lib/32而不是$TARGET/lib32下
cd $PREFIX/$TARGET/lib
ln -s ../lib32 32
```

### 15编译安装完整gcc

```shell
cd ~/gcc/build
rm -rf *
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET
make -j 20
make install-strip -j 20
# 单独安装带调试符号的库文件
make install-target-libgcc install-target-libstdc++-v3 install-target-libatomic install-target-libquadmath -j 20
```

### 16剥离调试符号到独立符号文件

在[第15步](#15编译安装完整gcc)中我们保留了以下库的调试符号：libgcc libstdc++ libatomic libquadmath。但需要注意的是，x86_64下libgcc名为`libgcc_s_seh-1.dll`，而i386下libgcc名为`libgcc_s_dw2-1.dll`。

接下来逐个完成剥离操作：

```shell
# 生成独立的调试符号文件
$TARGET-objcopy --only-keep-debug $PREFIX/$TARGET/lib/libgcc_s_seh-1.dll $PREFIX/$TARGET/lib/libgcc_s_seh-1.dll.debug
# 剥离动态库的调试符号
$TARGET-strip $PREFIX/$TARGET/lib/libgcc_s_seh-1.dll
# 关联调试符号和动态库
$TARGET-objcopy --add-gnu-debuglink=$PREFIX/$TARGET/lib/libgcc_s_seh-1.dll.debug $PREFIX/$TARGET/lib/libgcc_s_seh-1.dll
# 重复上述操作直到处理完所有动态库
```

### 17编译安装pexports

```shell
cd ~/pexports
mkdir build
cd build
../configure --prefix=$PREFIX
make -j 20
make install-strip -j 20
# 添加pexports前缀
mv $PREFIX/bin/pexports $PREFIX/bin/$TARGET-pexports
```

### 18打包工具链

```shell
cd ~
export PACKAGE=$HOST-host-$TARGET-target-gcc14
tar -cf $PACKAGE.tar $PACKAGE/
xz -ev9 -T 0 --memlimit=$MEMORY $PACKAGE.tar
```

## 构建mingw[加拿大工具链](https://en.wikipedia.org/wiki/Cross_compiler#Canadian_Cross)

| build            | host               | target             |
| :--------------- | :----------------- | :----------------- |
| x86_64-linux-gnu | x86_64-w64-mingw32 | x86_64-w64-mingw32 |

### 19设置环境变量

```shell
export BUILD=x86_64-linux-gnu
export HOST=x86_64-w64-mingw32
export TARGET=$HOST
export PREFIX=~/$HOST-native-gcc14
```

### 20编译安装gcc

```shell
cd ~/gcc/build
rm -rf *
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --enable-nls --disable-sjlj-exceptions --enable-threads=win32 --prefix=$PREFIX --target=$TARGET --host=$HOST
make -j 20
make install-strip -j 20
```

此时我们执行如下命令：

```shell
cd $PREFIX/bin
file *.dll
```

会得到如下结果：

```log
libatomic-1.dll:   PE32 executable (DLL) (console) Intel 80386 (stripped to external PDB), for MS Windows, 10 sections
libquadmath-0.dll: PE32 executable (DLL) (console) Intel 80386 (stripped to external PDB), for MS Windows, 10 sections
libssp-0.dll:      PE32 executable (DLL) (console) Intel 80386 (stripped to external PDB), for MS Windows, 10 sections
libstdc++-6.dll:   PE32 executable (DLL) (console) Intel 80386 (stripped to external PDB), for MS Windows, 10 sections
```

由此可见，`make install-strip`时安装的dll是x86而非x86_64的，这是由于开启multilib后，gcc的安装脚本会后安装multilib对应的dll,导致32位dll覆盖64位dll。
同时，我们会发现`lib`和`lib32`目录下没有这些dll，这是因为gcc的安装脚本默认将它们安装到了bin目录下。综上所述，dll的安装是完全错误的。
还可以发现，`include`、`lib`和`lib32`目录下都没有libc和sdk文件。故我们需要手动从先前安装的[交叉工具链](#构建mingw交叉工具链)中复制这些文件。

### 21从交叉工具链中复制所需的库和头文件

这样不但不需要再次编译mingw-w64，而且可以直接复制[编译交叉工具链](#16剥离调试符号到独立符号文件)时生成的调试符号文件，不需要再次剥离调试符号。

```shell
rm *.dll
cd ~/$BUILD-host-$TARGET-target-gcc14/$TARGET
# ldscripts会在后续安装binutils时安装
cp -n lib/* $PREFIX/lib
cp -n lib32/* $PREFIX/lib32
cp -nr include/* $PREFIX/include
```

### 22为python动态库创建归档文件

在接下来的5步中，我们将构建编译gdb所需的依赖项。具体说明请参见[构建gdb的要求](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Requirements.html#Requirements)。

```shell
cd ~/python-embed
$TARGET-pexports python311.dll > libpython.def
$TARGET-dlltool -D python311.dll -d libpython.def -l libpython.a
```

### 23编译安装libgmp

```shell
cd ~/gmp
export GMP=~/gmp/install
mkdir build
cd build
# 禁用动态库，否则编译出来的gdb会依赖libgmp.dll
../configure --host=$HOST --prefix=$GMP --disable-shared
make -j 20
make install-strip -j 20
```

### 24编译安装libexpat

```shell
cd ~/expat/expat
export EXPAT=~/expat/install
mkdir build
cd build
# 此处也需要禁用动态库
../configure --prefix=$EXPAT --host=$HOST --disable-shared
make -j 20
make install-strip -j 20
```

### 25编译安装libiconv

```shell
cd ~/iconv
export ICONV=~/iconv/install
mkdir build
cd build
# 此处也需要禁用动态库
../configure --prefix=$ICONV --host=$HOST --disable-shared
make -j 20
make install-strip -j 20
```

### 26编译安装libmpfr

```shell
cd ~/mpfr
export MPFR=~/mpfr/install
mkdir build
cd build
# 此处也需要禁用动态库
../configure --prefix=$MPFR --host=$HOST --with-gmp=$GMP --disable-shared
make -j 20
make install-strip -j 20
```

### 27编译安装binutils和gdb

要编译带有python支持的gdb就必须在编译gdb时传入python安装信息，但在交叉环境中提供这些信息是困难的。因此我们需要手动将这些信息传递给`configure`脚本。
具体说明请参见[使用交叉编译器编译带有python支持的gdb](https://sourceware.org/gdb/wiki/CrossCompilingWithPythonSupport)。
编写一个python脚本以提供上述信息：

```python
import sys
import os
from gcc_environment import environment

# sys.argv[0] shell脚本路径
# sys.argv[1] binutils/gdb/python-config.py路径
# sys.argv[2:] python脚本所需的参数
def get_config() -> None:
    assert len(sys.argv) >= 3, "Too few args"
    env = environment("")
    python_dir = env.lib_dir_list["python-embed"]
    result_list = {
        "--includes": f"-I{os.path.join(python_dir, 'include')}",
        "--ldflags": f"-L{python_dir} -lpython",
        "--exec-prefix": f"-L{python_dir}",
    }
    option_list = sys.argv[2:]
    for option in option_list:
        if option in result_list:
            print(result_list[option])
            return
    assert False, f'Invalid option list: {" ".join(option_list)}'

if __name__ == "__main__":
    get_config()
```

编写一个shell脚本以转发参数给上述python脚本：

```shell
# 获取当前文件的绝对路径
current_file="$(readlink -f $0)"
# 提取当前文件夹
current_dir="$(dirname $current_file)"
# 将接受到的参数转发给python_config.py
python3 "$current_dir/python_config.py" $@
```

值得注意的是，gdb依赖于c++11提供的条件变量，而win32线程模型仅在Windows Vista和Windows Server 2008之后的系统上支持该功能，即要求_WIN32_WINNT>=0x0600，而默认情况下该条件是不满足的。
因此需要手动设置`CXXFLAGS`来指定Windows版本。否则在编译gdbsupport时将会产生如下错误：

```log
.../std_mutex.h:164:5: 错误： ‘__gthread_cond_t’ does not name a type; did you mean ‘__gthread_once_t’?
  164 |     __gthread_cond_t* native_handle() noexcept { return &_M_cond; }
      |     ^~~~~~~~~~~~~~~~
      |     __gthread_once_t
```

交叉编译带python支持的gdb的所有要求都已经满足了，下面开始编译binutils和gdb：

```shell
cd ~/binutils/build
rm -rf *
../configure --host=$HOST --target=$TARGET --prefix=$PREFIX --disable-werror --with-gmp=$GMP --with-mpfr=$MPFR --with-expat --with-libexpat-prefix=$EXPAT --with-libiconv-prefix=$ICONV --with-system-gdbinit=$PREFIX/share/.gdbinit --with-python=$HOME/toolchains/python_config.sh CXXFLAGS=-D_WIN32_WINNT=0x0600
make -j 20
make install-strip -j 20
```

### 28编译安装pexports

我们在Window下也提供pexports实用工具，下面开始编译pexports：

```shell
cd ~/pexports/build
rm -rf *
../configure --prefix=$PREFIX --host=$HOST
make -j 20
make install-strip -j 20
```

### 29复制python embed package

```shell
cp ~/python-embed
cp python* $PREFIX/bin
```

### 30打包工具链

```shell
cd ~
export PACKAGE=$HOST-native-gcc14
tar -cf $PACKAGE.tar $PACKAGE/
xz -ev9 -T 0 --memlimit=$MEMORY $PACKAGE.tar
```

### 31使用工具链

在开启multilib后，`lib`和`lib32`目录下会各有一份dll，这也就是为什么不能将dll文件复制到`bin`目录下。
因而在使用时需要将`bin`，`lib`和`lib32`文件夹都添加到PATH环境变量。程序在加载dll时Windows会顺序搜索PATH中的目录，直到找到一个dll可以被加载。
因此同时将`lib`和`lib32`添加到PATH即可实现根据程序体系结构选择相应的dll。
如果将`lib`和`lib32`下的dll分别复制到`System32`和`SysWOW64`目录下，则只需要将`bin`文件夹添加到PATH环境变量，但不推荐这么做。
值得注意的是，.debug文件需要和.dll文件处于同一级目录下，否则调试时需要手动加载符号文件。

## 构建arm独立交叉工具链

| build            | host             | target        |
| :--------------- | :--------------- | :------------ |
| x86_64-linux-gnu | x86_64-linux-gnu | arm-none-eabi |

### 32设置环境变量

```shell
export BUILD=x86_64-linux-gnu
export HOST=$BUILD
export TARGET=arm-none-eabi
export PREFIX=~/$HOST-host-$TARGET-target-gcc14
```

### 33编译binutils和gdb

```shell
cd ~/binutils/build
rm -rf *
export ORIGIN='$$ORIGIN'
../configure --disable-werror --enable-nls --target=$TARGET --prefix=$PREFIX --with-system-gdbinit=$PREFIX/share/.gdbinit LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64" --enable-gold
make -j 20
make install-strip -j 20
```

### 34编译安装gcc

这是一个不使用newlib的完全独立的工具链，故而需要禁用所有依赖宿主系统的库和特性。此时支持的库仅包含libstdc++和libgcc。由于此时禁用了动态库，故不需要再手动剥离调试符号。

```shell
cd ~/gcc/build
rm -rf *
../configure --disable-werror --enable-nls --target=$TARGET --prefix=$PREFIX --enable-multilib --enable-languages=c,c++ --disable-threads --disable-hosted-libstdcxx --disable-libstdcxx-verbose --disable-shared --without-headers --disable-libvtv --disable-libsanitizer --disable-libssp --disable-libquadmath --disable-libgomp
make -j 20
make install-strip -j 20
make install-target-libstdc++-v3 install-target-libgcc -j 20
```

### 35复制库和pretty-printer

编译出的arm-none-eabi-gdb依赖libstdc++，故需要从[gcc本地工具链](#构建gcc本地工具链)中复制一份。同时独立工具链不会安装pretty-printer，故也需要复制一份。

```shell
cd ~/$BUILD-native-gcc14
cp lib64/libstdc++.so.6 $PREFIX/lib64
cp -r share/gcc-14.0.1 $PREFIX/share
```

### 36打包工具链

```shell
cd ~
export PACKAGE=$HOST-host-$TARGET-target-gcc14
tar -cf $PACKAGE.tar $PACKAGE/
xz -ev9 -T 0 --memlimit=$MEMORY $PACKAGE.tar
```

## 构建arm独立加拿大工具链

| build            | host               | target        |
| :--------------- | :----------------- | :------------ |
| x86_64-linux-gnu | x86_64-w64-mingw32 | arm-none-eabi |

### 37设置环境变量

```shell
export BUILD=x86_64-linux-gnu
export HOST=x86_64-w64-mingw32
export TARGET=arm-none-eabi
export PREFIX=~/$HOST-host-$TARGET-target-gcc14
```

### 38准备编译gdb所需的库

请参阅前文构建出[libpython.a](#22为python动态库创建归档文件), [libgmp](#23编译安装libgmp), [libexpat](#24编译安装libexpat), [libiconv](#25编译安装libiconv), [libmpfr](#26编译安装libmpfr)。

### 39编译安装binutils和gdb

原理请参阅[x86_64-w64-mingw32本地gdb构建](#27编译安装binutils和gdb)。

```shell
cd ~/binutils/build
rm -rf *
../configure --host=$HOST --target=$TARGET --prefix=$PREFIX --disable-werror --with-gmp=$GMP --with-mpfr=$MPFR --with-expat --with-libexpat-prefix=$EXPAT --with-libiconv-prefix=$ICONV --with-system-gdbinit=$PREFIX/share/.gdbinit --with-python=$HOME/toolchains/python_config.sh CXXFLAGS=-D_WIN32_WINNT=0x0600
make -j 20
make install-strip -j 20
```

### 40编译安装gcc

原理请参阅[x86_64-linux-gnu交叉工具链](#34编译安装gcc)。

```shell
cd ~/gcc/build
rm -rf *
../configure --disable-werror --enable-nls --host=$HOST --target=$TARGET --prefix=$PREFIX --enable-multilib --enable-languages=c,c++ --disable-threads --disable-hosted-libstdcxx --disable-libstdcxx-verbose --disable-shared --without-headers --disable-libvtv --disable-libsanitizer --disable-libssp --disable-libquadmath --disable-libgomp
make -j 20
make install-strip -j 20
make install-target-libstdc++-v3 install-target-libgcc -j 20
```

### 41从其他工具链中复制所需库和pretty-printer

从[mingw交叉工具链](#构建mingw交叉工具链)中复制动态库：

```shell
cd ~/$BUILD-host-$HOST-target-gcc14/$HOST
cp lib/libstdc++-6.dll $PREFIX/bin
cp lib/libgcc_s_seh-1.dll $PREFIX/bin
```

从[gcc本地工具链](#构建gcc本地工具链)中复制pretty-printer：

```shell
cd ~/$BUILD-native-gcc14
cp -r share/gcc-14.0.1 $PREFIX/share
```

### 42打包工具链

```shell
cd ~
export PACKAGE=$HOST-host-$TARGET-target-gcc14
tar -cf $PACKAGE.tar $PACKAGE/
xz -ev9 -T 0 --memlimit=$MEMORY $PACKAGE.tar
```
