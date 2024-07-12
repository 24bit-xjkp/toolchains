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
sudo apt install git python3 cmake ninja-build clang lld libxml2-dev
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
