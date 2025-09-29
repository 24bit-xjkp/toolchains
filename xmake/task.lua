task("llvm-profdata", function()
    on_run(function()
        import("core.base.option")
        import("core.project.config")
        import("lib.detect.find_program")
        config.load()

        local target = import("utility.utility").check_target_for_coverage()
        local target_name = target:name()
        -- 查找 llvm-profdata 工具
        local llvm_profdata = find_program("llvm-profdata")
        assert(llvm_profdata, "llvm-profdata not found!")
        -- 获取输出文件名称，默认是 <target>.profdata
        local profdata = option.get("profdata") or (target_name .. ".profdata")
        -- 进入目标所在目录
        os.cd(target:targetdir())
        -- 查找所有的 profraw 文件
        local files = os.files(target_name .. "*.profraw")
        assert(#files ~= 0, [[Target "%s" has no profraw files!]], target_name)
        local args = { "merge", table.unpack(files), "-o", profdata }
        if option.get("sparse") then
            table.insert(args, "-sparse")
        end
        -- 合并所有的 profraw 文件到 profdata 文件
        os.vrunv(llvm_profdata, args)
    end)
    set_category("plugin")
    set_menu {
        usage = "xmake llvm-profdata [option]",
        description = "Merge profraw files to profdata file by llvm-profdata",
        options = {
            { nil, "sparse",   "kv", true, "Enable sparse profraw files." },
            { nil, "profdata", "kv", nil,  "Set the output profdata file name. Default is <target>.profdata" },
            { nil, "target",   "v",  nil,  "Set the target." },
        }
    }
end)

task("llvm-cov", function()
    on_run(function()
        import("core.base.option")
        import("core.project.config")
        import("lib.detect.find_program")
        import("utility.utility")
        config.load()

        local target = utility.check_target_for_coverage()
        local target_name = target:name()
        -- 查找 llvm-cov 工具
        local llvm_cov = find_program("llvm-cov")
        assert(llvm_cov, "llvm-cov not found!")
        local task = option.get("task")
        assert(table.contains({ "export", "report", "show" }, task), [[Task must be one of "export", "report", "show"!]])
        local default_format
        if task == "show" then
            default_format = "html"
        elseif task == "export" then
            default_format = "lcov"
        elseif task == "report" then
            default_format = "text"
        end
        local format = option.get("format") or default_format
        local target_file = path.filename(target:targetfile())
        local output_dir = target_name .. "_coverage"
        local output_path = option.get("output") or (task == "show" and output_dir or path.join(output_dir, "lcov.info"))
        local exec_target = utility.check_target_for_coverage("exec", false)
        local exec_name = exec_target and exec_target:name()
        local profdata_option = option.get("profdata")
        local profdata = profdata_option or (exec_name and (exec_name .. ".profdata") or (target_name .. ".profdata"))
        local args = { task, target_file, "-instr-profile=" .. profdata, "-format=" .. format }
        -- 启用 MC/DC 覆盖率
        local mcdc_flag = task ~= "export" and "-show-mcdc" or nil
        if option.get("mcdc") and mcdc_flag then
            table.insert(args, mcdc_flag)
        end
        if task == "show" then
            -- 设置输出路径
            table.insert(args, "-output-dir=" .. output_path)
            if option.get("branch") then
                table.insert(args, "--show-branches=count")
            end
            if option.get("expansion") then
                table.insert(args, "--show-expansions")
            end
        end
        -- 进入目标所在目录
        os.cd(target:targetdir())
        -- 获取输出文件名称，默认是 <target>.profdata
        assert(os.isfile(profdata), [[Profdata file "%s" not found!]], profdata)
        -- 执行 llvm-cov 工具
        if task ~= "export" then
            os.execv(llvm_cov, args)
        else
            if not os.isdir(output_dir) then
                os.mkdir(output_dir)
            end
            local outdata, errdata = os.iorunv(llvm_cov, args)
            if errdata ~= "" then
                raise(errdata)
                return
            end
            io.writefile(output_path, outdata)
        end
    end)
    set_category("plugin")
    set_menu {
        usage = "xmake llvm-cov [option]",
        description = "Show code coverage by llvm-cov",
        options = {
            { "t", "task", "v", nil, "Set the task name.",
                "    - export",
                "    - report",
                "    - show", },
            { "e", "exec",      "kv", nil,  "Set the executable target name. This is useful when generate report for a shared target." },
            { nil, "profdata",  "kv", nil,  [[Set the input profdata file name. Default is <target>.profdata or <exec>.profdata if "exec" is set.]] },
            { nil, "mcdc",      "kv", true, "Enable MC/DC coverage." },
            { nil, "branch",    "kv", true, "Enable branch coverage." },
            { nil, "expansion", "kv", true, "Enable macro expansion coverage." },
            { "f", "format", "kv", nil, [[Set the output format. Default is "html" for "show" task, "lcov" for "export" task and "text" for "report" task.]],
                "    - html",
                "    - lcov",
                "    - text", },
            { "o", "output", "kv", nil, [[Set the output path. Default is <target>_coverage directory for "show" task and <target>_coverage/lcov.info for "export" task.]] },
            { nil, "target", "v",  nil, "Set the target." },
        }
    }
end)

task("genhtml", function()
    on_run(function()
        import("core.base.option")
        import("core.project.config")
        import("lib.detect.find_program")
        import("utility.utility")
        config.load()

        local target = utility.check_target_for_coverage()
        local target_name = target:name()
        -- 查找 genhtml 工具
        local genhtml = find_program("genhtml")
        assert(genhtml, "genhtml not found!")
        local coverage_dir = target_name .. "_coverage"
        local output_dir = option.get("output") or path.join(coverage_dir, "coverage_html")
        local lcov_path = path.join(coverage_dir, option.get("lcov-file"))
        -- 进入目标所在目录
        os.cd(target:targetdir())
        assert(os.isfile(lcov_path), [[Lcov file "%s" not found!]], lcov_path)
        local args = { lcov_path, "-o", output_dir }
        -- 忽略错误
        local ignore_errors = option.get("ignore-errors")
        if ignore_errors then
            table.join2(args, { "--ignore-errors", ignore_errors })
        end
        -- 执行 genhtml 工具
        os.execv(genhtml, args)
    end)
    set_category("plugin")
    set_menu {
        usage = "xmake genhtml [option]",
        description = "Generate code coverage report by genhtml.",
        options = {
            { "o", "output",        "kv", nil,         [[Set the output directory. Default is <target>_coverage/coverage_html directory.]] },
            { "f", "lcov-file",     "kv", "lcov.info", [[Set the input lcov file name. Default is lcov.info]] },
            { nil, "ignore-errors", "kv", nil,         "Specify errors and warnings to ignore." },
            { nil, "target",        "v",  nil,         "Set the target." },
        }
    }
end)

task("coverage_clean", function()
    on_run(function()
        import("core.base.option")
        import("core.project.config")
        import("core.project.project")
        import("lib.detect.find_program")
        config.load()

        local targets = {}
        local targets_name = option.get("targets")
        if targets_name then
            for _, target_name in ipairs(targets_name) do
                local target = project.target(target_name)
                assert(target, "Target %s not found!", target_name)
                table.insert(targets, target)
            end
        else
            for _, target in pairs(project.targets()) do
                table.insert(targets, target)
            end
        end

        for _, target in ipairs(targets) do
            local target_dir = target:targetdir()
            local target_name = target:name()
            local coverage_dir = target_name .. "_coverage"
            os.tryrm(path.join(target_dir, target_name .. "*.profraw"))
            os.tryrm(path.join(target_dir, target_name .. "*.profdata"))
            os.tryrm(path.join(target_dir, coverage_dir))
        end
    end)
    set_category("plugin")
    set_menu {
        usage = "xmake coverage_clean [option]",
        description = "Clean code coverage information.",
        options = {
            { nil, "targets", "vs", nil, "Set the targets." },
        }
    }
end)
