#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import psutil
import shutil
import sys
from math import floor


def run_command(command: str, ignore_error: bool = False) -> None:
    """运行指定命令，若不忽略错误，则在命令执行出错时抛出AssertionError，反之打印错误吗

    Args:
        command (str): 要运行的命令
        ignore_error (bool, optional): 是否忽略错误. 默认不忽略错误.
    """

    # 打印运行的命令
    print(command)
    errno = os.system(command)
    if not ignore_error:
        assert errno == 0, f'Command "{command}" failed.'
    elif errno != 0:
        print(f'Command "{command}" failed with errno={errno}, but it is ignored.')


def copy(src: str, dst: str, overwrite=True, follow_symlinks: bool = False) -> None:
    """复制文件或目录

    Args:
        src (str): 源路径
        dst (str): 目标路径
        overwrite (bool, optional): 是否覆盖已存在项. 默认为覆盖.
        follow_symlinks (bool, optional): 是否复制软链接指向的目标，而不是软链接本身. 默认为保留软链接.
    """
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
    message = f'Cannot find lib "{lib}" in directory "{lib_dir}"'
    if do_assert and not os.path.exists(lib_dir):
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
    num_cores: int  # < 编译所用线程数
    current_dir: str  # < toolchains项目所在目录
    name_without_version: str  # < 不带版本号的工具链名
    name: str  # < 工具链名
    bin_dir: str  # < 安装后可执行文件所在目录

    def __init__(self, version: str, name_without_version: str) -> None:
        self.version = version
        self.major_version = self.version.split('.')[0]
        self.name_without_version = name_without_version
        self.name = self.name_without_version + self.major_version
        self.home_dir = ""
        for option in sys.argv:
            if option.startswith("--home="):
                self.home_dir = option[7:]
                break
        if self.home_dir == "":
            self.home_dir = os.environ["HOME"]
        self.num_cores = floor(psutil.cpu_count() * 1.5)
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.bin_dir = os.path.join(self.home_dir, self.name, "bin")

    def compress(self) -> None:
        """压缩构建完成的工具链"""
        os.chdir(self.home_dir)
        run_command(f"tar -cf {self.name}.tar {self.name}")
        memory_MB = psutil.virtual_memory().available // 1048576 + 3072
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")

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


assert __name__ != "__main__", "Import this file instead of running it directly."
