from collections.abc import Callable
from pathlib import Path

from . import common

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports", "python-embed", "glibc", "newlib", "zstd")

# 带newlib的独立环境需禁用的特性列表
disable_hosted_option = (
    "--disable-threads",
    "--disable-libstdcxx-verbose",
    "--disable-shared",
    "--with-headers",
    "--disable-libsanitizer",
    "--disable-libssp",
    "--disable-libquadmath",
    "--disable-libgomp",
    "--with-newlib",
)
# 无newlib的独立环境需禁用的特性列表
disable_hosted_option_pure = (
    "--disable-threads",
    "--disable-hosted-libstdcxx",
    "--disable-libstdcxx-verbose",
    "--disable-shared",
    "--without-headers",
    "--disable-libvtv",
    "--disable-libsanitizer",
    "--disable-libssp",
    "--disable-libquadmath",
    "--disable-libgomp",
)

# 32位架构，其他32位架构需自行添加
arch_32_bit_list = ("arm", "armeb", "i486", "i686", "risc32", "risc32be")


def get_specific_environment(self: common.basic_environment, host: str | None = None, target: str | None = None) -> "gcc_environment":
    """在一个basic_environment的配置基础上获取指定配置的gcc环境

    Args:
        self (common.basic_environment): 基环境
        host (str | None, optional): 指定的host平台. 默认使用self中的配置.
        target (str | None, optional): 指定的target平台. 默认使用self中的配置.

    Returns:
        gcc_environment: 指定配置的gcc环境
    """

    return gcc_environment(
        self.build,
        host,
        target,
        self.home,
        self.jobs,
        self.prefix_dir,
        self.compress_level,
        self.long_distance_match,
        self.build_tmp,
        True,
    )


class gcc_environment(common.basic_environment):
    """gcc构建环境"""

    build: str  # build平台
    host: str  # host平台
    target: str  # target平台
    toolchain_type: "common.toolchain_type"  # 工具链类别
    cross_compiler: bool  # 是否是交叉编译器
    prefix: Path  # 工具链安装位置
    lib_prefix: Path  # 安装后库目录的前缀]
    share_dir: Path  # 安装后share目录
    gdbinit_path: Path  # 安装后.gdbinit文件所在路径
    lib_dir_list: dict[str, Path]  # 所有库所在目录
    tool_prefix: str  # 工具的前缀，如x86_64-w64-mingw32-
    python_config_path: Path  # python_config.sh所在路径
    host_32_bit: bool  # host平台是否是32位的
    target_32_bit: bool  # target平台是否是32位的
    rpath_option: str  # 设置rpath的链接选项
    rpath_dir: Path  # rpath所在目录
    freestanding: bool  # 是否为独立工具链
    host_field: common.triplet_field  # host平台各个域
    target_field: common.triplet_field  # target平台各个域

    def __init__(
        self,
        build: str,
        host: None | str,
        target: None | str,
        home: Path,
        jobs: int,
        prefix_dir: Path,
        compress_level: int,
        long_distance_match: int,
        build_tmp: Path,
        simple: bool = False,
    ) -> None:
        self.build = build
        self.host = host or build
        self.target = target or self.host
        # 鉴别工具链类别
        self.toolchain_type = common.toolchain_type.classify_toolchain(self.build, self.host, self.target)
        self.freestanding = self.toolchain_type.contain(common.toolchain_type.freestanding)
        self.cross_compiler = self.toolchain_type.contain(common.toolchain_type.cross | common.toolchain_type.canadian_cross)

        name_without_version = (f"{self.host}-host-{self.target}-target" if self.cross_compiler else f"{self.host}-native") + "-gcc"
        super().__init__(build, "16.0.0", name_without_version, home, jobs, prefix_dir, compress_level, long_distance_match, build_tmp)

        self.prefix = self.prefix_dir / self.name
        self.lib_prefix = self.prefix / self.target if not self.toolchain_type.contain(common.toolchain_type.canadian) else self.prefix
        self.share_dir = self.prefix / "share"
        self.gdbinit_path = self.share_dir / ".gdbinit"
        self.host_32_bit = self.host.startswith(arch_32_bit_list)
        self.target_32_bit = self.target.startswith(arch_32_bit_list)
        lib_name = f'lib{"32" if self.host_32_bit else "64"}'
        self.rpath_dir = self.prefix / lib_name
        lib_path = Path("'$ORIGIN'") / ".." / lib_name
        self.rpath_option = f"-Wl,-rpath={lib_path}"
        self.host_field = common.triplet_field(self.host, True)
        self.target_field = common.triplet_field(self.target, True)

        if simple:
            return

        common.mkdir(self.build_tmp, False)
        self.lib_dir_list = {}
        for lib in lib_list:
            lib_dir = self.home / lib
            match lib:
                # 支持使用厂商修改过的源代码
                case "glibc" | "linux" if self.target_field.vendor != "unknown":
                    vendor = self.target_field.vendor
                    custom_lib_dir = self.home / f"{lib}-{vendor}"
                    if common.check_lib_dir(lib, custom_lib_dir, False):
                        lib_dir = custom_lib_dir
                    else:
                        common.toolchains_print(
                            common.toolchains_warning(f'Can\'t find custom lib "{lib}" in "{custom_lib_dir}", fallback to use common lib.')
                        )
                        common.check_lib_dir(lib, lib_dir)
                case _:
                    common.check_lib_dir(lib, lib_dir)
            self.lib_dir_list[lib] = lib_dir
        self.lib_dir_list["gdbserver"] = self.lib_dir_list["binutils"]
        self.tool_prefix = f"{self.target}-" if self.cross_compiler else ""

        self.python_config_path = self.root_dir.parent / "script" / "python_config.sh"
        # 加载工具链
        if self.toolchain_type.contain(common.toolchain_type.cross | common.toolchain_type.canadian | common.toolchain_type.canadian_cross):
            get_specific_environment(self).register_in_env()
        if self.toolchain_type.contain(common.toolchain_type.canadian | common.toolchain_type.canadian_cross):
            get_specific_environment(self, target=self.host).register_in_env()
        if self.toolchain_type.contain(common.toolchain_type.canadian_cross):
            get_specific_environment(self, target=self.target).register_in_env()
        # 将自身注册到环境变量中
        self.register_in_env()

        # 从LD_LIBRARY_PATH中过滤掉空路径
        ld_library_path = [*filter(lambda path: path != "", common.get_environ_list("LD_LIBRARY_PATH", True))]
        common.set_environ_list("LD_LIBRARY_PATH", ld_library_path)

    def enter_build_dir(self, lib: str, remove_if_exist: bool = False) -> None:
        """进入构建目录

        Args:
            lib (str): 要构建的库
            remove_if_exist(bool): 是否删除已经存在的目录
        """

        assert lib in self.lib_dir_list
        need_make_build_dir = True  # 是否需要建立build目录
        match lib:
            case "python-embed" | "linux":
                need_make_build_dir = False  # 跳过python-embed和linux，python-embed仅需要生成静态库，linux有独立的编译方式
                build_dir = self.lib_dir_list[lib]
            case "glibc" | "mingw" | "newlib":
                build_dir = self.build_tmp / f"{self.target}-{lib}"
            case "expat" | "gmp" | "mpfr" | "zstd":
                build_dir = self.build_tmp / f"{self.host}-{lib}"
            case _:
                build_dir = self.build_tmp / f"{self.host}-host-{self.target}-target-{lib}"

        if need_make_build_dir:
            common.mkdir(build_dir, remove_if_exist)

        common.chdir(build_dir)
        # 添加构建gdb所需的环境变量
        if lib == "binutils":
            common.add_environ("ORIGIN", "$$ORIGIN")
            common.add_environ("PYTHON_EMBED_PACKAGE", self.lib_dir_list["python-embed"])  # mingw下编译带python支持的gdb需要

    def configure(self, lib: str, *option: str) -> None:
        """自动对库进行配置

        Args:
            lib (str): 要构建的库
            option (tuple[str, ...]): 配置选项
        """

        options = " ".join(("", *option))
        configure_prefix = self.lib_dir_list[lib] if lib != "expat" else self.lib_dir_list[lib] / "expat"
        common.run_command(f"{configure_prefix / 'configure'} {common.command_quiet.get_option()} {options}")

    def make(self, *target: str, ignore_error: bool = False) -> None:
        """自动对库进行编译

        Args:
            target (tuple[str, ...]): 要编译的目标
        """

        targets = " ".join(("", *target))
        common.run_command(f"make {common.command_quiet.get_option()} {targets} -j {self.jobs}", ignore_error)

    def install(self, *target: str, ignore_error: bool = False) -> None:
        """自动对库进行安装

        Args:
            target (tuple[str, ...]): 要安装的目标
        """

        if target != ():
            targets = " ".join(("", *target))
        else:
            targets = "install-strip"
        common.run_command(f"make {common.command_quiet.get_option()} {targets} -j {self.jobs}", ignore_error)

    def copy_gdbinit(self) -> None:
        """复制.gdbinit文件"""

        gdbinit_src_path = self.root_dir.parent / "script" / ".gdbinit"
        common.copy(gdbinit_src_path, self.gdbinit_path)

    def build_libpython(self) -> None:
        """创建libpython.a"""

        lib_dir = self.lib_dir_list["python-embed"]
        lib_path = lib_dir / "libpython.a"
        def_path = lib_dir / "libpython.def"
        if not lib_path.exists():
            dll_list = list(filter(lambda dll: dll.name.startswith("python") and dll.name.endswith(".dll"), lib_dir.iterdir()))
            assert dll_list != [], common.toolchains_error(f'Cannot find python*.dll in "{lib_dir}" directory.')
            assert len(dll_list) == 1, common.toolchains_error(f'Find too many python*.dll in "{lib_dir}" directory.')
            dll_path = lib_dir / dll_list[0]
            # 工具链最后运行在宿主平台上，故而应该使用宿主平台的工具链从.lib文件制作.a文件
            common.run_command(f"{self.host}-pexports {dll_path} > {def_path}")
            common.run_command(f"{self.host}-dlltool -D {dll_path} -d {def_path} -l {lib_path}")

    def copy_python_embed_package(self) -> None:
        """复制python embed package到安装目录"""

        for file in filter(lambda x: x.name.startswith("python"), self.lib_dir_list["python-embed"].iterdir()):
            common.copy(
                file,
                self.bin_dir / file.name,
            )

    def package(self, need_gdbinit: bool = True, need_python_embed_package: bool = False) -> None:
        """打包工具链

        Args:
            need_gdbinit (bool, optional): 是否需要打包.gdbinit文件. 默认需要.
            need_python_embed_package (bool, optional): 是否需要打包python embed package. 默认不需要.
        """

        if self.toolchain_type.contain(common.toolchain_type.native):
            # 本地工具链需要添加cc以代替系统提供的cc
            common.symlink(Path("gcc"), self.bin_dir / "cc")
        if need_gdbinit:
            self.copy_gdbinit()
        if need_python_embed_package:
            self.copy_python_embed_package()
        self.compress()

    def remove_unused_glibc_file(self) -> None:
        """移除不需要的glibc文件"""

        for dir in (
            "etc",
            "libexec",
            "sbin",
            "share",
            "var",
            "lib/gconv",
            "lib/audit",
        ):
            common.remove_if_exists(self.lib_prefix / dir)

    def strip_glibc_file(self) -> None:
        """剥离调试符号"""

        strip = f"{self.tool_prefix}strip"
        common.run_command(f"{strip} {self.lib_prefix / 'lib' / '*.so.*'}", True)

    def change_glibc_ldscript(self, arch: str | None = None) -> None:
        """替换带有绝对路径的链接器脚本

        Args:
            arch (str | None, optional): glibc链接器脚本的arch字段，若为None则从target中推导. 默认为 None.
                                  手动设置arch可以用于需要额外字段来区分链接器脚本的情况
        """

        arch = arch or self.target_field.arch
        dst_dir = self.lib_prefix / "lib"
        for file in filter(lambda file: file.name.startswith(f"{arch}-lib"), self.script_dir.iterdir()):
            if file.suffix == ".py":
                with common.dynamic_import_module(file) as module:
                    generate_ldscript: Callable[[Path], None] = common.dynamic_import_function("main", module)
                    generate_ldscript(dst_dir)
            else:
                common.copy(file, dst_dir / file.name[len(f"{arch}-") :])

    def adjust_glibc(self, arch: str | None = None) -> None:
        """调整glibc
        Args:
            arch (str | None, optional): glibc链接器脚本的arch字段，若为None则自动推导. 默认为 None.
        """

        self.remove_unused_glibc_file()
        self.strip_glibc_file()
        self.change_glibc_ldscript(arch)
        symlink_path = self.lib_prefix / "lib" / "libmvec_nonshared.a"
        if not symlink_path.exists():
            common.symlink_if_exist(Path("libmvec.a"), symlink_path)

    def solve_libgcc_limits(self) -> None:
        """解决libgcc的limits.h中提供错误MB_LEN_MAX的问题"""

        libgcc_prefix = self.prefix / "lib" / "gcc" / self.target
        include_path = next(libgcc_prefix.iterdir()) / "include" / "limits.h"
        with include_path.open("a") as file:
            file.write("#undef MB_LEN_MAX\n" "#define MB_LEN_MAX 16\n")

    def copy_from_other_toolchain(self, need_gdbserver: bool) -> bool:
        """从交叉工具链或本地工具链中复制libc、libstdc++、libgcc、linux头文件、gdbserver等到本工具链中

        Args:
            need_gdbserver (bool): 是否需要复制gdbserver

        Returns:
            bool: gdbserver是否成功复制
        """

        target_dir = self.lib_prefix
        # 复制libc、libstdc++、linux头文件等到本工具链中
        toolchain = get_specific_environment(self, target=self.target)
        if toolchain.toolchain_type.contain(common.toolchain_type.native):
            # 复制include和lib64
            for dir in ("include", "lib64"):
                common.copy(toolchain.prefix / dir, target_dir / dir)
            # 复制glibc链接库
            common.copy(toolchain.lib_prefix / "lib", target_dir / "lib")
            # 复制glibc头和linux头
            for item in (toolchain.lib_prefix / "include").iterdir():
                common.copy(item, target_dir / "include" / item.name)
        else:
            for dir in filter(lambda x: x.name != "bin", toolchain.lib_prefix.iterdir()):
                common.copy(dir, target_dir / dir.name)

        # 复制libgcc到本工具链中
        common.copy(toolchain.prefix / "lib" / "gcc", self.prefix / "lib" / "gcc")

        # 复制gdbserver
        if need_gdbserver:
            gdbserver = "gdbserver" if self.target_field.os == "linux" else "gdbserver.exe"
            return bool(common.copy_if_exist(toolchain.bin_dir / gdbserver, self.bin_dir / gdbserver))
        else:
            return False


def get_mingw_gdb_lib_prefix_list(env: gcc_environment) -> dict[str, Path]:
    """获取mingw平台下gdb所需包的安装路径

    Args:
        env (gcc_environment): gcc环境

    Returns:
        dict[str,Path]: {包名:安装路径}
    """

    return {lib: env.build_tmp / f"{env.host}-{lib}-install" for lib in ("gmp", "expat", "mpfr")}


def get_mingw_gcc_lib_prefix_list(env: gcc_environment) -> dict[str, Path]:
    """获取mingw平台下gcc所需包的安装路径

    Args:
        env (gcc_environment): gcc环境

    Returns:
        dict[str,Path]: {包名:安装路径}
    """

    return {lib: env.build_tmp / f"{env.host}-{lib}-install" for lib in ("zstd",)}


def build_mingw_gdb_requirements(env: gcc_environment) -> None:
    """编译安装gdb依赖库

    Args:
        env (gcc_environment): gcc环境
    """

    lib_prefix_list = get_mingw_gdb_lib_prefix_list(env)
    for lib, prefix in lib_prefix_list.items():
        with common.cached_lib_builder(prefix, env.host) as is_built:
            if is_built:
                continue

            assert not common.binfmt.is_enabled("DOSWin"), common.toolchains_error(
                "Cannot build gdb dependencies because wine-binfmt is enabled.\n"
                'Execute "toolchains-util wine-binfmt disable" to disable wine-binfmt.'
            )
            env.enter_build_dir(lib)
            env.configure(
                lib,
                f"--host={env.host} --disable-shared --enable-static",
                f"--prefix={prefix}",
                f"--with-gmp={lib_prefix_list['gmp']}" if lib == "mpfr" else "",
                'CFLAGS="-O3 -std=c11"',
                'CXXFLAGS="-O3"',
            )
            env.make()
            env.install()


def build_mingw_gcc_requirements(env: gcc_environment) -> None:
    """编译安装gcc依赖库

    Args:
        env (gcc_environment): gcc环境
    """

    lib_prefix_list = get_mingw_gcc_lib_prefix_list(env)
    for lib, prefix in lib_prefix_list.items():
        with common.cached_lib_builder(prefix, env.host) as is_built:
            if is_built:
                continue

            env.enter_build_dir(lib)
            if lib == "zstd":
                cmake_option_list = [
                    f"-S {env.lib_dir_list['zstd'] / 'build' / 'cmake'}",
                    "-B .",
                    "-G Ninja",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_SYSTEM_NAME=Windows",
                    "-DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc",
                    "-DZSTD_BUILD_STATIC=ON",
                    "-DZSTD_BUILD_SHARED=OFF",
                    "-DZSTD_BUILD_PROGRAMS=OFF",
                    f"-DCMAKE_INSTALL_PREFIX={prefix}",
                ]
                common.run_command(f"cmake {' '.join(cmake_option_list)}")
                common.run_command(f"ninja -j {env.jobs}")
                common.run_command(f"ninja install/strip -j {env.jobs}")


def get_mingw_gdb_lib_options(env: gcc_environment) -> list[str]:
    """获取mingw平台下gdb所需包配置选项

    Args:
        env (gcc_environment): gcc环境
    """

    lib_prefix_list = get_mingw_gdb_lib_prefix_list(env)
    prefix_selector: Callable[[str], str] = lambda lib: f"--with-{lib}=" if lib in ("gmp", "mpfr") else f"--with-lib{lib}-prefix="
    return [prefix_selector(lib) + f"{lib_prefix_list[lib]}" for lib in lib_prefix_list.keys()]


def get_mingw_gcc_lib_options(env: gcc_environment) -> list[str]:
    """获取mingw平台下gcc所需包配置选项

    Args:
        env (gcc_environment): gcc环境
    """

    lib_prefix_list = get_mingw_gcc_lib_prefix_list(env)
    return [f"--with-{lib}={prefix}" for lib, prefix in lib_prefix_list.items()]


def copy_pretty_printer(env: gcc_environment) -> None:
    """从x86_64-linux-gnu本地工具链中复制pretty-printer到不带newlib的独立工具链"""

    native_gcc = get_specific_environment(env)
    for src_dir in native_gcc.share_dir.iterdir():
        if src_dir.name.startswith("gcc") and src_dir.is_dir() and not (dst_dir := env.share_dir / src_dir.name).is_dir():
            common.copy(src_dir, dst_dir)
            return


class build_gcc_environment:
    """gcc工具链构建环境"""

    env: gcc_environment  # gcc构建环境
    host_os: str  # gcc环境的host操作系统
    target_os: str  # gcc环境的target操作系统
    target_arch: str  # gcc环境的target架构
    basic_option: list[str]  # 基本选项
    libc_option: list[str]  # libc相关选项
    gcc_option: list[str]  # gcc相关选项
    gdb_option: list[str]  # gdb相关选项
    linux_option: list[str]  # linux相关选项
    gdbserver_option: list[str]  # gdbserver相关选项
    full_build: bool  # 是否进行完整自举流程
    glibc_phony_stubs_path: Path  # glibc占位文件所在路径
    adjust_glibc_arch: str  # 调整glibc链接器脚本时使用的架构名
    need_gdb: bool  # 是否需要编译gdb
    need_gdbserver: bool  # 是否需要编译gdbserver
    need_newlib: bool  # 是否需要编译newlib，仅对独立工具链有效
    native_or_canadian = common.toolchain_type.native | common.toolchain_type.canadian  # host == target

    def __init__(
        self,
        build: str,
        host: str,
        target: str,
        gdb: bool,
        gdbserver: bool,
        newlib: bool,
        home: Path,
        jobs: int,
        prefix_dir: Path,
        nls: bool,
        compress_level: int,
        long_distance_match: int,
        build_tmp: Path,
    ) -> None:
        """gcc交叉工具链对象

        Args:
            build (str): 构建平台
            host (str): 宿主平台
            target (str): 目标平台
            gdb (bool): 是否启用gdb
            gdbserver (bool): 是否启用gdbserver
            newlib (bool): 是否启用newlib, 仅对独立工具链有效
            home (Path): 源代码树搜索主目录
            jobs (int): 并发构建数
            prefix_dir (Path): 安装根目录
            nls (bool): 是否启用nls
            compress_level (int): zstd压缩等级
            long_distance_match (int): 长距离匹配窗口大小
            build_tmp (Path): 构建工具链时存放临时文件的路径
        """

        self.env = gcc_environment(build, host, target, home, jobs, prefix_dir, compress_level, long_distance_match, build_tmp)
        self.host_os = self.env.host_field.os
        self.target_os = self.env.target_field.os
        self.target_arch = self.env.target_field.arch
        self.basic_option = [
            "--disable-werror",
            " --enable-nls" if nls else "--disable-nls",
            f"--build={self.env.build}",
            f"--target={self.env.target}",
            f"--prefix={self.env.prefix}",
            f"--host={self.env.host}",
            "CFLAGS=-O3",
            "CXXFLAGS=-O3",
        ]
        self.need_gdb, self.need_gdbserver, self.need_newlib = gdb, gdbserver, newlib
        assert not self.env.freestanding or not self.need_gdbserver, common.toolchains_error(
            "Cannot build gdbserver for freestanding platform.\n" "You should use other server implementing the gdb protocol like OpenOCD."
        )

        libc_option_list: dict[str, list[str]] = {
            "linux": [f"--prefix={self.env.lib_prefix}", f"--host={self.env.target}", f"--build={self.env.build}", "--disable-werror"],
            "w64": [
                f"--host={self.env.target}",
                f"--prefix={self.env.lib_prefix}",
                "--with-default-msvcrt=ucrt",
                "--disable-werror",
            ],
            # newlib会自动设置安装路径的子目录
            "unknown": [f"--prefix={self.env.prefix}", f"--target={self.env.target}", f"--build={self.env.build}", "--disable-werror"],
        }
        self.libc_option = libc_option_list[self.target_os]

        gcc_target_option_list: dict[str, list[str]] = {
            "linux": ["--disable-bootstrap"],
            "w64": ["--disable-sjlj-exceptions", "--enable-threads=win32"],
            "unknown": [*disable_hosted_option] if self.need_newlib else [*disable_hosted_option_pure],
        }
        gcc_host_option_list: dict[str, list[str]] = {"linux": [], "w64": get_mingw_gcc_lib_options(self.env), "unknown": []}
        self.gcc_option = [
            *gcc_target_option_list[self.target_os],
            *gcc_host_option_list[self.host_os],
            "--enable-languages=c,c++",
            "--disable-multilib",
        ]

        w64_gdbsupport_option = 'CXXFLAGS="-O3 -D_WIN32_WINNT=0x0600"'
        gdb_option_list: dict[str, list[str]] = {
            "linux": [f'LDFLAGS="{self.env.rpath_option}"', "--with-python=/usr/bin/python3"],
            "w64": [
                f"--with-python={self.env.python_config_path}",
                w64_gdbsupport_option,
                "--with-expat",
                *get_mingw_gdb_lib_options(self.env),
            ],
        }
        enable_gdbserver_when_build_gdb = gdbserver and self.env.toolchain_type.contain(self.native_or_canadian)
        gdbserver_option = "--enable-gdbserver" if enable_gdbserver_when_build_gdb else "--disable-gdbserver"
        self.gdb_option = (
            [
                *gdb_option_list[self.host_os],
                f"--with-system-gdbinit={self.env.gdbinit_path}",
                gdbserver_option,
                "--enable-gdb",
                "--disable-unit-tests",
            ]
            if gdb
            else [gdbserver_option, "--disable-gdb"]
        )
        # 创建libpython.a
        if gdb and self.host_os == "w64":
            self.env.build_libpython()

        linux_arch_list: dict[str, str] = {
            "i686": "x86",
            "x86_64": "x86",
            "arm": "arm",
            "aarch64": "arm64",
            "loongarch64": "loongarch",
            "riscv64": "riscv",
            "mips64el": "mips",
        }
        self.linux_option = [f"ARCH={linux_arch_list[self.target_arch]}", f"INSTALL_HDR_PATH={self.env.lib_prefix}", "headers_install"]

        self.gdbserver_option = ["--disable-gdb", f"--host={self.env.target}", "--enable-gdbserver", "--disable-binutils"]
        if self.target_os == "w64":
            self.gdbserver_option.append(w64_gdbsupport_option)

        # 本地工具链和交叉工具链需要完整编译
        self.full_build = self.env.toolchain_type.contain(common.toolchain_type.native | common.toolchain_type.cross)
        # 编译不完整libgcc时所需的stubs.h所在路径
        self.glibc_phony_stubs_path = self.env.lib_prefix / "include" / "gnu" / "stubs.h"
        # 由相关函数自动推动架构名
        self.adjust_glibc_arch = ""

    def after_build_gcc(self, skip_gdbserver: bool = False) -> None:
        """在编译完gcc后完成收尾工作

        Args:
            skip_gdbserver (bool, optional): 跳过gdbserver构建. 默认为False.
        """

        self.need_gdbserver = self.need_gdbserver and not skip_gdbserver
        # 从完整工具链复制文件
        if not self.full_build:
            copy_success = self.env.copy_from_other_toolchain(self.need_gdbserver)
            self.need_gdbserver = self.need_gdbserver and not copy_success
        if self.need_gdb:
            copy_pretty_printer(self.env)

        # 编译gdbserver
        if self.need_gdbserver:
            self.env.solve_libgcc_limits()
            self.env.enter_build_dir("gdbserver", True)
            self.env.configure("gdbserver", *self.basic_option, *self.gdbserver_option)
            self.env.make()
            self.env.install("install-strip-gdbserver")

        # 复制gdb所需运行库
        if self.need_gdb and not self.env.toolchain_type.contain(self.native_or_canadian):
            gcc = get_specific_environment(self.env, target=self.env.host)
            if self.host_os == "linux":
                for dll in ("libstdc++.so.6", "libgcc_s.so.1"):
                    common.copy(gcc.rpath_dir / dll, self.env.rpath_dir / dll, follow_symlinks=True)
            else:
                for dll in ("libstdc++-6.dll", "libgcc_s_seh-1.dll"):
                    common.copy(gcc.lib_prefix / "lib" / dll, self.env.bin_dir / dll)

        # 打包工具链
        self.env.package(self.need_gdb, self.need_gdb and self.host_os == "w64")

    @staticmethod
    def native_build_linux(build_env: "build_gcc_environment") -> None:
        """编译linux本地工具链

        Args:
            build_env (build_environment): gcc构建环境
        """

        env = build_env.env
        # 编译gcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
        env.make()
        env.install()

        # 安装Linux头文件
        env.enter_build_dir("linux")
        env.make(*build_env.linux_option)

        # 编译安装glibc
        env.enter_build_dir("glibc")
        env.configure("glibc", *build_env.libc_option)
        env.make()
        env.install("install")
        env.adjust_glibc(build_env.adjust_glibc_arch)

        # 编译binutils，如果启用gdb和gdbserver则一并编译
        env.enter_build_dir("binutils")
        env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
        env.make()
        env.install()
        # 完成后续工作
        build_env.after_build_gcc(True)

    @staticmethod
    def make_with_libbacktrace_patch(env: gcc_environment, target: str | None = None) -> None:
        """在构建时修正libbacktrace构建流程

        gcc会删除构建完成的libbacktrace，然后只将stat.o打包为libbacktrace.a，进而导致链接错误
        该函数首先尝试make，构建失败后重新编译libbacktrace，然后继续make流程

        Args:
            env (gcc_environment): gcc构建环境
            target (str | None, optional): 传递给env.make函数的目标，为None表示调用env.make(). 默认为None.
        """

        make: Callable[[], None] = lambda: env.make(*([target] if target is not None else []))
        try:
            make()
        except:
            # 由于实际上没有出错，因此将计数器减1
            common.status_counter.sub_error()
            with common.chdir_guard(Path("libbacktrace")):
                env.make("clean")
                env.make()
            make()

    @staticmethod
    def full_build_linux(build_env: "build_gcc_environment") -> None:
        """完整自举target为linux的gcc

        Args:
            build_env (build_environment): gcc构建环境
        """

        env = build_env.env
        # 编译binutils，如果启用gdb则一并编译
        env.enter_build_dir(lib="binutils")
        env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
        env.make()
        env.install()

        # 编译gcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option, "--disable-shared", "--disable-gcov")
        build_gcc_environment.make_with_libbacktrace_patch(env, "all-gcc")
        env.install("install-strip-gcc")

        # 安装Linux头文件
        env.enter_build_dir("linux")
        env.make(*build_env.linux_option)

        # 安装glibc头文件
        env.enter_build_dir("glibc")
        env.configure("glibc", *build_env.libc_option, "libc_cv_forced_unwind=yes")
        env.make("install-headers")
        # 为了跨平台，不能使用mknod
        with build_env.glibc_phony_stubs_path.open("w"):
            pass

        # 编译安装libgcc
        env.enter_build_dir("gcc")
        env.make("all-target-libgcc")
        env.install("install-target-libgcc")

        # 编译安装glibc
        env.enter_build_dir("glibc")
        env.configure("glibc", *build_env.libc_option)
        env.make()
        env.install("install")
        env.adjust_glibc(build_env.adjust_glibc_arch)

        # 编译完整gcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
        build_gcc_environment.make_with_libbacktrace_patch(env)
        env.install()

        # 完成后续工作
        build_env.after_build_gcc()

    def build_pexports(self) -> None:
        """ # 编译pexports
        self.env.enter_build_dir("pexports")
        self.env.configure(
            "pexports",
            f"--prefix={self.env.prefix} --host={self.env.host}",
            "CFLAGS=-O3",
            "CXXFLAGS=-O3",
        )
        self.env.make()
        self.env.install()
        # 为交叉工具链添加target前缀
        if not self.env.toolchain_type.contain(self.native_or_canadian):
            pexports = "pexports.exe" if self.host_os == "w64" else "pexports"
            common.rename(self.env.bin_dir / pexports, self.env.bin_dir / f"{self.env.target}-{pexports}") """

        # TODO: 添加meson支持
        common.toolchains_warning("Pexports is now using meson build system. It's not supported yet.")

    @staticmethod
    def full_build_mingw(build_env: "build_gcc_environment") -> None:
        """完整自举target为mingw的gcc

        Args:
            build_env (build_environment): gcc构建环境
        """

        env = build_env.env
        # 编译binutils，如果启用gdb则一并编译
        env.enter_build_dir("binutils")
        env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
        env.make()
        env.install()

        # 编译安装mingw-w64头文件
        env.enter_build_dir("mingw")
        env.configure("mingw", *build_env.libc_option, "--without-crt")
        env.make()
        env.install()

        # 编译gcc和libgcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option, "--disable-shared")
        build_gcc_environment.make_with_libbacktrace_patch(env, "all-gcc all-target-libgcc")
        env.install("install-strip-gcc install-target-libgcc")

        # 编译完整mingw-w64
        env.enter_build_dir("mingw")
        env.configure("mingw", *build_env.libc_option)
        env.make()
        env.install()

        # 编译完整的gcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
        build_gcc_environment.make_with_libbacktrace_patch(env)
        env.install()

        build_env.build_pexports()
        # 完成后续工作
        build_env.after_build_gcc()

    @staticmethod
    def full_build_freestanding(build_env: "build_gcc_environment") -> None:
        """完整自举target为独立平台的gcc

        Args:
            build_env (build_environment): gcc构建环境
        """

        env = build_env.env
        # 编译binutils，如果启用gdb则一并编译
        env.enter_build_dir("binutils")
        env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
        env.make()
        env.install()

        if build_env.need_newlib:
            # 编译安装gcc
            env.enter_build_dir("gcc")
            env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
            env.make("all-gcc")
            env.install("install-strip-gcc")

            # 编译安装newlib
            env.enter_build_dir("newlib")
            env.configure("newlib", *build_env.libc_option)
            env.make()
            env.install()

            # 编译安装完整gcc
            env.enter_build_dir("gcc")
            env.make()
            env.install()
        else:
            # 编译安装完整gcc
            env.enter_build_dir("gcc")
            env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
            env.make()
            env.install("install-strip")

        # 完成后续工作
        build_env.after_build_gcc()

    @staticmethod
    def partial_build(build_env: "build_gcc_environment") -> None:
        """编译gcc而无需自举

        Args:
            build_env (build_environment): gcc构建环境
        """

        env = build_env.env
        # 编译binutils，如果启用gdb则一并编译
        env.enter_build_dir("binutils")
        env.configure("binutils", *build_env.basic_option, *build_env.gdb_option)
        env.make()
        env.install()

        # 编译安装gcc
        env.enter_build_dir("gcc")
        env.configure("gcc", *build_env.basic_option, *build_env.gcc_option)
        build_gcc_environment.make_with_libbacktrace_patch(env, "all-gcc")
        env.install("install-strip-gcc")

        # 有需要则编译安装pexports
        if build_env.target_os == "w64":
            build_env.build_pexports()

        # 完成后续工作
        build_env.after_build_gcc()

    def build(self) -> None:
        """构建gcc工具链"""

        # 编译gcc依赖库
        if self.host_os == "w64":
            build_mingw_gcc_requirements(self.env)
        # 编译gdb依赖库
        if self.need_gdb and self.host_os == "w64":
            build_mingw_gdb_requirements(self.env)
        if self.env.toolchain_type.contain(common.toolchain_type.native):
            self.native_build_linux(self)
        elif self.full_build:
            assert self.target_os in ("linux", "w64", "unknown"), common.toolchains_error(
                f"Unknown os: {self.target_os}.", common.message_type.toolchain_internal
            )
            match (self.target_os):
                case "linux":
                    self.full_build_linux(self)
                case "w64":
                    self.full_build_mingw(self)
                case "unknown":
                    self.full_build_freestanding(self)
        else:
            self.partial_build(self)


assert __name__ != "__main__", "Import this file instead of running it directly."
