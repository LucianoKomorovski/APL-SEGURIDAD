import requests
import time

# Configuramos nuestro "tótem"
URL_API = "http://127.0.0.1:8000/api/totem/lectura/"
IP_DE_ESTE_TOTEM = "199.1.1.0" # Cambiá esto por la IP de un Controlador que hayas creado en Django admin

def pasar_tarjeta(codigo_rfid):
    print(f"\n[Lector RFID] Leyendo tarjeta: {codigo_rfid}...")
    
    paquete_datos = {
        "codigo_rfid": codigo_rfid,
        "ip_totem": IP_DE_ESTE_TOTEM
    }
    
    try:
        respuesta = requests.post(URL_API, json=paquete_datos)
        
        # 1. Intentamos leer el JSON
        try:
            datos = respuesta.json()
        except ValueError:
            print(f"🔴 ERROR: Django devolvió algo que no es JSON. Respuesta cruda:\n{respuesta.text}")
            return

        # 2. EL ESCUDO: Si Django devuelve una lista de errores en vez de un diccionario
        if isinstance(datos, list):
            print(f"🔴 LUZ ROJA - Django devolvió un error de validación:\n{datos}")
            return

        # 3. Flujo normal (si es un diccionario como esperábamos)
        if respuesta.status_code == 200:
            print(f"🟢 LUZ VERDE - Respuesta del servidor: {datos.get('accion')}")
        else:
            print(f"🔴 LUZ ROJA - Respuesta del servidor: {datos.get('accion', 'BLOQUEADO')} ({datos.get('error', 'Acceso denegado')})")
            
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar con el servidor central.")

# Simulamos la actividad en la puerta
if __name__ == "__main__":
    print("=== TÓTEM DE ACCESO INICIADO ===")
    
    while True:
        # Esperamos que alguien escriba un código de tarjeta en la consola
        codigo_ingresado = input("\nPase una tarjeta (escriba el código y presione Enter, o 'q' para salir): ")
        
        if codigo_ingresado.lower() == 'q':
            break
            
        pasar_tarjeta(codigo_ingresado)
        time.sleep(1)