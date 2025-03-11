#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import argparse

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


def decompress(config: compress_configure) -> None:
    """解压缩打包的工具链

    Args:
        config (compress_configure): 工具链压缩环境
    """

    output_dir, file_list, env = config._output_dir, config._item_list, config.to_environment()
    common.mkdir(output_dir, False)
    with common.chdir_guard(output_dir):
        for file in file_list or filter(lambda file: common.toolchains_package(file), env.prefix_dir.iterdir()):
            env.decompress_path(str(file.relative_to(env.prefix_dir)), output_dir, False)

    common.toolchains_print(common.toolchains_success("Decompress toolchains successfully."))


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

    common.support_argcomplete(parser)
    errno = 0
    args = parser.parse_args()
    try:
        match (args.command):
            case "compress":
                compress(compress_configure.parse_args(args))
            case "decompress":
                decompress(compress_configure.parse_args(args))
            case _:
                pass
    except Exception as e:
        common.toolchains_print(e)
        errno = 1
    finally:
        common.status_counter.show_status()
        return errno
