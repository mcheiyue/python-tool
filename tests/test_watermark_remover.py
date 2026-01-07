import pytest
import numpy as np
from PIL import Image
from core.features.image.gemini_watermark_remover import GeminiWatermarkRemover

class TestGeminiWatermarkRemover:
    @pytest.fixture
    def remover(self):
        return GeminiWatermarkRemover()
        
    def test_detect_watermark_config(self, remover):
        # Small image
        config = remover.detect_watermark_config(500, 500)
        assert config["logoSize"] == 48
        assert config["marginRight"] == 32
        assert config["marginBottom"] == 32
        
        # Large image
        config = remover.detect_watermark_config(2000, 2000)
        assert config["logoSize"] == 96
        assert config["marginRight"] == 64
        assert config["marginBottom"] == 64
        
        # Mixed dimensions (width > 1024, height < 1024) -> small
        config = remover.detect_watermark_config(2000, 500)
        assert config["logoSize"] == 48
        
        # Mixed dimensions (width < 1024, height > 1024) -> small
        config = remover.detect_watermark_config(500, 2000)
        assert config["logoSize"] == 48

    def test_calculate_watermark_position(self, remover):
        config = {
            "logoSize": 48,
            "marginRight": 32,
            "marginBottom": 32
        }
        
        # 1000x1000 image
        pos = remover.calculate_watermark_position(1000, 1000, config)
        
        assert pos["width"] == 48
        assert pos["height"] == 48
        # x = 1000 - 32 - 48 = 920
        assert pos["x"] == 920
        # y = 1000 - 32 - 48 = 920
        assert pos["y"] == 920

    def test_calculate_alpha_map(self, remover):
        # Create a dummy background image (RGB)
        # 2x2 image
        data = np.array([
            [[0, 0, 0], [128, 128, 128]],
            [[255, 255, 255], [0, 255, 0]]
        ], dtype=np.uint8)
        
        bg_image = Image.fromarray(data)
        
        alpha_map = remover.calculate_alpha_map(bg_image)
        
        assert alpha_map.shape == (2, 2)
        assert alpha_map[0, 0] == 0.0          # Black -> 0
        assert np.isclose(alpha_map[0, 1], 128/255.0)  # Grey -> ~0.5
        assert alpha_map[1, 0] == 1.0          # White -> 1.0
        assert alpha_map[1, 1] == 1.0          # Green -> 1.0 (max channel is 255)

    def test_remove_watermark_logic(self, remover):
        # This tests the mathematical logic of removal
        
        # 1. Create original pixel: 100 (grey)
        original_val = 100.0
        
        # 2. Define alpha: 0.5
        alpha = 0.5
        logo_val = 255.0
        
        # 3. Calculate watermarked value
        # watermarked = alpha * logo + (1 - alpha) * original
        # watermarked = 0.5 * 255 + 0.5 * 100 = 127.5 + 50 = 177.5 -> 178
        watermarked_val = 178
        
        # 4. Create dummy data structures
        # 1x1 image region
        image_data = np.array([[[watermarked_val, watermarked_val, watermarked_val]]], dtype=np.uint8)
        
        # 1x1 alpha map
        alpha_map = np.array([[alpha]], dtype=np.float32)
        
        position = {"x": 0, "y": 0, "width": 1, "height": 1}
        
        # 5. Run removal
        result = remover.remove_watermark(image_data, alpha_map, position)
        
        # 6. Check if original value is restored
        # recovered = (178 - 0.5 * 255) / 0.5 = (178 - 127.5) / 0.5 = 50.5 / 0.5 = 101
        # Due to integer rounding during watermarking, we expect small error
        recovered_val = result[0, 0, 0]
        
        assert 99 <= recovered_val <= 102