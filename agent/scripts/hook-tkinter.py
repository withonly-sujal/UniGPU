# PyInstaller hook — bundle Tcl/Tk data directories
import os
import sys
import tkinter

# Get the Tcl/Tk library paths
root = tkinter.Tk()
root.withdraw()
tcl_dir = root.tk.eval('info library').replace('/', os.sep)
tk_dir = root.tk.eval('set tk_library').replace('/', os.sep)
root.destroy()

datas = []

if tcl_dir and os.path.isdir(tcl_dir):
    # Bundle tcl library → _tcl_data in the output
    for root_dir, dirs, files in os.walk(tcl_dir):
        for f in files:
            src = os.path.join(root_dir, f)
            rel = os.path.relpath(root_dir, tcl_dir)
            dst = os.path.join('_tcl_data', rel)
            datas.append((src, dst))

if tk_dir and os.path.isdir(tk_dir):
    for root_dir, dirs, files in os.walk(tk_dir):
        for f in files:
            src = os.path.join(root_dir, f)
            rel = os.path.relpath(root_dir, tk_dir)
            dst = os.path.join('_tk_data', rel)
            datas.append((src, dst))
