import uuid
import io
import base64
from datetime import date
import qrcode
from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    ROLE_CHOICES = [('Staff', 'Staff'), ('Admin', 'Admin')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Staff')
    qualification = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    contact_no = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.user.username


class Patient(models.Model):
    PRIORITY_CHOICES = [('Critical', 'Critical'), ('Urgent', 'Urgent'), ('Stable', 'Stable')]
    STATUS_CHOICES = [('active', 'Active'), ('discharge', 'Discharge')]

    mr_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    cnic = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    pregnancy_status = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    bp = models.CharField(max_length=20, blank=True, null=True)
    pulse = models.CharField(max_length=10, blank=True, null=True)
    rr = models.CharField(max_length=10, blank=True, null=True)
    temp = models.CharField(max_length=10, blank=True, null=True)
    spo2 = models.CharField(max_length=10, blank=True, null=True)
    gcs = models.CharField(max_length=10, blank=True, null=True)

    chief_complaints = models.TextField(blank=True, null=True)   # multiple rows joined by " | "
    history_present_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    past_surgical_history = models.TextField(blank=True, null=True)
    allergies = models.CharField(max_length=255, blank=True, null=True)     # comma separated tags
    drug_history = models.CharField(max_length=255, blank=True, null=True)  # comma separated tags
    family_history = models.CharField(max_length=255, blank=True, null=True) # comma separated tags

    referring_doctor_name = models.CharField(max_length=150, blank=True, null=True)
    referring_doctor_designation = models.CharField(max_length=100, blank=True, null=True)
    referring_doctor_contact = models.CharField(max_length=20, blank=True, null=True)
    referring_doctor_signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    consent_details = models.CharField(max_length=255, blank=True, null=True)
    gps_location = models.CharField(max_length=100, blank=True, null=True)

    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Stable')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    entry_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mr_number} - {self.full_name}"

    @property
    def vitals(self):
        if self.bp or self.pulse:
            return f"{self.bp or '-'}/{self.pulse or '-'}"
        return "-"

    @property
    def age_display(self):
        if not self.date_of_birth:
            return "0Y 0M 0D"
        today = date.today()
        years = today.year - self.date_of_birth.year
        months = today.month - self.date_of_birth.month
        days = today.day - self.date_of_birth.day
        if days < 0:
            months -= 1
            days += 30
        if months < 0:
            years -= 1
            months += 12
        return f"{years}Y {months}M {days}D"


class PatientAttachment(models.Model):
    CATEGORY_CHOICES = [
        ('lab_reports', 'Lab Reports'),
        ('radiology', 'Radiology Images'),
        ('medical_records', 'Medical Records'),
        ('prescription', 'Prescription'),
        ('referral_letter', 'Referral Letter'),
        ('clinical_photos', 'Clinical Photos'),
        ('investigation', 'Investigation'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='attachments')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to='attachments/')
    remarks = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} - {self.patient.mr_number}"


class ClinicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinical_records')

    # Physical Examination
    pe_general = models.TextField(blank=True, null=True)
    pe_cardiovascular = models.TextField(blank=True, null=True)
    pe_respiratory = models.TextField(blank=True, null=True)
    pe_abdomen = models.TextField(blank=True, null=True)
    pe_neurological = models.TextField(blank=True, null=True)
    pe_others = models.TextField(blank=True, null=True)

    # Comorbidities
    co_blood_pressure = models.BooleanField(default=False)
    co_hepatitis_bc = models.BooleanField(default=False)
    co_heart_disease = models.BooleanField(default=False)
    co_asthma = models.BooleanField(default=False)
    co_diabetes = models.BooleanField(default=False)
    co_renal_liver_disease = models.BooleanField(default=False)
    co_stroke = models.BooleanField(default=False)
    co_cancer = models.BooleanField(default=False)
    comorbidity_notes = models.TextField(blank=True, null=True)

    # Diagnosis
    working_diagnosis = models.CharField(max_length=255)
    differential_diagnosis = models.CharField(max_length=255, blank=True, null=True)

    # Treatment Given
    tr_iv_line = models.BooleanField(default=False)
    tr_oxygen = models.BooleanField(default=False)
    tr_blood_products = models.BooleanField(default=False)
    tr_medications_administered = models.TextField(blank=True, null=True)
    tr_procedure_performed = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Clinical record for {self.patient.mr_number} at {self.created_at}"


class TransferReceipt(models.Model):
    
    transfer_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='transfers')

    reason_specialist_care = models.BooleanField(default=False)
    reason_icu_bed = models.BooleanField(default=False)
    reason_surgery = models.BooleanField(default=False)
    reason_advanced_imaging = models.BooleanField(default=False)
    reason_higher_level_care = models.BooleanField(default=False)
    reason_other = models.BooleanField(default=False)
    other_reason_details = models.CharField(max_length=255, blank=True, null=True)

    ambulance_number = models.CharField(max_length=50, blank=True, null=True)
    accompanying_staff = models.CharField(max_length=150, blank=True, null=True)
    eta = models.CharField(max_length=50, blank=True, null=True)
    oxygen = models.BooleanField(default=False)
    ventilator = models.BooleanField(default=False)
    monitor = models.BooleanField(default=False)

    receiving_hospital_name = models.CharField(max_length=150, blank=True, null=True)
    receiving_department = models.CharField(max_length=100, blank=True, null=True)
    receiving_consultant = models.CharField(max_length=150, blank=True, null=True)
    receiving_contact = models.CharField(max_length=20, blank=True, null=True)

    referring_doctor_name = models.CharField(max_length=150)
    referring_doctor_pmdc = models.CharField(max_length=50, blank=True, null=True)
    referring_doctor_designation = models.CharField(max_length=100)
    referring_doctor_contact = models.CharField(max_length=20, blank=True, null=True)
    referring_doctor_signature = models.ImageField(upload_to='signatures/', blank=True, null=True)

    consent_details = models.CharField(max_length=255, blank=True, null=True)
    gps_location = models.CharField(max_length=100, blank=True, null=True)

    is_synced = models.BooleanField(default=True)
    received_at_destination = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    def generate_otp(self):
        import random
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp_code

    def is_otp_valid(self, code):
        if not self.otp_code or not self.otp_created_at:
            return False
        if timezone.now() > self.otp_created_at + timedelta(minutes=10):
            return False
        return code == self.otp_code
    def __str__(self):
        return f"Transfer {self.transfer_uuid} - {self.patient.full_name}"
    
    def qr_base64(self, request=None):
        if request:
            verify_url = request.build_absolute_uri(f"/verify/{self.transfer_uuid}/")
        else:
            verify_url = f"https://emergiscan-production.up.railway.app/verify/{self.transfer_uuid}/"
        img = qrcode.make(verify_url)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def offline_qr_base64(self):
        latest_clinical = self.patient.clinical_records.order_by('-created_at').first()
        diagnosis_line = latest_clinical.working_diagnosis if latest_clinical else "-"

        text_block = (
            "=== PATIENT INFO ===\n"
            f"MRNO : {self.patient.mr_number}\n"
            f"Age  : {self.patient.age_display}\n"
            f"Sex  : {self.patient.gender or '-'}\n"
            f"B.G  : {self.patient.blood_group or '-'}\n\n"
            "=== VITALS ===\n"
            f"BP: {self.patient.bp or '-'} | HR: {self.patient.pulse or '-'} | RR: {self.patient.rr or '-'}\n"
            f"Temp: {self.patient.temp or '-'} | SpO2: {self.patient.spo2 or '-'} | GCS: {self.patient.gcs or '-'}\n"
            f"Pri: {self.patient.priority}\n\n"
            "=== COMPLAINTS ===\n"
            f"{self.patient.chief_complaints or '-'}\n\n"
            "=== WORKING DIAGNOSIS ===\n"
            f"{diagnosis_line}\n\n"
            "=== DOCTOR ===\n"
            f"{self.referring_doctor_name} ({self.referring_doctor_designation})\n\n"
            "=== TRANSFER ===\n"
            f"To: {self.receiving_hospital_name or '-'} ({self.receiving_department or '-'})\n"
            f"Ambulance: {self.ambulance_number or '-'} | ETA: {self.eta or '-'}\n"
        )
        img = qrcode.make(text_block)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')