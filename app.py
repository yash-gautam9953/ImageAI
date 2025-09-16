# app.py (The Ultimate Version with Padding)

import os
import re
import magic
import fitz  # PyMuPDF
from flask import Flask, request, send_file, jsonify
from PIL import Image
from io import BytesIO
import zipfile

# --- Flask App Setup ---
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Helper Functions ---

def parse_prompt(prompt):
    """Prompt se size aur formats nikalta hai."""
    target_size_kb = None
    target_formats = []
    size_match = re.search(r'(\d+)\s*kb', prompt, re.IGNORECASE)
    if size_match:
        target_size_kb = int(size_match.group(1))
    if 'jpg' in prompt.lower() or 'jpeg' in prompt.lower():
        target_formats.append('jpeg')
    if 'png' in prompt.lower():
        target_formats.append('png')
    if 'pdf' in prompt.lower():
        target_formats.append('pdf')
    if not target_formats:
        target_formats.append('jpeg')
    return target_size_kb, list(set(target_formats))


def find_best_quality_buffer(img_object, target_size_kb):
    """
    Ek simple aur reliable linear search ka istemaal karke target size ke 
    sabse nazdeeki size ka buffer aur quality level return karta hai.
    """
    best_buffer = None
    best_quality = 0
    smallest_diff = float('inf')

    for quality in range(95, 0, -1): # Start from high quality for faster compression checks
        buffer = BytesIO()
        img_object.save(buffer, format='JPEG', quality=quality, optimize=True)
        current_size_kb = buffer.tell() / 1024
        
        diff = abs(target_size_kb - current_size_kb)
        if diff <= smallest_diff:
            smallest_diff = diff
            best_buffer = buffer
            best_quality = quality
        # For compression, if we get below the target, we can stop searching higher qualities
        elif current_size_kb < target_size_kb:
            break
            
    best_buffer.seek(0)
    return best_buffer, best_quality


# --- API Endpoint ---
@app.route('/process', methods=['POST'])
def handle_processing():
    if 'image' not in request.files: return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']; prompt = request.form.get('prompt', ''); force_compression = request.form.get('force', 'false').lower() == 'true'
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    target_size_kb, _ = parse_prompt(prompt)
    if not target_size_kb:
        return jsonify({"error": "Prompt me size (KB me) nahi mila."}), 400
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(input_path)
    base_filename = os.path.splitext(file.filename)[0]

    # --- Size Boundaries ---
    original_size_kb = os.path.getsize(input_path) / 1024
    min_allowed_kb = max(1, int(original_size_kb * 0.1))  # 10% of original, at least 1KB
    max_allowed_kb = int(original_size_kb * 2)            # 200% of original
    if target_size_kb < min_allowed_kb:
        return jsonify({
            "error": f"Requested size {target_size_kb}KB is too small. Minimum allowed is {min_allowed_kb}KB (10% of original)."
        }), 400
    if target_size_kb > max_allowed_kb:
        return jsonify({
            "error": f"Requested size {target_size_kb}KB is too large. Maximum allowed is {max_allowed_kb}KB (200% of original)."
        }), 400

    try:
        # Load the image object once
        file_type = magic.from_file(input_path, mime=True)
        img = None
        if file_type == 'application/pdf':
            doc = fitz.open(input_path)
            if doc.get_page_images(0):
                xref = doc.get_page_images(0)[0][0]
                pix = fitz.Pixmap(doc, xref)
                img = Image.open(BytesIO(pix.tobytes()))
                doc.close()
            else:
                return jsonify({"error": "No images found in the PDF file. Only image and PDF files are supported. Output will always be JPEG."}), 400
        elif file_type.startswith('image/'):
            try:
                img = Image.open(input_path)
            except Exception:
                return jsonify({"error": "File could not be opened as an image. Only image and PDF files are supported. Output will always be JPEG."}), 400
        else:
            return jsonify({"error": "Only image and PDF files are supported. Output will always be JPEG."}), 400
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")

        # --- Compression vs Extension Logic ---
        # Case 1: EXTENSION (Target is bigger than original)
        if target_size_kb > original_size_kb:
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=95, optimize=True)
            current_size_kb = len(buffer.getvalue()) / 1024
            # Add padding if needed
            if target_size_kb > current_size_kb:
                padding_size = int((target_size_kb - current_size_kb) * 1024)
                buffer.seek(0, 2)
                buffer.write(b'\0' * padding_size)
            best_buffer = buffer
            final_quality = 95
        # Case 2: COMPRESSION (Target is smaller than original)
        else:
            best_buffer, final_quality = find_best_quality_buffer(img, target_size_kb)
            current_size_kb = len(best_buffer.getvalue()) / 1024
            # Always pad to exact size if needed
            if current_size_kb < target_size_kb:
                padding_size = int((target_size_kb - current_size_kb) * 1024)
                best_buffer.seek(0, 2)
                best_buffer.write(b'\0' * padding_size)

        # --- Quality Warning Logic ---
        QUALITY_THRESHOLD = 40
        if final_quality < QUALITY_THRESHOLD and not force_compression:
            return jsonify({"status": "warning", "message": f"Warning: Image quality will be very low (Level: {final_quality}). To proceed, send request again with 'force=true'.", "quality_level": final_quality}), 400
        
        # --- Always return JPEG ---
        best_buffer.seek(0)
        output_filename = f"compressed_{base_filename}.jpeg"
        return send_file(best_buffer, as_attachment=True, download_name=output_filename, mimetype='image/jpeg')

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(input_path): os.remove(input_path)

# --- Start the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)