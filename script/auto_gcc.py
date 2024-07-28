import os
from importlib import import_module


class script_list:
    freestanding_script_list: list[str] = []  # 独立工具链构建脚本列表
    host_script_list: list[str] = []  # 宿主工具链构建脚本列表
    native_script_list: list[str] = []  # 本地工具链构建脚本列表
    cross_script_list: list[str] = []  # 交叉工具链构建脚本列表
    canadian_script_list: list[str] = []  # 加拿大工具链构建脚本列表
    canadian_cross_script_list: list[str] = []  # 加拿大交叉工具链构建脚本列表
    freestanding_target_list: list[str] = []  # 独立target列表
    host_target_list: list[str] = []  # 宿主target列表
    target_list: list[str] = []  # 所有target列表
    build_list: list[str] = []  # 所有构建脚本列表，按构建顺序排序
    path_list: list[str] = []  # 工具链bin目录列表，用于添加path环境变量
    script_dir: str  # 构建脚本所在目录

    def __init__(self) -> None:
        self.script_dir = os.path.abspath(os.path.dirname(__file__))
        for script in filter(lambda x: x.endswith("gcc.py") and x != "auto_gcc.py", os.listdir(self.script_dir)):
            script = script[:-3]
            try:
                gcc = import_module(script).env
            except:
                print(f"Loading gcc script {script} failed. Skipping...")
                continue
            if gcc.freestanding:
                self.freestanding_script_list.append(script)
                if gcc.target not in self.freestanding_target_list:
                    self.freestanding_target_list.append(gcc.target)
            else:
                self.host_script_list.append(script)
                if gcc.target not in self.host_target_list:
                    self.host_target_list.append(gcc.target)
            match gcc.toolchain_type:
                case "native":
                    self.native_script_list.append(script)
                    self.path_list.append(gcc.bin_dir)
                case "cross":
                    self.cross_script_list.append(script)
                    self.path_list.append(gcc.bin_dir)
                case "canadian":
                    self.canadian_script_list.append(script)
                case "canadian cross":
                    self.canadian_cross_script_list.append(script)
        self.target_list = self.freestanding_target_list + self.host_target_list
        for list in (self.freestanding_script_list, self.host_script_list, self.target_list):
            list.sort()
        for list in (self.native_script_list, self.cross_script_list, self.canadian_script_list, self.canadian_cross_script_list):
            list.sort()
            self.build_list += list

    def build(self) -> None:
        """构建所有脚本"""
        for script in self.build_list:
            print(f"Building {script}...")
            import_module(script).env.build()

    def dump(self) -> None:
        """打印所有构建脚本"""
        print("Freestanding scripts:")
        for script in scripts.freestanding_script_list:
            print(f"- {script}")
        print("\nHost scripts:")
        for script in scripts.host_script_list:
            print(f"- {script}")
        print("\nNative scripts:")
        for script in scripts.native_script_list:
            print(f"- {script}")
        print("\nCross scripts:")
        for script in scripts.cross_script_list:
            print(f"- {script}")
        print("\nCanadian scripts:")
        for script in scripts.canadian_script_list:
            print(f"- {script}")
        print("\nCanadian cross scripts:")
        for script in scripts.canadian_cross_script_list:
            print(f"- {script}")
        print("\nFreestanding target list:")
        for target in scripts.freestanding_target_list:
            print(f"- {target}")
        print("\nHost target list:")
        for target in scripts.host_target_list:
            print(f"- {target}")
        print("\nBuild flow:")
        for script in scripts.build_list:
            print(f"- {script}")

    def dump_path(self) -> None:
        """打印bin目录列表，用于设置PATH环境变量"""
        for path in scripts.path_list:
            print(f"export PATH={path}:$PATH")


scripts = script_list()

if __name__ == "__main__":
    scripts.build()
