from PIL import Image
import numpy as np

def analyze(path):
    try:
        img = Image.open(path)
        print(f"Format: {img.format}")
        print(f"Mode: {img.mode}")
        print(f"Size: {img.size}")
        
        img_array = np.array(img)
        print(f"Corner pixel (0,0): {img_array[0,0]}")
        print(f"Corner pixel (0, -1): {img_array[0,-1]}")
        print(f"Corner pixel (-1, 0): {img_array[-1,0]}")
        print(f"Corner pixel (-1, -1): {img_array[-1,-1]}")
        
        # Check if corners are white
        is_white = np.all(img_array[0,0] > 250)
        print(f"Is background likely white? {is_white}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze(r"D:\Github\python-tool\icon.png")
