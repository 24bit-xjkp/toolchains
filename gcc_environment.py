#!/usr/bin/python3
import os

lib_list = ("expat", "gcc", "binutils", "gmp", "mpfr", "linux", "mingw", "pexports")


class environment:
    major_version: int
    build: str
    host: set
    target: str
    cross_compiler: bool
    name: str
    home_dir: str
    prefix: str

    def __init__(self, major_version: int, build: str = "x86_64-linux-gnu", host: str = "", target: str = "") -> None:
        self.major_version = major_version
        self.build = build
        self.host = host if host != "" else build
        self.target = target if target != "" else self.host
        self.cross_compiler = self.host != self.target
        self.name = (f"{self.host}-host-{self.target}-target" if self.cross_compiler else f"{self.host}-native") + f"-gcc{major_version}"
        self.home_dir = os.environ["HOME"]
        self.prefix = os.path.join(self.home_dir, self.name)

    def update(self) -> None:
        for lib in ("expat", "gcc", "binutils", "linux", "mingw", "pexports"):
            path = os.path.join(self.home_dir, lib)
            os.chdir(path)
            os.system("git pull")


class auto_build:
    env: environment

    def __init__(self, env: environment, lib: str) -> None:
        assert lib in lib_list
        self.env = env
        build_dir = os.path.join(self.env.home_dir, lib, "build" if lib != "expat" else "expat/build")
        if not os.path.isdir(build_dir):
            os.mkdir(build_dir)
        os.chdir(build_dir)
        os.system("rm -rf *")

    def configure(self, prefix="", *extra_args: str) -> None:
        command = f"../"
