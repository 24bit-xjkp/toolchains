import("core.cache.detectcache")

-- @brief 判断工具链是否是clang
-- @return boolean 是否是clang工具链
function _is_clang()
    return string.find(get_config("toolchain") or "", "clang", 1, true) ~= nil
end

-- 本模块使用的缓存键
local cache_key = "toolchain.utility"

-- @brief 获取缓存信息
-- @return table 缓存信息表
function _get_cache()
    local cache_info = detectcache:get(cache_key)
    if not cache_info then
        cache_info = {}
        detectcache:set(cache_key, cache_info)
    end
    return cache_info
end

-- @brief 更新缓存信息
-- @param cache_info 要保存的缓存信息
function _update_cache(cache_info)
    detectcache:set(cache_key, cache_info)
    detectcache:save()
end

-- @brief 根据选项或探测结果获取sysroot选项列表
-- @return {flag, option}/nil 选项列表
function get_sysroot_option()
    local cache_info = _get_cache()
    -- sysroot缓存
    local sysroot = cache_info["sysroot"]
    -- 根据sysroot获取选项列表
    local function get_option_list()
        local sysroot_option = "--sysroot=" .. sysroot
        -- 判断是不是libc++
        local is_libcxx = (get_config("runtimes") or ""):startswith("c++")
        local libcxx_option = is_libcxx and "-isystem" .. path.join(sysroot, "include", "c++", "v1") or nil
        return { cxflags = { sysroot_option, libcxx_option }, ldflags = sysroot_option, shflags = sysroot_option }
    end
    if sysroot == "" then
        return nil                      -- 已经探测过，无sysroot可用
    elseif sysroot then
        return get_option_list(sysroot) -- 已经探测过，使用缓存的sysroot
    end

    -- 检查给定sysroot或者自动探测sysroot
    sysroot = get_config("sysroot")
    sysroot = sysroot ~= "" and sysroot or nil
    if sysroot then         -- 有指定sysroot则检查合法性
        assert(os.isdir(sysroot), string.format([[The sysroot "%s" is not a directory.]], sysroot))
    elseif _is_clang() then -- 若使用clang工具链且未指定sysroot则尝试自动探测
        local bin_dir = get_config("bin") or try { function() return os.iorunv("llvm-config", { "--bindir" }) end }
        if bin_dir then
            local prefix = path.directory(bin_dir)
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
    _update_cache(cache_info)

    if sysroot then
        return get_option_list(sysroot)
    else
        cprint("detecting for sysroot ... ${color.failure}no")
        return nil
    end
end

-- @brief 获取march选项
-- @param target 目标平台
-- @param toolchain 工具链类型
-- @note 在target和toolchain存在时才检查选项合法性
-- @return string/nil march选项
function get_march_option(target, toolchain)
    local cache_info = _get_cache()
    local option = cache_info["march"]
    if option == "" then
        return nil    -- 已经探测过，-march不受支持
    elseif option then
        return option -- 已经探测过，支持-march选项
    end

    -- 探测march是否受支持
    local arch = get_config("march")
    if arch ~= "no" then
        option = { "-march=" .. arch }
        -- 在target和toolchain存在时才检查选项合法性
        if target and toolchain then
            import("core.tool.compiler")
            if toolchain == "clang" and target ~= "native" then
                table.insert(option, "--target=" .. target)
            end
            local support = compiler.has_flags("cxx", table.concat(option, " "))
            local message = "checking for march ... "
            cprint(message .. (support and "${color.success}" or "${color.failure}") .. arch)
            if not support then
                if arch == "native" then
                    cprint(
                        [[${color.warning}The toolchain doesn't support the arch "native". No "-march" option will be set.]])
                else
                    raise(string.format([[The toolchain doesn't support the arch "%s"]], arch))
                end
            end
        end
        option = option[1]
    else
        option = ""
    end

    -- 更新缓存
    cache_info["march"] = option
    _update_cache(cache_info)
    return option
end

-- @brief 获取rtlib选项
-- @return string/nil rtlib选项
function get_rtlib_option()
    local config = get_config("rtlib")
    return (_is_clang() and config ~= "default") and "-rtlib=" .. config or nil
end

-- @brief 获取unwindlib选项
-- @return string/nil unwindlib选项
function get_unwindlib_option()
    local config = get_config("unwindlib")
    local force = config:startswith("force")
    local lib = force and string.sub(config, 7, #config) or config
    local option = config ~= "default" and "-unwindlib=" .. lib or nil
    return (_is_clang() and (force or get_config("rtlib") == "compiler-rt")) and option or nil
end

-- @brief 将mode映射为cmake风格
-- @param mode xmake风格编译模式
-- @return string/nil cmake风格编译模式
function get_cmake_mode(mode)
    local table = { debug = "Debug", release = "Release", minsizerel = "MinSizeRel", releasedbg = "RelWithDebInfo" }
    return table[mode]
end
