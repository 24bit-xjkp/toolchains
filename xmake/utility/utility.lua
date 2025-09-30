import("common")

---根据arch和plat推导target和modifier
---@param target string @目标平台
---@param toolchain string @工具链名称
---@return string @目标平台
---@return modifier_t @调整函数
function get_target_modifier(target, toolchain)
    ---@type modifier_table_t
    local target_list = import("target", { anonymous = true }).get_target_list()
    if target ~= "target" then
        return target, target_list[target]
    end

    ---@type table<string, any>
    local cache_info = common.get_cache()
    local modifier
    ---@type string?, modifier_t?
    target, modifier = table.unpack(cache_info["target"] or {})
    if target and modifier then -- 已经探测过，直接返回target和modifier
        return target, modifier
    end

    ---@type string
    local origin_arch = get_config("arch")
    ---@type string
    local origin_plat = get_config("plat")
    ---@type string
    local target_os = get_config("target_os") or "none"
    local message = [[Unsupported %s "%s". Please select a specific toolchain.]]

    ---将xmake风格arch映射为triplet风格
    ---@type map_t
    local arch_table = {
        x86 = "i686",
        i386 = "i686",
        i686 = "i686",
        x64 = "x86_64",
        x86_64 = "x86_64",
        loong64 = "loongarch64",
        riscv64 = "riscv64",
        arm = "arm",
        armv7 = "arm",
        armv7s = "arm",
        ["arm64-v8a"] = "aarch64",
        arm64 = "aarch64",
        arm64ec = "aarch64"
    }
    ---@type string?
    local arch = arch_table[origin_arch]
    assert(arch, format(message, "arch", origin_arch))

    if origin_plat == "windows" and toolchain == "gcc" then
        origin_plat = "mingw" -- gcc不支持msvc目标，但clang支持
    end
    ---@type map_t
    local plat_table = {
        mingw = "w64",
        msys = "w64",
        linux = "linux",
        windows = "windows",
        macosx = "apple",
        cross = target_os
    }
    ---@type string?
    local plat = plat_table[origin_plat]
    assert(plat, format(message, "plat", origin_plat))

    ---@type map_t
    local x86_abi_table = {
        windows = "msvc",
        w64 = "mingw32",
        linux = "gnu",
        none = "elf"
    }
    ---@type map_t
    local linux_abi_table = { linux = "gnu" }
    ---@type table<string, map_t>
    local abi_table = {
        i686 = x86_abi_table,
        x86_64 = x86_abi_table,
        arm = {
            linux = "gnueabihf",
            none = "eabi"
        },
        aarch64 = {
            linux = "gnu",
            apple = "darwin24"
        },
        riscv64 = linux_abi_table,
        loongarch64 = linux_abi_table
    }
    ---@type string
    local abi = (abi_table[arch] or {})[plat] or "unknown"

    ---@type string[]
    local field = { arch, plat, abi }
    -- 针对arch-elf的特殊处理
    if plat == "none" and abi == "elf" then
        table.remove(field, 2)
    end
    target = table.concat(field, "-")

    ---@type modifier_t?
    modifier = target_list[target]
    cprint("detecting for target .. " .. (modifier and "${color.success}" or "${color.failure}") .. target)
    assert(modifier, format(message, "target", target))

    cache_info["target"] = { target, modifier }
    common.update_cache(cache_info)

    return target, modifier
end

---根据选项或探测结果获取sysroot选项列表
---@return table<string, string>? @选项列表
function get_sysroot_option()
    ---@type table<string, any>
    local cache_info = common.get_cache()
    ---sysroot缓存
    ---@type string?
    local sysroot = cache_info["sysroot"]
    ---根据sysroot获取选项列表
    ---@return table<string, string> --选项列表
    local function get_option_list()
        local sysroot_option = "--sysroot=" .. sysroot
        return { cxflags = sysroot_option, ldflags = sysroot_option, shflags = sysroot_option }
    end
    if sysroot == "" then
        return nil               -- 已经探测过，无sysroot可用
    elseif sysroot then
        return get_option_list() -- 已经探测过，使用缓存的sysroot
    end

    -- 检查给定sysroot或者自动探测sysroot
    ---@type string?
    sysroot = get_config("sysroot")
    local detect = sysroot == "detect"
    -- sysroot不为"none"或"detect"则为指定的sysroot
    sysroot = (sysroot ~= "none" and not detect) and sysroot or nil
    -- 若使用clang工具链且未指定sysroot则尝试自动探测
    ---@type boolean
    detect = detect and common.is_clang()
    cache_info["sysroot_set_by_user"] = sysroot and true or false
    if sysroot then    -- 有指定sysroot则检查合法性
        assert(os.isdir(sysroot), string.format([[The sysroot "%s" is not a directory.]], sysroot))
    elseif detect then -- 尝试探测
        ---@type string?
        local prefix
        if get_config("bin") then
            prefix = path.join(string.trim(get_config("bin")), "..")
        else
            prefix = try { function() return os.iorunv("llvm-config", { "--prefix" }) end }
            prefix = prefix and string.trim(prefix)
        end
        if prefix then
            -- 尝试下列目录：1. prefix/sysroot 2. prefix/../sysroot 优先使用更局部的目录
            for _, v in ipairs({ "sysroot", "../sysroot" }) do
                local dir = path.join(prefix, v)
                if os.isdir(dir) then
                    sysroot = path.normalize(dir)
                    cprint("detecting for sysroot ... ${color.success}%s", sysroot)
                    break
                end
            end
        end
    end

    -- 更新缓存
    cache_info["sysroot"] = sysroot or ""
    common.update_cache(cache_info)

    if sysroot then
        return get_option_list()
    else
        if detect then
            cprint("detecting for sysroot ... ${color.failure}no")
        end
        return nil
    end
end

---获取march选项
---@param target string? @目标平台
---@param toolchain string? @工具链类型
---@note 在target和toolchain存在时才检查选项合法性
---@return string? @march选项
function get_march_option(target, toolchain)
    ---@type table<string, any>
    local cache_info = common.get_cache()
    -- 支持一个工程同时使用目标平台和本地两套工具链
    -- 目标平台为native或该工具链为host工具链时，march选项为march_host；其他平台时，march选项为march
    local is_host = target == "native" or get_config("toolchain_host") == format("%s-%s", target, toolchain)
    local march_key = is_host and "march_host" or "march"
    ---@type string?
    local option = cache_info[march_key]
    if option == "" then
        return nil    -- 已经探测过，-march不受支持
    elseif option then
        return option -- 已经探测过，支持-march选项
    end

    ---探测march是否受支持
    ---@type string
    local arch = get_config(march_key)
    if arch ~= "none" then
        local march = (arch ~= "default" and arch or "native")
        local options = { "-march=" .. march }
        -- 在target和toolchain存在时才检查选项合法性
        if target and toolchain then
            import("core.tool.compiler")
            if toolchain == "clang" and target ~= "native" then
                table.insert(options, "--target=" .. target)
            end
            ---@type boolean
            local support = compiler.has_flags("cxx", table.concat(options, " "))
            cprint("checking for %s ... %s%s", march_key, support and "${color.success}" or "${color.failure}", march)
            if not support then
                if arch ~= "default" then
                    raise(format([[The toolchain doesn't support the arch "%s"]], march))
                end
                option = ""
            else
                option = options[1]
            end
        else
            option = nil -- 未探测，设置为nil在下次进行探测
        end
    else
        option = ""
    end

    -- 更新缓存
    cache_info[march_key] = option
    common.update_cache(cache_info)
    return option
end

---获取rtlib选项
---@return string? @rtlib选项
function get_rtlib_option()
    local config = get_config("rtlib")
    return (common.is_clang() and config ~= "default") and "-rtlib=" .. config or nil
end

---获取unwindlib选项
---@return string? @unwindlib选项
function get_unwindlib_option()
    local config = get_config("unwindlib")
    local force = config:startswith("force")
    local lib = force and string.sub(config, 7, #config) or config
    local option = config ~= "default" and "-unwindlib=" .. lib or nil
    return (common.is_clang() and (force or get_config("rtlib") == "compiler-rt")) and option or nil
end

---将mode映射为cmake风格
---@param mode string @xmake风格编译模式
---@return string? @cmake风格编译模式
function get_cmake_mode(mode)
    ---@type map_t
    local table = { debug = "Debug", release = "Release", minsizerel = "MinSizeRel", releasedbg = "RelWithDebInfo" }
    return table[mode]
end

---@class check_target_for_coverage_opt_t
---@field option_name string? @选项名称，默认为target
---@field allow_kinds string[] @允许的目标类型，默认为{"binary", "shared"}
---@field is_array boolean? @是否为数组，默认为false

---检查目标是否支持覆盖率分析
---@param opt check_target_for_coverage_opt_t? @选项名称，默认为target
---@return table | table[] @目标实例
function check_target_for_coverage(opt)
    import("core.base.option")
    import("core.project.project")

    ---@type check_target_for_coverage_opt_t
    opt = opt or {}
    local option_name = opt.option_name or "target"
    local allow_kinds = opt.allow_kinds or { "binary", "shared" }
    local is_array = opt.is_array == nil and false or opt.is_array
    local len = #allow_kinds
    local message = table.concat(allow_kinds, ", ", 1, len - 1) .. ", or " .. allow_kinds[len]

    ---检查目标是否支持覆盖率分析
    ---@param target_name string? @目标名称
    ---@return table | table[] @目标实例
    local function do_check(target_name)
        local target = project.target(target_name)
        -- 从工程中查找指定目标
        assert(target, [[Target "%s" not found!]], target_name)
        local target_kind = target:targetkind()
        -- 目标应当是可执行文件或动态库
        local is_allowed = table.contains(allow_kinds, target_kind)
        assert(is_allowed, [[Target "%s" should be a %s target!]], target_name, message)
        return target
    end

    if is_array then
        ---@type string[]?
        local target_names = option.get(option_name)
        assert(target_names, "Targets not set!")
        target_names = table.unique(target_names)
        ---@type table[]
        local targets = {}
        for _, target_name in ipairs(target_names) do
            table.insert(targets, do_check(target_name))
        end
        return targets
    else
        local target_name = option.get(option_name)
        assert(target_name, "Target not set!")
        return do_check(target_name)
    end
end

---覆盖率分析任务执行成功后的回显函数
---@param output_path string @输出目录
---@param start_time number @任务开始时间
function coverage_task_echo_on_success(output_path, start_time)
    local seconds = (os.mclock() - start_time) / 1000
    cprint("${color.success}[100%%]: Output has been written to %s, spent %.3f s", output_path, seconds)
end
