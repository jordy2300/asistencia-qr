"""
Vistas principales del sistema de asistencia.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.db.models import Q

import json
from datetime import date

from .models import CodigoQR, Tecnico, OTPRegistro, RegistroAsistencia
from .services import (
    crear_otp, verificar_otp, enviar_sms_otp, validar_ubicacion,
    crear_qr, obtener_qr_imagen_base64, exportar_asistencia_excel,
    importar_tecnicos_excel
)


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── FLUJO DE REGISTRO (MÓVIL) ───────────────────────────────────────────────

def inicio_registro(request, token):
    """Paso 1: El técnico escanea el QR y llega aquí."""
    try:
        qr = CodigoQR.objects.get(token=token)
    except CodigoQR.DoesNotExist:
        return render(request, 'asistencia/error.html', {'mensaje': 'Código QR no reconocido.'})

    if not qr.esta_vigente():
        return render(request, 'asistencia/error.html', {'mensaje': 'Este código QR ha expirado o fue desactivado.'})

    # Guardar token en sesión
    request.session['qr_token'] = token
    return render(request, 'asistencia/registro_cedula.html', {'qr': qr})


@require_POST
def verificar_cedula(request):
    """Paso 2: Verifica cédula, valida ubicación y envía OTP."""
    cedula = request.POST.get('cedula', '').strip()
    lat = request.POST.get('latitud')
    lng = request.POST.get('longitud')

    # Validar QR en sesión
    token = request.session.get('qr_token')
    if not token:
        return JsonResponse({'ok': False, 'error': 'Sesión expirada. Escanee el QR nuevamente.'})

    try:
        qr = CodigoQR.objects.get(token=token, activo=True)
        if not qr.esta_vigente():
            return JsonResponse({'ok': False, 'error': 'QR expirado.'})
    except CodigoQR.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'QR inválido.'})

    # Validar técnico
    try:
        tecnico = Tecnico.objects.get(cedula=cedula, activo=True)
    except Tecnico.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Cédula no encontrada en el sistema.'})

    # Validar ubicación
    if lat and lng:
        try:
            dentro, distancia = validar_ubicacion(float(lat), float(lng))
            if not dentro:
                return JsonResponse({
                    'ok': False,
                    'error': f'Fuera del perímetro autorizado ({distancia} m). Debe estar dentro de {settings.GEO_RADIO_METROS} m de la empresa.'
                })
            request.session['geo_lat'] = lat
            request.session['geo_lng'] = lng
            request.session['geo_distancia'] = distancia
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Error al procesar coordenadas GPS.'})
    else:
        return JsonResponse({'ok': False, 'error': 'No se pudo obtener su ubicación. Active el GPS e intente nuevamente.'})

    # Verificar asistencia duplicada hoy
    hoy = timezone.localdate()
    if RegistroAsistencia.objects.filter(tecnico=tecnico, fecha=hoy).exists():
        return JsonResponse({'ok': False, 'error': 'Ya registró asistencia hoy.'})

    # Crear y enviar OTP
    otp = crear_otp(tecnico)
    enviado = enviar_sms_otp(tecnico.celular, otp.codigo)

    if not enviado:
        return JsonResponse({'ok': False, 'error': 'Error al enviar SMS. Contacte al administrador.'})

    # Guardar en sesión para el siguiente paso
    request.session['tecnico_cedula'] = cedula
    celular_enmascarado = f"***{tecnico.celular[-4:]}"

    return JsonResponse({
        'ok': True,
        'celular': celular_enmascarado,
        'nombre': tecnico.nombre,
        # En desarrollo mostramos el OTP en respuesta; en producción quitar esto
        'otp_dev': otp.codigo if settings.SMS_BACKEND == 'console' else None,
    })


@require_POST
def confirmar_otp(request):
    """Paso 3: Valida OTP y registra la asistencia."""
    codigo = request.POST.get('codigo', '').strip()
    cedula = request.session.get('tecnico_cedula')
    token = request.session.get('qr_token')

    if not cedula or not token:
        return JsonResponse({'ok': False, 'error': 'Sesión expirada. Escanee el QR nuevamente.'})

    try:
        tecnico = Tecnico.objects.get(cedula=cedula)
        qr = CodigoQR.objects.get(token=token)
    except (Tecnico.DoesNotExist, CodigoQR.DoesNotExist):
        return JsonResponse({'ok': False, 'error': 'Datos de sesión inválidos.'})

    valido, mensaje = verificar_otp(tecnico, codigo)
    if not valido:
        return JsonResponse({'ok': False, 'error': mensaje})

    # Registrar asistencia
    ahora = timezone.now()
    hora_limite_str = settings.HORA_LIMITE_ASISTENCIA
    h, m = map(int, hora_limite_str.split(':'))
    hora_local = timezone.localtime(ahora)
    tarde = hora_local.hour > h or (hora_local.hour == h and hora_local.minute > m)

    lat = request.session.get('geo_lat')
    lng = request.session.get('geo_lng')
    distancia = request.session.get('geo_distancia')

    reg = RegistroAsistencia.objects.create(
        tecnico=tecnico,
        fecha=timezone.localdate(),
        hora_registro=ahora,
        estado='validado',
        tarde=tarde,
        latitud=lat,
        longitud=lng,
        distancia_metros=distancia,
        otp_utilizado=codigo,
        ip_dispositivo=_get_client_ip(request),
        qr_usado=qr,
    )

    # Limpiar sesión
    for key in ['qr_token', 'tecnico_cedula', 'geo_lat', 'geo_lng', 'geo_distancia']:
        request.session.pop(key, None)

    return JsonResponse({
        'ok': True,
        'nombre': tecnico.nombre,
        'hora': hora_local.strftime('%H:%M'),
        'fecha': timezone.localdate().strftime('%d/%m/%Y'),
        'tarde': tarde,
    })


# ─── PANEL ADMINISTRATIVO ────────────────────────────────────────────────────

@login_required
def panel(request):
    """Dashboard principal del administrador."""
    hoy = date.today()
    registros_hoy = RegistroAsistencia.objects.filter(fecha=hoy).select_related('tecnico')
    alertas_tardanza = registros_hoy.filter(tarde=True)
    total_tecnicos = Tecnico.objects.filter(activo=True).count()
    qr_activo = CodigoQR.objects.filter(activo=True).first()

    context = {
        'registros_hoy': registros_hoy,
        'alertas_tardanza': alertas_tardanza,
        'total_tecnicos': total_tecnicos,
        'qr_activo': qr_activo,
        'hoy': hoy,
    }
    return render(request, 'asistencia/panel.html', context)


@login_required
def lista_asistencia(request):
    """Lista de registros con filtros."""
    qs = RegistroAsistencia.objects.select_related('tecnico').all()

    # Filtros
    busqueda = request.GET.get('q', '')
    fecha_desde = request.GET.get('desde', '')
    fecha_hasta = request.GET.get('hasta', '')
    solo_tarde = request.GET.get('tarde', '')

    if busqueda:
        qs = qs.filter(
            Q(tecnico__nombre__icontains=busqueda) |
            Q(tecnico__cedula__icontains=busqueda)
        )
    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)
    if solo_tarde == '1':
        qs = qs.filter(tarde=True)

    context = {
        'registros': qs[:200],
        'busqueda': busqueda,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'solo_tarde': solo_tarde,
        'total': qs.count(),
    }
    return render(request, 'asistencia/lista_asistencia.html', context)


@login_required
def exportar_excel(request):
    """Exporta los registros filtrados a Excel."""
    qs = RegistroAsistencia.objects.select_related('tecnico').all()

    fecha_desde = request.GET.get('desde', '')
    fecha_hasta = request.GET.get('hasta', '')
    busqueda = request.GET.get('q', '')

    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)
    if busqueda:
        qs = qs.filter(
            Q(tecnico__nombre__icontains=busqueda) |
            Q(tecnico__cedula__icontains=busqueda)
        )

    output = exportar_asistencia_excel(qs)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="asistencia.xlsx"'
    return response


@login_required
def gestion_qr(request):
    """Gestión de códigos QR."""
    qr_activo = CodigoQR.objects.filter(activo=True).first()
    historial = CodigoQR.objects.all()[:10]

    qr_imagen = None
    if qr_activo:
        qr_imagen = obtener_qr_imagen_base64(qr_activo.token)

    context = {
        'qr_activo': qr_activo,
        'historial': historial,
        'qr_imagen': qr_imagen,
    }
    return render(request, 'asistencia/gestion_qr.html', context)


@login_required
@require_POST
def generar_nuevo_qr(request):
    """Genera un nuevo código QR e invalida los anteriores."""
    dias = int(request.POST.get('dias_vigencia', 30))
    qr = crear_qr(request, dias_vigencia=dias)
    messages.success(request, f'Nuevo QR generado. Válido hasta {qr.fecha_vencimiento.strftime("%d/%m/%Y")}.')
    return redirect('gestion_qr')


@login_required
@require_POST
def invalidar_qr(request, pk):
    """Invalida un QR específico."""
    qr = get_object_or_404(CodigoQR, pk=pk)
    qr.activo = False
    qr.save()
    messages.warning(request, 'QR invalidado.')
    return redirect('gestion_qr')


@login_required
def gestion_tecnicos(request):
    """Listado de técnicos autorizados."""
    tecnicos = Tecnico.objects.all()
    return render(request, 'asistencia/tecnicos.html', {'tecnicos': tecnicos})


@login_required
@require_POST
def importar_excel_view(request):
    """Importa técnicos desde el Excel GESTION.xlsx interno."""
    import os
    ruta = os.path.join(settings.BASE_DIR, 'asistencia', 'GESTION.xlsx')
    if not os.path.exists(ruta):
        messages.error(request, 'Archivo GESTION.xlsx no encontrado.')
        return redirect('gestion_tecnicos')

    stats = importar_tecnicos_excel(ruta)
    messages.success(
        request,
        f"Importación completada: {stats['creados']} creados, {stats['actualizados']} actualizados, {stats['errores']} errores."
    )
    return redirect('gestion_tecnicos')
