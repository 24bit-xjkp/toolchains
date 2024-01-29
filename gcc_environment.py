#!/usr/bin/python3
import os
import psutil
import shutil
import io

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports")


def run_command(command: str) -> None:
    print(command)
    assert os.system(command) == 0, f'Command "{command}" failed.'


class environment:
    major_version: str  # < GCC的主版本号
    build: str  # < build平台
    host: str  # < host平台
    target: str  # < target平台
    cross_compiler: bool  # < 是否是交叉编译器
    name_without_version: str  # < 不带版本号的工具链名
    name: str  # < 工具链名
    home_dir: str  # < $HOME
    prefix: str  # < 工具链安装位置
    num_cores: int  # < 编译所用线程数
    current_dir: str  # < 该文件所在目录
    lib_prefix: str  # < 安装后库所在路径
    symlink_list: list  # < 构建过程中创建的软链接表

    def __init__(self, major_version: str, build: str = "x86_64-linux-gnu", host: str = "", target: str = "") -> None:
        self.major_version = major_version
        self.build = build
        self.host = host if host != "" else build
        self.target = target if target != "" else self.host
        self.cross_compiler = self.host != self.target
        self.name_without_version = (f"{self.host}-host-{self.target}-target" if self.cross_compiler else f"{self.host}-native") + "-gcc"
        self.name = self.name_without_version + major_version
        self.home_dir = os.environ["HOME"]
        self.prefix = os.path.join(self.home_dir, self.name)
        self.num_cores = psutil.cpu_count() + 4
        self.current_dir = os.path.abspath(os.path.dirname(__file__))
        self.lib_prefix = os.path.join(self.prefix, self.target) if self.cross_compiler else self.prefix

    def update(self) -> None:
        for lib in ("expat", "gcc", "binutils", "linux", "mingw", "pexports", "glibc"):
            path = os.path.join(self.home_dir, lib)
            os.chdir(path)
            run_command("git pull")

    def enter_build_dir(self, lib: str) -> str:
        assert lib in lib_list
        build_dir = os.path.join(self.home_dir, lib, "build" if lib != "expat" else "expat/build")
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)
        os.chdir(build_dir)
        return build_dir

    def configure(self, *option: str) -> None:
        options = " ".join(("", *option))
        run_command(f"../configure {options}")

    def make(self, *target: str) -> None:
        targets = " ".join(("", *target))
        run_command(f"make {targets} -j {self.num_cores}")

    def install(self, *target: str) -> None:
        targets = " ".join(("", *target)) if target != () else "install-strip"
        run_command(f"make {targets} -j {self.num_cores}")

    def register_in_env(self) -> None:
        bin_path = os.path.join(self.prefix, "bin")
        os.environ["PATH"] = bin_path + ":" + os.environ["PATH"]

    def register_in_bashrc(self) -> None:
        bin_path = os.path.join(self.prefix, "bin")
        bashrc_file = io.open(os.path.join(self.home_dir, ".bashrc"), "a")
        bashrc_file.writelines(f"export PATH={bin_path}:$PATH")
        self.register_in_env()

    def copy_gdbinit(self) -> None:
        gdbinit_path = os.path.join(self.current_dir, ".gdbinit")
        target_path = os.path.join(self.prefix, "share", ".gdbinit")
        shutil.copyfile(gdbinit_path, target_path)

    def copy_readme(self) -> None:
        readme_path = os.path.join(self.current_dir, f"{self.name_without_version}.md")
        target_path = os.path.join(self.prefix, "README.md")
        shutil.copyfile(readme_path, target_path)

    def symlink_multilib(self) -> None:
        multilib_list = {}
        for multilib in os.listdir(self.lib_prefix):
            if multilib != "lib" and multilib[0:3] == "lib" and os.path.isdir(multilib):
                multilib_list[multilib] = multilib[3:]
        lib_path = os.path.join(self.lib_prefix, "lib")
        cwd = os.getcwd()
        os.chdir(lib_path)
        for multilib, suffix in multilib_list:
            os.symlink(os.path.join("..", multilib), suffix, True)
            self.symlink_list.append(os.path.join(lib_path, suffix))
        os.chdir(cwd)

    def delete_symlink(self) -> None:
        for symlink in self.symlink_list:
            os.unlink(symlink)

    def package(self, need_gdbinit: bool = True) -> None:
        if need_gdbinit:
            self.copy_gdbinit()
        self.copy_readme()
        os.chdir(self.home_dir)
        run_command(f"tar -cf {self.name}.tar {self.name}/")
        memory_MB = psutil.virtual_memory().available // 1048576
        run_command(f"xz -fev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")


assert __name__ != "__main__", "Import this file instead of running it directly."
