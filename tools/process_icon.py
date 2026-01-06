import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from rembg import remove, new_session
from scipy.ndimage import label

def process_image(input_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Processing: {input_path}")
    
    # 1. Read Original Image
    try:
        original = Image.open(input_path).convert("RGBA")
    except Exception as e:
        print(f"Error reading image: {e}")
        return

    # 2. Remove Background using rembg (AI)
    print("Removing background (AI - lightweight model)...")
    try:
        # Use u2netp (lightweight model ~4MB) to avoid timeout
        session = new_session("u2netp")
        no_bg = remove(original, session=session)
    except Exception as e:
        print(f"rembg failed: {e}")
        return
    
    # 3. Filter connected components to remove star (Keep largest component)
    print("Removing clutter (star)...")
    alpha = np.array(no_bg.split()[-1])
    # Binarize
    mask = alpha > 10
    
    # Label connected components
    labeled_array, num_features = label(mask)
    
    if num_features > 1:
        # Find the largest component (assuming it's the toolbox)
        sizes = [np.sum(labeled_array == i) for i in range(1, num_features + 1)]
        max_label = np.argmax(sizes) + 1
        print(f"Found {num_features} components. Keeping component {max_label} with size {sizes[max_label-1]}")
        
        # Create mask for the largest component
        clean_mask = (labeled_array == max_label).astype(np.uint8) * 255
        clean_mask_img = Image.fromarray(clean_mask, mode='L')
        
        # Apply new mask to alpha channel
        clean_no_bg = no_bg.copy()
        # We need to preserve RGB channels but update Alpha
        r, g, b, a = clean_no_bg.split()
        # Combine original alpha with mask to ensure we don't add opacity where there was none
        # But here clean_mask effectively selects the object.
        clean_no_bg.putalpha(clean_mask_img)
        
        # Crop to bbox
        bbox = clean_no_bg.getbbox()
        if bbox:
            clean_subject = clean_no_bg.crop(bbox)
        else:
            clean_subject = clean_no_bg
    else:
        print("Only one component found.")
        clean_subject = no_bg
        bbox = clean_subject.getbbox()
        if bbox:
            clean_subject = clean_subject.crop(bbox)

    # 4. Generate Version A: With Background (Reconstructed)
    # Get subject dimensions
    w, h = clean_subject.size
    max_dim = max(w, h)
    
    # Define canvas size (add padding)
    # Icon usually has some padding. Let's make the subject occupy about 70-80% of the icon
    icon_size = int(max_dim * 1.4) 
    
    # Background rectangle size
    bg_size = int(max_dim * 1.25)
    
    # Create Canvas
    version_a = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
    
    # Draw Rounded Rectangle Background (Light Grey #F0F0F0)
    bg_color = (240, 240, 240, 255)
    draw = ImageDraw.Draw(version_a)
    
    # Center background
    bg_x = (icon_size - bg_size) // 2
    bg_y = (icon_size - bg_size) // 2
    rect_xy = [bg_x, bg_y, bg_x + bg_size, bg_y + bg_size]
    radius = bg_size // 4.5  # Rounded corner radius (standard is often ~22% of size)
    
    draw.rounded_rectangle(rect_xy, radius=radius, fill=bg_color)
    
    # Center Subject on top
    subject_x = (icon_size - w) // 2
    subject_y = (icon_size - h) // 2
    version_a.alpha_composite(clean_subject, (subject_x, subject_y))

    # 5. Generate Version B: Transparent Background
    # Use smaller padding for transparent version to make icon appear larger in taskbar
    icon_size_transparent = int(max_dim * 1.1)  # Subject occupies ~91% of canvas
    version_b = Image.new("RGBA", (icon_size_transparent, icon_size_transparent), (0, 0, 0, 0))
    subject_x_transparent = (icon_size_transparent - w) // 2
    subject_y_transparent = (icon_size_transparent - h) // 2
    version_b.alpha_composite(clean_subject, (subject_x_transparent, subject_y_transparent))

    # 6. Save Outputs
    save_icons(version_a, output_dir, "icon_with_bg")
    save_icons(version_b, output_dir, "icon_transparent")
    
    print("Processing Complete!")

def save_icons(image, output_dir, prefix):
    # Required Sizes
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Save PNGs
    for size in sizes:
        resized = image.resize((size, size), Image.Resampling.LANCZOS)
        filename = f"{prefix}_{size}.png"
        resized.save(os.path.join(output_dir, filename))
    
    # Save ICO
    # For ICO, we need to ensure the image is square and high quality
    ico_path = os.path.join(output_dir, f"{prefix}.ico")
    image.save(ico_path, format='ICO', sizes=ico_sizes)
    print(f"Generated: {prefix} (PNGs + ICO)")

if __name__ == "__main__":
    # 使用相对路径，从项目根目录引用
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_file = os.path.join(project_root, "assets", "icon.png")
    output_folder = os.path.join(project_root, "assets", "processed_icons")
    process_image(input_file, output_folder)
