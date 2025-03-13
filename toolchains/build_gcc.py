#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import argparse

from . import common
from .build_gcc_source import *


def _check_input(args: argparse.Namespace, need_check: bool) -> None:
    if need_check:
        assert args.jobs > 0, common.toolchains_error(f"Invalid jobs: {args.jobs}.")
        assert 1 <= args.compress_level <= 22, common.toolchains_error(f"Invalid compress level: {args.compress_level}")
        check_triplet(args.host, args.target)


def build_specific_gcc(
    config: configure,
    host: str,
    target: str,
) -> None:
    """构建gcc工具链

    Args:
        config (configure): 编译环境
        host (str): 宿主平台
        target (str): 目标平台
    """

    config_list = config.get_public_fields()
    env = build_gcc_environment(host=host, target=target, **config_list)
    modifier_list.modify(env, target)
    env.build()
    common.toolchains_print(common.toolchains_success(f"Build {env.env.name} successfully."))


def dump_support_platform() -> None:
    """打印所有受支持的平台"""

    print(common.color.note.wrapper("Host support:"))
    for host in support_platform_list.host_list:
        print(f"\t{host}")
    print(common.color.note.wrapper("Target support:"))
    for target in support_platform_list.target_list:
        print(f"\t{target}")

    print(common.color.note.wrapper("NOTE:"), "You can add a vendor field to triplets above.")
    # 没有执行任何实际操作，无需打印状态计数
    common.status_counter.set_quiet(True)


__all__ = [
    "modifier_list",
    "support_platform_list",
    "configure",
    "build_gcc_environment",
    "check_triplet",
    "build_specific_gcc",
    "dump_support_platform",
]


def main() -> int:
    default_config = configure()

    parser = argparse.ArgumentParser(description="Build GCC toolchain to specific platform.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands.")
    build_parser = subparsers.add_parser("build", help="Build the GCC toolchain.", formatter_class=common.arg_formatter)
    subparsers.add_parser("dump", help="Print support platforms and exit.", formatter_class=common.arg_formatter)

    # 添加build相关选项
    configure.add_argument(build_parser)
    action = build_parser.add_argument("--host", type=str, help="The host platform of the GCC toolchain.", default=default_config.build)
    common.register_completer(action, common.triplet_completer(support_platform_list.host_list))
    action = build_parser.add_argument("--target", type=str, help="The target platform of the GCC toolchain.", default=default_config.build)
    common.register_completer(action, common.triplet_completer(support_platform_list.target_list))
    build_parser.add_argument(
        "--gdb", action=argparse.BooleanOptionalAction, help="Whether to enable gdb support in GCC toolchain.", default=default_config.gdb
    )
    build_parser.add_argument(
        "--gdbserver",
        action=argparse.BooleanOptionalAction,
        help="Whether to enable gdbserver support in GCC toolchain.",
        default=default_config.gdbserver,
    )
    build_parser.add_argument(
        "--newlib",
        action=argparse.BooleanOptionalAction,
        help="Whether to enable newlib support in GCC freestanding toolchain.",
        default=default_config.newlib,
    )
    build_parser.add_argument(
        "--nls",
        action=argparse.BooleanOptionalAction,
        help="Whether to enable nls(nature language support) in GCC toolchain.",
        default=default_config.nls,
    )

    common.support_argcomplete(parser)
    args = parser.parse_args()

    def do_main() -> None:
        match (args.command):
            case "build":
                _check_input(args, args.command == "build")
                current_config = configure.parse_args(args)

                # 检查合并配置后环境是否正确
                current_config.check()
                current_config.save_config()
                build_specific_gcc(current_config, args.host, args.target)
            case "dump":
                dump_support_platform()
            case _:
                pass

    return common.toolchains_main(do_main)
