from django.contrib import admin
from .models import Patient, PatientAttachment, ClinicalNote, TransferReceipt, UserProfile

admin.site.register(Patient)
admin.site.register(PatientAttachment)
admin.site.register(ClinicalNote)
admin.site.register(TransferReceipt)
admin.site.register(UserProfile)