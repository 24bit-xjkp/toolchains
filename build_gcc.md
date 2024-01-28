# 构建GCC工具链

## 基本信息

| 项目     | 版本         |
| -------- | ------------ |
| OS       | Ubuntu 23.10 |
| GCC      | 14.0.1       |
| GDB      | 15.0.50      |
| Binutils | 2.42.50      |
| Python   | 3.11.6       |
| Glibc    | 2.38         |

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
```

### 3.安装依赖库

```shell
cd ~/gcc
contrib/download_prerequisites
cp -rfL gmp mpfr ..
```

## 构建gcc本地工具链

| build            | host             | target           |
| ---------------- | ---------------- | ---------------- |
| x86_64-linux-gnu | x86_64-linux-gnu | x86_64-linux-gnu |

### 1.编译安装gcc

```shell
export PREFIX=~/x86_64-linux-gnu-native-gcc14
cd ~/gcc
mkdir build
cd build
../configure --disable-werror --enable-multilib --enable-languages=c,c++ --disable-bootstrap --enable-nls --prefix=$PREFIX
make -j 20
make install-strip -j 20
echo "export PATH=$PREFIX/bin:"'$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 2.编译安装binutils和gdb

```shell
cd ~/binutils
mkdir build
cd build
export ORIGIN='$$ORIGIN'
../configure --prefix=$PREFIX --disable-werror --enable-nls --with-system-gdbinit=$PREFIX/share/.gdbinit LDFLAGS="-Wl,-rpath='$ORIGIN'/../lib64"
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
