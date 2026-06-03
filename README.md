# Sistema de Control de Asistencia con QR, Geolocalización y OTP

Aplicación web Django para registro de asistencia de técnicos mediante escaneo de QR, validación GPS y verificación por SMS (OTP).

---

## ⚡ Inicio Rápido (Desarrollo Local)

### 1. Requisitos previos
- Python 3.10+
- pip

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Variables de entorno (opcional en desarrollo)
Copie `.env.example` a `.env` y ajuste los valores. En modo `DEBUG=True` el OTP aparece en pantalla.

### 4. Crear base de datos
```bash
python manage.py migrate
```

### 5. Crear usuario administrador
```bash
python manage.py createsuperuser
```

### 6. Importar técnicos desde Excel
Coloque su archivo `GESTION.xlsx` en `asistencia/` y ejecute:
```bash
python manage.py shell -c "from asistencia.services import importar_tecnicos_excel; print(importar_tecnicos_excel('asistencia/GESTION.xlsx'))"
```

### 7. Ejecutar el servidor
```bash
python manage.py runserver
```
Abra http://localhost:8000 en el navegador.

---

## 🔐 Credenciales por defecto
- Usuario: `admin`
- Contraseña: `admin123`

⚠ **Cámbielas antes de desplegar en producción.**

---

## 📱 Flujo del técnico
1. Escanea el código QR desde su celular
2. El sistema obtiene su GPS
3. Ingresa su número de cédula
4. El sistema valida: cédula en BD + ubicación dentro del perímetro
5. Recibe un código OTP por SMS (válido 5 min)
6. Ingresa el OTP → asistencia registrada

---

## 🖥️ Panel Administrativo

Acceda en `/` (requiere login):

| Ruta | Función |
|------|---------|
| `/` | Dashboard con asistencias del día y alertas |
| `/asistencia/` | Listado con filtros por fecha, nombre, cédula |
| `/asistencia/exportar/` | Exportar a Excel |
| `/qr/` | Gestionar códigos QR |
| `/tecnicos/` | Ver e importar técnicos |

---

## 🔧 Configuración

### Geolocalización (`config/settings.py`)
```python
GEO_LAT = 7.831299        # Latitud de la empresa
GEO_LNG = -72.4971869     # Longitud de la empresa
GEO_RADIO_METROS = 50     # Radio permitido en metros
```

### Hora límite de asistencia
```python
HORA_LIMITE_ASISTENCIA = '07:00'  # Formato HH:MM
```

### SMS con Twilio (producción)
1. Cree una cuenta en https://twilio.com
2. Obtenga Account SID, Auth Token y número de teléfono
3. Configure las variables de entorno:
```
SMS_BACKEND=twilio
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_PHONE_NUMBER=+15xxxxxxx
```
4. Instale: `pip install twilio`

> En desarrollo (`SMS_BACKEND=console`) el OTP aparece en pantalla sin necesidad de Twilio.

---

## 🚀 Despliegue en Render (gratuito)

1. **Suba el proyecto a GitHub**
```bash
git init
git add .
git commit -m "Sistema de asistencia QR"
git remote add origin https://github.com/su-usuario/asistencia-qr.git
git push -u origin main
```

2. **Cree un Web Service en Render**
   - Vaya a https://render.com → New → Web Service
   - Conecte su repositorio de GitHub
   - Build Command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - Start Command: `gunicorn config.wsgi:application`

3. **Configure variables de entorno en Render**
   - `SECRET_KEY` → clave segura larga
   - `DEBUG` → `False`
   - `SMS_BACKEND` → `twilio` (o `console` para pruebas)
   - Variables de Twilio si aplica

4. **Primera vez: importe los técnicos**
   - En Render → Shell del servicio: `python manage.py shell -c "from asistencia.services import importar_tecnicos_excel; importar_tecnicos_excel('asistencia/GESTION.xlsx')"`

---

## 📁 Estructura del Proyecto

```
asistencia_qr/
├── config/               # Configuración Django
│   ├── settings.py
│   └── urls.py
├── asistencia/           # App principal
│   ├── models.py         # Modelos de datos
│   ├── views.py          # Vistas y lógica HTTP
│   ├── services.py       # Lógica de negocio (OTP, QR, SMS, geo)
│   ├── urls.py           # Rutas
│   ├── admin.py          # Panel admin de Django
│   ├── GESTION.xlsx      # Base de técnicos
│   ├── templates/        # HTML
│   │   └── asistencia/
│   │       ├── base.html
│   │       ├── panel.html
│   │       ├── lista_asistencia.html
│   │       ├── gestion_qr.html
│   │       ├── tecnicos.html
│   │       ├── registro_cedula.html  ← vista móvil
│   │       ├── error.html
│   │       └── login.html
│   └── static/asistencia/
│       ├── css/main.css        # Estilos panel admin
│       ├── css/mobile.css      # Estilos vista móvil
│       └── js/registro.js      # Lógica JS del flujo móvil
├── media/qrcodes/        # Imágenes QR generadas
├── requirements.txt
├── Procfile              # Para Render/Heroku
└── README.md
```

---

## 🔄 Actualizar técnicos

1. Actualice `asistencia/GESTION.xlsx` con el nuevo listado
2. En el panel admin → **Técnicos** → **Importar desde Excel**
3. El sistema actualiza registros existentes y crea nuevos sin duplicar

---

## ⚠ Notas de seguridad para producción

- Cambie `SECRET_KEY` por una clave larga y aleatoria
- Establezca `DEBUG=False`
- Configure `ALLOWED_HOSTS` con su dominio real
- Use HTTPS (Render lo provee automáticamente)
- Cambie la contraseña del usuario `admin`
