import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    print("Testing imports...")
    try:
        import PyQt6
        print("[OK] PyQt6 imported")
    except ImportError as e:
        print(f"[FAIL] PyQt6 failed: {e}")

    try:
        import qfluentwidgets
        print("[OK] qfluentwidgets imported")
    except ImportError as e:
        print(f"[FAIL] qfluentwidgets failed: {e}")

    try:
        import comtypes
        print("[OK] comtypes imported")
    except ImportError as e:
        print(f"[FAIL] comtypes failed: {e}")

    try:
        import pypdf
        print("[OK] pypdf imported")
    except ImportError as e:
        print(f"[FAIL] pypdf failed: {e}")

    try:
        import vtracer
        print("[OK] vtracer imported")
    except ImportError as e:
        print(f"[FAIL] vtracer failed: {e}")
        
    try:
        from core.engines.office import WordEngine, PowerPointEngine
        from core.features.image.image_vectorizer import ImageVectorizer
        print("[OK] Core modules imported")
    except ImportError as e:
        print(f"[FAIL] Core modules failed: {e}")

if __name__ == "__main__":
    test_imports()
