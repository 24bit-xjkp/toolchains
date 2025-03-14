#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import argparse
import typing

from . import common
from .build_llvm_source import *
from .gcc_environment import get_specific_environment


def sysroot(env: llvm_environment) -> None:
    """从已安装的gcc中复制库并创建sysroot

    Args:
        env (llvm_environment): llvm构建环境
    """

    # TODO:armv7m-none-eabi的sysroot生成
    sysroot_dir = env.sysroot_dir[env.build]
    common.mkdir(sysroot_dir, True)
    libgcc_prefix = sysroot_dir / "lib" / "gcc"
    common.mkdir(libgcc_prefix)
    for target in llvm_support_platform_list.hosted_list:
        gcc = get_specific_environment(env, env.build, target)
        target_dir = sysroot_dir / target
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


def build_specific_llvm(env: llvm_environment) -> None:
    """构建指定llvm

    Args:
        env (llvm_environment): llvm构建环境
    """

    modifier_list.modify(env, [*env.runtime_build_options])
    build_llvm_environment.build(env)


__all__ = ["modifier_list", "llvm_support_platform_list", "configure", "llvm_environment", "sysroot_config", "sysroot"]


def main() -> int:
    default_config = configure()

    parser = argparse.ArgumentParser(description="Build LLVM toolchain to specific platform.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands.")
    sysroot_parser = subparsers.add_parser(
        "sysroot", help="Build sysroot for llvm toolchain using installed gcc toolchains.", formatter_class=common.arg_formatter
    )
    build_parser = subparsers.add_parser("build", help="Build the LLVM toolchain.", formatter_class=common.arg_formatter)

    sysroot_config.add_argument(sysroot_parser)
    configure.add_argument(build_parser)
    action = build_parser.add_argument("--host", type=str, help="The host platform of the LLVM toolchain.", default=default_config.build)
    common.register_completer(action, common.triplet_completer(llvm_support_platform_list.host_list))
    build_parser.add_argument(
        "--family", "-f", type=str, help="The runtime family of the LLVM toolchain.", default=runtime_family.gnu, choices=runtime_family
    )

    common.support_argcomplete(parser)
    args = parser.parse_args()

    def do_main() -> None:
        match (args.command):
            case "sysroot":
                sysroot_config_v: dict[str, typing.Any] = {}
                for key, val in vars(sysroot_config.parse_args(args)).items():
                    if not key.startswith("_"):
                        sysroot_config_v[key] = val
                sysroot_config_v["jobs"] = 1
                sysroot_config_v["compress_level"] = 1
                sysroot_config_v["host"] = None
                sysroot(llvm_environment(**sysroot_config_v))
            case "build":
                build_config = configure.parse_args(args)
                assert args.host in llvm_support_platform_list.host_list, common.toolchains_error(f"Host {args.host} is not supported.")
                env = llvm_environment(
                    host=args.host,
                    family=args.family,
                    runtime_target_list=llvm_support_platform_list.target_list,
                    **build_config.get_public_fields(),
                )
                build_specific_llvm(env)
            case _:
                pass

    return common.toolchains_main(do_main)
