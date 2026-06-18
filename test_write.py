import os
import sys

with open(r"c:/Users/abrah/nails_nice_py/nails_nice/nails_nice_pyy/python/Nails_Nice_py/test_output.txt", "w") as f:
    f.write(f"Cwd: {os.getcwd()}\n")
    f.write(f"Python path: {sys.executable}\n")
    f.write(f"Exists: {os.path.exists('respaldo.sql')}\n")
