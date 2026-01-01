import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    print("Testing imports...")
    try:
        import PyQt6
        print("✅ PyQt6 imported")
    except ImportError as e:
        print(f"❌ PyQt6 failed: {e}")

    try:
        import qfluentwidgets
        print("✅ qfluentwidgets imported")
    except ImportError as e:
        print(f"❌ qfluentwidgets failed: {e}")

    try:
        import comtypes
        print("✅ comtypes imported")
    except ImportError as e:
        print(f"❌ comtypes failed: {e}")

    try:
        import pypdf
        print("✅ pypdf imported")
    except ImportError as e:
        print(f"❌ pypdf failed: {e}")

    try:
        import vtracer
        print("✅ vtracer imported")
    except ImportError as e:
        print(f"❌ vtracer failed: {e}")
        
    try:
        from core.ppt_converter import PPTConverter
        from core.word_converter import WordConverter
        from core.image_vectorizer import ImageVectorizer
        print("✅ Core modules imported")
    except ImportError as e:
        print(f"❌ Core modules failed: {e}")

if __name__ == "__main__":
    test_imports()
