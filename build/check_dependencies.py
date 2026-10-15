"""
依赖清理检查脚本
检测环境中的无关依赖
"""

import subprocess
import sys

# requirements.txt 中的合法依赖
REQUIRED_PACKAGES = {
    "PyQt6", "PyQt6-Qt6", "PyQt6-sip", "PyQt6-Fluent-Widgets", "PyQt6-Frameless-Window",
    "pypdf", "python-docx", "python-pptx",
    "Pillow", "qfluentwidgets", "comtypes",
    "Markdown", "openpyxl",
    # 打包工具
    "nuitka", "zstandard", "ordered-set",
    # 系统/环境依赖 (保留以防万一)
    "pywin32", "winshell", "pyreadline3" 
}

# 允许的依赖包前缀（包括子依赖）
ALLOWED_PREFIXES = (
    "PyQt6", "qfluentwidgets", "pypdf", 
    "python-", "Pillow", "comtypes", 
    "Markdown", "openpyxl",
    "nuitka", "zstandard", "ordered-set",
    # 标准库依赖/pip工具
    "setuptools", "pip", "wheel", "packaging",
    # 子依赖
    "lxml", "et-xmlfile",  # openpyxl 依赖
    "typing", "annotated", "pydantic", # 新版库常用依赖
    "click", "colorama", # 常规CLI依赖
    "darkdetect", # qfluentwidgets 可能依赖
)

# 危险的无关依赖 (主要的大体积库)
UNWANTED_PACKAGES = {
    "jupyter", "notebook", "ipykernel",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "flask", "django", "fastapi", "uvicorn", "starlette",
    "pytest", "pytest-cov",
    "scikit-image", "onnxruntime", "rembg", "vtracer", # 图像处理大库
    "networkx", "sympy", "mpmath", "llvmlite", "numba" # 科学计算
}

def get_installed_packages():
    """获取已安装包列表"""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True, text=True
    )
    packages = []
    for line in result.stdout.strip().split("\n"):
        if "==" in line:
            name, version = line.split("==")
            packages.append((name, version))
    return packages

def check_dependencies():
    """检查依赖合法性"""
    packages = get_installed_packages()
    
    print("=" * 60)
    print("依赖检查报告")
    print("=" * 60)
    
    unwanted_found = []
    unknown_found = []
    
    for name, version in packages:
        name_lower = name.lower()
        
        # 检查是否为无关依赖
        if name_lower in UNWANTED_PACKAGES:
            unwanted_found.append((name, version))
            continue
        
        # 检查是否为已知依赖或其子依赖
        is_allowed = False
        if name_lower in {p.lower() for p in REQUIRED_PACKAGES}:
            is_allowed = True
        elif any(name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            is_allowed = True
            
        if not is_allowed:
            unknown_found.append((name, version))
    
    # 输出结果
    if unwanted_found:
        print("\n⚠️  发现无关依赖 (强烈建议卸载):")
        for name, version in unwanted_found:
            print(f"   - {name}=={version}")
            
    if unknown_found:
        print("\n❓ 发现未知依赖 (请确认是否需要，如果不需要建议卸载):")
        for name, version in unknown_found:
            print(f"   - {name}=={version}")
    
    if not unwanted_found:
        print("\n✅ 未发现主要的无关大体积依赖。")
        return True
    
    print("\n建议清理命令 (复制并运行):")
    if unwanted_found:
        names = " ".join([name for name, _ in unwanted_found])
        print(f"pip uninstall {names} -y")
    
    return False

if __name__ == "__main__":
    check_dependencies()
