#!/usr/bin/python3
# -*- coding: utf-8 -*-
from typing import Callable
from gcc_environment import cross_environment as cross
from common import triplet_field
import argparse
from modifier import modifier_list

# 列表不包含vendor字段
host_list = ("x86_64-linux-gnu", "x86_64-w64-mingw32")
target_list = (
    "x86_64-linux-gnu",
    "i686-linux-gnu",
    "aarch64-linux-gnu",
    "arm-linux-gnueabi",
    "arm-linux-gnueabihf",
    "loongarch64-linux-gnu",
    "riscv64-linux-gnu",
    "x86_64-w64-mingw32",
    "i686-w64-mingw32",
    "arm-none-eabi",
    "x86_64-elf",
)


def check_triplet(host: str, target: str) -> None:
    """检查输入triplet是否合法

    Args:
        host (str): 宿主平台
        target (str): 目标平台
    """
    for input_triplet, triplet_list in ((host, host_list), (target, target_list)):
        input_triplet_field = triplet_field(input_triplet)
        for support_triplet in triplet_list:
            support_triplet_field = triplet_field(support_triplet)
            if input_triplet_field.weak_eq(support_triplet_field):
                break
        else:
            assert False, f'{"Host" if input_triplet == host else "Target"} "{input_triplet}" is not support.'


def get_modifier(target: str) -> Callable[[cross], None] | None:
    """从修改器列表中查找对应函数

    Args:
        target (str): 目标平台

    Returns:
        Callable | None: 修改器
    """
    if target in modifier_list:
        return modifier_list[target]


def build_gcc(
    build: str,
    host: str,
    target: str,
    multilib: bool,
    gdb: bool,
    gdbserver: bool,
    newlib: bool = True,
    modifier=None,
    home: str = "",
    num_cores: int = 0,
) -> None:
    """构建gcc工具链

    Args:
        build (str): 构建平台
        host (str): 宿主平台
        target (str): 目标平台
        multilib (bool): 是否启用multilib
        gdb (bool): 是否启用gdb
        gdbserver (bool): 是否启用gdbserver
        newlib (bool): 是否启用newlib，仅对独立工具链有效
        modifier (_type_, optional): 平台相关的修改器. 默认为None.
        home (str, optional): 源代码树搜索主目录. 默认为"".
        num_cores (int, optional): 并发构建数. 默认为0.
    """
    env = cross(build, host, target, multilib, gdb, gdbserver, newlib, modifier, home, num_cores)
    env.build()


def dump_support_platform() -> None:
    print("Host support:")
    for host in host_list:
        print(f"\t{host}")
    print("Target support:")
    for target in target_list:
        print(f"\t{target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=str, help="The build platform of the GCC toolchain.", default="x86_64-linux-gnu")
    parser.add_argument("--host", type=str, help="The host platform of the GCC toolchain.", default="x86_64-linux-gnu")
    parser.add_argument("--target", type=str, help="The target platform of the GCC toolchain.")
    parser.add_argument("--multilib", type=bool, help="Whether to enable multilib support in GCC toolchain.", default=False)
    parser.add_argument("--gdb", type=bool, help="Whether to enable gdb support in GCC toolchain.", default=True)
    parser.add_argument("--gdbserver", type=bool, help="Whether to enable gdbserver support in GCC toolchain.", default=False)
    parser.add_argument("--newlib", type=bool, help="Whether to enable newlib support in GCC freestanding toolchain.", default=True)
    parser.add_argument("--home", type=str, help="The home directory to find source trees.", default="")
    parser.add_argument("--jobs", type=int, help="Number of concurrent jobs at build time. Set 0 to use 1.5 times of cpu cores.", default=0)
    parser.add_argument("--dump", action="store_true", help="Print support platforms and exit.")
    args = parser.parse_args()

    if args.dump:
        dump_support_platform()
        quit()

    build: str = args.build
    host: str = args.host
    target: str = args.target
    multilib: bool = args.multilib
    gdb: bool = args.gdb
    gdbserver: bool = args.gdbserver
    newlib: bool = args.newlib
    home: str = args.home
    num_cores: int = args.jobs

    check_triplet(host, target)
    modifier = get_modifier(target)
    build_gcc(build, host, target, multilib, gdb, gdbserver, newlib, modifier, home, num_cores)
