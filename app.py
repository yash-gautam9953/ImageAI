
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


from flask import render_template
# --- Web UI Route ---
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


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
    Linear search for the highest quality that produces a file <= target size.
    """
    best_buffer = None
    best_quality = 0
    for quality in range(95, 0, -1):
        buffer = BytesIO()
        img_object.save(buffer, format='JPEG', quality=quality, optimize=True)
        current_size_kb = buffer.tell() / 1024
        if current_size_kb <= target_size_kb:
            best_buffer = buffer
            best_quality = quality
            break  # Stop at the highest quality that fits
    if best_buffer is None:
        # If nothing fits, return the smallest possible
        buffer = BytesIO()
        img_object.save(buffer, format='JPEG', quality=1, optimize=True)
        best_buffer = buffer
        best_quality = 1
    best_buffer.seek(0)
    return best_buffer, best_quality


# --- API Endpoint ---
@app.route('/process', methods=['POST'])
def handle_processing():
    if 'image' not in request.files: return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']; prompt = request.form.get('prompt', ''); force_compression = request.form.get('force', 'false').lower() == 'true'
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    target_size_kb, target_formats = parse_prompt(prompt)
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
                raise ValueError("No images found in the PDF file.")
        else:
            img = Image.open(input_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # --- Compression vs Extension Logic ---
        # Always use JPEG as intermediate for all formats
        if target_size_kb > original_size_kb:
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=95, optimize=True)
            current_size_kb = len(buffer.getvalue()) / 1024
            # Do not pad, just return as close as possible (never above target)
            best_buffer = buffer
            final_quality = 95
        else:
            best_buffer, final_quality = find_best_quality_buffer(img, target_size_kb)
            current_size_kb = len(best_buffer.getvalue()) / 1024

        # --- Quality Warning Logic (applies to all formats) ---
        QUALITY_THRESHOLD = 40
        if final_quality < QUALITY_THRESHOLD and not force_compression:
            return jsonify({
                "status": "warning",
                "message": f"Warning: Image quality will be very low (Level: {final_quality}). To proceed, send request again with 'force=true'.",
                "quality_level": final_quality
            }), 400

        # --- File Sending Logic (with PNG/PDF warning) ---
        best_buffer.seek(0)
        warning = None
        def get_size_kb(buf):
            return len(buf.getvalue()) / 1024

        if len(target_formats) == 1:
            output_format = target_formats[0]
            output_filename = f"compressed_{base_filename}.{output_format}"
            if output_format == 'jpeg':
                # Strict: never return above target size
                if len(best_buffer.getvalue()) / 1024 > target_size_kb:
                    return jsonify({"error": "Could not compress JPEG to requested size. Try a larger value."}), 400
                return send_file(best_buffer, as_attachment=True, download_name=output_filename, mimetype='image/jpeg')
            else:
                # PNG/PDF: Try to get as close as possible, never above target if possible
                final_img = Image.open(best_buffer)
                output_buffer = BytesIO()
                # Try reducing quality for PNG if needed
                for png_quality in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]:
                    output_buffer.seek(0)
                    output_buffer.truncate(0)
                    if output_format == 'png':
                        final_img.save(output_buffer, format='PNG', optimize=True, compress_level=int((100-png_quality)/10))
                    else:
                        final_img.save(output_buffer, format=output_format)
                    actual_size_kb = get_size_kb(output_buffer)
                    if actual_size_kb <= target_size_kb:
                        break
                mimetype = f'application/{output_format}' if output_format == 'pdf' else f'image/{output_format}'
                output_buffer.seek(0)
                actual_size_kb = get_size_kb(output_buffer)
                if actual_size_kb > target_size_kb:
                    warning = f"Warning: {output_format.upper()} output size is {actual_size_kb:.2f}KB, which may not match requested {target_size_kb}KB due to format limitations."
                if final_quality < QUALITY_THRESHOLD:
                    warning = (warning or "") + f" (Low quality: {final_quality})"
                response = send_file(output_buffer, as_attachment=True, download_name=output_filename, mimetype=mimetype)
                if warning:
                    response.headers['X-Size-Warning'] = warning
                return response
        else:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                for f in target_formats:
                    filename = f"compressed_{base_filename}.{f}"
                    if f == 'jpeg':
                        zip_file.writestr(filename, best_buffer.getvalue())
                    else:
                        best_buffer.seek(0)
                        final_img = Image.open(best_buffer)
                        output_buffer = BytesIO()
                        final_img.save(output_buffer, format=f)
                        actual_size_kb = get_size_kb(output_buffer)
                        if abs(actual_size_kb - target_size_kb) > 5:
                            warning = f"Warning: {f.upper()} output size is {actual_size_kb:.2f}KB, which may not match requested {target_size_kb}KB due to format limitations."
                        if final_quality < QUALITY_THRESHOLD:
                            warning = (warning or "") + f" (Low quality: {final_quality})"
                        zip_file.writestr(filename, output_buffer.getvalue())
            zip_buffer.seek(0)
            response = send_file(zip_buffer, as_attachment=True, download_name='compressed_files.zip', mimetype='application/zip')
            if warning:
                response.headers['X-Size-Warning'] = warning
            return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

# --- Start the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)