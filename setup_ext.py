"""把 backend.py 编译为 backend.pyd（Cython 二进制扩展）。
用法：python setup_ext.py build_ext --inplace
依赖：cython + Microsoft Visual C++ Build Tools 14.0+
"""
import os
import sys
import shutil

from setuptools import setup
from Cython.Build import cythonize
from Cython.Compiler import Options

# 编译选项：放弃可调试性换取更难逆向
Options.docstrings = False                  # 移除 docstring
Options.emit_code_comments = False          # 不生成代码注释
Options.embed_pos_in_docstring = False
Options.fast_fail = True

compiler_directives = {
    "language_level": "3",
    "always_allow_keywords": True,
    "binding": True,
    "embedsignature": False,
}

extensions = cythonize(
    ["backend.py"],
    compiler_directives=compiler_directives,
    nthreads=2,
    annotate=False,                          # 不生成 .html 注解（暴露源码）
)

setup(
    name="seedboxes_ext",
    ext_modules=extensions,
    zip_safe=False,
)


def _post_clean():
    """编译后清理中间产物，只留 .pyd。"""
    for ext in (".c", ".html"):
        f = f"backend{ext}"
        if os.path.isfile(f):
            os.remove(f)
    if os.path.isdir("build"):
        shutil.rmtree("build", ignore_errors=True)


if __name__ != "__main__":
    pass
elif "build_ext" in sys.argv:
    _post_clean()
