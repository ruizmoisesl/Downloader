function descargar_spdl() {
    let url = document.getElementById("spotify-url").value;
    let status = document.getElementById("status");
    let link = document.getElementById("descargar-link")
    let carpeta = document.getElementById("descargas");

    if (!url) {
        status.style.display = "block";
        status.textContent = "⚠️ Enter a valid link";
        return;
    }

    status.style.display = "block";
    status.textContent = "⏳ Downloading...";
     

    fetch("/download-spdl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            status.textContent = "❌ Mistake: " + data.error;
        } else {
            status.textContent = "✅ Download completed.";
            link.href = data.file_url;
            carpeta.style.display = "flex";
            link.textContent = "⬇️ Download Song";
        }
    })
    .catch(error => {
        status.textContent = "❌ Download failed.";
        console.error(error);
    });
}

function descargar_ypdl() {
    let url = document.getElementById("ypdl-url").value;
    let status = document.getElementById("status");
    let link = document.getElementById("descargar-link")
    let carpeta = document.getElementById("descargas");

    if (!url) {
        status.style.display = "block";
        status.textContent = "⚠️ Enter a valid link";
        return;
    }

    status.style.display = "block";
    status.textContent = "⏳ Downloading...";
     

    fetch("/download-ytdl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            status.textContent = "❌ Mistake: " + data.error;
        } else {
            status.textContent = "✅ Download completed.";
            link.href = data.file_url;
            carpeta.style.display = "flex";
            link.textContent = "⬇️ Download Song";
        }
    })
    .catch(error => {
        status.textContent = "❌ Download failed.";
        console.error(error);
    });
}