# 构建LLVM工具链

## 基本信息

| 项目 | 版本         |
| :--- | :----------- |
| OS   | Ubuntu 24.04 |
| LLVM | 19.0.0       |
| GCC  | 15.0.0       |

## 准备工作

### 1.安装系统包

```shell
# 使用clang自举
sudo apt install git python3 cmake ninja-build clang lld libxml2-dev zlib1g-dev
```

### 2.准备sysroot

作为一个交叉编译器，clang需要设置sysroot来查找所需的库和头文件，值得注意的是，clang不适用multilib，故而需要为32位目标和64位目标分别制作sysroot。
一个平台的sysroot需要包含如下内容：

| 内容         | 说明                   |
| ------------ | ---------------------- |
| Linux Header | 内核头文件             |
| libc         | C 标准库               |
| libgcc       | 提供异常处理等底层功能 |
| libstdc++    | C++ 标准库             |
| ldscripts    | 链接器脚本             |

故而制作一个sysroot需要用到如下项目：

| 项目                                   | 说明                                    |
| -------------------------------------- | --------------------------------------- |
| Linux                                  | 提供内核头文件                          |
| Glibc/Mingw-w64                        | 提供C 标准库                            |
| gcc                                    | 提供libgcc和C++ 标准库                  |
| binutils                               | 提供链接器脚本                          |
| compiler-rt/libunwind/libcxx/libcxxabi | 在完成LLVM工具链编译后用于替代GNU相关库 |

对于一个安装在`prefix`并且交叉到`target`平台的交叉工具链，在`prefix/target`目录下可以找到`include`、`lib`、`lib64`等文件夹，而在`prefix/lib/gcc`可以找到libgcc相关文件夹，
其中已经包含了sysroot所需的全部文件。对于一个本地工具链，由于系统相关的库和头文件安装在系统目录下，故本地工具链本身仅带有gcc和binutils相关文件，
而linux和libc相关文件需要自行安装，安装流程可以参考[build_gcc.md](build_gcc.md)中的说明。

故而制作一个sysroot的流程如下：

| 平台       | 流程                                                                                                                                                      |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 非host平台 | 直接从`prefix/target`目录下复制`include`、`lib`、`lib64`（如果存在）文件夹                                                                                |
| host平台   | 首先安装Linux头文件和libc文件，然后从`prefix`目录下复制`include`、`lib32/64`（取决于host的性质，复制成lib文件夹），再从`prefix/host/lib`下复制`ldscripts` |
| 通用       | 从`prefix/lib`下复制`gcc`文件夹                                                                                                                           |

对于启用multilib编译的gcc，在制作sysroot时需要视作两个目标处理。例如对于启用了multilib的`x86_64-linux-gnu-gcc`，制作sysroot时需要拆分成`x86_64-linux-gnu`和`i686-linux-gnu`两个目标。
故而在编译gcc时也可以选择不启用multilib来简化sysroot的制作流程。

一个sysroot的目录结构实例如下：

```txt
sysroot
├── aarch64-linux-gnu
├── i686-linux-gnu
├── i686-w64-mingw32
├── lib
│   └── gcc
│       ├── aarch64-linux-gnu
│       ├── i686-linux-gnu
│       ├── i686-w64-mingw32
│       ├── loongarch64-linux-gnu
│       ├── riscv64-linux-gnu
│       ├── x86_64-linux-gnu
│       └── x86_64-w64-mingw32
├── loongarch64-linux-gnu
├── riscv64-linux-gnu
├── x86_64-linux-gnu
└── x86_64-w64-mingw32
```

### 3.编译x86_64-linux-gnu-llvm工具链

通过clang自举出不依赖gnu相关库的完整llvm工具链需要分为4个阶段进行：

1. 第一次编译llvm及runtimes，依赖gnu相关库
2. 使用刚才编译的llvm和runtimes重新编译llvm，得到不依赖gnu相关库的llvm
3. 使用刚才编译的llvm和runtimes重新编译runtimes，得到不依赖gnu相关库的runtimes
4. 打包工具链

#### (1)首次编译llvm以及runtimes

首先编译llvm：

```shell
export llvm_prefix=~/x86_64-linux-gnu-clang19
export runtimes_prefix=$llvm_prefix/install
export compiler_rt_prefix=$llvm_prefix/lib/clang/19/lib
# 启用动态链接以减小项目体积
export dylib_option_list="-DLLVM_LINK_LLVM_DYLIB=ON -DLLVM_BUILD_LLVM_DYLIB=ON -DCLANG_LINK_CLANG_DYLIB=ON"
# 设置构建模式为Release
# 关闭llvm文档、示例、基准测试和单元测试的构建
# 构建目标：X86;AArch64;WebAssembly;RISCV;ARM;LoongArch
# 在编译llvm时编译子项目：clang;lld
# 在编译llvm时编译运行时：libcxx;libcxxabi;libunwind;compiler-rt
# 禁用警告以减少回显噪音
# 关闭clang单元测试的构建
# 禁止基准测试安装文档
# 设置clang默认链接器为lld
# 使用lld作为链接器（支持多核链接，可加速链接）
# 使用rpath连接选项，在Linux系统上可以避免动态库环境混乱
# 关闭libcxx基准测试的构建
# 使用compiler-rt和libcxxabi构建libcxx
# 使用compiler-rt和libunwind构建libcxxabi
# 使用compiler-rt构建libunwind
# compiler-rt只需构建默认目标即可，禁止自动构建multilib
# 使用libcxx构建compiler-rt中的asan等项目
export llvm_option_list1='-DCMAKE_BUILD_TYPE=Release -DLLVM_BUILD_DOCS=OFF -DLLVM_BUILD_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_TARGETS_TO_BUILD="X86;AArch64;WebAssembly;RISCV;ARM;LoongArch" -DLLVM_ENABLE_PROJECTS="clang;lld" -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind;compiler-rt" -DLLVM_ENABLE_WARNINGS=OFF -DCLANG_INCLUDE_TESTS=OFF -DBENCHMARK_INSTALL_DOCS=OFF -DCLANG_DEFAULT_LINKER=lld -DLLVM_ENABLE_LLD=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DLIBCXX_INCLUDE_BENCHMARKS=OFF -DLIBCXX_USE_COMPILER_RT=ON -DLIBCXX_CXX_ABI=libcxxabi -DLIBCXXABI_USE_LLVM_UNWINDER=ON -DLIBCXXABI_USE_COMPILER_RT=ON -DLIBUNWIND_USE_COMPILER_RT=ON -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON -DCOMPILER_RT_USE_LIBCXX=ON'
# 设置编译器为clang
# 编译器目标平台：x86_64-linux-gnu
# 禁用unused-command-line-argument警告并设置gcc查找路径以使用最新的gcc
# 设置COMPILER_WORKS选项以跳过探测（有时探测不能正常工作，尤其是交叉编译时）
# 设置llvm运行时的目标平台：x86_64-linux-gnu
# 设置llvm默认的目标平台：x86_64-unknown-linux-gnu
# 设置llvm的宿主平台：x86_64-unknown-linux-gnu
export flags="\"-Wno-unused-command-line-argument --gcc-toolchain=$HOME/sysroot\""
export target=x86_64-linux-gnu
export host=x86_64-unknown-linux-gnu
export compiler_option="-DCMAKE_C_COMPILER=\"clang\" -DCMAKE_C_COMPILER_TARGET=$target -DCMAKE_C_FLAGS=$flags -DCMAKE_C_COMPILER_WORKS=ON -DCMAKE_CXX_COMPILER=\"clang++\" -DCMAKE_CXX_COMPILER_TARGET=$target -DCMAKE_CXX_FLAGS=$flags -DCMAKE_CXX_COMPILER_WORKS=ON -DCMAKE_ASM_COMPILER=\"clang\" -DCMAKE_ASM_COMPILER_TARGET=$target -DCMAKE_ASM_FLAGS=$flags -DCMAKE_ASM_COMPILER_WORKS=ON -DLLVM_RUNTIMES_TARGET=$target -DLLVM_DEFAULT_TARGET_TRIPLE=$host -DLLVM_HOST_TRIPLE=$host"
# 进入llvm项目目录
cd ~/llvm
# 配置llvm
cmake -G Ninja --install-prefix $llvm_prefix -B build-x86_64-linux-gnu-llvm -S llvm $dylib_option_list $llvm_option_list1 $compiler_option
# 编译llvm
ninja -C build -j 20
# 安装llvm
ninja -C build install/strip -j 20
```

接下来编译所有需要的runtimes，值得注意的是，在Windows上尚不支持使用libcxxabi，故而需要改用libsupc++作为libcxx的abi。此时需要额外的设置
`LIBCXX_CXX_ABI_INCLUDE_PATHS`来确定libsupc++头文件的查找路径。而在`sysroot/x86_64(i686)-w64-mingw32/include/c++/version`下可以查找到所需的头文件。

```shell
export version="15.0.0"
# 为llvm_option_list1移除libcxxabi相关选项并且使用libsupc++作为abi
export llvm_option_list_w_1='-DCMAKE_BUILD_TYPE=Release -DLLVM_BUILD_DOCS=OFF -DLLVM_BUILD_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_TARGETS_TO_BUILD="X86;AArch64;WebAssembly;RISCV;ARM;LoongArch" -DLLVM_ENABLE_PROJECTS="clang;lld" -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind;compiler-rt" -DLLVM_ENABLE_WARNINGS=OFF -DCLANG_INCLUDE_TESTS=OFF -DBENCHMARK_INSTALL_DOCS=OFF -DCLANG_DEFAULT_LINKER=lld -DLLVM_ENABLE_LLD=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DLIBCXX_INCLUDE_BENCHMARKS=OFF -DLIBCXX_USE_COMPILER_RT=ON -DLIBCXXABI_USE_COMPILER_RT=ON -DLIBUNWIND_USE_COMPILER_RT=ON -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON -DCOMPILER_RT_USE_LIBCXX=ON -DLLVM_ENABLE_RUNTIMES="libcxx;libunwind;compiler-rt" -DLIBCXX_CXX_ABI=libsupc++'
# 增加头文件搜索路径
export llvm_option_list_w64_1="$llvm_option_list_w_1 -DLIBCXX_CXX_ABI_INCLUDE_PATHS=\"$HOME/sysroot/x86_64-w64-mingw32/include/c++/$version\""
export llvm_option_list_w32_1="$llvm_option_list_w_1 -DLIBCXX_CXX_ABI_INCLUDE_PATHS=\"$HOME/sysroot/i686-w64-mingw32/include/c++/$version\""
# 进入llvm项目目录
cd ~/llvm
# 配置runtimes
cmake -G Ninja --install-prefix $runtimes_prefix -B build-x86_64-linux-gnu-runtimes -S runtimes $dylib_option_list $llvm_option_list1 $compiler_option
# 编译runtimes
ninja -C build -j 20
# 安装runtimes
ninja -C build install/strip -j 20

# 在编译非host平台的runtimes时需要进行交叉编译，故而需要修改compiler_option
# 以编译x86_64-w64-mingw32上的runtimes为例
export target=x86_64-w64-mingw32
# 设置编译器为clang
# 设置编译器的目标平台为x86_64-w64-mingw32
# 禁用unused-command-line-argument警告并设置gcc查找路径以使用最新的gcc
# 设置COMPILER_WORKS选项以跳过探测（有时探测不能正常工作，尤其是交叉编译时）
# 设置目标平台：Windows，目标架构：x86_64
# 设置sysroot为先前制作的sysroot以进行交叉编译
# 设置llvm运行时的目标平台：x86_64-w64-mingw32
# 设置llvm默认的目标平台：x86_64-unknown-w64-mingw32
# 设置llvm的宿主平台：x86_64-unknown-linux-gnu
export compiler_option="-DCMAKE_C_COMPILER=\"clang\" -DCMAKE_C_COMPILER_TARGET=$target -DCMAKE_C_FLAGS=$flags -DCMAKE_C_COMPILER_WORKS=ON -DCMAKE_CXX_COMPILER=\"clang++\" -DCMAKE_CXX_COMPILER_TARGET=$target -DCMAKE_CXX_FLAGS=$flags -DCMAKE_CXX_COMPILER_WORKS=ON -DCMAKE_ASM_COMPILER=\"clang\" -DCMAKE_ASM_COMPILER_TARGET=$target -DCMAKE_ASM_FLAGS=$flags -DCMAKE_ASM_COMPILER_WORKS=ON -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR=x86_64 -DCMAKE_SYSROOT=\"$HOME/sysroot\" -DLLVM_RUNTIMES_TARGET=$target -DLLVM_DEFAULT_TARGET_TRIPLE=x86_64-unknown-w64-mingw32 -DLLVM_HOST_TRIPLE=$host"
# 进入llvm项目目录
cd ~/llvm
# 配置runtimes（编译Windows平台的需要设置llvm_option_list_w64(32)_1，Linux平台使用llvm_option_list1）
cmake -G Ninja --install-prefix $runtimes_prefix -B build-x86_64-linux-gnu-runtimes -S runtimes $dylib_option_list $llvm_option_list_w64_1 $compiler_option
# 编译runtimes
ninja -C build -j 20
# 安装runtimes
ninja -C build install/strip -j 20
```

在编译完runtimes后还需要将llvm相关库复制到sysroot下，以便在后续使用过程中通过命令行选项切换使用的库，以及编译出不依赖gnu相关库的llvm。
值得注意的是，compiler-rt相关库需要复制到`prefix/lib/clang/version`而不是sysroot下。同时，对于Windows平台而言，dll位于`bin`目录下，而对于
Linux平台而言，so位于`lib`目录下。最后，在安装带runtimes的llvm时会安装一份libcxx的头文件到`prefix/include/c++/v1`下，此部分头文件是跨平台的，无需重复
复制到sysroot下。而libcxx中与平台相关的部分储存在`__config_site`文件中，故该文件需要复制到sysroot下。
下面以复制`x86_64-linux-gnu`相关的库为例：

```python
import os
import shutil

def overwrite_copy(src: str, dst: str, is_dir: bool = False):
    """复制文件或目录，会覆盖已存在项

    Args:
        src (str): 源路径
        dst (str): 目标路径
        is_dir (bool, optional): 目标是否为目录. 默认为否（文件）
    """
    if is_dir:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copyfile(src, dst, follow_symlinks=False)

home = os.environ["HOME"]
prefix = f"{home}/x86_64-linux-gnu-clang19/install"
sysroot = f"{home}/sysroot"
compiler_rt = f"{home}/x86_64-linux-gnu-clang19/lib/clang/19/lib"
for dir in os.listdir(prefix):
    src_dir = os.path.join(prefix, dir)
    match dir:
        case "lib":
            dst_dir = os.path.join(sysroot, target, "lib")
            if not os.path.exists(compiler_rt):
                os.mkdir(compiler_rt)
            for item in os.listdir(src_dir):
                # 复制compiler-rt
                if item == "linux":
                    item = item.lower()
                    rt_dir = os.path.join(compiler_rt, item)
                    if not os.path.exists(rt_dir):
                        os.mkdir(rt_dir)
                    for file in os.listdir(os.path.join(src_dir, item)):
                        overwrite_copy(os.path.join(src_dir, item, file), os.path.join(rt_dir, file))
                    continue
                # 复制其他库
                overwrite_copy(os.path.join(src_dir, item), os.path.join(dst_dir, item))
        case "include":
            # 复制__config_site
            dst_dir = os.path.join(sysroot, target, "include")
            overwrite_copy(os.path.join(src_dir, "c++", "v1", "__config_site"), os.path.join(dst_dir, "__config_site"))
```

#### (2)再次编译llvm

此次只编译llvm及子项目，不编译runtimes，但可以启用`clang-tools-extra`等额外的子项目。值得注意的是，本次构建结束后需要保留构建目录，其中包含交叉
编译`clang-tools-extra`等项目所需的本地工具，同时它们不会被构建脚本安装到`prefix`中。如果删除该目录，在交叉编译时llvm的`NATIVE`编译过程不能正确的生成这部分工具，
进而导致交叉编译失败。

为了实现全面的llvm化，可以将clang默认的库设置成llvm相关库而不是gnu相关库，以实现运行库的替换。它们的关系如下：

| gnu          | llvm                            |
| ------------ | ------------------------------- |
| libsanitizer | compiler-rt                     |
| libgcc       | compiler-rt+libunwind+libcxxabi |
| libstdc++    | libcxx                          |

使用选项`-stdlib=libc++`，`-unwindlib=libunwind`和`-rtlib=compiler-rt`即可将clang使用的运行库切换到llvm相关库上。

下面是再次编译llvm的相关选项（一些重复选项的说明请参阅[首次编译流程](#1首次编译llvm以及runtimes)：

```shell
# 重复部分参考llvm_option_list1
# 增加子项目：clang-tools-extra
# 开启LTO以提升性能
# 设置clang默认运行库为libcxx、libunwind和compiler-rt
export llvm_option_list2='-DCMAKE_BUILD_TYPE=Release -DLLVM_BUILD_DOCS=OFF -DLLVM_BUILD_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_TARGETS_TO_BUILD="X86;AArch64;WebAssembly;RISCV;ARM;LoongArch" -DLLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lld" -DLLVM_ENABLE_WARNINGS=OFF -DCLANG_INCLUDE_TESTS=OFF -DBENCHMARK_INSTALL_DOCS=OFF -DCLANG_DEFAULT_LINKER=lld -DLLVM_ENABLE_LLD=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DLIBCXX_INCLUDE_BENCHMARKS=OFF -DLIBCXX_USE_COMPILER_RT=ON -DLIBCXX_CXX_ABI=libcxxabi -DLIBCXXABI_USE_LLVM_UNWINDER=ON -DLIBCXXABI_USE_COMPILER_RT=ON -DLIBUNWIND_USE_COMPILER_RT=ON -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON -DCOMPILER_RT_USE_LIBCXX=ON -DLLVM_ENABLE_LTO=Thin -DCLANG_DEFAULT_CXX_STDLIB=libc++ -DCLANG_DEFAULT_RTLIB=compiler-rt -DCLANG_DEFAULT_UNWINDLIB=libunwind'
# 切换运行库为llvm相关库
export lib_flags="-stdlib=libc++ -unwindlib=libunwind -rtlib=compiler-rt"
# 设置编译器为clang并且使用llvm相关库
export flags="\"-Wno-unused-command-line-argument --gcc-toolchain=$HOME/sysroot $lib_flags\""
export compiler_option="-DCMAKE_C_COMPILER=\"clang\" -DCMAKE_C_COMPILER_TARGET=$target -DCMAKE_C_FLAGS=$flags -DCMAKE_C_COMPILER_WORKS=ON -DCMAKE_CXX_COMPILER=\"clang++\" -DCMAKE_CXX_COMPILER_TARGET=$target -DCMAKE_CXX_FLAGS=$flags -DCMAKE_CXX_COMPILER_WORKS=ON -DCMAKE_ASM_COMPILER=\"clang\" -DCMAKE_ASM_COMPILER_TARGET=$target -DCMAKE_ASM_FLAGS=$flags -DCMAKE_ASM_COMPILER_WORKS=ON -DLLVM_RUNTIMES_TARGET=$target -DLLVM_DEFAULT_TARGET_TRIPLE=$host -DLLVM_HOST_TRIPLE=$host -DCMAKE_LINK_FLAGS=\"$lib_flags\""
# 进入llvm项目目录
cd ~/llvm
# 配置llvm
cmake -G Ninja --install-prefix $llvm_prefix -B build-x86_64-linux-gnu-llvm -S llvm $dylib_option_list $llvm_option_list2 $compiler_option
# 编译llvm
ninja -C build -j 20
# 安装llvm
ninja -C build install/strip -j 20
```
