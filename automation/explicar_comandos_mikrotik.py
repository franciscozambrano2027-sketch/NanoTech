#!/usr/bin/env python3
"""
Reemplaza el texto generico repetido ('Ejecuta primero la consulta...')
en las guias mikrotik-*.html por una explicacion tecnica real de cada
comando: que hace y que deberia mostrar si todo esta bien.

Se ejecuta una sola vez sobre los archivos existentes (no es parte del
pipeline diario, porque estas paginas son guias fijas, no generadas por IA).
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Explicacion por PREFIJO de comando (se usa el mas especifico que matchee).
EXPLICACIONES = [
    ("/export terse file=", "Exporta toda la configuracion actual a un archivo de texto (.rsc) legible, que puedes descargar o leer en pantalla. Es tu respaldo \"en texto plano\" antes de tocar nada: si algo sale mal, sabes exactamente que habia antes."),
    ("/system backup save name=", "Crea un respaldo binario completo (.backup) del router, incluyendo usuarios y certificados. A diferencia del export, este archivo solo se puede restaurar en un router con el mismo modelo/arquitectura, pero recupera el equipo tal cual estaba."),
    ("/system routerboard print", "Muestra el modelo de la placa, la version de RouterBOOT y el numero de serie. Sirve para confirmar que el respaldo corresponde al equipo correcto antes de restaurar en otro router."),
    ("/import file-name=", "Aplica un archivo .rsc previamente exportado, ejecutando esos comandos como si los escribieras a mano. Se usa para restaurar una configuracion guardada; si el archivo tiene errores, RouterOS se detiene en la primera linea que falle."),
    ("/interface ethernet monitor", "Revisa el estado fisico del puerto Ethernet (enlace, velocidad, duplex) al instante, sin esperar eventos. Si ves \"status: link-ok\", el cable y el otro extremo estan bien conectados; \"no-link\" apunta a un problema fisico (cable, puerto o equipo apagado)."),
    ("/interface bridge port print", "Lista que puertos fisicos pertenecen a cada bridge (la \"red\" logica que agrupa varios puertos). Si el puerto de tu cliente no aparece aqui, esta fisicamente conectado pero no forma parte de esa red."),
    ("/interface bridge host print", "Muestra la tabla de direcciones MAC que el bridge ha aprendido en cada puerto. Si el MAC del equipo del cliente aparece aqui, el router ya lo ve a nivel de cableado/switch, y el problema (si existe) esta mas arriba, en IP o DHCP."),
    ("/interface bridge print", "Muestra los bridges configurados en el router. Confirma que el bridge existe, esta habilitado y tiene el nombre que esperas usar en los siguientes pasos."),
    ("/interface print", "Lista todas las interfaces fisicas y virtuales con su estado. Busca una \"R\" junto al nombre: significa \"running\" (activa). Si falta, la interfaz esta caida o deshabilitada."),
    ("/ip address add", "Asigna una direccion IP a una interfaz del router (aqui, la propia IP del router dentro de la LAN). Sin este paso el router no tiene una \"puerta\" en esa red y no puede repartir direcciones ni enrutar trafico."),
    ("/ip address print", "Lista las direcciones IP asignadas a cada interfaz. Confirma que la IP se creo correctamente y que no choca con otra direccion ya existente en la red."),
    ("/ip pool add", "Define un rango de direcciones IP reservado para repartir a los clientes. El servidor DHCP tomara direcciones de este pool, nunca fuera de el."),
    ("/ip pool print", "Muestra los pools creados y cuantas direcciones libres tiene cada uno. Si el pool aparece vacio o con rango incorrecto, revisa el paso anterior."),
    ("/ip dhcp-server network add", "Define los parametros que el DHCP entregara a los clientes de esa subred -gateway y DNS-, independientemente del servicio DHCP en si. Es la \"tarjeta de datos\" que acompaña a cada IP entregada."),
    ("/ip dhcp-server network set", "Corrige que gateway o DNS se esta anunciando a los clientes de una red DHCP especifica, sin necesidad de borrar y recrear la red completa."),
    ("/ip dhcp-server network print", "Confirma que gateway y DNS se estan anunciando a los clientes de esa red. Si un cliente tiene mala configuracion de DNS, normalmente el error esta aqui."),
    ("/ip dhcp-server add", "Crea el servicio de DHCP Server propiamente dicho: lo asocia a una interfaz y a un pool de direcciones, y lo deja activo (disabled=no)."),
    ("/ip dhcp-server print", "Confirma que el servidor DHCP existe y esta habilitado. Si aparece \"disabled=yes\", el servicio esta creado pero apagado y no repartira direcciones."),
    ("/ip dhcp-server lease print", "Lista las direcciones IP actualmente entregadas a clientes (leases). Si el equipo del cliente aparece con estado \"bound\", el DHCP esta funcionando de punta a punta."),
    ("/ip dhcp-client print", "Muestra si el propio router esta recibiendo IP por DHCP en su interfaz WAN (tipico al conectarse a un modem/ISP). \"status: bound\" significa que ya obtuvo IP, gateway y DNS del proveedor; cualquier otro estado indica que el router no ha logrado conectarse."),
    ("/ip route print", "Lista las rutas que el router conoce. Para salir a Internet debe existir una ruta \"0.0.0.0/0\" (ruta por defecto); si no aparece, el router no sabe hacia donde mandar el trafico que no es de su propia red."),
    ("/ping 1.1.1.1", "Prueba de conectividad hacia Internet usando una IP publica conocida (Cloudflare), sin depender del DNS. Si responde con 0% de perdida, el problema NO es de ruteo o de Internet, sino probablemente de DNS."),
    ("/ping 192.168.88.1", "Prueba de conectividad hacia el propio router/gateway desde un cliente de la LAN. Si no responde, el problema esta en la red local -cableado, bridge o IP-, no en Internet."),
    ("/resolve ", "Pide al router que resuelva un nombre de dominio a una direccion IP usando el DNS configurado. Si esto falla pero el ping por IP funciona, el problema es especificamente de DNS, no de conectividad."),
    ("/ip dns cache print", "Muestra las resoluciones DNS que el router ya tiene guardadas en cache. Ayuda a diferenciar un fallo de resolucion nuevo de uno que ya estaba fallando desde antes."),
    ("/ip dns set", "Configura que servidores DNS usara el router y le permite responder consultas DNS de los clientes de la LAN (\"allow-remote-requests=yes\" es necesario si quieres que el router sea el DNS de tu red)."),
    ("/ip dns print", "Muestra los servidores DNS configurados en el router y si tiene habilitado el modo \"allow-remote-requests\" para servir de DNS a los clientes."),
    ("/ip firewall filter print stats", "Igual que el listado normal, pero suma cuantos paquetes y bytes ha procesado cada regla. Una regla con contador en cero probablemente nunca se esta aplicando -revisa su orden o sus condiciones-."),
    ("/ip firewall filter print", "Lista todas las reglas del firewall en el orden exacto en que se evaluan. El orden importa: la PRIMERA regla que coincide con un paquete es la que se aplica, las siguientes ya no se evaluan para ese paquete."),
    ("/ip firewall filter\n", "Bloque de reglas base de firewall: permite el trafico de conexiones ya establecidas o relacionadas, permite ICMP (ping), permite administracion solo desde la LAN, y finalmente bloquea todo lo demas (regla \"drop\" al final). El orden es critico: las reglas de permiso SIEMPRE deben ir antes que el drop general, o bloquearan tambien el trafico que querias permitir."),
    ("/ip firewall connection print count-only", "Devuelve solo el numero total de conexiones activas que el router esta rastreando, util para ver la carga sin saturar la pantalla con el detalle de cada una."),
    ("/ip firewall connection print where", "Filtra las conexiones activas por un criterio especifico -aqui, solo las que se estan estableciendo en ese momento-, para ver trafico nuevo en tiempo real sin el ruido de las conexiones ya existentes."),
    ("/ip firewall connection print", "Lista las conexiones activas que el router esta rastreando (connection tracking). Si el trafico de un cliente no aparece aqui, es probable que ni siquiera este llegando al router."),
    ("/ip firewall nat add", "La regla que permite que TODA la LAN salga a Internet compartiendo una sola IP publica (NAT / masquerade). Sin esta regla, los paquetes salen con una IP privada y el proveedor de Internet los descarta."),
    ("/ip firewall nat print stats", "Muestra cuantos paquetes ha traducido esa regla de NAT. Un contador en cero sugiere que el trafico no esta pasando por ahi -revisa que \"out-interface-list=WAN\" apunte a la interfaz correcta-."),
    ("/ip firewall nat print", "Confirma que la regla de NAT existe, esta activa y tiene la accion \"masquerade\"."),
    ("/log print where", "Filtra el registro de eventos del router mostrando solo los que coinciden con el criterio indicado -aqui, los relacionados al firewall-. Util para ver en tiempo real que regla esta bloqueando un trafico, si esa regla tiene \"log\" activado."),
    ("/system resource print", "Muestra el uso de CPU, la memoria RAM libre y el tiempo de actividad (uptime) del router. Sirve para descartar que el problema sea, simplemente, un equipo sobrecargado."),
    ("/system package print", "Lista los paquetes de RouterOS instalados y su version. Confirma que no falte un paquete necesario para lo que estas configurando (por ejemplo, \"dhcp\" o \"wireless\")."),
    ("/file print", "Lista los archivos guardados en el router -respaldos, exports, logs-. Usalo para confirmar que el archivo se creo, revisar su tamano y su fecha."),
]


def explicar_bloque(codigos: list[str]) -> str:
    """Genera una explicacion combinando los comandos presentes en el bloque."""
    partes = []
    vistos = set()
    for codigo in codigos:
        primera_linea = codigo.strip().split("\r\n")[0].split("\n")[0].strip()
        clave = None
        texto = None
        for prefijo, explicacion in EXPLICACIONES:
            if primera_linea.startswith(prefijo) or codigo.strip().startswith(prefijo):
                clave, texto = prefijo, explicacion
                break
        if texto and texto not in vistos:
            partes.append(texto)
            vistos.add(texto)
    if not partes:
        return ("Ejecuta primero la consulta cuando sea una etapa de diagnostico. Si modificas la configuracion, "
                "vuelve a ejecutar la consulta y compara el resultado. Adapta interfaces, subredes, listas WAN/LAN "
                "y nombres a tu topologia.")
    return " ".join(partes)


PATRON_BLOQUE = re.compile(
    r'(<div class="mikrotik-code-injected">.*?)'
    r'<p class="code-caption">.*?</p>',
    re.S,
)
PATRON_CODE = re.compile(r"<code>(.*?)</code>", re.S)


def procesar_archivo(ruta: Path) -> int:
    contenido = ruta.read_text(encoding="utf-8")
    cambios = 0

    def reemplazo(m):
        nonlocal cambios
        bloque = m.group(1)
        codigos = [re.sub(r"<[^>]+>", "", c) for c in PATRON_CODE.findall(bloque)]
        explicacion = explicar_bloque(codigos)
        cambios += 1
        return bloque + f'<p class="code-caption">{explicacion}</p>'

    nuevo = PATRON_BLOQUE.sub(reemplazo, contenido)
    if nuevo != contenido:
        ruta.write_text(nuevo, encoding="utf-8")
    return cambios


if __name__ == "__main__":
    archivos = [
        "mikrotik-backup-configuracion.html",
        "mikrotik-dhcp-lan.html",
        "mikrotik-dns-clientes.html",
        "mikrotik-firewall-basico.html",
        "mikrotik-ip-sin-direccion.html",
        "mikrotik-nat-internet.html",
        "mikrotik-no-internet.html",
        "mikrotik-redes.html",
    ]
    total = 0
    for nombre in archivos:
        ruta = BASE / nombre
        if not ruta.exists():
            print(f"[aviso] no existe {nombre}")
            continue
        n = procesar_archivo(ruta)
        print(f"[ok] {nombre}: {n} bloque(s) actualizados")
        total += n
    print(f"TOTAL: {total} bloques actualizados")
