python
import os
import gdb
import sys

share_dir = os.path.abspath(os.path.join(sys.path[0], "../../"))
python_dir = ""
for dir in os.listdir(share_dir):
    current_dir = os.path.join(share_dir, dir, "python")
    if dir[0:3] == "gcc" and os.path.isdir(current_dir):
        python_dir = current_dir
        break
if python_dir != "":
    sys.path.insert(0, python_dir)
    from libstdcxx.v6 import register_libstdcxx_printers
    register_libstdcxx_printers(gdb.current_objfile())
else:
    print("Cannot find gcc python support because share/gcc*/python directory does not exist.")
end
