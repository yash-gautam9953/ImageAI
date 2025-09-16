# batch_processing.py
# Handles batch image upload, compression, and ZIP output

import os
from PIL import Image
from io import BytesIO
import zipfile
import magic
import fitz

def find_best_quality_buffer(img_object, target_size_kb):
    best_buffer = None
    best_quality = 0
    smallest_diff = float('inf')
    for quality in range(95, 0, -1):
        buffer = BytesIO()
        img_object.save(buffer, format='JPEG', quality=quality, optimize=True)
        current_size_kb = buffer.tell() / 1024
        diff = abs(target_size_kb - current_size_kb)
        if diff <= smallest_diff:
            smallest_diff = diff
            best_buffer = buffer
            best_quality = quality
        elif current_size_kb < target_size_kb:
            break
    best_buffer.seek(0)
    return best_buffer, best_quality

def process_batch_images(files, prompt, force):
    # Parse prompt for target size
    import re
    size_match = re.search(r'(\d+)\s*kb', prompt, re.IGNORECASE)
    if not size_match:
        return None, 'Prompt me size (KB me) nahi mila.'
    target_size_kb = int(size_match.group(1))

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_storage in files:
            filename = file_storage.filename
            try:
                # Save to temp
                temp_path = f"/tmp/{filename}"
                file_storage.save(temp_path)
                file_type = magic.from_file(temp_path, mime=True)
                img = None
                if file_type == 'application/pdf':
                    doc = fitz.open(temp_path)
                    if doc.get_page_images(0):
                        xref = doc.get_page_images(0)[0][0]
                        pix = fitz.Pixmap(doc, xref)
                        img = Image.open(BytesIO(pix.tobytes()))
                        doc.close()
                    else:
                        continue
                elif file_type.startswith('image/'):
                    img = Image.open(temp_path)
                else:
                    continue
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                best_buffer, final_quality = find_best_quality_buffer(img, target_size_kb)
                # Pad if needed
                current_size_kb = len(best_buffer.getvalue()) / 1024
                if current_size_kb < target_size_kb:
                    padding_size = int((target_size_kb - current_size_kb) * 1024)
                    best_buffer.seek(0, 2)
                    best_buffer.write(b'\0' * padding_size)
                best_buffer.seek(0)
                out_name = f"compressed_{os.path.splitext(filename)[0]}.jpeg"
                zip_file.writestr(out_name, best_buffer.getvalue())
                os.remove(temp_path)
            except Exception as e:
                continue
    zip_buffer.seek(0)
    return zip_buffer, None
