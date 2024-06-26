#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import psutil
import shutil
import sys
from math import floor

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports", "iconv", "python-embed", "glibc")
dll_target_list = (
    "install-target-libgcc",
    "install-target-libstdc++-v3",
    "install-target-libatomic",
    "install-target-libquadmath",
    "install-target-libgomp",
)
dll_name_list_linux = (
    "libgcc_s.so.1",
    "libstdc++.so",
    "libatomic.so",
    "libquadmath.so",
    "libgomp.so",
)
dll_name_list_windows = (
    "libgcc_s_seh-1.dll",
    "libgcc_s_dw2-1.dll",
    "libstdc++-6.dll",
    "libatomic-1.dll",
    "libquadmath-0.dll",
)

disable_hosted_option = (
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


def run_command(command: str) -> None:
    print(command)
    assert os.system(command) == 0, f'Command "{command}" failed.'


class environment:
    major_version: str  # < GCC的主版本号
    build: str  # < build平台
    host: str  # < host平台
    target: str  # < target平台
    toolchain_type: str  # < 工具链类别
    cross_compiler: bool  # < 是否是交叉编译器
    name_without_version: str  # < 不带版本号的工具链名
    name: str  # < 工具链名
    home_dir: str  # < 源代码所在的目录，默认为$HOME
    prefix: str  # < 工具链安装位置
    num_cores: int  # < 编译所用线程数
    current_dir: str  # < toolchains项目所在目录
    lib_prefix: str  # < 安装后库目录的前缀
    bin_dir: str  # < 安装后可执行文件所在目录
    symlink_list: list[str]  # < 构建过程中创建的软链接表
    share_dir: str  # < 安装后.share目录
    gdbinit_path: str  # < 安装后.gdbinit文件所在路径
    lib_dir_list: dict[str, str]  # < 所有库所在目录
    tool_prefix: str  # < 工具的前缀，如x86_64-w64-mingw32-
    dll_name_list: tuple  # < 该平台上需要保留调试符号的dll列表
    python_config_path: str  # < python_config.sh所在路径
    host_32_bit: bool  # < 宿主环境是否是32位的
    rpath_option: str  # < 设置rpath的链接选项
    rpath_dir: str  # < rpath所在目录

    def __init__(self, build: str = "x86_64-linux-gnu", host: str = "", target: str = "") -> None:
        self.major_version = "15"
        self.build = build
        self.host = host if host != "" else build
        self.target = target if target != "" else self.host
        # 鉴别工具链类别
        if self.build == self.host == self.target:
            self.toolchain_type = "native"
        elif self.build == self.host != self.target:
            self.toolchain_type = "cross"
        elif self.build != self.host == self.target:
            self.toolchain_type = "canadian"
        else:
            self.toolchain_type = "canadian cross"
        self.cross_compiler = self.host != self.target
        self.name_without_version = (f"{self.host}-host-{self.target}-target" if self.cross_compiler else f"{self.host}-native") + "-gcc"
        self.name = self.name_without_version + self.major_version
        self.home_dir = ""
        for option in sys.argv:
            if option.startswith("--home="):
                self.home_dir = option[7:]
                break
        if self.home_dir == "":
            self.home_dir = os.environ["HOME"]
        self.prefix = os.path.join(self.home_dir, self.name)
        self.num_cores = floor(psutil.cpu_count() * 1.5)
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.lib_prefix = os.path.join(self.prefix, self.target) if self.cross_compiler else self.prefix
        self.bin_dir = os.path.join(self.prefix, "bin")
        self.symlink_list = []
        self.share_dir = os.path.join(self.prefix, "share")
        self.gdbinit_path = os.path.join(self.share_dir, ".gdbinit")
        self.lib_dir_list = {}
        for lib in lib_list:
            lib_dir = os.path.join(self.home_dir, lib)
            assert os.path.exists(lib_dir), f'Cannot find lib "{lib}" in directory "{lib_dir}"'
            self.lib_dir_list[lib] = lib_dir
        self.tool_prefix = f"{self.target}-" if self.cross_compiler else ""
        # NOTE：添加平台后需要在此处注册dll_name_list
        if self.target.endswith("linux-gnu"):
            self.dll_name_list = dll_name_list_linux
        elif self.target.endswith("w64-mingw32"):
            self.dll_name_list = dll_name_list_windows
        self.python_config_path = os.path.join(self.current_dir, "python_config.sh")
        self.host_32_bit = host.startswith(arch_32_bit_list)
        lib_name = f'lib{"32" if self.host_32_bit else "64"}'
        self.rpath_dir = os.path.join(self.prefix, lib_name)
        lib_name = os.path.join("'$ORIGIN'", "..", lib_name)
        self.rpath_option = f'"-Wl,-rpath={lib_name}"'
        # 加载工具链
        if self.toolchain_type in ("cross", "canadian", "canadian cross"):
            environment().register_in_env()
        if self.toolchain_type in ("canadian", "canadian cross"):
            environment(target=self.host).register_in_env()
        if self.toolchain_type == "canadian cross":
            environment(target=self.target).register_in_env()
        # 将自身注册到环境变量中
        self.register_in_env()

    def update(self) -> None:
        """更新源代码"""
        for lib in ("expat", "gcc", "binutils", "linux", "mingw", "pexports", "glibc"):
            path = os.path.join(self.home_dir, lib)
            os.chdir(path)
            run_command("git pull")

    def enter_build_dir(self, lib: str, remove_files: bool = True) -> None:
        """进入构建目录

        Args:
            lib (str): 要构建的库
        """
        assert lib in lib_list
        build_dir = self.lib_dir_list[lib]
        if lib not in ("python-embed", "linux"):
            build_dir = os.path.join(self.home_dir, lib, "build" if lib != "expat" else "expat/build")
            if os.path.isdir(build_dir) and remove_files:
                shutil.rmtree(build_dir)
            if not os.path.isdir(build_dir):
                os.mkdir(build_dir)
        os.chdir(build_dir)
        # 添加构建gdb所需的环境变量
        if lib == "binutils":
            os.environ["ORIGIN"] = "$$ORIGIN"

    def configure(self, *option: str) -> None:
        """自动对库进行配置

        Args:
            option (tuple[str, ...]): 配置选项
        """
        options = " ".join(("", *option))
        run_command(f"../configure {options}")

    def make(self, *target: str) -> None:
        """自动对库进行编译

        Args:
            target (tuple[str, ...]): 要编译的目标
        """
        targets = " ".join(("", *target))
        run_command(f"make {targets} -j {self.num_cores}")

    def install(self, *target: str) -> None:
        """自动对库进行安装

        Args:
            target (tuple[str, ...]): 要安装的目标
        """
        if target != ():
            targets = " ".join(("", *target))
        elif os.getcwd() == os.path.join(self.lib_dir_list["gcc"], "build"):
            run_command(f"make install-strip -j {self.num_cores}")
            targets = " ".join(dll_target_list)
        else:
            targets = "install-strip"
        run_command(f"make {targets} -j {self.num_cores}")

    def strip_debug_symbol(self) -> None:
        """剥离动态库的调试符号到独立的符号文件"""
        for dir in filter(lambda dir: dir.startswith("lib"), os.listdir(self.lib_prefix)):
            lib_dir = os.path.join(self.lib_prefix, dir)
            for file in filter(lambda file: file in self.dll_name_list, os.listdir(lib_dir)):
                dll_path = os.path.join(lib_dir, file)
                symbol_path = dll_path + ".debug"
                run_command(f"{self.tool_prefix}objcopy --only-keep-debug {dll_path} {symbol_path}")
                run_command(f"{self.tool_prefix}strip {dll_path}")
                run_command(f"{self.tool_prefix}objcopy --add-gnu-debuglink={symbol_path} {dll_path}")

    def register_in_env(self) -> None:
        """注册安装路径到环境变量"""
        os.environ["PATH"] = f"{self.bin_dir}:{os.environ['PATH']}"

    def register_in_bashrc(self) -> None:
        """注册安装路径到用户配置文件"""
        with open(os.path.join(self.home_dir, ".bashrc"), "a") as bashrc_file:
            bashrc_file.write(f"export PATH={self.bin_dir}:$PATH\n")

    def copy_gdbinit(self) -> None:
        """复制.gdbinit文件"""
        gdbinit_src_path = os.path.join(self.current_dir, ".gdbinit")
        shutil.copyfile(gdbinit_src_path, self.gdbinit_path)

    def copy_readme(self) -> None:
        """复制工具链说明文件"""
        readme_path = os.path.join(self.current_dir, "..", "readme", f"{self.name_without_version}.md")
        target_path = os.path.join(self.prefix, "README.md")
        shutil.copyfile(readme_path, target_path)

    def build_libpython(self) -> None:
        """创建libpython.a"""
        lib_dir = self.lib_dir_list["python-embed"]
        lib_path = os.path.join(lib_dir, "libpython.a")
        def_path = os.path.join(lib_dir, "libpython.def")
        if not os.path.exists(lib_path):
            dll_list = tuple(filter(lambda dll: dll.startswith("python") and dll.endswith(".dll"), os.listdir(lib_dir)))
            assert dll_list != (), f'Cannot find python*.dll in "{lib_dir}" directory.'
            assert len(dll_list) == 1, f'Find too many python*.dll in "{lib_dir}" directory:\n{" ".join(dll_list)}'
            dll_path = os.path.join(lib_dir, dll_list[0])
            run_command(f"{self.target}-pexports {dll_path} > {def_path}")
            run_command(f"{self.target}-dlltool -D {dll_path} -d {def_path} -l {lib_path}")

    def copy_python_embed_package(self) -> None:
        """复制python embed package到安装目录"""
        for file in os.listdir(self.lib_dir_list["python-embed"]):
            if file.startswith("python"):
                shutil.copyfile(
                    os.path.join(self.lib_dir_list["python-embed"], file),
                    os.path.join(self.bin_dir, file),
                )

    def symlink_multilib(self) -> None:
        """为编译带有multilib支持的交叉编译器创建软链接，如将lib/32链接到lib32"""
        multilib_list = {}
        for multilib in os.listdir(self.lib_prefix):
            if multilib != "lib" and multilib.startswith("lib") and multilib[3:].isdigit():
                multilib_list[multilib] = multilib[3:]
        lib_path = os.path.join(self.lib_prefix, "lib")
        cwd = os.getcwd()
        os.chdir(lib_path)
        for multilib, suffix in multilib_list.items():
            if os.path.exists(suffix):
                os.unlink(suffix)
            os.symlink(os.path.join("..", multilib), suffix, True)
            self.symlink_list.append(os.path.join(lib_path, suffix))
        os.chdir(cwd)

    def delete_symlink(self) -> None:
        """删除编译交叉编译器所需的软链接，在完成编译后不再需要这些软链接"""
        for symlink in self.symlink_list:
            os.unlink(symlink)

    def make_sysroot_link(self) -> None:
        """设置sysroot"""
        path = os.path.join(self.lib_prefix, "lib", "gcc")
        if not os.path.exists(path):
            os.chdir(self.lib_prefix)
            os.symlink("../../lib/gcc", path)

    def package(self, need_gdbinit: bool = True, need_python_embed_package: bool = False) -> None:
        """打包工具链

        Args:
            need_gdbinit (bool, optional): 是否需要打包.gdbinit文件. 默认需要.
            need_python_embed_package (bool, optional): 是否需要打包python embed package. 默认不需要.
        """
        if need_gdbinit:
            self.copy_gdbinit()
        if need_python_embed_package:
            self.copy_python_embed_package()
        self.copy_readme()
        self.make_sysroot_link()
        os.chdir(self.home_dir)
        run_command(f"tar -cf {self.name}.tar {self.name}")
        memory_MB = psutil.virtual_memory().available // 1048576 + 3072
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")

    def remove_unused_glibc_file(self) -> None:
        """移除不需要的glibc文件"""
        for dir in (
            "etc",
            "libexec",
            "sbin",
            "share",
            "var",
            os.path.join(self.lib_prefix, "lib", "gconv"),
            os.path.join(self.lib_prefix, "lib", "audit"),
        ):
            shutil.rmtree(os.path.join(self.lib_prefix, dir))

    def strip_glibc_file(self) -> None:
        """剥离调试符号"""
        strip = f"{self.tool_prefix}strip"
        lib_dir = os.path.join(self.lib_prefix, "lib")
        os.system(f"{strip} {os.path.join(lib_dir, '*.so')}")

    def change_glibc_ldscript(self, arch: str = "") -> None:
        """替换带有绝对路径的链接器脚本"""
        arch = arch if arch != "" else self.target[: self.target.find("-")]
        dst_dir = os.path.join(self.lib_prefix, "lib")
        for file in filter(lambda file: file.startswith(f"{arch}-lib"), os.listdir(self.current_dir)):
            dst_path = os.path.join(dst_dir, file[len(f"{arch}-") :])
            src_path = os.path.join(self.current_dir, file)
            os.remove(dst_path)
            shutil.copyfile(src_path, dst_path)

    def adjust_glibc(self, arch: str = "") -> None:
        """调整glibc"""
        self.remove_unused_glibc_file()
        self.strip_glibc_file()
        self.change_glibc_ldscript(arch)

    def solve_libgcc_limits(self) -> None:
        """解决libgcc的limits.h中提供错误MB_LEN_MAX的问题"""
        libgcc_prefix = os.path.join(self.prefix, "lib", "gcc", self.target)
        include_dir = os.path.join(libgcc_prefix, os.listdir(libgcc_prefix)[0], "include")
        with open(os.path.join(include_dir, "limits.h"), "a") as file:
            file.writelines(("#undef MB_LEN_MAX\n", "#define MB_LEN_MAX 16\n"))


assert __name__ != "__main__", "Import this file instead of running it directly."
