import os
from PIL import Image

def sanitize_path_for_ffmpeg_filter(path):
    if not path:
        return ""
    return path.replace('\\', '/').replace(':', '\\:')

def load_and_resize_image(image_path, size):
    if not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"画像のリサイズ中にエラー: {e}")
        return None