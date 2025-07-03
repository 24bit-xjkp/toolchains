#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import argparse
import functools
import multiprocessing
from pathlib import Path

from . import common
from .utils_source import *


def compress(config: compress_configure) -> None:
    """压缩工具链

    Args:
        config (compress_configure): 工具链压缩环境
    """

    output_dir, dir_list, env = config._output_dir, config._item_list, config.to_environment()
    common.mkdir(output_dir, False)
    with common.chdir_guard(env.prefix_dir):
        for dir in dir_list or filter(lambda dir: common.toolchains_dir(dir), env.prefix_dir.iterdir()):
            env.compress_path(str(dir.relative_to(env.prefix_dir)), output_dir, False)

    common.toolchains_print(common.toolchains_success("Compress toolchains successfully."))


def _decompress_worker(env: common.compress_environment, output_dir: Path, mutex: common.optional_lock, file: Path) -> None:
    """执行解压缩操作

    Args:
        env (common.compress_environment): 工具链压缩环境
        output_dir (Path): 输出目录
        mutex (common.optional_lock): 并行环境下的互斥锁
        file (Path): 要解压的文件
    """

    env.decompress_path(str(file.relative_to(env.prefix_dir)), output_dir, False, mutex)


def decompress(config: compress_configure) -> None:
    """解压缩打包的工具链

    Args:
        config (compress_configure): 工具链压缩环境
    """

    output_dir, file_list, env = config._output_dir, config._item_list, config.to_environment()
    common.mkdir(output_dir, False)
    with common.chdir_guard(output_dir):
        file_list = file_list or [*filter(lambda file: common.toolchains_package(file), env.prefix_dir.iterdir())]

        if env.jobs > 1:
            with multiprocessing.Manager() as manager, multiprocessing.Pool(config.jobs) as pool:
                mutex = manager.Lock()
                pool.map(functools.partial(_decompress_worker, env, output_dir, mutex), file_list)
        else:
            for file in file_list:
                _decompress_worker(env, output_dir, None, file)

    common.toolchains_print(common.toolchains_success("Decompress toolchains successfully."))


def disable_wine_binfmt() -> None:
    """禁用Wine的binfmt_misc格式"""

    common.binfmt.disable("DOSWin")


def enable_wine_binfmt() -> None:
    """启用Wine的binfmt_misc格式"""

    common.binfmt.enable("DOSWin")


__all__ = ["compress_configure", "compress", "decompress", "disable_wine_binfmt", "enable_wine_binfmt"]


def main() -> int:
    default_config = compress_configure()

    parser = argparse.ArgumentParser(description="Utilities for toolchains.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands.")

    compress_parser = subparsers.add_parser(
        "compress", help="Compress installed toolchains under the prefix directory.", formatter_class=common.arg_formatter
    )
    decompress_parser = subparsers.add_parser(
        "decompress", help="Decompress packed toolchains under the prefix directory.", formatter_class=common.arg_formatter
    )
    wine_binfmt_parser = subparsers.add_parser(
        "wine-binfmt",
        help="Set Wine's binfmt_misc support.",
        formatter_class=common.arg_formatter,
    )

    compress_configure.add_argument(compress_parser)
    action = compress_parser.add_argument(
        "--dir",
        "-d",
        dest="item_list",
        action="extend",
        nargs="*",
        help="Directories of toolchains to compress. This is a path relative to the prefix directory.",
    )
    common.register_completer(action, common.item_with_prefix_completer("prefix_dir", common.toolchains_dir))
    compress_configure.add_argument(decompress_parser)
    action = decompress_parser.add_argument(
        "--file",
        "-f",
        dest="item_list",
        action="extend",
        nargs="*",
        help="Files of packed toolchains to decompress. This is a path relative to the prefix directory.",
    )
    common.register_completer(action, common.item_with_prefix_completer("prefix_dir", common.toolchains_package))
    wine_binfmt_parser.add_argument(
        "action",
        choices=["enable", "disable"],
        help="Action to perform on Wine's binfmt_misc support.",
    )

    common.support_argcomplete(parser)
    args = parser.parse_args()

    def do_main() -> None:
        match (args.command):
            case "compress":
                compress(compress_configure.parse_args(args))
            case "decompress":
                decompress(compress_configure.parse_args(args))
            case "wine-binfmt":
                common.status_counter.set_quiet(True)
                if args.action == "enable":
                    enable_wine_binfmt()
                else:
                    disable_wine_binfmt()
            case _:
                pass

    return common.toolchains_main(do_main)
