function descargar_spdl() {
    let url = document.getElementById("spotify-url").value;
    let status = document.getElementById("status");
    let link = document.getElementById("descargar-link")
    let carpeta = document.getElementById("descargas");

    if (!url) {
        status.textContent = "⚠️ Ingresa un enlace valido";
        return;
    }

    status.textContent = "⏳ Descargando...";
     

    fetch("/download-spdl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            status.textContent = "❌ Error: " + data.error;
        } else {
            status.textContent = "✅ Descarga completada.";
            link.href = data.file_url;
            carpeta.style.display = "block";
            link.textContent = "⬇️ Descargar Canción";
        }
    })
    .catch(error => {
        status.textContent = "❌ Error en la descarga.";
        console.error(error);
    });
}

function descargar_ypdl() {
    let url = document.getElementById("spotify-url").value;
    let status = document.getElementById("status");
    let link = document.getElementById("descargar-link")
    let carpeta = document.getElementById("descargas");

    if (!url) {
        status.textContent = "⚠️ Ingresa un enlace valido";
        return;
    }

    status.textContent = "⏳ Descargando...";
     

    fetch("/download-ypdl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            status.textContent = "❌ Error: " + data.error;
        } else {
            status.textContent = "✅ Descarga completada.";
            link.href = data.file_url;
            carpeta.style.display = "block";
            link.textContent = "⬇️ Descargar Canción";
        }
    })
    .catch(error => {
        status.textContent = "❌ Error en la descarga.";
        console.error(error);
    });
}