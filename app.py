import os
import re
from flask import Flask, jsonify, render_template_string, send_file

app = Flask(__name__)

LOG_CREDENCIALES = "capturas_ftp.txt"
LOG_TRAFICO_CRUDO = "contenido_trafico.txt"

# 📁 CONFIGURACIÓN DE RUTA FTP (La carpeta local donde caen o donde simulas el recibo)
# Puedes apuntar a la ruta exacta compartida o mantener los archivos de prueba en tu carpeta de hacking.
RUTA_ALMACENAMIENTO_FTP = "./" 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard MITM Avanzado - Panel de Control</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1e1e24; color: #fff; margin: 20px; }
        h1 { color: #ff5555; text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .container { display: flex; gap: 20px; justify-content: space-between; margin-bottom: 20px; }
        .panel { flex: 1; background: #2a2a35; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); display: flex; flex-direction: column; }
        .panel-full { background: #2a2a35; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        h2 { border-bottom: 1px solid #ff5555; padding-bottom: 5px; color: #ffb86c; margin-top: 0; }
        pre { background: #111; padding: 10px; border-radius: 5px; overflow-x: auto; color: #50fa7b; font-family: 'Courier New', Courier, monospace; flex-grow: 1; min-height: 200px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
        
        /* 🚨 Estilo Alerta Superior */
        .alert { background: #44475a; color: #ff5555; border: 2px solid #ff5555; padding: 15px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px; display: none; font-size: 1.2em; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.7; } 50% { opacity: 1; } 100% { opacity: 0.7; } }
        
        /* 📥 Botón Descarga */
        .btn-download { display: inline-block; background: #50fa7b; color: #111; padding: 10px 15px; border: none; border-radius: 5px; font-weight: bold; text-decoration: none; cursor: pointer; margin-top: 10px; text-align: center; transition: 0.3s; }
        .btn-download:hover { background: #8be9fd; }

        /* 🔲 MODAL ALERTA IMPACTANTE */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.8); }
        .modal-content { background-color: #282a36; margin: 15% auto; padding: 20px; border: 3px solid #ff5555; width: 40%; border-radius: 10px; text-align: center; box-shadow: 0px 0px 25px #ff5555; }
        .modal-h2 { color: #ff5555; margin-top: 0; font-size: 24px; }
        .modal-btn { background: #ff5555; color: #fff; border: none; padding: 10px 20px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-top: 15px; }
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
            <div id="meta-archivo" style="color: #8be9fd; font-weight: bold; margin-bottom: 5px;">Ningún archivo capturado aún.</div>
            <pre id="contenido-archivo">Esperando comando STOR / transferencia de datos...</pre>
            <a id="link-descarga" href="#" class="btn-download" style="display: none;">📥 Descargar Archivo Interceptado</a>
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
                
                // 1. Logs de Credenciales
                if(data.credenciales.trim().length > 0) {
                    document.getElementById('logs-credenciales').innerText = data.credenciales;
                }
                
                // 2. Tráfico Crudo 
                const crudosDiv = document.getElementById('logs-crudos');
                if(data.trafico_crudo.trim().length > 0) {
                    crudosDiv.innerText = data.trafico_crudo;
                }
                
                // 3. Control de Archivo e Intercepción Activa
                if (data.archivo_detectado) {
                    document.getElementById('alerta-archivo').style.display = 'block';
                    document.getElementById('meta-archivo').innerText = `Archivo detectado: ${data.nombre_archivo}`;
                    document.getElementById('contenido-archivo').innerText = data.contenido_archivo;
                    
                    // Configurar el botón de descarga dinámico
                    const downloadBtn = document.getElementById('link-descarga');
                    downloadBtn.href = `/api/download/${data.nombre_archivo}`;
                    downloadBtn.style.display = 'block';

                    // 💥 Lanzar Modal si es un archivo nuevo o modificado
                    if (data.nombre_archivo !== ultimoArchivoCapturado) {
                        ultimoArchivoCapturado = data.nombre_archivo;
                        mostrarModal(`Se ha interceptado una carga útil en la red local. Nombre del archivo exfiltrado: <b>${data.nombre_archivo}</b>`);
                    }
                } else {
                    document.getElementById('alerta-archivo').style.display = 'none';
                    document.getElementById('link-descarga').style.display = 'none';
                }
            } catch (err) {
                console.error("Error al conectar con el backend", err);
            }
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

def obtener_ultimo_archivo_ftp(contenido_tcpdump):
    """
    Analiza de forma inversa el contenido de tcpdump para encontrar el ÚLTIMO comando STOR 
    ejecutado por el cliente de Windows, evitando que se quede pegado en el primer intento.
    """
    matches = re.findall(r"STOR\s+([^\s\r\n]+)", contenido_tcpdump)
    if matches:
        return matches[-1] # Devolvemos siempre el ÚLTIMO comando ejecutado
    return None

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    credenciales = ""
    # 1. Leer logs de ngrep
    if os.path.exists(LOG_CREDENCIALES):
        with open(LOG_CREDENCIALES, "r", errors='ignore') as f:
            lineas = f.readlines()
            filtradas = [l for l in lineas if "USER" in l or "PASS" in l]
            credenciales = "".join(filtradas[-12:])

    # 2. Leer tráfico crudo de tcpdump
    trafico_crudo = ""
    contenido_completo_tcpdump = ""
    if os.path.exists(LOG_TRAFICO_CRUDO):
        with open(LOG_TRAFICO_CRUDO, "r", errors='ignore') as f:
            contenido_completo_tcpdump = f.read()
            lineas_crudas = contenido_completo_tcpdump.splitlines()
            trafico_crudo = "\n".join(lineas_crudas[-40:])

    # 3. Detectar el último archivo enviado basándonos en la red
    archivo_detectado = False
    nombre_archivo = ""
    contenido_archivo = ""

    ultimo_stor = obtener_ultimo_archivo_ftp(contenido_completo_tcpdump)
    
    if ultimo_stor:
        nombre_archivo = ultimo_stor
        # Buscamos si el archivo se guardó físicamente en el entorno de pruebas
        ruta_real = os.path.join(RUTA_ALMACENAMIENTO_FTP, nombre_archivo)
        
        if os.path.exists(ruta_real):
            archivo_detectado = True
            with open(ruta_real, "r", errors='ignore') as f:
                contenido_archivo = f.read()
        else:
            # Si el archivo físico no está local (porque cayó en Ubuntu), extraemos 
            # de forma limpia el payload de texto que venía después del STOR en tcpdump
            archivo_detectado = True
            partes = contenido_completo_tcpdump.split(f"STOR {nombre_archivo}")
            if len(partes) > 1:
                segmento_datos = partes[-1][:1000] # Analizamos el último bloque de datos posterior
                lineas_datos = segmento_datos.split('\n')
                texto_limpio = []
                for l in lineas_datos:
                    if not re.match(r'^\d{2}:\d{2}:\d{2}', l) and not l.startswith('E..') and len(l.strip()) > 0:
                        limpia = "".join([c for c in l if c.isprintable() or c in ['\n', '\r']])
                        limpia = limpia.replace('.', '').strip()
                        if limpia and not any(x in limpia for x in ['IP ', 'Flags', 'win', 'length', 'Transfer', 'complete', 'Ok to send']):
                            texto_clean = limpia.strip()
                            if texto_clean:
                                texto_clean_final = re.sub(r'^[a-zA-Z0-9]{1,4}\s*', '', texto_clean)
                                texto_limpio.append(texto_clean_final)
                contenido_archivo = "\n".join(texto_limpio).strip()

    return jsonify({
        "credenciales": credenciales if credenciales else "Esperando tráfico...",
        "trafico_crudo": trafico_crudo if trafico_crudo else "Monitoreando interfaz...",
        "archivo_detectado": archivo_detectado,
        "nombre_archivo": nombre_archivo,
        "contenido_archivo": contenido_archivo if contenido_archivo else "Esperando transferencia de archivos (put)..."
    })

# 📥 ENDPOINT DE DESCARGA BINARIA DIRECTA
@app.route('/api/download/<filename>')
def download_file(filename):
    ruta_archivo = os.path.join(RUTA_ALMACENAMIENTO_FTP, filename)
    if os.path.exists(ruta_archivo):
        return send_file(ruta_archivo, as_attachment=True)
    
    # Si el archivo físico reside en Ubuntu y no en Debian, creamos un archivo temporal "al vuelo"
    # con el texto exfiltrado de la red para que el profesor pueda descargarlo de todas formas
    if os.path.exists(LOG_TRAFICO_CRUDO):
        with open(LOG_TRAFICO_CRUDO, "r", errors='ignore') as f:
            contenido = f.read()
        partes = contenido.split(filename)
        if len(partes) > 1:
            with open(f"exfiltrado_{filename}", "w") as out:
                out.write(partes[-1][:500])
            return send_file(f"exfiltrado_{filename}", as_attachment=True, download_name=filename)
            
    return "Error: Archivo no disponible en los búferes de red.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)