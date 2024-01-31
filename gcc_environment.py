#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import psutil
import shutil
import io
import sys

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports", "iconv")
rpath_lib = "\"-Wl,-rpath='$ORIGIN'/../lib64\""


def run_command(command: str) -> None:
    print(command)
    assert os.system(command) == 0, f'Command "{command}" failed.'


class environment:
    major_version: str  # < GCC的主版本号
    build: str  # < build平台
    host: str  # < host平台
    target: str  # < target平台
    cross_compiler: bool  # < 是否是交叉编译器
    name_without_version: str  # < 不带版本号的工具链名
    name: str  # < 工具链名
    home_dir: str  # < 源代码所在的目录，默认为$HOME
    prefix: str  # < 工具链安装位置
    num_cores: int  # < 编译所用线程数
    current_dir: str  # < toolchains项目所在目录
    lib_prefix: str  # < 安装后库目录的前缀
    bin_dir: str  # <安装后可执行文件所在目录
    symlink_list: list  # < 构建过程中创建的软链接表
    gdbinit_path: str  # <安装后.gdbinit文件所在路径

    def __init__(self, major_version: str, build: str = "x86_64-linux-gnu", host: str = "", target: str = "") -> None:
        self.major_version = major_version
        self.build = build
        self.host = host if host != "" else build
        self.target = target if target != "" else self.host
        self.cross_compiler = self.host != self.target
        self.name_without_version = (f"{self.host}-host-{self.target}-target" if self.cross_compiler else f"{self.host}-native") + "-gcc"
        self.name = self.name_without_version + major_version
        self.home_dir = ""
        for option in sys.argv:
            if option.startswith("--home="):
                self.home_dir = option[7:]
                break
        if self.home_dir == "":
            self.home_dir = os.environ["HOME"]
        for lib in lib_list:
            assert os.path.isdir(os.path.join(self.home_dir, lib)), f'Cannot find "{lib}" in directory "{self.home_dir}".'
        self.prefix = os.path.join(self.home_dir, self.name)
        self.num_cores = psutil.cpu_count() + 4
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.lib_prefix = os.path.join(self.prefix, self.target) if self.cross_compiler else self.prefix
        self.bin_dir = os.path.join(self.prefix, "bin")
        self.symlink_list = []
        self.gdbinit_path = os.path.join(self.prefix, "share", ".gdbinit")

    def update(self) -> None:
        """更新源代码

        """
        for lib in ("expat", "gcc", "binutils", "linux", "mingw", "pexports", "glibc"):
            path = os.path.join(self.home_dir, lib)
            os.chdir(path)
            run_command("git pull")

    def enter_build_dir(self, lib: str) -> None:
        """进入构建目录

        Args:
            lib (str): 要构建的库
        """
        assert lib in lib_list
        build_dir = os.path.join(self.home_dir, lib, "build" if lib != "expat" else "expat/build")
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)
        os.chdir(build_dir)

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
        else:
            run_command(f"make install-strip -j {self.num_cores}")
            targets = ""
            for dll in dll_list:
                targets += f"install-target-{dll} "
        run_command(f"make {targets} -j {self.num_cores}")

    def register_in_env(self) -> None:
        """注册安装路径到环境变量
        """
        os.environ["PATH"] = self.bin_dir + ":" + os.environ["PATH"]

    def register_in_bashrc(self) -> None:
        """注册安装路径到用户配置文件
        """
        bashrc_file = io.open(os.path.join(self.home_dir, ".bashrc"), "a")
        bashrc_file.writelines(f"export PATH={self.bin_dir}:$PATH")
        bashrc_file.close()
        self.register_in_env()

    def copy_gdbinit(self) -> None:
        """复制.gdbinit文件
        """
        gdbinit_src_path = os.path.join(self.current_dir, ".gdbinit")
        shutil.copyfile(gdbinit_src_path, self.gdbinit_path)

    def copy_readme(self) -> None:
        readme_path = os.path.join(self.current_dir, f"{self.name_without_version}.md")
        target_path = os.path.join(self.prefix, "README.md")
        shutil.copyfile(readme_path, target_path)

    def symlink_multilib(self) -> None:
        """为编译带有multilib支持的交叉编译器创建软链接，如将lib/32链接到lib32
        """
        multilib_list = {}
        for multilib in os.listdir(self.lib_prefix):
            if multilib != "lib" and multilib.startswith("lib") and os.path.isdir(os.path.join(self.lib_prefix, multilib)):
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
        """删除编译交叉编译器所需的软链接，在完成编译后不再需要这些软链接
        """
        for symlink in self.symlink_list:
            os.unlink(symlink)

    def package(self, need_gdbinit: bool = True) -> None:
        if need_gdbinit:
            self.copy_gdbinit()
        self.copy_readme()
        os.chdir(self.home_dir)
        run_command(f"tar -cf {self.name}.tar {self.name}/")
        memory_MB = psutil.virtual_memory().available // 1048576
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")


assert __name__ != "__main__", "Import this file instead of running it directly."
