import cv2
import numpy as np
from fastapi import UploadFile

def normalize_image(file: UploadFile, target_max_dimensions: int = 1024):
    try:
        contents = file.file.read()
        np_array = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if image is None:
            print("Failed to decode image")
            return None

        # Resize if max dimension is exceeded
        height, width = image.shape[:2]
        max_dimensions = max(height, width)
        if max_dimensions > target_max_dimensions:
            scale = target_max_dimensions / max_dimensions
            image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

        # Ensure array is contiguous in memory
        image = np.ascontiguousarray(image)

        if not np.isfinite(image).all():
            print("Image contains invalid values")
            return None

        return image

    except Exception as e:
        print(f"[ERROR] Exception reading image {file.filename}: {e}")
        return None