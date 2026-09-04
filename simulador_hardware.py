import argparse
import sys
import time

import requests

URL_BASE = "http://127.0.0.1:8000/api"
IP_PELLEGRINI = "199.1.1.0"
IP_OFICINAS = "10.0.0.20"
IP_COCHERA = "10.0.0.30"
IP_SALIDA_PEL = "10.0.0.31"
IP_DEPOSITO = "10.0.0.40"

TAGS_DEMO = [
    ("TAG-PEL-01", "Residente Consorcio Pellegrini"),
    ("TAG-OF-01", "Empleada Oficinas Macrocentro"),
    ("TAG-ENC-01", "Encargado Pellegrini (ingreso + cochera)"),
    ("TAG-TEC-01", "Técnico APL — todos los edificios clientes"),
    ("TAG-VIS-01", "Visitante Pellegrini, lun-vie 08-18"),
    ("TAG-BLOQ-01", "Llavero bloqueado"),
    ("TAG-VENC-01", "Llavero vencido"),
]


def post(path, payload):
    try:
        respuesta = requests.post(f"{URL_BASE}{path}", json=payload, timeout=5)
    except requests.exceptions.ConnectionError:
        print("No se pudo conectar con Django en http://127.0.0.1:8000")
        print("Arrancá el backend: cd backend && python manage.py runserver")
        sys.exit(1)

    try:
        datos = respuesta.json()
    except ValueError:
        print(f"El servidor no devolvió JSON:\n{respuesta.text}")
        return respuesta.status_code, None
    return respuesta.status_code, datos


def pasar_tarjeta(codigo_rfid, ip_totem):
    print(f"\n[Lector RFID {ip_totem}] leyendo {codigo_rfid}...")
    status, datos = post("/totem/lectura/", {"codigo_rfid": codigo_rfid, "ip_totem": ip_totem})
    if datos is None:
        return
    if status == 200:
        print(f"  LUZ VERDE — {datos.get('accion')}")
    else:
        print(f"  LUZ ROJA  — {datos.get('accion', 'BLOQUEADO')} ({datos.get('motivo') or datos.get('error')})")


def emitir_evento(tipo, ip_totem):
    status, datos = post("/totem/evento/", {"tipo": tipo, "ip_totem": ip_totem})
    print(f"[{tipo} @ {ip_totem}] HTTP {status} → {datos}")


def heartbeat(ip_totem):
    status, datos = post("/totem/heartbeat/", {"ip_totem": ip_totem})
    print(f"[heartbeat {ip_totem}] HTTP {status} → {datos}")


def menu_interactivo(ip_totem):
    print("=== TÓTEM SGCA-APL ===")
    print(f"IP de este controlador: {ip_totem}")
    print("Códigos demo:")
    for tag, desc in TAGS_DEMO:
        print(f"  {tag:12} {desc}")
    print("Comandos:  f = puerta forzada | d = desconexión | r = reconexión | h = heartbeat | q = salir")

    while True:
        codigo = input("\nPase una tarjeta (código) o comando: ").strip()
        if not codigo:
            continue
        if codigo.lower() == "q":
            break
        if codigo.lower() == "f":
            emitir_evento("PUERTA_FORZADA", ip_totem)
        elif codigo.lower() == "d":
            emitir_evento("DESCONEXION", ip_totem)
        elif codigo.lower() == "r":
            emitir_evento("RECONEXION", ip_totem)
        elif codigo.lower() == "h":
            heartbeat(ip_totem)
        else:
            pasar_tarjeta(codigo, ip_totem)
        time.sleep(0.3)


def demo_automatica():
    print("=== Demo multi-edificio ===")
    heartbeat(IP_PELLEGRINI)
    pasar_tarjeta("TAG-PEL-01", IP_PELLEGRINI)
    pasar_tarjeta("TAG-ENC-01", IP_SALIDA_PEL)
    pasar_tarjeta("TAG-PEL-01", IP_OFICINAS)
    pasar_tarjeta("TAG-PEL-01", IP_COCHERA)
    pasar_tarjeta("TAG-TEC-01", IP_DEPOSITO)
    pasar_tarjeta("TAG-BLOQ-01", IP_PELLEGRINI)
    emitir_evento("PUERTA_FORZADA", IP_PELLEGRINI)


def main():
    parser = argparse.ArgumentParser(description="Simulador de tótem SGCA-APL")
    parser.add_argument(
        "--ip",
        default=IP_PELLEGRINI,
        help="IP del ControladorAcceso (default ingreso Pellegrini 199.1.1.0)",
    )
    parser.add_argument("--demo", action="store_true", help="Corre escenarios multi-edificio")
    args = parser.parse_args()
    if args.demo:
        demo_automatica()
    else:
        menu_interactivo(args.ip)


if __name__ == "__main__":
    main()
