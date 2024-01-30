#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gcc_environment as gcc
import x86_64_linux_gnu_host_x86_64_w64_mingw32_target_gcc as cross_gcc
import os
import shutil

env = gcc.environment("14", host="x86_64-w64-mingw32")
lib_install_dir = {}
for lib in ("gmp", "expat", "iconv", "mpfr"):
    lib_install_dir[lib] = os.path.join(env.home_dir, lib, "install")


def build():
    # 更新源代码
    # env.update()

    basic_option = f"--disable-werror --prefix={env.prefix} --host={env.host} --target={env.target}"
    gcc_option = "--enable-multilib --enable-languages=c,c++ --disable-sjlj-exceptions --enable-threads=win32"
    lib_option = f"--host={env.host} --disable-shared"
    # 编译安装完整gcc
    env.enter_build_dir("gcc")
    env.configure(basic_option, gcc_option)
    env.make()
    env.install()

    # 删除已安装的dll
    os.chdir(env.bin_dir)
    for file in os.listdir(env.bin_dir):
        if file.endswith(".dll"):
            os.remove(file)
    # 从交叉工具链复制文件
    for dir in ("include", "lib", "lib32"):
        cross_dir = os.path.join(cross_gcc.env.lib_prefix, dir)
        current_dir = os.path.join(env.lib_prefix, dir)
        for item in os.listdir(cross_dir):
            dst_path = os.path.join(current_dir, item)
            src_path = os.path.join(cross_dir, item)
            if not os.path.exists(dst_path):
                shutil.copytree(src_path, dst_path) if os.path.isdir(src_path) else shutil.copyfile(src_path, dst_path)

    # 创建libpython.a
    python_dir = os.path.join(env.home_dir, "python-embed")
    os.chdir(python_dir)
    if not os.path.exists("libpython.a"):
        dll_name = ""
        for file in os.listdir("."):
            if file.endswith(".dll"):
                dll_name = file
                break
        assert dll_name != "", 'Cannot find python*.dll in "~/python-embed" directory.'
        gcc.run_command(f"{env.target}-pexports {dll_name} > libpython.def")
        gcc.run_command(f"{env.target}-dlltool -D {dll_name} -d libpython.def -l libpython.a")

    # 编译安装libgmp, libexpat, libiconv, libmpfr
    for lib, prefix in lib_install_dir.items():
        env.enter_build_dir(lib)
        env.configure(lib_option, f"--prefix={prefix}", f"--with-gmp={lib_install_dir['gmp']}" if lib == "mpfr" else "")
        env.make()
        env.install()

    lib_option = ["--with-expat"]
    for lib in ("gmp", "mpfr"):
        lib_option.append(f"--with-{lib}={lib_install_dir[lib]}")
    for lib in ("expat", "iconv"):
        lib_option.append(f"--with-lib{lib}-prefix={lib_install_dir[lib]}")

    # 编译安装binutils和gdb
    env.enter_build_dir("binutils")
    env.configure(basic_option, *lib_option, f"--with-system-gdbinit={env.gdbinit_path} --with-python={os.path.join(env.current_dir, 'python_config.sh')}")
    env.make()
    env.install()

    # 复制python embed package
    os.chdir(python_dir)
    for file in os.listdir("."):
        if file.startswith("python"):
            shutil.copyfile(os.path.join(python_dir, file), os.path.join(env.bin_dir, file))

    # 打包工具链
    env.package()

if __name__ == "__main__":
    build()
