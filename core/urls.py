from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('debug-env/', views.debug_env, name='debug_env'),
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('patients/', views.patient_database, name='patient_database'),
    path('add_patient/', views.add_patient, name='add_patient'),
    path('emergency_entry/', views.emergency_entry, name='emergency_entry'),
    path('clinical/', views.clinical_entry, name='clinical'),
    path('discharge/', views.discharge, name='discharge'),
    path('user_management/', views.user_management, name='user_management'),
    path('receipt/<uuid:transfer_uuid>/', views.view_receipt, name='view_receipt'),
    path('receipt/<uuid:transfer_uuid>/download/', views.download_receipt, name='download_receipt'),
    path('patients/<str:mr_number>/', views.patient_view, name='patient_view'),
    path('patients/<str:mr_number>/edit/', views.patient_edit, name='patient_edit'),
    path('patient_search/', views.patient_search, name='patient_search'),
    path('patients/<str:mr_number>/delete/', views.patient_delete, name='patient_delete'),
    path('user_management/<int:user_id>/toggle/', views.user_toggle_status, name='user_toggle_status'),
    path('user_management/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('settings/pin/', views.change_verification_pin, name='change_verification_pin'),
    path('verify/<uuid:transfer_uuid>/', views.verify_transfer, name='verify_transfer'),
    path('offline_receipt/<str:local_id>/', views.offline_receipt, name='offline_receipt'),
    path('user_management/<int:user_id>/delete/', views.user_delete, name='user_delete'),   
]