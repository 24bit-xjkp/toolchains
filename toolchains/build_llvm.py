#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import argparse
import typing

from . import common
from .build_llvm_source import *
from .gcc_environment import get_specific_environment


def sysroot(env: environment) -> None:
    """从已安装的gcc中复制库并创建sysroot

    Args:
        env (environment): llvm构建环境
    """

    common.mkdir(env.sysroot_dir, True)
    libgcc_prefix = env.sysroot_dir / "lib" / "gcc"
    common.mkdir(libgcc_prefix)
    for target in support_platform_list.hosted_list:
        gcc = get_specific_environment(env, env.build, target)
        target_dir = env.sysroot_dir / target
        common.mkdir(target_dir)
        if gcc.toolchain_type.contain(common.toolchain_type.native):
            # 复制include和lib64
            for dir in ("include", "lib64"):
                common.copy(gcc.prefix / dir, target_dir / dir)
            # 复制glibc链接库
            common.copy(gcc.lib_prefix / "lib", target_dir / "lib")
            # 复制glibc头和linux头
            for item in (gcc.lib_prefix / "include").iterdir():
                common.copy(item, target_dir / "include" / item.name)
        else:
            # 复制除libgcc外所有库
            for dir in ("include", "lib", "lib64"):
                common.copy_if_exist(gcc.lib_prefix / dir, target_dir / dir)
        # 复制libgcc
        common.copy(gcc.prefix / "lib" / "gcc" / target, libgcc_prefix / target)

    common.toolchains_print(common.toolchains_success("Build sysroot successfully."))


def main() -> int:
    default_config = configure()

    parser = argparse.ArgumentParser(description="Build LLVM toolchain to specific platform.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands.")
    sysroot_parser = subparsers.add_parser(
        "sysroot",
        help="Build sysroot for llvm toolchain using installed gcc toolchains.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sysroot_config.add_argument(sysroot_parser)

    common.support_argcomplete(parser)
    errno = 0
    args = parser.parse_args()
    try:
        match (args.command):
            case "sysroot":
                config: dict[str, typing.Any] = {}
                for key, val in vars(sysroot_config.parse_args(args)).items():
                    if not key.startswith("_"):
                        config[key] = val
                config["jobs"] = 1
                config["compress_level"] = 1
                config["host"] = None
                sysroot(environment(**config))
            case _:
                pass
    except Exception as e:
        common.toolchains_print(e)
        errno = 1
    finally:
        common.status_counter.show_status()
        return errno
