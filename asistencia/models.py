from django.db import models
from django.utils import timezone


class Tecnico(models.Model):
    """Técnico autorizado importado desde Excel."""
    cedula = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    celular = models.CharField(max_length=15)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Técnico'
        verbose_name_plural = 'Técnicos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.cedula})"


class CodigoQR(models.Model):
    """QR único para registro de asistencia."""
    token = models.CharField(max_length=64, unique=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = 'Código QR'
        verbose_name_plural = 'Códigos QR'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"QR {self.token[:8]}... ({'Activo' if self.activo else 'Inactivo'})"

    def esta_vigente(self):
        if not self.activo:
            return False
        if self.fecha_vencimiento and timezone.now() > self.fecha_vencimiento:
            return False
        return True


class OTPRegistro(models.Model):
    """Código OTP temporal enviado al técnico por SMS."""
    tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()

    class Meta:
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'
        ordering = ['-creado']

    def __str__(self):
        return f"OTP {self.tecnico.cedula} - {self.creado.strftime('%Y-%m-%d %H:%M')}"

    def esta_vigente(self):
        return not self.usado and timezone.now() < self.expira


class RegistroAsistencia(models.Model):
    """Registro completo de asistencia de un técnico."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('validado', 'Validado'),
        ('rechazado', 'Rechazado'),
    ]

    tecnico = models.ForeignKey(Tecnico, on_delete=models.PROTECT)
    fecha = models.DateField()
    hora_registro = models.DateTimeField()  # Hora del servidor
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='validado')
    tarde = models.BooleanField(default=False)  # True si llegó después de la hora límite

    # Geolocalización
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distancia_metros = models.IntegerField(null=True, blank=True)

    # OTP
    otp_utilizado = models.CharField(max_length=6, blank=True)

    # Auditoría
    ip_dispositivo = models.GenericIPAddressField(null=True, blank=True)
    qr_usado = models.ForeignKey(CodigoQR, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        ordering = ['-hora_registro']

    def __str__(self):
        return f"{self.tecnico.nombre} - {self.fecha} {self.hora_registro.strftime('%H:%M')}"
