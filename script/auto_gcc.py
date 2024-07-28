#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from importlib import import_module
import sys


class script_list:
    # list[tuple[字段, 是否存在]]
    freestanding_script_list: list[tuple[str, bool]] = []  # 独立工具链构建脚本列表
    host_script_list: list[tuple[str, bool]] = []  # 宿主工具链构建脚本列表
    native_script_list: list[tuple[str, bool]] = []  # 本地工具链构建脚本列表
    cross_script_list: list[tuple[str, bool]] = []  # 交叉工具链构建脚本列表
    canadian_script_list: list[tuple[str, bool]] = []  # 加拿大工具链构建脚本列表
    canadian_cross_script_list: list[tuple[str, bool]] = []  # 加拿大交叉工具链构建脚本列表
    freestanding_target_list: list[tuple[str, bool]] = []  # 独立target列表，不考虑加拿大工具链是否存在
    host_target_list: list[tuple[str, bool]] = []  # 宿主target列表，不考虑加拿大工具链是否存在
    target_list: list[tuple[str, bool]] = []  # 所有target列表，不考虑加拿大工具链是否存在
    build_list: list[str] = []  # 所有构建脚本列表，按构建顺序排序
    path_list: list[tuple[str, bool]] = []  # 工具链bin目录列表，用于添加path环境变量
    script_dir: str  # 构建脚本所在目录

    @staticmethod
    def _insert_list(target: str, exist: bool, list: list[tuple[str, bool]]) -> None:
        if (target, True) not in list and (target, False) not in list:
            list.append((target, exist))

    def __init__(self) -> None:
        self.script_dir = os.path.abspath(os.path.dirname(__file__))
        for script in filter(lambda x: x.endswith("gcc.py") and x != "auto_gcc.py", os.listdir(self.script_dir)):
            script = script[:-3]
            try:
                gcc = import_module(script).env
            except:
                print(f"Loading gcc script {script} failed. Skipping...")
                continue
            exist = os.path.exists(gcc.prefix)
            if gcc.freestanding:
                self.freestanding_script_list.append((script, exist))
                script_list._insert_list(gcc.target, exist, self.freestanding_target_list)
            else:
                self.host_script_list.append((script, exist))
                script_list._insert_list(gcc.target, exist, self.host_target_list)
            match gcc.toolchain_type:
                case "native":
                    self.native_script_list.append((script, exist))
                    self.path_list.append((gcc.bin_dir, exist))
                case "cross":
                    self.cross_script_list.append((script, exist))
                    self.path_list.append((gcc.bin_dir, exist))
                case "canadian":
                    self.canadian_script_list.append((script, exist))
                case "canadian cross":
                    self.canadian_cross_script_list.append((script, exist))
        self.target_list = self.freestanding_target_list + self.host_target_list
        sort_key = lambda x: x[0]
        for list in (self.freestanding_script_list, self.host_script_list, self.target_list):
            list.sort(key=sort_key)
        for list in (self.native_script_list, self.cross_script_list, self.canadian_script_list, self.canadian_cross_script_list):
            list.sort(key=sort_key)
            self.build_list = [*self.build_list, *[script[0] for script in list]]

    def build(self) -> None:
        """构建所有脚本"""
        for script in self.build_list:
            print(f"Building {script}...")
            import_module(script).build()

    def dump_info(self) -> None:
        """打印所有构建脚本信息"""
        print("Freestanding scripts:")
        for script, exist in scripts.freestanding_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nHost scripts:")
        for script, exist in scripts.host_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nNative scripts:")
        for script, exist in scripts.native_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nCross scripts:")
        for script, exist in scripts.cross_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nCanadian scripts:")
        for script, exist in scripts.canadian_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nCanadian cross scripts:")
        for script, exist in scripts.canadian_cross_script_list:
            print(f"- {script}, Exist={exist}")
        print("\nFreestanding target list:")
        for target, exist in scripts.freestanding_target_list:
            print(f"- {target}, Exist={exist}")
        print("\nHost target list:")
        for target, exist in scripts.host_target_list:
            print(f"- {target}, Exist={exist}")
        print("\nBuild flow:")
        for script in scripts.build_list:
            print(f"- {script}")

    def dump_path(self) -> None:
        """打印所有存在的工具链的bin目录列表，用于设置PATH环境变量"""
        for path, _ in filter(lambda x: x[1], scripts.path_list):
            print(f"export PATH={path}:$PATH")


scripts = script_list()

if __name__ == "__main__":
    assert len(sys.argv) <= 2, "Too many arguments"
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        match arg:
            case "--build":
                scripts.build()
            case "--dump_info":
                scripts.dump_info()
            case "--dump_path":
                scripts.dump_path()
            case "--help":
                print("Usage: python build_scripts.py --[build|dump_info|dump_path|help]")
            case _:
                assert False, f'Invalid argument "{arg}". Use "help" to get help.'
    else:
        scripts.build()
