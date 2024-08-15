import("core.cache.detectcache")

-- @brief 判断工具链是否是clang
-- @return boolean 是否是clang工具链
function _is_clang()
    return string.find(get_config("toolchain") or "", "clang") ~= nil
end

-- @brief 根据选项或探测结果获取sysroot选项列表
-- @return {flag, option}/{} 选项列表
function get_sysroot_option()
    local cache_key = "toolchain.utility.get_sysroot"
    local cache_info = detectcache:get(cache_key)
    if not cache_info then
        cache_info = {}
        detectcache:set(cache_key, cache_info)
    end
    -- sysroot缓存
    local sysroot_cache = cache_info["sysroot"]
    -- 通过探测获得的sysroot缓存，探测失败为"no"，未探测为nil
    local detect_sysroot_cache = cache_info["detect_sysroot"]
    -- 是否发生了更改
    local changed = false

    local sysroot = get_config("sysroot")
    sysroot = sysroot ~= "" and sysroot or nil
    -- 有指定sysroot且和缓存不一致则检查合法性
    if sysroot and sysroot ~= sysroot_cache then
        assert(os.isdir(sysroot), string.format([[The sysroot "%s" is not a directory.]], sysroot))
        changed = true
    end

    -- 若使用clang工具链且未指定sysroot则尝试自动探测
    if not sysroot and _is_clang() then
        -- 没有探测缓存则进行探测
        if not detect_sysroot_cache then
            changed = true
            local bin_dir = get_config("bin") or try {function () return os.iorunv("llvm-config", {"--bindir"}) end}
            if bin_dir then
                prefix = path.directory(bin_dir)
                -- 尝试下列目录：1. prefix/sysroot 2. prefix/../sysroot 优先使用更局部的目录
                for _, v in ipairs({"sysroot", "../sysroot"}) do
                    local dir = path.join(prefix, v)
                    if os.isdir(dir) then
                        sysroot = dir
                        detect_sysroot_cache = sysroot
                        cprint("detecting for sysroot ... ${color.success}%s", sysroot)
                        break
                    end
                end
            end

            if not sysroot then
                detect_sysroot_cache = "no"
                cprint("detecting for sysroot ... ${color.failure}not found")
            end
        -- 有缓存直接用缓存
        else
            sysroot = detect_sysroot_cache ~= "no" and detect_sysroot_cache or nil
            changed = sysroot ~= sysroot_cache
        end
    end

    -- 更新缓存
    if changed then
        cache_info["sysroot"] = sysroot
        cache_info["detect_sysroot"] = detect_sysroot_cache
        detectcache:set(cache_key, cache_info)
        detectcache:save()
    end

    if sysroot then
        local sysroot_option = "--sysroot="..sysroot
        -- 判断是不是libc++
        local is_libcxx = (get_config("runtimes") or ""):startswith("c++")
        local libcxx_option = is_libcxx and "-isystem"..path.join(sysroot, "include", "c++", "v1") or nil
        return {cxflags = {sysroot_option, libcxx_option}, ldflags = sysroot_option, shflags = sysroot_option}
    else
        return {}
    end
end

-- @brief 获取march选项
-- @param target 目标平台
-- @param toolchain 工具链类型
-- @note 在target和toolchain存在时才检查选项合法性
-- @return string/nil march选项
function get_march_option(target, toolchain)
    local arch = get_config("march")
    if arch ~= "no" then
        local option = {"-march="..arch}
        -- 在target和toolchain存在时才检查选项合法性
        if target and toolchain then
            import("core.tool.compiler")
            if toolchain == "clang" and target ~= "native" then
                table.insert(option, "--target="..target)
            end
            local support = compiler.has_flags("cxx", table.concat(option, " "))
            local message = "checking for march ... "
            cprint(message..(support and "${color.success}" or "${color.failure}")..arch)
            if not support then
                if arch == "native" then
                    cprint([[${color.warning}The toolchain doesn't support the arch "native". No "-march" option will be set.]])
                else
                    raise(string.format([[The toolchain doesn't support the arch "%s"]], arch))
                end
            end
        end
        return option[1]
    else
        return nil
    end
end

-- @brief 获取rtlib选项
-- @return string/nil rtlib选项
function get_rtlib_option()
    local config = get_config("rtlib")
    return (_is_clang() and config ~= "default") and "-rtlib="..config or nil
end

-- @brief 获取unwindlib选项
-- @return string/nil unwindlib选项
function get_unwindlib_option()
    local config = get_config("unwindlib")
    local force = config:startswith("force")
    local lib = force and string.sub(config, 7, #config) or config
    local option = config ~= "default" and "-unwindlib="..lib or nil
    return (_is_clang() and (force or get_config("rtlib") == "compiler-rt")) and option or nil
end

-- @brief 将mode映射为cmake风格
-- @param mode xmake风格编译模式
-- @return string/nil cmake风格编译模式
function get_cmake_mode(mode)
    local table = {debug = "Debug", release = "Release", minsizerel = "MinSizeRel", releasedbg = "RelWithDebInfo"}
    return table[mode]
end
