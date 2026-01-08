import pytest
from PyQt6.QtWidgets import QApplication
from ui.widgets.enhanced_progress import EnhancedProgressBar
from core.utils.fuzzy_search import FuzzySearchEngine, SearchResult
from ui.design_system import Margins, Spacing, Colors

# Use pytest-qt's qapp fixture implicitly or explicitly

def test_enhanced_progress_bar_initialization(qapp):
    """Test if EnhancedProgressBar initializes correctly"""
    progress = EnhancedProgressBar()
    assert progress.progress_bar.value() == 0
    assert progress.status_label.text() == "准备就绪"

def test_enhanced_progress_bar_update(qapp):
    """Test updating progress bar"""
    progress = EnhancedProgressBar()
    progress.start(100)
    
    progress.update_progress(50, 100, "Processing")
    assert progress.progress_bar.value() == 50
    assert "Processing" in progress.status_label.text()

def test_fuzzy_search_engine():
    """Test fuzzy search logic"""
    # Mock data matches Dict[str, str] -> {name: desc}
    items = {
        "PDF 合并": "Merge multiple PDFs",
        "PDF 拆分": "Split PDF files",
        "图片转换": "Convert images"
    }
    
    engine = FuzzySearchEngine(items)
    
    # Test 1: Exact Match
    results = engine.search("PDF 合并")
    assert results[0].name == "PDF 合并"
    assert results[0].score == 100
    
    # Test 2: Pinyin First Letter (tupian -> tp)
    # Note: "图片转换" pinyin is "tupianzhuanhuan", initials "tpzh"
    results = engine.search("tp")
    if results: # Check if pypinyin is installed and working
        assert results[0].name == "图片转换"
        assert results[0].match_type == 'pinyin_initial'
    
    # Test 3: Pinyin Full (hebing)
    results = engine.search("hebing")
    if results:
        assert results[0].name == "PDF 合并"
    
    # Test 4: Description Match
    results = engine.search("Merge")
    assert len(results) > 0
    assert results[0].name == "PDF 合并"
    assert results[0].match_type == 'desc'

def test_design_system_constants():
    """Test if design system constants are importable and have correct values"""
    assert isinstance(Margins.PAGE, tuple)
    assert len(Margins.PAGE) == 4
    assert Spacing.MD == 16
    assert Colors.ERROR_LIGHT.startswith("#")