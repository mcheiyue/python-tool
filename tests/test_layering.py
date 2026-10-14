"""
分层守护测试 (ratchet)

规则 A: core/features 禁止直接 import PyQt6（豁免清单随迁移逐行收缩）
规则 B: core/features 禁止依赖 app / ui（零容忍）

豁免机制: 每个豁免项必须仍是规则 A 的违规文件——文件去 Qt 后必须同步从清单移除，
过期豁免会使测试变红，防止清单僵尸化。
"""
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = PROJECT_ROOT / "core" / "features"

# 规则 A 豁免基线（21 文件，随迁移任务逐行删除）
QT_EXEMPT_FILES = {
    "pdf/pdf_metadata.py",                 # R3/R4 移除
    "pdf/pdf_security.py",                 # R3/R4 移除
    "pdf/pdf_page_renderer.py",            # R3/R4 移除
    "pdf/image_to_pdf_converter.py",       # R3/R4 移除
    "office/word_converter.py",            # R5 移除
    "office/libreoffice_converter.py",     # R5 移除
    "office/doc_to_docx_converter.py",     # R5 移除
    "office/ppt_image_exporter.py",        # R5 移除
    "text/markdown_converter.py",          # R6 移除
    "text/markdown_pdf_pandoc.py",         # R6 移除
    "text/code_extractor.py",              # R6 移除
    "text/txt_converter.py",               # R6 移除
    "image/image_converter.py",            # R7 移除
    "image/image_vectorizer.py",           # R7 移除
    "image/color_extractor.py",            # R7 移除
    "image/clipboard_handler.py",          # PERMANENT: QMimeData/QApplication 剪贴板桥即功能本体
}


def _iter_feature_files():
    return sorted(FEATURES_DIR.rglob("*.py"))


def _rel(path: Path) -> str:
    return path.relative_to(FEATURES_DIR).as_posix()


def _qt_direct_violations() -> set:
    """规则 A 违规: 直接 import PyQt6 的文件（相对路径集合）"""
    violations = set()
    for path in _iter_feature_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "PyQt6" for alias in node.names):
                    violations.add(_rel(path))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] == "PyQt6":
                    violations.add(_rel(path))
    return violations


def _forbidden_layer_violations() -> list:
    """规则 B 违规: features 直接依赖 app / ui"""
    violations = []
    for path in _iter_feature_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in {"app", "ui"}:
                        violations.append(f"{_rel(path)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module.split(".")[0] in {"app", "ui"}:
                    violations.append(f"{_rel(path)}: from {node.module}")
    return violations


def test_rule_a_no_new_qt_imports():
    """规则 A: 违规集必须完全被豁免清单覆盖"""
    unexpected = _qt_direct_violations() - QT_EXEMPT_FILES
    assert not unexpected, (
        "core/features 出现新的 PyQt6 直接依赖:\n"
        + "\n".join(sorted(unexpected))
        + "\n业务逻辑应零 Qt；若确属永久例外，在 QT_EXEMPT_FILES 登记并注释理由"
    )


def test_rule_a_no_stale_exemptions():
    """豁免项必须仍是违规文件——去 Qt 后须同步移除豁免，防清单僵尸化"""
    stale = QT_EXEMPT_FILES - _qt_direct_violations()
    assert not stale, (
        "以下文件已无 PyQt6 依赖，请从 QT_EXEMPT_FILES 移除:\n"
        + "\n".join(sorted(stale))
    )


def test_rule_b_no_app_ui_dependency():
    """规则 B: features 禁止依赖 app / ui（零容忍）"""
    violations = _forbidden_layer_violations()
    assert not violations, "core/features 违反依赖方向:\n" + "\n".join(sorted(violations))
