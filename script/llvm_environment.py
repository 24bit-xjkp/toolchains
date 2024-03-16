#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import psutil
import shutil
import sys
from math import floor


def run_command(command: str) -> None:
    """运行程序，并在失败时退出脚本"""
    print(command)
    assert os.system(command) == 0, f'Command "{command}" failed.'


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


class environment:
    major_version: str  # < LLVM的主版本号
    host: str  # < host平台
    build: str  # build平台
    name_without_version: str  # < 不带版本号的工具链名
    name: str  # < 工具链名
    home_dir: str  # < 源代码所在的目录，默认为$HOME
    prefix: dict[str, str] = {}  # < 工具链安装位置
    num_cores: int  # < 编译所用线程数
    current_dir: str  # < toolchains项目所在目录
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
        "CMAKE_BUILD_TYPE": "Release",
        "LLVM_BUILD_DOCS": "OFF",
        "LLVM_BUILD_EXAMPLES": "OFF",
        "LLVM_INCLUDE_BENCHMARKS": "OFF",
        "LLVM_INCLUDE_EXAMPLES": "OFF",
        "LLVM_INCLUDE_TESTS": "OFF",
        "LLVM_TARGETS_TO_BUILD": '"X86;AArch64;WebAssembly;RISCV;ARM;LoongArch"',
        "LLVM_ENABLE_PROJECTS": '"clang;lld"',
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libcxxabi;libunwind;compiler-rt"',
        "LLVM_ENABLE_WARNINGS": "OFF",
        "LLVM_INCLUDE_TESTS": "OFF",
        "CLANG_INCLUDE_TESTS": "OFF",
        "BENCHMARK_INSTALL_DOCS": "OFF",
        "LLVM_INCLUDE_BENCHMARKS": "OFF",
        "CLANG_DEFAULT_LINKER": "lld",
        "LLVM_ENABLE_LLD": "ON",
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "ON",
        "LIBCXX_INCLUDE_BENCHMARKS": "OFF",
        "LIBCXX_USE_COMPILER_RT": "ON",
        "LIBCXX_CXX_ABI": "libcxxabi",
        "COMPILER_RT_DEFAULT_TARGET_ONLY": "ON",
        "COMPILER_RT_BUILD_BUILTINS": "ON",
        "COMPILER_RT_USE_LIBCXX": "ON",
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

    def __init__(self, major_version: str, build: str, host: str = "") -> None:
        self.major_version = major_version
        self.build = build
        self.host = host if host != "" else self.build
        self.name_without_version = f"{self.host}-clang"
        self.name = self.name_without_version + major_version
        self.home_dir = ""
        for option in sys.argv:
            if option.startswith("--home="):
                self.home_dir = option[7:]
            elif option.startswith("--stage="):
                value = option[8:]
                assert value.isdigit(), 'Option "--stage=" needs an integer'
                self.stage = int(value)
                assert 1 <= self.stage <= 4, "Stage should range from 1 to 4"
        if self.home_dir == "":
            self.home_dir = os.environ["HOME"]
        # 设置prefix
        self._set_prefix()
        for lib in lib_list:
            self.prefix[lib] = os.path.join(self.home_dir, lib, "install")
        # 设置并发数
        self.num_cores = floor(psutil.cpu_count() * 1.5)
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.bin_dir = os.path.join(os.path.join(self.home_dir, self.name), "bin")
        # 设置源目录和构建目录
        for project in subproject_list:
            self.source_dir[project] = os.path.join(self.home_dir, "llvm", project)
            self.build_dir[project] = os.path.join(self.home_dir, "llvm", f"build-{self.host}-{project}")
        for lib in lib_list:
            self.source_dir[lib] = os.path.join(self.home_dir, lib)
            self.build_dir[lib] = os.path.join(self.source_dir[lib], "build")
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

    def register_in_env(self) -> None:
        """注册安装路径到环境变量"""
        os.environ["PATH"] = f"{self.bin_dir}:{os.environ['PATH']}"

    def register_in_bashrc(self) -> None:
        """注册安装路径到用户配置文件"""
        with open(os.path.join(self.home_dir, ".bashrc"), "a") as bashrc_file:
            bashrc_file.write(f"export PATH={self.bin_dir}:$PATH\n")

    def get_compiler(self, target: str, *command_list_in) -> list[str]:
        """获取编译器选项

        Args:
            target (str): 目标平台

        Returns:
            list[str]: 编译选项
        """
        assert target in system_list
        gcc = f"--gcc-toolchain={os.path.join(self.home_dir, 'sysroot')}"
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
                            overwrite_copy(os.path.join(src_dir, file), os.path.join(dst_dir, file))
                case "lib":
                    dst_dir = os.path.join(self.sysroot_dir, target, "lib")
                    if not os.path.exists(self.compiler_rt_dir):
                        os.mkdir(self.compiler_rt_dir)
                    for item in os.listdir(src_dir):
                        # 复制compiler-rt
                        if item == system_list[target].lower():
                            item = item.lower()
                            rt_dir = os.path.join(self.compiler_rt_dir, item)
                            if not os.path.exists(rt_dir):
                                os.mkdir(rt_dir)
                            for file in os.listdir(os.path.join(src_dir, item)):
                                overwrite_copy(os.path.join(src_dir, item, file), os.path.join(rt_dir, file))
                            continue
                        # 复制其他库
                        overwrite_copy(os.path.join(src_dir, item), os.path.join(dst_dir, item))
                case "include":
                    # 复制__config_site
                    dst_dir = os.path.join(self.sysroot_dir, target, "include")
                    overwrite_copy(os.path.join(src_dir, "c++", "v1", "__config_site"), os.path.join(dst_dir, "__config_site"))

    def copy_llvm_libs(self) -> None:
        """复制工具链所需库"""
        src_dir = os.path.join(self.sysroot_dir, self.host, "lib")
        dst_dir = os.path.join(self.prefix["llvm"], "lib")
        native_dir = os.path.join(self.home_dir, f"{self.build}-clang{self.major_version}")
        native_bin_dir = os.path.join(native_dir, "bin")
        native_compiler_rt_dir = os.path.join(native_dir, "lib", "clang", self.major_version, "lib")
        # 复制libc++和libunwind运行库
        for file in filter(lambda file: file.startswith(("libc++", "libunwind")) and not file.endswith(".a"), os.listdir(src_dir)):
            overwrite_copy(os.path.join(src_dir, file), os.path.join(dst_dir, file))
        # 复制公用libc++头文件
        src_dir = os.path.join(native_bin_dir, "..", "include", "c++", "v1")
        dst_dir = os.path.join(self.prefix["llvm"], "include", "c++")
        if not os.path.exists(dst_dir):
            os.mkdir(dst_dir)
        dst_dir = os.path.join(dst_dir, "v1")
        overwrite_copy(src_dir, dst_dir, True)
        if self.build != self.host:
            # 从build下的本地工具链复制compiler-rt
            # 其他库在sysroot中，无需复制
            src_dir = native_compiler_rt_dir
            dst_dir = self.compiler_rt_dir
            overwrite_copy(src_dir, dst_dir, True)
            # 复制libxml2
            src_path = os.path.join(self.prefix["libxml2"], "bin", "libxml2.dll")
            dst_path = os.path.join(self.prefix["llvm"], "lib", "libxml2.dll")
            overwrite_copy(src_path, dst_path)

    def copy_readme(self) -> None:
        """复制工具链说明文件"""
        readme_path = os.path.join(self.current_dir, "..", "readme", f"{self.name_without_version}.md")
        target_path = os.path.join(os.path.join(self.home_dir, self.name), "README.md")
        shutil.copyfile(readme_path, target_path)

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
        os.chdir(self.home_dir)
        run_command(f"tar -cf {self.name}.tar {self.name}")
        memory_MB = psutil.virtual_memory().total // 1048576
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")
