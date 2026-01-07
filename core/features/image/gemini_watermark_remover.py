import os
import numpy as np
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal
from core.utils.resource_path import get_resource_path

# Constants
ALPHA_THRESHOLD = 0.002  # Ignore very small alpha values (noise)
MAX_ALPHA = 0.99         # Avoid division by near-zero values
LOGO_VALUE = 255.0       # Color value for white watermark

class GeminiWatermarkRemover(QObject):
    finished = pyqtSignal(bool, str)  # success, message/output_path
    log = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.bg48_path = get_resource_path("assets/watermark/bg_48.png")
        self.bg96_path = get_resource_path("assets/watermark/bg_96.png")
        self.alpha_maps = {}  # Cache alpha maps
        
    def _load_bg_image(self, size: int) -> Image.Image:
        """Load background image for specific size"""
        path = self.bg48_path if size == 48 else self.bg96_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Watermark background resource not found: {path}")
        return Image.open(path).convert('RGB')
        
    def detect_watermark_config(self, width: int, height: int) -> dict:
        """Detect watermark configuration based on image size"""
        # Gemini's watermark rules:
        # If both image width and height are greater than 1024, use 96×96 watermark
        # Otherwise, use 48×48 watermark
        if width > 1024 and height > 1024:
            return {
                "logoSize": 96,
                "marginRight": 64,
                "marginBottom": 64
            }
        else:
            return {
                "logoSize": 48,
                "marginRight": 32,
                "marginBottom": 32
            }
            
    def calculate_alpha_map(self, bg_image: Image.Image) -> np.ndarray:
        """Calculate alpha map from background image"""
        # Convert to numpy array
        img_array = np.array(bg_image, dtype=np.float32)
        
        # Calculate max channel value and normalize to [0, 1]
        # alphaMap[i] = max(r, g, b) / 255.0
        alpha_map = np.max(img_array, axis=2) / 255.0
        
        return alpha_map
        
    def get_alpha_map(self, size: int) -> np.ndarray:
        """Get or calculate alpha map for specific size"""
        if size in self.alpha_maps:
            return self.alpha_maps[size]
            
        bg_image = self._load_bg_image(size)
        alpha_map = self.calculate_alpha_map(bg_image)
        self.alpha_maps[size] = alpha_map
        return alpha_map
        
    def calculate_watermark_position(self, width: int, height: int, config: dict) -> dict:
        """Calculate watermark position"""
        logo_size = config["logoSize"]
        margin_right = config["marginRight"]
        margin_bottom = config["marginBottom"]
        
        return {
            "x": width - margin_right - logo_size,
            "y": height - margin_bottom - logo_size,
            "width": logo_size,
            "height": logo_size
        }
        
    def remove_watermark(self, image_data: np.ndarray, alpha_map: np.ndarray, position: dict) -> np.ndarray:
        """Remove watermark using reverse alpha blending"""
        x = position["x"]
        y = position["y"]
        w = position["width"]
        h = position["height"]
        
        # Extract watermark region
        region = image_data[y:y+h, x:x+w].astype(np.float32)
        
        # Prepare alpha map (broadcast to match channels if needed)
        # alpha_map shape: (h, w), region shape: (h, w, 3) or (h, w, 4)
        alpha = alpha_map.copy()
        
        # Create masks
        # Skip very small alpha values (noise)
        mask_threshold = alpha >= ALPHA_THRESHOLD
        
        # Limit alpha value to avoid division by near-zero
        alpha = np.minimum(alpha, MAX_ALPHA)
        one_minus_alpha = 1.0 - alpha
        
        # Expand dims for broadcasting
        alpha_expanded = alpha[:, :, np.newaxis]
        one_minus_alpha_expanded = one_minus_alpha[:, :, np.newaxis]
        
        # Process RGB channels only
        for c in range(3):
            # Reverse alpha blending formula:
            # original = (watermarked - alpha * logo) / (1 - alpha)
            original = (region[:, :, c] - alpha * LOGO_VALUE) / one_minus_alpha
            
            # Apply only where alpha >= threshold
            # Use np.where to update only necessary pixels
            region[:, :, c] = np.where(
                mask_threshold,
                np.clip(original, 0, 255),  # Clip to valid range
                region[:, :, c]
            )
            
        # Update original image data
        image_data[y:y+h, x:x+w] = region.astype(np.uint8)
        
        return image_data

    def process_image_data(self, image: Image.Image) -> Image.Image:
        """Process PIL Image object and return a new Image object (for preview)"""
        # Convert to RGBA for processing
        img_rgba = image.convert("RGBA")
        width, height = img_rgba.size
        
        # Detect config
        config = self.detect_watermark_config(width, height)
        position = self.calculate_watermark_position(width, height, config)
        
        # Get alpha map
        alpha_map = self.get_alpha_map(config["logoSize"])
        
        # Convert to numpy array
        image_data = np.array(img_rgba)
        
        # Remove watermark
        processed_data = self.remove_watermark(image_data, alpha_map, position)
        
        # Convert back to PIL Image
        return Image.fromarray(processed_data)

    def process_image(self, input_path: str, output_path: str = None) -> bool:
        """Process image file"""
        try:
            self.log.emit(f"Processing: {os.path.basename(input_path)}")
            
            with Image.open(input_path) as img:
                processed_img = self.process_image_data(img)
                
                # Determine output path
                if not output_path:
                    dir_name = os.path.dirname(input_path)
                    file_name = os.path.basename(input_path)
                    name, ext = os.path.splitext(file_name)
                    output_path = os.path.join(dir_name, f"{name}_clean{ext}")
                
                # Create output directory if needed
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save result
                # Preserve format specific options if possible, but default to simple save
                save_kwargs = {}
                if img.format == 'JPEG':
                    save_kwargs['quality'] = 95
                    save_kwargs['subsampling'] = 0
                
                # Convert back to original mode if it wasn't RGBA
                if img.mode != 'RGBA' and processed_img.mode == 'RGBA':
                    if img.mode == 'RGB':
                        # Compose with white background if removing alpha
                        bg = Image.new('RGB', processed_img.size, (255, 255, 255))
                        bg.paste(processed_img, mask=processed_img.split()[3])
                        processed_img = bg
                    else:
                        processed_img = processed_img.convert(img.mode)
                        
                processed_img.save(output_path, format=img.format, **save_kwargs)
                
            self.log.emit(f"Successfully processed: {os.path.basename(output_path)}")
            self.finished.emit(True, output_path)
            return True
            
        except Exception as e:
            error_msg = f"Failed to process {os.path.basename(input_path)}: {str(e)}"
            self.log.emit(error_msg)
            self.finished.emit(False, error_msg)
            return False