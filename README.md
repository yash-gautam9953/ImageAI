# 🖼️ PixelSqueeze
PixelSqueeze is a user-friendly web app that precisely compresses images to a specific file size. Powered by a Python & Flask backend, it lets you define your needs with a simple prompt (like "50kb jpg") and get a perfectly optimized image in seconds. 🚀

## ✨ Features
🎯 Targeted Compression: Squeezes images down to the exact file size you need in KB.

📂 Multiple Format Support: Converts images to JPG or PNG, or creates a ZIP file for both.

📄 PDF Image Extraction: Pulls the main image out of a PDF file and processes it.

✨ Modern UI: A clean, responsive interface with a drag-and-drop file uploader.

🖼️ Live Image Preview: Instantly shows a preview of your selected image.

⚠️ Quality Warning System: Warns you if compression will result in very low quality.

⏳ Dynamic Loading: A spinner provides clear feedback while the image is processing.

## 📋 Requirements
Python 3.x installed ✅

Flask, Pillow, PyMuPDF, python-magic libraries ✅

A web browser to use the app ✅

## 🚀 Setup & Run
Follow these simple steps to run the project on your local machine.

Clone the repository:

Create a virtual environment & install dependencies:

Create a requirements.txt file with this content:

Then run the installer:

Run the app:

The app will now be running at http://127.0.0.1:5000!

## 📖 How to Use
⬆️ Upload an Image: Drag & drop your file or click to select it.

✍️ Write a Prompt: Tell PixelSqueeze what you want (e.g., 100kb jpg png).

🖱️ Click "Squeeze It!": Let the backend do the heavy lifting.

📥 Download: Your processed file will be ready to download.

## 📂 Project Structure
For the Flask app to work correctly, your files should be organized like this:

## 👨‍💻 Author
Built with ❤️ & 🐍 by [Your Name]
