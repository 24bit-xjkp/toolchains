includes("option.lua")

-- @brief 注册clang工具链
-- @parma target clang工具链目标平台
-- @parma modifier 回调函数，为target定制一些flag
function register_clang_toolchain(target, modifier)
    toolchain(target .. "-clang")
        set_kind("standalone")
        set_homepage("https://github.com/24bit-xjkp/toolchains/")
        set_description("A clang toolchain for " .. target)
        set_runtimes("c++_static", "c++_shared", "stdc++_static", "stdc++_shared")

        set_toolset("cc",      "clang")
        set_toolset("cxx",     "clang",   "clang++")
        set_toolset("ld",      "clang++", "clang")
        set_toolset("sh",      "clang++", "clang")
        set_toolset("as",      "clang")
        set_toolset("ar",      "llvm-ar")
        set_toolset("strip",   "llvm-strip")
        set_toolset("ranlib",  "llvm-ranlib")
        set_toolset("objcopy", "llvm-objcopy")
        set_toolset("mrc",     "llvm-rc")

        on_check(function (toolchain)
            return import("lib.detect.find_program")("clang")
        end)

        on_load(function (toolchain)
            import("utility")
            if toolchain:is_plat("windows") then
                toolchain:add("runtimes", "MT", "MTd", "MD", "MDd")
            end

            toolchain:add("cxflags", utility.get_march_option(target, "clang"))
            local sysroot_option = utility.get_sysroot_option()
            for flag, option in pairs(sysroot_option) do
                toolchain:add(flag, option)
            end

            local rtlib_option = utility.get_rtlib_option()
            local unwind_option = utility.get_unwindlib_option()
            for _, flag in ipairs({ "cxflags", "ldflags", "shflags" }) do
                toolchain:add(flag, target ~= "native" and "--target=" .. target or nil)
                toolchain:add(flag ~= "cxflags" and flag or nil, rtlib_option, unwind_option)
            end

            modifier(toolchain)
        end)
    toolchain_end()
end

includes("target.lua")
for target, modifier in pairs(target_list) do
    register_clang_toolchain(target, modifier)
end

-- @brief 注册gcc工具链
-- @parma target gcc工具链目标平台
-- @parma modifier 回调函数，为target定制一些flag
function register_gcc_toolchain(target, modifier)
    toolchain(target .. "-gcc")
        set_kind("standalone")
        set_homepage("https://github.com/24bit-xjkp/toolchains/")
        set_description("A gcc toolchain for " .. target)
        set_runtimes("stdc++_static", "stdc++_shared")
        local prefix = target == "native" and "" or target .. "-"

        set_toolset("cc",      prefix.."gcc")
        set_toolset("cxx",     prefix.."gcc", prefix.."g++")
        set_toolset("ld",      prefix.."g++", prefix.."gcc")
        set_toolset("sh",      prefix.."g++", prefix.."gcc")
        set_toolset("ar",      prefix.."ar")
        set_toolset("strip",   prefix.."strip")
        set_toolset("objcopy", prefix.."objcopy")
        set_toolset("ranlib",  prefix.."ranlib")
        set_toolset("as",      prefix.."gcc")

        on_check(function (toolchain)
            return import("lib.detect.find_program")(prefix .. "gcc")
        end)

        on_load(function (toolchain)
            import("utility")

            toolchain:add("cxflags", utility.get_march_option(target, "gcc"))
            local sysroot_option = utility.get_sysroot_option()
            for flag, option in pairs(sysroot_option) do
                toolchain:add(flag, option)
            end

            modifier(toolchain)
        end)
    toolchain_end()
end

for target, modifier in pairs(general_target_list) do
    register_gcc_toolchain(target, modifier)
end
