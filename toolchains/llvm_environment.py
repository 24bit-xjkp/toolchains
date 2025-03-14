from pathlib import Path

from . import common
from .gcc_environment import get_specific_environment
from enum import StrEnum
from copy import deepcopy
import typing

lib_list = ("zlib", "libxml2")
subproject_list = ("llvm", "runtimes")


def get_cmake_option(options: dict[str, str]) -> list[str]:
    """将字典转化为cmake选项列表

    Returns:
        list[str]: cmake选项列表
    """

    option_list: list[str] = []
    for key, value in options.items():
        option_list.append(f"-D{key}={value}")
    return option_list


def gnu_to_llvm(target: str) -> str:
    """将gnu风格triplet转化为llvm风格

    Args:
        target (str): 目标平台

    Returns:
        str: llvm风格triplet
    """

    triplet_filed = common.triplet_field(target, False)
    if triplet_filed.os == "w64":
        triplet_filed.os = "windows"
    if triplet_filed.abi == "mingw32":
        triplet_filed.abi = "gnu"
    return str(triplet_filed)


class runtime_family(StrEnum):
    """运行库类型

    Attributes:
        llvm: LLVM系运行库
        gnu : GCC系运行库
    """

    llvm = "llvm"
    gnu = "gnu"


class cmake_generator(StrEnum):
    """cmake生成工具

    Attributes:
        make: Linux默认的生成工具
        ninja : ninja可以提供更快的生成速度
    """

    make = "make"
    ninja = "ninja"

    def get_cmake_option(self) -> str:
        """获取cmake生成器选项中的名称

        Returns:
            str: 生成器名称
        """

        option_map = {"make": '"Unix Makefiles"', "ninja": "Ninja"}
        return option_map[self]


class build_options:
    basic_option: list[str]
    cmake_option: dict[str, str]
    system_name: str

    def __init__(self, basic_option: list[str], cmake_option: dict[str, str], system_name: str) -> None:
        """构建相关选项

        Args:
            basic_option (list[str]): 传递给工具链的基本选项
            cmake_option (dict[str, str]): 传递给cmake的configure选项
            system_name (str): CMAKE_SYSTEM_NAME选项
        """

        self.basic_option = basic_option
        self.cmake_option = cmake_option
        self.system_name = system_name

    def __repr__(self) -> str:
        return vars(self).__repr__()


class llvm_environment(common.basic_environment):
    host: str  # host平台
    family: runtime_family  # 使用的运行库类型
    prefix: dict[str, Path] = {}  # 工具链安装位置
    lib_dir_list: dict[str, Path]  # 所有库所在目录
    source_dir: dict[str, Path] = {}  # 源代码所在目录
    build_dir: dict[str, Path] = {}  # 构建时所在目录
    compiler_list = ("C", "CXX", "ASM")  # 编译器列表
    sysroot_dir: dict[str, Path]  # sysroot所在路径
    generator_list: dict[str, cmake_generator]  # 构建指定目标平台的工具时使用的生成器
    llvm_build_options: build_options  # llvm构建选项
    runtime_build_options: dict[str, build_options]  # 运行库构建选项
    dylib_option_list: typing.Final[dict[str, str]] = {  # llvm动态链接选项
        "LLVM_LINK_LLVM_DYLIB": "ON",
        "LLVM_BUILD_LLVM_DYLIB": "ON",
        "CLANG_LINK_CLANG_DYLIB": "ON",
    }
    # 如果符号过多则Windows下需要改用该选项
    # dylib_option_list_windows: dict[str, str] = {"BUILD_SHARED_LIBS": "ON"}
    llvm_option_list: typing.Final[dict[str, str]] = {  # 第1阶段编译选项，同时构建工具链和运行库
        "CMAKE_BUILD_TYPE": "Release",  # 设置构建类型
        "LLVM_BUILD_DOCS": "OFF",  # 禁用llvm文档构建
        "LLVM_BUILD_EXAMPLES": "OFF",  # 禁用llvm示例构建
        "LLVM_INCLUDE_BENCHMARKS": "OFF",  # 禁用llvm基准测试构建
        "LLVM_INCLUDE_EXAMPLES": "OFF",  # llvm不包含示例
        "LLVM_INCLUDE_TESTS": "OFF",  # llvm不包含单元测试
        "LLVM_TARGETS_TO_BUILD": '"X86;AArch64;RISCV;ARM;LoongArch;Mips"',  # 设置需要构建的目标
        "LLVM_ENABLE_PROJECTS": '"clang;clang-tools-extra;lld;lldb;bolt"',  # 设置一同构建的子项目
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libcxxabi;libunwind;compiler-rt;openmp"',  # 设置一同构建的运行时项目
        "LLVM_ENABLE_WARNINGS": "OFF",  # 禁用警告
        "LLVM_ENABLE_LTO": "Thin",  # 启用lto
        "LLVM_INCLUDE_TESTS": "OFF",  # llvm不包含单元测试
        "CLANG_INCLUDE_TESTS": "OFF",  # clang不包含单元测试
        "LLVM_INCLUDE_BENCHMARKS": "OFF",  # llvm不包含基准测试
        "CLANG_DEFAULT_LINKER": "lld",  # 使用lld作为clang默认的链接器
        "LLVM_ENABLE_LLD": "ON",  # 使用lld链接llvm以加速链接
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "ON",  # 在linux系统上设置rpath以避免动态库环境混乱
        "LIBCXX_INCLUDE_BENCHMARKS": "OFF",  # libcxx不包含测试
        "LIBCXX_USE_COMPILER_RT": "ON",  # 使用compiler-rt构建libcxx
        "LIBCXX_CXX_ABI": "libcxxabi",  # 使用libcxxabi构建libcxx
        "LIBCXXABI_USE_LLVM_UNWINDER": "ON",  # 使用libunwind构建libcxxabi
        "LIBCXXABI_USE_COMPILER_RT": "ON",  # 使用compiler-rt构建libcxxabi
        "COMPILER_RT_DEFAULT_TARGET_ONLY": "ON",  # compiler-rt只需构建默认目标即可，禁止自动构建multilib
        "COMPILER_RT_CXX_LIBRARY": "libcxx",  # 使用libcxx构建compiler-rt
        "LIBCXXABI_ENABLE_ASSERTIONS": "OFF",  # 禁用断言
        "LIBCXXABI_INCLUDE_TESTS": "OFF",  # 禁用libcxxabi测试
        "LLDB_INCLUDE_TESTS": "OFF",  # 禁用lldb测试
        "LLDB_ENABLE_PYTHON": "ON",  # 启用python支持
        "LIBOMP_OMPD_GDB_SUPPORT": "OFF",  # 禁用openmpd的gdb支持，该支持需要python，而交叉编译时无法提供
    }
    lib_option: typing.Final[dict[str, str]] = {  # llvm依赖库编译选项
        "BUILD_SHARED_LIBS": "OFF",
        "LIBXML2_WITH_ICONV": "OFF",
        "LIBXML2_WITH_LZMA": "OFF",
        "LIBXML2_WITH_PYTHON": "OFF",
        "LIBXML2_WITH_ZLIB": "OFF",
        "LIBXML2_WITH_THREADS": "OFF",
        "LIBXML2_WITH_CATALOG": "OFF",
        "LIBXML2_WITH_TESTS": "OFF",
        "CMAKE_RC_COMPILER": "llvm-windres",
        "CMAKE_BUILD_WITH_INSTALL_RPATH": "ON",
    }
    win32_options: typing.Final[dict[str, str]] = {
        "LIBCXXABI_ENABLE_THREADS": "ON",
        "LIBCXXABI_HAS_WIN32_THREAD_API": "ON",
        "LIBCXXABI_ENABLE_SHARED": "OFF",
        "LIBCXX_ENABLE_STATIC_ABI_LIBRARY": "ON",
        "LIBCXX_ENABLE_THREADS": "ON",
        "LIBCXX_HAS_WIN32_THREAD_API": "ON",
        "CMAKE_RC_COMPILER": "llvm-windres",
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libcxxabi;libunwind;compiler-rt"',  # 交叉编译下没有ml编译不了openmp
    }
    freestanding_option: typing.Final[dict[str, str]] = {
        "LIBUNWIND_IS_BAREMETAL": "ON",
        "LIBUNWIND_ENABLE_SHARED": "OFF",
        "COMPILER_RT_BUILD_SANITIZERS": "OFF",
        "COMPILER_RT_BUILD_XRAY": "OFF",
        "COMPILER_RT_BUILD_PROFILE": "OFF",
        "COMPILER_RT_BUILD_CTX_PROFILE": "OFF",
        "COMPILER_RT_BUILD_MEMPROF": "OFF",
        "COMPILER_RT_BUILD_GWP_ASAN": "OFF",
        "COMPILER_RT_BAREMETAL_BUILD": "ON",
        "LIBCXX_ENABLE_THREADS": "OFF",
        "LIBCXXABI_ENABLE_THREADS": "OFF",
        "LIBCXXABI_ENABLE_SHARED": "OFF",
        "LIBCXXABI_BAREMETAL": "ON",
        "LLVM_ENABLE_RUNTIMES": '"libcxx;libcxxabi;libunwind;compiler-rt"',
        "CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",
        "LIBCXX_ENABLE_SHARED": "OFF",
        "BUILD_SHARED_LIBS": "OFF",
        "LIBUNWIND_ENABLE_THREADS": "OFF",
        "LIBCXX_ENABLE_MONOTONIC_CLOCK": "OFF",
        "LIBCXX_ENABLE_FILESYSTEM": "OFF",
    }

    compiler_rt_dir: Path  # compiler-rt所在路径

    def __init__(
        self,
        build: str,
        host: str | None,
        family: runtime_family,
        runtime_target_list: list[str],
        home: Path,
        jobs: int,
        prefix_dir: Path,
        compress_level: int,
        long_distance_match: int,
        build_tmp: Path,
        default_generator: cmake_generator,
    ) -> None:
        """llvm构建环境

        Args:
            build (str): 构建平台
            host (str): 宿主平台
            family (runtime_family): 运行库类型
            runtime_target_list (list[str]): llvm运行时目标平台列表
            home (Path): 源代码树搜索主目录
            jobs (int): 并发构建数
            prefix_dir (str): 安装根目录
            compress_level (int): zstd压缩等级
            long_distance_match (int): 长距离匹配窗口大小
            build_tmp (Path): 构建工具链时存放临时文件的路径
            default_generator (cmake_generator): 默认的cmake生成工具
        """
        self.build = build
        self.host = host or self.build
        self.family = family
        name_without_version = f"{self.host}-clang"
        super().__init__(build, "21.0.0", name_without_version, home, jobs, prefix_dir, compress_level, long_distance_match, build_tmp)
        # 设置prefix
        self.prefix["llvm"] = self.prefix_dir / self.name
        self.compiler_rt_dir = self.prefix["llvm"] / "lib" / "clang" / self.major_version / "lib"
        common.mkdir(self.build_tmp, False)

        self.llvm_build_options = build_options(
            (
                ["-stdlib=libstdc++", "-unwindlib=libgcc", "-rtlib=libgcc"]
                if self.family == runtime_family.gnu
                else ["-stdlib=libc++", "-unwindlib=libunwind", "-rtlib=compiler-rt"]
            ),
            {**self.llvm_option_list, **self.dylib_option_list, "LLVM_PARALLEL_LINK_JOBS": str(self.jobs // 6)},
            "Linux" if common.triplet_field(self.host).os == "linux" else "Windows",
        )
        if self.family == runtime_family.llvm:
            self.llvm_build_options.cmake_option["LIBUNWIND_USE_COMPILER_RT"] = "ON"

        self.runtime_build_options = {}
        self.sysroot_dir = {}
        self.generator_list = {}
        for target in runtime_target_list:
            self.runtime_build_options[target] = deepcopy(self.llvm_build_options)
            gcc = get_specific_environment(self, target=target)
            if gcc.freestanding:
                self.runtime_build_options[target].system_name = "Generic"
                self.runtime_build_options[target].cmake_option.update(self.freestanding_option)
            elif gcc.target_field.os == "linux":
                self.runtime_build_options[target].system_name = "Linux"
            else:
                self.runtime_build_options[target].system_name = "Windows"
                self.runtime_build_options[target].cmake_option.update(self.win32_options)
            self.build_dir[f"{target}-runtimes"] = self.build_tmp / f"{target}-runtimes"
            self.prefix[f"{target}-runtimes"] = self.build_tmp / f"{target}-runtimes-install"
            self.sysroot_dir[target] = self.prefix_dir / "sysroot"
            self.generator_list[target] = default_generator
        for lib in lib_list:
            self.prefix[lib] = self.build_tmp / f"{self.host}-{lib}-install"
        # 设置源目录和构建目录
        for project in subproject_list:
            self.source_dir[project] = self.home / "llvm" / project
            common.check_lib_dir(project, self.source_dir[project])
        self.build_dir["llvm"] = self.build_tmp / f"{self.host}-llvm"
        for lib in lib_list:
            self.source_dir[lib] = self.home / lib
            self.build_dir[lib] = self.build_tmp / f"{self.host}-{lib}"
            common.check_lib_dir(lib, self.source_dir[lib])
        if self.build != self.host:
            # 交叉编译时runtimes已经编译过了
            del self.llvm_build_options.cmake_option["LLVM_ENABLE_RUNTIMES"]
            # 设置llvm依赖库编译选项
            zlib = f'"{self.prefix["zlib"] / "lib" / "libzlibstatic.a"}"'
            self.llvm_build_options.cmake_option.update(
                {
                    "LIBXML2_INCLUDE_DIR": f'"{self.prefix["libxml2"] / "include" / "libxml2"}"',
                    "LIBXML2_LIBRARY": f'"{self.prefix["libxml2"] / "lib" / "libxml2.a"}"',
                    "CLANG_ENABLE_LIBXML2": "ON",
                    "ZLIB_INCLUDE_DIR": f'"{self.prefix["zlib"] / "include"}"',
                    "ZLIB_LIBRARY": zlib,
                    "ZLIB_LIBRARY_RELEASE": zlib,
                    "LLVM_NATIVE_TOOL_DIR": f'"{self.prefix["llvm"] / f'{self.build}-clang{self.major_version}' / "bin"}"',
                }
            )
        # 将自身注册到环境变量中
        self.register_in_env()

    def get_compiler(self, target: str, command_list_in: list[str]) -> list[str]:
        """获取编译器选项

        Args:
            target (str): 目标平台
            command_list_in (list[str]): 编译器选项

        Returns:
            list[str]: 编译选项
        """

        assert target in [*self.runtime_build_options, self.host]
        command_list: list[str] = []
        compiler_path = {"C": "clang", "CXX": "clang++", "ASM": "clang"}
        sysroot_dir = self.sysroot_dir[target]
        gcc_toolchain = f"--gcc-toolchain={sysroot_dir}" if target == self.build else ""
        for compiler in self.compiler_list:
            command_list.append(f'-DCMAKE_{compiler}_COMPILER="{compiler_path[compiler]}"')
            command_list.append(f"-DCMAKE_{compiler}_COMPILER_TARGET={target}")
            command_list.append(f'-DCMAKE_{compiler}_FLAGS="-Wno-unused-command-line-argument {gcc_toolchain} {" ".join(command_list_in)}"')
            command_list.append(f"-DCMAKE_{compiler}_COMPILER_WORKS=ON")
        if target != self.build:
            system_name = (
                self.runtime_build_options[target].system_name
                if target in self.runtime_build_options
                else self.llvm_build_options.system_name
            )
            command_list.append(f"-DCMAKE_SYSTEM_NAME={system_name}")
            command_list.append(f"-DCMAKE_SYSTEM_PROCESSOR={common.triplet_field(target).arch}")
            command_list.append("-DCMAKE_CROSSCOMPILING=TRUE")
            command_list.append(f'-DCMAKE_SYSROOT="{sysroot_dir}"')
        command_list.append(f"-DLLVM_RUNTIMES_TARGET={target}")
        command_list.append(f"-DLLVM_DEFAULT_TARGET_TRIPLE={gnu_to_llvm(target)}")
        command_list.append(f"-DLLVM_HOST_TRIPLE={gnu_to_llvm(self.host)}")
        return command_list

    def config(self, project: str, target: str, command_list: list[str], cmake_option_list: dict[str, str]) -> None:
        """配置项目

        Args:
            project (str): 子项目
            target (str): 目标平台
            command_list (list[str]): 附加编译选项
            cmake_option_list (dict[str, str]): 附加cmake配置选项
        """

        assert project in self.build_dir
        source_dir = self.source_dir[project] if "runtimes" not in project else self.source_dir["runtimes"]
        command = f"cmake -G {self.generator_list[target].get_cmake_option()} --install-prefix {self.prefix[project]} -B {self.build_dir[project]} -S {source_dir} "
        command += " ".join(self.get_compiler(target, command_list) + get_cmake_option(cmake_option_list))
        common.run_command(command)

    def make(self, project: str, target: str) -> None:
        """构建项目

        Args:
            project (str): 目标项目
            target (str): 目标平台
        """

        assert project in self.build_dir
        common.run_command(f"{self.generator_list[target]} -C {self.build_dir[project]} -j{self.jobs}")

    def install(self, project: str, target: str) -> None:
        """安装项目

        Args:
            project (str): 目标项目
            target (str): 目标平台
        """

        assert project in self.build_dir
        common.run_command(f"{self.generator_list[target]} -C {self.build_dir[project]} install/strip -j{self.jobs}")

    def build_sysroot(self, target: str) -> None:
        """构建sysroot

        Args:
            target (str): 目标平台
        """
        # TODO:armv7m-none-eabi的sysroot生成

        prefix = self.prefix[f"{target}-runtimes"]
        arch = common.triplet_field(target).arch
        sysroot_dir = self.sysroot_dir[target]
        for src_dir in prefix.iterdir():
            match src_dir.name:
                case "bin":
                    # 复制dll
                    dst_dir = sysroot_dir / target / "lib"
                    for file in src_dir.iterdir():
                        if file.suffix == ".dll":
                            common.copy(file, dst_dir / file.name)
                case "lib":
                    dst_dir = sysroot_dir / target / "lib"
                    common.mkdir(dst_dir, False)
                    for item in src_dir.iterdir():
                        # 复制compiler-rt
                        if item.name == self.runtime_build_options[target].system_name.lower():
                            if target == self.build:
                                continue
                            rt_dir = self.compiler_rt_dir / gnu_to_llvm(target)
                            common.mkdir(rt_dir, False)
                            for file in item.iterdir():
                                name = file.name
                                pos = name.find(f"-{arch}")
                                if pos != -1:
                                    name = name[:pos] + name[pos + len(f"-{arch}") :]
                                common.copy(file, rt_dir / name)
                        else:
                            # 复制其他库
                            common.copy(item, dst_dir / item.name)
                case "include":
                    # 复制__config_site
                    dst_dir = sysroot_dir / target / "include"
                    common.copy(src_dir / "c++" / "v1" / "__config_site", dst_dir / "__config_site")
                    # 对于Windows目标，需要在sysroot/include下准备一份头文件
                    dst_dir = sysroot_dir / "include" / "c++"
                    common.copy(self.prefix["llvm"] / "include" / "c++", dst_dir, False)
                case "share":
                    dst_dir = sysroot_dir / target / "share"
                    common.mkdir(dst_dir, False)
                    for item in src_dir.iterdir():
                        common.copy(item, dst_dir / item.name)
                case _:
                    pass
        # 为mingw目标建立软链接
        match (target):
            case "x86_64-w64-mingw32":
                common.symlink(Path("x86_64-unknown-windows-gnu"), self.compiler_rt_dir / "x86_64-w64-windows-gnu")
            case "i686-w64-mingw32":
                common.symlink(Path("i686-unknown-windows-gnu"), self.compiler_rt_dir / "i686-w64-windows-gnu")
            case _:
                pass

    def copy_llvm_libs(self) -> None:
        """复制工具链所需库"""

        src_prefix = self.sysroot_dir[self.build] / self.host / "lib"
        dst_prefix = self.prefix["llvm"] / ("bin" if common.triplet_field(self.host).os == "w64" else "lib")
        native_dir = self.prefix_dir / f"{self.build}-clang{self.major_version}"
        native_bin_dir = native_dir / "bin"
        native_compiler_rt_dir = native_dir / "lib" / "clang" / self.major_version / "lib"
        # 复制libc++和libunwind运行库
        if self.family == runtime_family.llvm:
            for file in filter(
                lambda file: file.name.startswith(("libc++", "libunwind")) and not file.name.endswith((".a", ".json")), src_prefix.iterdir()
            ):
                common.copy(file, dst_prefix / file.name)
        # 复制公用libc++和libunwind头文件
        src_prefix = native_bin_dir.parent / "include"
        dst_prefix = self.prefix["llvm"] / "include"
        for item in filter(lambda item: "unwind" in item.name or item.name == "c++", src_prefix.iterdir()):
            common.copy(item, dst_prefix / item.name)

        if self.build != self.host:
            # 从build下的本地工具链复制compiler-rt
            # 其他库在sysroot中，无需复制
            src_prefix = native_compiler_rt_dir
            dst_prefix = self.compiler_rt_dir
            common.copy(src_prefix, dst_prefix, True)

    def package(self) -> None:
        """打包工具链"""

        self.compress()
        # 编译本地工具链时才需要打包sysroot
        if self.build == self.host:
            self.compress("sysroot")


class build_llvm_environment:

    @staticmethod
    def _build_linux(env: llvm_environment) -> None:
        """构建host为linux的llvm

        Args:
            env (llvm_environment): llvm构建环境
        """

        # 构建llvm
        env.config("llvm", env.host, env.llvm_build_options.basic_option, env.llvm_build_options.cmake_option)
        env.make("llvm", env.host)
        env.install("llvm", env.host)
        # 构建运行库
        for target, option in env.runtime_build_options.items():
            runtimes_name = f"{target}-runtimes"
            env.config(runtimes_name, target, option.basic_option, option.cmake_option)
            env.make(runtimes_name, target)
            env.install(runtimes_name, target)
            env.build_sysroot(target)
        # 打包
        env.package()

    @staticmethod
    def _build_mingw(env: llvm_environment) -> None:
        """构建host为mingw的llvm

        Args:
            env (llvm_environment): llvm构建环境
        """

        # 构建依赖库
        lib_basic_command = [*env.llvm_build_options.basic_option, "-lws2_32", "-lbcrypt"]
        for lib in lib_list:
            env.config(lib, env.host, lib_basic_command, env.lib_option)
            env.make(lib, env.host)
            env.install(lib, env.host)
        # 构建llvm
        env.config("llvm", env.host, env.llvm_build_options.basic_option, env.llvm_build_options.cmake_option)
        env.make("llvm", env.host)
        env.install("llvm", env.host)
        env.copy_llvm_libs()
        env.package()

    @staticmethod
    def build(env: llvm_environment) -> None:
        if env.llvm_build_options.system_name == "Linux":
            build_llvm_environment._build_linux(env)
        else:
            build_llvm_environment._build_mingw(env)
