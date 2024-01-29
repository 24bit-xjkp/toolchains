#!/usr/bin/python3
import os
import psutil
import shutil
import io

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports")


class environment:
    major_version: str
    build: str
    host: set
    target: str
    cross_compiler: bool
    name_without_version: str
    name: str
    home_dir: str
    prefix: str
    num_cores: int
    current_dir: str

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
        self.num_cores = psutil.cpu_count()
        self.current_dir = os.getcwd()
        assert os.path.isfile(os.path.join(self.current_dir, f"{self.name_without_version}.md")), "We must run the script in the project directory and ensure that the project is unbroken."

    def update(self) -> None:
        for lib in ("expat", "gcc", "binutils", "linux", "mingw", "pexports", "glibc"):
            path = os.path.join(self.home_dir, lib)
            os.chdir(path)
            os.system("git pull")

    def enter_build_dir(self, lib: str) -> None:
        assert lib in lib_list
        build_dir = os.path.join(self.home_dir, lib, "build" if lib != "expat" else "expat/build")
        if os.path.isdir(build_dir):
            os.chdir(build_dir)
            os.system("rm -rf *")
        else:
            os.mkdir(build_dir)
            os.chdir(build_dir)

    def make(self, *target: str) -> None:
        targets = " ".join(target)
        os.system(f"make {targets} -j {self.num_cores}")

    def install(self, *target: str) -> None:
        targets = " ".join(target) if target != [] else "install-strip"
        os.system(f"make {targets} -j {self.num_cores}")

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

    def package(self, need_gdbinit: bool = True) -> None:
        if need_gdbinit:
            self.copy_gdbinit()
        self.copy_readme()
        os.chdir(self.home_dir)
        os.system(f"tar -cf {self.name}.tar {self.name}/")
        memory_MB = psutil.virtual_memory().available // 1048576
        os.system(f"xz -ev9 -T 0 --memlimit={memory_MB}MiB {self.name}.tar")


assert __name__ != "__main__", "Import this file instead of running it directly."
