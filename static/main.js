// --- Particles.js Background ---
tsParticles.load({
  id: "particles-container",
  options: {
    fullScreen: { enable: true, zIndex: 0 },
    background: { color: "#f7fafc" },
    particles: {
      number: { value: 50 },
      color: { value: ["#4f8cff", "#1e90ff", "#a1c4fd", "#c2e9fb"] },
      shape: { type: "circle" },
      opacity: { value: 0.4, animation: { enable: true, speed: 1, minimumValue: 0.1 } },
      size: { value: { min: 1, max: 4 } },
      move: { enable: true, speed: 1.2, direction: "none", outModes: "out" },
      links: { enable: true, distance: 150, color: "#8bb6ff", opacity: 0.2, width: 1 },
    },
    interactivity: {
      events: { onHover: { enable: true, mode: "repulse" } },
      modes: { repulse: { distance: 100 } },
    },
    detectRetina: true,
  },
});

// --- Main Application Logic ---
document.addEventListener("DOMContentLoaded", function () {
  // Get all necessary DOM elements
  const modal = document.getElementById("noteModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const mainContent = document.getElementById("mainContent");
  const form = document.getElementById("uploadForm");
  const imageInput = document.getElementById("image");
  const fileDropArea = document.querySelector(".file-drop-area");
  const fileMsg = document.querySelector(".file-msg");
  const previewArea = document.getElementById("previewArea");
  const imagePreview = document.getElementById("imagePreview");
  const fileNameSpan = document.getElementById("fileName");
  const fileSizeSpan = document.getElementById("fileSize");
  const msgDiv = document.getElementById("msg");
  const downloadLink = document.getElementById("downloadLink");
  const downloadText = document.getElementById("downloadText");
  const submitButton = form.querySelector("button[type='submit']");
  const btnText = submitButton.querySelector(".btn-text");
  const spinner = submitButton.querySelector(".spinner");

  // --- Modal Logic ---
  closeModalBtn.onclick = function () {
    modal.style.display = "none";
    mainContent.style.filter = "";
    mainContent.style.pointerEvents = "";
  };

  // --- Drag & Drop Logic ---
  fileDropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileDropArea.classList.add("dragover");
  });
  fileDropArea.addEventListener("dragleave", () => {
    fileDropArea.classList.remove("dragover");
  });
  fileDropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    fileDropArea.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length) {
      imageInput.files = files;
      handleFile(files[0]);
    }
  });
  imageInput.addEventListener("change", () => {
    if (imageInput.files.length) {
      handleFile(imageInput.files[0]);
    }
  });

  // --- File Handling and Preview ---
  function handleFile(file) {
    if (!file) return;

    // Display file info
    fileNameSpan.textContent = file.name;
    let size = file.size;
    let sizeStr = size < 1024 * 1024
      ? (size / 1024).toFixed(1) + " KB"
      : (size / (1024 * 1024)).toFixed(2) + " MB";
    fileSizeSpan.textContent = sizeStr;

    // Show preview
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
      };
      reader.readAsDataURL(file);
    } else {
      // Use a generic icon for non-image files like PDFs
      imagePreview.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="%234f8cff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"%3E%3Cpath d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"%3E%3C/path%3E%3Cpolyline points="14 2 14 8 20 8"%3E%3C/polyline%3E%3C/svg%3E';
    }

    previewArea.style.display = "flex";
    fileMsg.textContent = "File selected. Choose another or process.";
  }

  // --- Form Submission Logic ---
  form.onsubmit = async (e) => {
    e.preventDefault();
    msgDiv.innerHTML = "";
    downloadLink.style.display = "none";
    
    // Show spinner and disable button
    btnText.style.display = 'none';
    spinner.style.display = 'block';
    submitButton.disabled = true;

    const formData = new FormData(form);
    try {
      const res = await fetch("/process", { method: "POST", body: formData });
      if (res.ok) {
        const warning = res.headers.get("X-Size-Warning");
        msgDiv.innerHTML = `<div class='msg ${warning ? 'warning' : 'success'}'>${warning || 'Success! Your file is ready.'}</div>`;
        const blob = await res.blob();
        let filename = "result";
        const disposition = res.headers.get("Content-Disposition");
        if (disposition && disposition.includes("filename=")) {
          filename = disposition.split("filename=")[1].replace(/['"]/g, "");
        }
        const url = URL.createObjectURL(blob);
        downloadLink.href = url;
        downloadLink.download = filename;
        downloadText.textContent = `Download: ${filename}`;
        downloadLink.style.display = "flex";
      } else {
        const data = await res.json();
        msgDiv.innerHTML = `<div class='msg error'>${data.message || data.error}</div>`;
      }
    } catch (err) {
      msgDiv.innerHTML = `<div class='msg error'>Network Error: Could not connect to server.</div>`;
    } finally {
      // Hide spinner and re-enable button
      btnText.style.display = 'block';
      spinner.style.display = 'none';
      submitButton.disabled = false;
    }
  };
});