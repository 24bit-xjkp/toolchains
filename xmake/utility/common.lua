import("core.cache.detectcache")
---@alias map_t table<string, string>

---判断工具链是否是clang
---@return boolean --是否是clang工具链
function is_clang()
    return string.find(get_config("toolchain") or "", "clang", 1, true) ~= nil
end

---本模块使用的缓存键
local cache_key = "toolchain.utility"

---获取缓存信息
---@return table<string, any> --缓存信息表
function get_cache()
    local cache_info = detectcache:get(cache_key)
    if not cache_info then
        cache_info = {}
        detectcache:set(cache_key, cache_info)
    end
    return cache_info
end

---更新缓存信息
---@param cache_info table --要保存的缓存信息
---@return nil
function update_cache(cache_info)
    detectcache:set(cache_key, cache_info)
    detectcache:save()
end
