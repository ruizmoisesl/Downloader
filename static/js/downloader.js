function descargar_spdl() {
    let url = document.getElementById("spotify-url").value;
    let status = document.getElementById("status");
    let link = document.getElementById("descargar-link");
    let carpeta = document.getElementById("descargas");

    if (!url) {
        status.style.display = "block";
        status.textContent = "⚠️ Enter a valid link";
        return;
    }

    status.style.display = "block";
    status.textContent = "⏳ Downloading...";

    // Primera llamada para iniciar la descarga
    fetch("/download-spdl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => {
        // Verificar si la respuesta es JSON (error) o un archivo
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json().then(data => {
                throw new Error(data.error || "Error desconocido");
            });
        }
        
        // Es un archivo, mostrar el enlace de descarga
        status.textContent = "✅ Download completed.";
        carpeta.style.display = "flex";
        
        // Actualizar el enlace de descarga
        link.href = "/descargar";
        link.textContent = "⬇️ Download Song";
        
        // Iniciar la descarga automáticamente
        window.location.href = "/descargar";
    })
    .catch(error => {
        status.textContent = "❌ Error: " + error.message;
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
            carpeta.style.display = "flex";
            link.textContent = "⬇️ Download Song";
        }
    })
    .catch(error => {
        status.textContent = "❌ Download failed.";
        console.error(error);
    });
}