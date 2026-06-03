from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='asistencia/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Panel admin
    path('', views.panel, name='panel'),
    path('asistencia/', views.lista_asistencia, name='lista_asistencia'),
    path('asistencia/exportar/', views.exportar_excel, name='exportar_excel'),
    path('qr/', views.gestion_qr, name='gestion_qr'),
    path('qr/nuevo/', views.generar_nuevo_qr, name='generar_nuevo_qr'),
    path('qr/invalidar/<int:pk>/', views.invalidar_qr, name='invalidar_qr'),
    path('tecnicos/', views.gestion_tecnicos, name='gestion_tecnicos'),
    path('tecnicos/importar/', views.importar_excel_view, name='importar_excel'),

    # Flujo de registro móvil
    path('registrar/<str:token>/', views.inicio_registro, name='inicio_registro'),
    path('registrar/cedula/', views.verificar_cedula, name='verificar_cedula'),
    path('registrar/otp/', views.confirmar_otp, name='confirmar_otp'),
]
