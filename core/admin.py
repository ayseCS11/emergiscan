from django.contrib import admin
from .models import Patient, PatientAttachment, ClinicalRecord, TransferReceipt, UserProfile, SystemSetting

admin.site.register(SystemSetting)
admin.site.register(Patient)
admin.site.register(PatientAttachment)
admin.site.register(ClinicalRecord)
admin.site.register(TransferReceipt)
admin.site.register(UserProfile)
