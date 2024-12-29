#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import psutil
import shutil
import sys
from math import floor


def run_command(command: str, ignore_error: bool = False) -> None:
    """运行指定命令, 若不忽略错误, 则在命令执行出错时抛出RuntimeError, 反之打印错误码

    Args:
        command (str): 要运行的命令
        ignore_error (bool, optional): 是否忽略错误. 默认不忽略错误.
    """

    # 打印运行的命令
    print("[toolchains] run command: ", command)
    errno = os.system(command)

    if errno == 0:
        return

    if ignore_error:
        print(f'Command "{command}" failed with errno={errno}, but it is ignored.')
    else:
        raise RuntimeError(f'Command "{command}" failed.')


def mkdir(path: str, remove_if_exist=True) -> None:
    """创建目录

    Args:
        path (str): 要创建的目录
        remove_if_exist (bool, optional): 是否先删除已存在的同名目录. 默认先删除已存在的同名目录.
    """
    if remove_if_exist and os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def copy(src: str, dst: str, overwrite=True, follow_symlinks: bool = False) -> None:
    """复制文件或目录

    Args:
        src (str): 源路径
        dst (str): 目标路径
        overwrite (bool, optional): 是否覆盖已存在项. 默认为覆盖.
        follow_symlinks (bool, optional): 是否复制软链接指向的目标，而不是软链接本身. 默认为保留软链接.
    """
    # 创建目标目录
    dir = os.path.dirname(dst)
    if dir != "":
        mkdir(dir, False)
    if not overwrite and os.path.exists(dst):
        return
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, not follow_symlinks)
    else:
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copyfile(src, dst, follow_symlinks=follow_symlinks)


def copy_if_exist(src: str, dst: str, overwrite=True, follow_symlinks: bool = False) -> None:
    """如果文件或目录存在则复制文件或目录

    Args:
        src (str): 源路径
        dst (str): 目标路径
        overwrite (bool, optional): 是否覆盖已存在项. 默认为覆盖.
        follow_symlinks (bool, optional): 是否复制软链接指向的目标，而不是软链接本身. 默认为保留软链接.
    """
    if os.path.exists(src):
        copy(src, dst, overwrite, follow_symlinks)


def remove(path: str) -> None:
    """删除指定路径

    Args:
        path (str): 要删除的路径
    """
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def remove_if_exists(path: str) -> None:
    """如果指定路径存在则删除指定路径

    Args:
        path (str): 要删除的路径
    """
    if os.path.exists(path):
        remove(path)


def check_lib_dir(lib: str, lib_dir: str, do_assert=True) -> bool:
    """检查库目录是否存在

    Args:
        lib (str): 库名称，用于提供错误报告信息
        lib_dir (str): 库目录
        do_assert (bool, optional): 是否断言库存在. 默认断言.

    Returns:
        bool: 返回库是否存在
    """
    message = f'[toolchains] Cannot find lib "{lib}" in directory "{lib_dir}"'
    if not do_assert and not os.path.exists(lib_dir):
        print(message)
        return False
    else:
        assert os.path.exists(lib_dir), message
    return True


class basic_environment:
    """gcc和llvm共用基本环境"""

    version: str  # 版本号
    major_version: str  # 主版本号
    home_dir: str  # 源代码所在的目录，默认为$HOME
    jobs: int  # 编译所用线程数
    current_dir: str  # toolchains项目所在目录
    name_without_version: str  # 不带版本号的工具链名
    name: str  # 工具链名
    bin_dir: str  # 安装后可执行文件所在目录

    def __init__(self, version: str, name_without_version: str, home: str, jobs: int) -> None:
        self.version = version
        self.major_version = self.version.split(".")[0]
        self.name_without_version = name_without_version
        self.name = self.name_without_version + self.major_version
        self.home_dir = home
        self.jobs = jobs
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.bin_dir = os.path.join(self.home_dir, self.name, "bin")

    def compress(self, name: str = "") -> None:
        """压缩构建完成的工具链

        Args:
            name (str, optional): 要压缩的目标名称，是相对于self.home_dir的路径. 默认为self.name.
        """
        os.chdir(self.home_dir)
        name = name or self.name
        run_command(f"tar -cf {name}.tar {name}")
        memory_MB = psutil.virtual_memory().available // 1048576 + 3072
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {name}.tar")

    def register_in_env(self) -> None:
        """注册安装路径到环境变量"""
        os.environ["PATH"] = f"{self.bin_dir}:{os.environ['PATH']}"

    def register_in_bashrc(self) -> None:
        """注册安装路径到用户配置文件"""
        with open(os.path.join(self.home_dir, ".bashrc"), "a") as bashrc_file:
            bashrc_file.write(f"export PATH={self.bin_dir}:$PATH\n")

    def copy_readme(self) -> None:
        """复制工具链说明文件"""
        readme_path = os.path.join(self.current_dir, "..", "readme", f"{self.name_without_version}.md")
        target_path = os.path.join(os.path.join(self.home_dir, self.name), "README.md")
        copy(readme_path, target_path)


class triplet_field:
    """平台名称各个域的内容"""

    arch: str  # 架构
    os: str  # 操作系统
    vendor: str  # 制造商
    abi: str  # abi/libc
    num: int  # 非unknown的字段数

    def __init__(self, triplet: str, normalize: bool = True) -> None:
        """解析平台名称

        Args:
            triplet (str): 输入平台名称
        """
        field = triplet.split("-")
        self.arch = field[0]
        self.num = len(field)
        match (self.num):
            case 2:
                self.os = "unknown"
                self.vendor = "unknown"
                self.abi = field[1]
            case 3:
                self.os = field[1]
                self.vendor = "unknown"
                self.abi = field[2]
            case 4:
                self.os = field[1]
                self.vendor = field[2]
                self.abi = field[3]
            case _:
                assert False, f'Illegal triplet "{triplet}"'

        # 正则化
        if normalize:
            if self.os == "none":
                self.os = "unknown"

    def weak_eq(self, other) -> bool:
        """弱相等比较，允许vendor字段不同

        Args:
            other (triplet_field): 待比较对象

        Returns:
            bool: 是否相同
        """
        return self.arch == other.arch and self.os == other.os and self.abi == other.abi


assert __name__ != "__main__", "Import this file instead of running it directly."
