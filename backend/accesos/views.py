from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import timedelta
from .models import SujetoAcceso, PuntoAcceso, RegistroAcceso, AlertaSeguridad, Credencial, ControladorAcceso, Edificio
from .serializers import SujetoAccesoSerializer, PuntoAccesoSerializer, RegistroAccesoSerializer, AlertaSeguridadSerializer, EdificioSerializer

class SujetoAccesoViewSet(viewsets.ModelViewSet):
    queryset = SujetoAcceso.objects.all()
    serializer_class = SujetoAccesoSerializer

    def create(self, request, *args, **kwargs):
        nombre = request.data.get('nombre')
        apellido = request.data.get('apellido')
        dni = request.data.get('dni')
        email = request.data.get('email')
        codigo_referencia = request.data.get('codigo_referencia')
        edificio_id = request.data.get('edificio')

        # VALIDACION MINIMA DE CAMPOS OBLIGATORIOS:
        if not all([nombre, apellido, dni, email]):
            return Response(
                {"error": "Faltan datos obligatorios (nombre, apellido, dni, email)."},
                status=400,
            )

        try:
            # transaction.atomic: si falla la credencial, se deshace TODO
            # (no queda un usuario a medias sin su credencial)
            with transaction.atomic():
                # 1. CREAMOS EL USUARIO (SujetoAcceso hereda de Persona):
                edificio_obj = None
                if edificio_id:
                    try:
                        edificio_obj = Edificio.objects.get(pk=edificio_id)
                    except Edificio.DoesNotExist:
                        return Response({"error": "Edificio no encontrado"}, status=400)

                sujeto = SujetoAcceso.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    dni=dni,
                    email=email,
                    edificio=edificio_obj,
                )

                # 2. SI VINO UN CODIGO RFID, CREAMOS LA CREDENCIAL VINCULADA:
                if codigo_referencia:
                    Credencial.objects.create(
                        codigo_referencia=codigo_referencia,
                        tipo='RFID',
                        fecha_vencimiento=timezone.now().date() + timedelta(days=365),
                        estado='Activa',
                        persona=sujeto,  # FK a Persona (un SujetoAcceso ES una Persona)
                    )
        except IntegrityError as e:
            # Por ej. dni, email o codigo_referencia duplicados (son campos unicos)
            return Response(
                {"error": f"Datos duplicados o invalidos: {str(e)}"},
                status=400,
            )

        serializer = self.get_serializer(sujeto)
        return Response(serializer.data, status=201)

class PuntoAccesoViewSet(viewsets.ModelViewSet):
    queryset = PuntoAcceso.objects.all()
    serializer_class = PuntoAccesoSerializer

class RegistroAccesoViewSet(viewsets.ModelViewSet):
    queryset = RegistroAcceso.objects.all()
    serializer_class = RegistroAccesoSerializer

class AlertaSeguridadViewSet(viewsets.ModelViewSet):
    queryset = AlertaSeguridad.objects.all()
    serializer_class = AlertaSeguridadSerializer

class EdificioViewSet(viewsets.ModelViewSet):
    queryset = Edificio.objects.all()
    serializer_class = EdificioSerializer



@api_view(['POST'])
def procesar_lectura_totem(request):
    codigo = request.data.get('codigo_rfid')
    ip_totem = request.data.get('ip_totem')

    try:

        # 1. BUSCAMOS DE QUE DISP. VIENE LA LECTURA:
        dispositivo = ControladorAcceso.objects.filter(direccion_ip = ip_totem).first()

        if not dispositivo:
            return Response({"dispositivo no encontrado en el sistema"}, status=404)
        
        #2. BUSCAMOS CREDENCIAL QUE PASO POR EL LECTOR:
        credencial = Credencial.objects.filter(codigo_referencia = codigo).first()

        # if not credencial:
           # return Response({"error en credencial, no encontrada"}, status=404)

        #3. Logica de Negocio
        if credencial and credencial.estado == 'Activa':
            #ESTA TOD0 EN ORDEN, REGISTRAMOS ACCESO Y ABRIMOS PUERTA:
            RegistroAcceso.objects.create(
                resultado='concedido',
                dispositivo=dispositivo,
                credencial=credencial
            )
            return Response({"status": "ok", "accion": "ABRIR_PUERTA" })
        else:
            #TARJETA FALSA, VENCIDA O BLOQUEADA:
            motivo = "tarjeta inexistente" if not credencial else f"Tarjeta {credencial.estado}"

            #Esa f corresponde a un f-string (literal de cadena formateada), una característica de Python 3.6+ que permite insertar variables directamente dentro de un texto.

            AlertaSeguridad.objects.create(
                tipo_alerta=f'acceso denegado: {motivo}',
                nivel_gravedad='Alta',
                estado_atencion='Pendiente',
                dispositivo=dispositivo
            )


            RegistroAcceso.objects.create(
                resultado='rechazado',
                motivo_rechazo=motivo,
                dispositivo=dispositivo,
                credencial=credencial if credencial else None #PERMITIMOS QUE LA CREDENCIAL SEA NULA
            )


            return Response({"status" : "ERROR" , "accion" : "BLOQUEAR_PUERTA"}, status=403)
    
    except Exception as e:
    #SI LA BASE DE DATOS TIRA CUALQUIER OTRO ERROR, LO ATRAPAMOS Y CONVERTIMOS EN JSON:
        return Response({"status" : "critical" , "accion" : "error_interno" , "error": str(e)}, status=500)
    
            

    


