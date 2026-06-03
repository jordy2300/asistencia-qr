from django.contrib import admin
from .models import Tecnico, CodigoQR, OTPRegistro, RegistroAsistencia


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = ['cedula', 'nombre', 'celular', 'activo']
    search_fields = ['cedula', 'nombre']
    list_filter = ['activo']


@admin.register(CodigoQR)
class CodigoQRAdmin(admin.ModelAdmin):
    list_display = ['token', 'activo', 'fecha_creacion', 'fecha_vencimiento']
    list_filter = ['activo']
    readonly_fields = ['token', 'fecha_creacion']


@admin.register(OTPRegistro)
class OTPRegistroAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'codigo', 'usado', 'creado', 'expira']
    list_filter = ['usado']
    search_fields = ['tecnico__cedula', 'tecnico__nombre']


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ['tecnico', 'fecha', 'hora_registro', 'estado', 'tarde']
    list_filter = ['estado', 'tarde', 'fecha']
    search_fields = ['tecnico__cedula', 'tecnico__nombre']
    date_hierarchy = 'fecha'
