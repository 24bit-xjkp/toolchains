option("march")
    set_description([[Set the "-march" option for gcc and clang.]],
                    "The option is automatically added if using our toolchain option.",
                    [[    no: Don't set the "-march" option, use the default march of the toolchain.]],
                    [[    arch: Set the "-march" option as "-march=arch". Note that "arch" is any value other than "no".]])
    set_default("native")
    after_check(function (option)
        import("utility.utility")
        option:add("cxflags", utility.get_march_option())
    end)
option_end()
option("sysroot")
    set_description("Set the `--sysroot` option for gcc and clang.",
                    "The option is automatically added if using our toolchain option.",
                    [[    no: Don't set the "--sysroot" option, use the default sysroot of the toolchain.]],
                    [[    detect: Detect and set the sysroot for clang, use the default sysroot for gcc.]],
                    [[    path: Set the "--sysroot" option as "--sysroot=path". Note that "path" is an absolute path or a relative path other than "no" and "detect".]])
    set_default("detect")
    after_check(function (option)
        import("utility.utility")
        local sysroot_option = utility.get_sysroot_option()
        for flag, opt in pairs(sysroot_option) do
            option:add(flag, opt)
        end
    end)
option_end()
option("rtlib")
    set_description([[Set the "-rtlib" option for clang.]],
                    "The option is automatically added if using our toolchain option.",
                    [[    default: Don't set the "rtlib" option, use the default rtlib of clang.]],
                    [[    libgcc/compiler-rt/platform: Set the "rtlib" option.]])
    set_default("default")
    set_values("default", "libgcc", "compiler-rt", "platform")
    after_check(function (option)
        import("utility.utility")
        local rtlib_option = utility.get_rtlib_option()
        for _, flag in ipairs({"ldflags", "shflags"}) do
            option:add(flag, rtlib_option)
        end
    end)
option_end()
option("unwindlib")
    set_description([[Set the "-unwindlib" option for clang."]],
                    "The option is automatically added if using our toolchain option.",
                    [[    default: Don't set the "unwindlib" option, use the default unwindlib of clang.]],
                    [[    libgcc/libunwind/platform: Set the option "unwindlib" if rtlib is "compiler-rt".]],
                    [[    force_libgcc/force_libunwind/force_platform: Always set the "unwindlib" option.]])
    set_default("default")
    set_values("default", "libgcc", "libunwind", "platform", "force_libgcc", "force_libunwind", "force_platform")
    add_deps("rtlib")
    after_check(function (option)
        import("utility.utility")
        local unwind_option = utility.get_unwindlib_option()
        for _, flag in ipairs({"ldflags", "shflags"}) do
            option:add(flag, unwind_option)
        end
    end)
option_end()
option("debug_strip")
    set_description("Whether to strip the symbols while building with debug information.",
                    [[    no: Don't strip the symbols if possible.]],
                    [[    debug: Strip the debug symbols to a independent symbol file while keeping other symbols in the target file.]],
                    [[    all: Strip the debug symbols to a independent symbol file then strip all symbols from the target file.]])
    set_default("no")
    set_values("no", "debug", "all")
option_end()
