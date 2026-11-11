# Image features package

__all__ = ["GeminiWatermarkRemover"]


def __getattr__(name):
    if name == "GeminiWatermarkRemover":
        from .gemini_watermark_remover import GeminiWatermarkRemover

        return GeminiWatermarkRemover
    raise AttributeError(name)
