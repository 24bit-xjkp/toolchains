#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import shutil
from common import *

lib_list = ("zlib", "libxml2")
system_list: dict[str, str] = {
    "x86_64-linux-gnu": "Linux",
    "i686-linux-gnu": "Linux",
    "aarch64-linux-gnu": "Linux",
    "riscv64-linux-gnu": "Linux",
    "loongarch64-linux-gnu": "Linux",
    "x86_64-w64-mingw32": "Windows",
    "i686-w64-mingw32": "Windows",
}
subproject_list = ("llvm", "runtimes")


def get_cmake_option(**kwargs) -> list[str]:
    """将字典转化为cmake选项列表

    Returns:
        list[str]: cmake选项列表
    """
    option_list: list[str] = []
    for key, value in kwargs.items():
        option_list.append(f"-D{key}={value}")
    return option_list


def gnu_to_llvm(target: str) -> str:
    """将gnu风格triplet转化为llvm风格

    Args:
        target (str): 目标平台

    Returns:
        str: llvm风格triplet
    """
    if target.count("-") == 2:
        index = target.find("-")
        result = target[:index]
        result += "-unknown"
        result += target[index:]
        return result
    else:
        return target


class environment(basic_environment):
    host: str  # < host平台
    build: str  # build平台
    prefix: dict[str, str] = {}  # < 工具链安装位置
    lib_dir_list: dict[str, str]  # < 所有库所在目录
    bin_dir: str  # < 安装后可执行文件所在目录
    source_dir: dict[str, str] = {}  # < 源代码所在目录
    build_dir: dict[str, str] = {}  # < 构建时所在目录
    stage: int = 1  # < 自举阶段
    compiler_list = ("C", "CXX", "ASM")  # < 编译器列表
    sysroot_dir: str  # < sysroot所在路径
    dylib_option_list: dict[str, str] = {  # < llvm动态链接选项
        "LLVM_LINK_LLVM_DYLIB": "ON",
        "LLVM_BUILD_LLVM_DYLIB": "ON",
        "CLANG_LINK_CLANG_DYLIB": "ON",
    }
    # 如果符号过多则Windows下需要该用该选项
    # dylib_option_list_windows: dict[str, str] = {"BUILD_SHARED_LIBS": "ON"}
    llvm_option_list_1: dict[str, str] = {  # < 第1阶段编译选项，同时构建工具链和运行库
        "CMAKE_BUILD_TYPE": "Release",  # < 设置构建类型
        "LLVM_BUILD_DOCS": "OFF",  # < 禁用llvm文档构建
        "LLVM_BUILD_EXAMPLES": "OFF",  # < 禁用llvm示例构建
        "LLVM_INCLUDE_BENCHMARKS": "OFF",  # < 禁用llvm基准测试构建
        "LLVM_INCLUDE_EXAMPLES": "OFF",  # < llvm不包含示例
        "LLVM_INCLUDE_TESTS": "OFF",  # < llvm不包含单元测试
        "LLVM_TARGETS_TO_BUILD": '"X86;AArch64;WebAssembly;RISCV;ARM;LoongArch"',  # < 设置需要构建的目标
        "LLVM_ENABLE_PROJECTS": '"clang;lld"',  # < 设置一同构建的子项目
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libcxxabi;libunwind;compiler-rt"',  # < 设置一同构建的运行时项目
        "LLVM_ENABLE_WARNINGS": "OFF",  # < 禁用警告
        "LLVM_INCLUDE_TESTS": "OFF",  # < llvm不包含单元测试
        "CLANG_INCLUDE_TESTS": "OFF",  # < clang不包含单元测试
        "BENCHMARK_INSTALL_DOCS": "OFF",  # < 基准测试不包含文档
        "LLVM_INCLUDE_BENCHMARKS": "OFF",  # < llvm不包含基准测试
        "CLANG_DEFAULT_LINKER": "lld",  # < 使用lld作为clang默认的链接器
        "LLVM_ENABLE_LLD": "ON",  # < 使用lld链接llvm以加速链接
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "ON",  # < 在linux系统上设置rpath以避免动态库环境混乱
        "LIBCXX_INCLUDE_BENCHMARKS": "OFF",  # < libcxx不包含测试
        "LIBCXX_USE_COMPILER_RT": "ON",  # < 使用compiler-rt构建libcxx
        "LIBCXX_CXX_ABI": "libcxxabi",  # 使用libcxxabi构建libcxx
        "LIBCXXABI_USE_LLVM_UNWINDER": "ON",  # < 使用libunwind构建libcxxabi
        "LIBCXXABI_USE_COMPILER_RT": "ON",  # < 使用compiler-rt构建libcxxabi
        "LIBUNWIND_USE_COMPILER_RT": "ON",  # < 使用compiler-rt构建libunwind
        "COMPILER_RT_DEFAULT_TARGET_ONLY": "ON",  # < compiler-rt只需构建默认目标即可，禁止自动构建multilib
        "COMPILER_RT_USE_LIBCXX": "ON",  # < 使用libcxx构建compiler-rt
    }
    llvm_option_list_w64_1: dict[str, str] = {  # < win64运行时第1阶段编译选项
        **llvm_option_list_1,
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libunwind;compiler-rt"',
        "LIBCXX_CXX_ABI": "libsupc++",
    }
    llvm_option_list_w32_1: dict[str, str] = {**llvm_option_list_w64_1}  # < win32运行时第1阶段编译选项
    llvm_option_list_2: dict[str, str] = {  # < 第2阶段编译选项，该阶段不编译运行库
        **llvm_option_list_1,
        "LLVM_ENABLE_PROJECTS": '"clang;clang-tools-extra;lld"',
        "LLVM_ENABLE_LTO": "Thin",
        "CLANG_DEFAULT_CXX_STDLIB": "libc++",
        "CLANG_DEFAULT_RTLIB": "compiler-rt",
        "CLANG_DEFAULT_UNWINDLIB": "libunwind",
    }
    llvm_option_list_3: dict[str, str] = {**llvm_option_list_2}  # < 第3阶段编译选项，编译运行库
    llvm_option_list_w64_3: dict[str, str] = {}  # < win64运行时第3阶段编译选项
    llvm_option_list_w32_3: dict[str, str] = {}  # < win32运行时第3阶段编译选项
    lib_option: dict[str, str] = {  # < llvm依赖库编译选项
        "BUILD_SHARED_LIBS": "ON",
        "LIBXML2_WITH_ICONV": "OFF",
        "LIBXML2_WITH_LZMA": "OFF",
        "LIBXML2_WITH_PYTHON": "OFF",
        "LIBXML2_WITH_ZLIB": "OFF",
        "LIBXML2_WITH_THREADS": "OFF",
        "LIBXML2_WITH_CATALOG": "OFF",
        "CMAKE_RC_COMPILER": "llvm-windres",
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "ON",
    }
    llvm_cross_option: dict[str, str] = {}  # < llvm交叉编译选项
    compiler_rt_dir: str  # < compiler-rt所在路径

    def _set_prefix(self) -> None:
        """设置安装路径"""
        self.prefix["llvm"] = os.path.join(self.home_dir, self.name) if self.stage == 1 else os.path.join(self.home_dir, f"{self.name}-new")
        self.prefix["runtimes"] = os.path.join(self.prefix["llvm"], "install")
        self.compiler_rt_dir = os.path.join(self.prefix["llvm"], "lib", "clang", self.major_version, "lib")

    def __init__(self, build: str = "x86_64-linux-gnu", host: str = "") -> None:
        self.build = build
        self.host = host if host != "" else self.build
        name_without_version = f"{self.host}-clang"
        super().__init__("19", name_without_version)
        # 设置prefix
        self._set_prefix()
        for lib in lib_list:
            self.prefix[lib] = os.path.join(self.home_dir, lib, "install")
        # 设置源目录和构建目录
        for project in subproject_list:
            self.source_dir[project] = os.path.join(self.home_dir, "llvm", project)
            self.build_dir[project] = os.path.join(self.home_dir, "llvm", f"build-{self.host}-{project}")
            check_lib_dir(project, self.source_dir[project])
        for lib in lib_list:
            self.source_dir[lib] = os.path.join(self.home_dir, lib)
            self.build_dir[lib] = os.path.join(self.source_dir[lib], "build")
            check_lib_dir(lib, self.source_dir[lib])
        # 设置sysroot目录
        self.sysroot_dir = os.path.join(self.home_dir, "sysroot")
        # 配置Windows运行库编译选项
        include_dir = os.path.join(self.sysroot_dir, "x86_64-w64-mingw32/include/c++")
        for dir in os.listdir(include_dir):
            if dir[0:2].isdigit():
                include_dir = os.path.join(include_dir, dir)
        self.llvm_option_list_w64_1["LIBCXX_CXX_ABI_INCLUDE_PATHS"] = include_dir
        include_dir = os.path.join(self.sysroot_dir, "i686-w64-mingw32/include/c++")
        for dir in os.listdir(include_dir):
            if dir[0:2].isdigit():
                include_dir = os.path.join(include_dir, dir)
        self.llvm_option_list_w32_1["LIBCXX_CXX_ABI_INCLUDE_PATHS"] = include_dir
        # 第2阶段不编译运行库
        if "LLVM_ENABLE_RUNTIMES" in self.llvm_option_list_2:
            del self.llvm_option_list_2["LLVM_ENABLE_RUNTIMES"]
        self.llvm_option_list_w64_3 = {**self.llvm_option_list_3, **self.llvm_option_list_w64_1}
        self.llvm_option_list_w32_3 = {**self.llvm_option_list_3, **self.llvm_option_list_w32_1}
        # 设置llvm依赖库编译选项
        zlib = f'"{os.path.join(self.prefix["zlib"], "lib", "libzlibstatic.a")}"'
        self.llvm_cross_option = {
            "LIBXML2_INCLUDE_DIR": f'"{os.path.join(self.prefix["libxml2"], "include", "libxml2")}"',
            "LIBXML2_LIBRARY": f'"{os.path.join(self.prefix["libxml2"], "lib", "libxml2.dll.a")}"',
            "CLANG_ENABLE_LIBXML2": "ON",
            "ZLIB_INCLUDE_DIR": f'"{os.path.join(self.prefix["zlib"], "include")}"',
            "ZLIB_LIBRARY": zlib,
            "ZLIB_LIBRARY_RELEASE": zlib,
            "LLVM_NATIVE_TOOL_DIR": f'"{os.path.join(self.source_dir["llvm"], f"build-{self.build}-llvm", "bin")}"',
        }
        # 将自身注册到环境变量中
        self.register_in_env()

    def next_stage(self) -> None:
        """进入下一阶段"""
        self.stage += 1
        self._set_prefix()

    def get_compiler(self, target: str, *command_list_in) -> list[str]:
        """获取编译器选项

        Args:
            target (str): 目标平台

        Returns:
            list[str]: 编译选项
        """
        assert target in system_list
        gcc = f"--gcc-toolchain={self.sysroot_dir}"
        command_list: list[str] = []
        compiler_path = {"C": "clang", "CXX": "clang++", "ASM": "clang"}
        no_warning = "-Wno-unused-command-line-argument"
        for compiler in self.compiler_list:
            command_list.append(f'-DCMAKE_{compiler}_COMPILER="{compiler_path[compiler]}"')
            command_list.append(f"-DCMAKE_{compiler}_COMPILER_TARGET={target}")
            command_list.append(f'-DCMAKE_{compiler}_FLAGS="{no_warning} {gcc} {" ".join(command_list_in)}"')
            command_list.append(f"-DCMAKE_{compiler}_COMPILER_WORKS=ON")
        if target != self.build:
            command_list.append(f"-DCMAKE_SYSTEM_NAME={system_list[target]}")
            command_list.append(f"-DCMAKE_SYSTEM_PROCESSOR={target[: target.find('-')]}")
            command_list.append(f'-DCMAKE_SYSROOT="{self.sysroot_dir}"')
            command_list.append("-DCMAKE_CROSSCOMPILING=TRUE")
        command_list.append(f"-DLLVM_RUNTIMES_TARGET={target}")
        command_list.append(f"-DLLVM_DEFAULT_TARGET_TRIPLE={gnu_to_llvm(target)}")
        command_list.append(f"-DLLVM_HOST_TRIPLE={gnu_to_llvm(self.host)}")
        command_list.append(f'-DCMAKE_LINK_FLAGS="{" ".join(command_list_in)}"')
        return command_list

    def config(self, project: str, target: str, *command_list, **cmake_option_list) -> None:
        """配置项目

        Args:
            project (str): 子项目
            target (str): 目标平台
            command_list: 附加编译选项
            cmake_option_list: 附加cmake配置选项
        """
        assert project in (*subproject_list, *lib_list)
        command = f"cmake -G Ninja --install-prefix {self.prefix[project]} -B {self.build_dir[project]} -S {self.source_dir[project]} "
        command += " ".join(self.get_compiler(target, *command_list) + get_cmake_option(**cmake_option_list))
        run_command(command)

    def make(self, project: str) -> None:
        """构建项目

        Args:
            project (str): 目标项目
        """
        assert project in (*subproject_list, *lib_list)
        run_command(f"ninja -C {self.build_dir[project]} -j{self.num_cores}")

    def install(self, project: str) -> None:
        """安装项目

        Args:
            project (str): 目标项目
        """
        assert project in (*subproject_list, *lib_list)
        run_command(f"ninja -C {self.build_dir[project]} install/strip -j{self.num_cores}")

    def remove_build_dir(self, project: str) -> None:
        """移除构建目录

        Args:
            project (str): 目标项目
        """
        assert project in subproject_list
        dir = self.build_dir[project]
        if os.path.exists(dir):
            shutil.rmtree(dir)
        if project == "runtimes":
            dir = self.prefix[project]
            if os.path.exists(dir):
                shutil.rmtree(dir)

    def build_sysroot(self, target: str) -> None:
        """构建sysroot

        Args:
            target (str): 目标平台
        """
        prefix = self.prefix["runtimes"]
        for dir in os.listdir(prefix):
            src_dir = os.path.join(prefix, dir)
            match dir:
                case "bin":
                    # 复制dll
                    dst_dir = os.path.join(self.sysroot_dir, target, "lib")
                    for file in os.listdir(src_dir):
                        if file.endswith("dll"):
                            copy(os.path.join(src_dir, file), os.path.join(dst_dir, file))
                case "lib":
                    dst_dir = os.path.join(self.sysroot_dir, target, "lib")
                    if not os.path.exists(self.compiler_rt_dir):
                        os.mkdir(self.compiler_rt_dir)
                    for item in os.listdir(src_dir):
                        # 复制compiler-rt
                        if item == system_list[target].lower():
                            rt_dir = os.path.join(self.compiler_rt_dir, item)
                            if not os.path.exists(rt_dir):
                                os.mkdir(rt_dir)
                            for file in os.listdir(os.path.join(src_dir, item)):
                                copy(os.path.join(src_dir, item, file), os.path.join(rt_dir, file))
                            continue
                        # 复制其他库
                        copy(os.path.join(src_dir, item), os.path.join(dst_dir, item))
                case "include":
                    # 复制__config_site
                    dst_dir = os.path.join(self.sysroot_dir, target, "include")
                    copy(os.path.join(src_dir, "c++", "v1", "__config_site"), os.path.join(dst_dir, "__config_site"))

    def copy_llvm_libs(self) -> None:
        """复制工具链所需库"""
        src_dir = os.path.join(self.sysroot_dir, self.host, "lib")
        dst_dir = os.path.join(self.prefix["llvm"], "lib")
        native_dir = os.path.join(self.home_dir, f"{self.build}-clang{self.major_version}")
        native_bin_dir = os.path.join(native_dir, "bin")
        native_compiler_rt_dir = os.path.join(native_dir, "lib", "clang", self.major_version, "lib")
        # 复制libc++和libunwind运行库
        for file in filter(lambda file: file.startswith(("libc++", "libunwind")) and not file.endswith(".a"), os.listdir(src_dir)):
            copy(os.path.join(src_dir, file), os.path.join(dst_dir, file))
        # 复制公用libc++头文件
        src_dir = os.path.join(native_bin_dir, "..", "include", "c++", "v1")
        dst_dir = os.path.join(self.prefix["llvm"], "include", "c++")
        if not os.path.exists(dst_dir):
            os.mkdir(dst_dir)
        dst_dir = os.path.join(dst_dir, "v1")
        copy(src_dir, dst_dir, True)
        if self.build != self.host:
            # 从build下的本地工具链复制compiler-rt
            # 其他库在sysroot中，无需复制
            src_dir = native_compiler_rt_dir
            dst_dir = self.compiler_rt_dir
            copy(src_dir, dst_dir, True)
            # 复制libxml2
            src_path = os.path.join(self.prefix["libxml2"], "bin", "libxml2.dll")
            dst_path = os.path.join(self.prefix["llvm"], "lib", "libxml2.dll")
            copy(src_path, dst_path)

    def change_name(self) -> None:
        """修改多阶段自举时的安装目录名"""
        name = os.path.join(self.home_dir, self.name)
        # clang->clang-old
        # clang-new->clang
        if not os.path.exists(f"{name}-old"):
            os.rename(name, f"{name}-old")
            os.rename(self.prefix["llvm"], name)

    def package(self) -> None:
        """打包工具链"""
        self.copy_readme()
        self.compress()
