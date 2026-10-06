from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q
from .models import Patient
from .models import Patient, PatientAttachment, ClinicalRecord, TransferReceipt, UserProfile , SystemSetting
from django.urls import reverse
from django.db.models import Count
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse

from django.db import connection

def send_otp_email(email, code):
    if not email:
        return False
    send_mail(
        subject='EmergiScan Transfer Verification Code',
        message=f'Your verification code is: {code}\n\nThis code expires in 10 minutes.',
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
    return True

def debug_env(request):
    db = connection.settings_dict
    return HttpResponse(
        f"CSRF_TRUSTED_ORIGINS = {settings.CSRF_TRUSTED_ORIGINS!r}<br>"
        f"ALLOWED_HOSTS = {settings.ALLOWED_HOSTS!r}<br>"
        f"DEBUG = {settings.DEBUG!r}<br>"
        f"DB ENGINE = {db.get('ENGINE')!r}<br>"
        f"DB HOST = {db.get('HOST')!r}<br>"
        f"DB NAME = {db.get('NAME')!r}"
    )

@login_required
def dashboard(request):
    today = timezone.now().date()

    total_doctors = UserProfile.objects.filter(designation__iexact='Doctor').count()

    dept_counts = (
        Patient.objects.exclude(department__isnull=True)
        .exclude(department__exact='')
        .values('department')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    department_labels = [d['department'] for d in dept_counts]
    department_values = [d['count'] for d in dept_counts]

    male_count = Patient.objects.filter(gender__iexact='Male').count()
    female_count = Patient.objects.filter(gender__iexact='Female').count()
    from datetime import timedelta

    trend_labels = []
    trend_admits = []
    trend_discharges = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        trend_labels.append(day.strftime('%a'))
        trend_admits.append(Patient.objects.filter(entry_date__date=day).count())
        trend_discharges.append(Patient.objects.filter(status='discharge', entry_date__date=day).count())
    context = {
        'total_users': User.objects.count(),
        'total_doctors': total_doctors,
        'emergency_active': Patient.objects.filter(status='active').count(),
        'critical_cases': Patient.objects.filter(priority='Critical').count(),
        'urgent_cases': Patient.objects.filter(priority='Urgent').count(),
        'stable_cases': Patient.objects.filter(priority='Stable').count(),
        'clinical_today': Patient.objects.filter(entry_date__date=today).count(),
        'discharged_today': Patient.objects.filter(status='discharge', entry_date__date=today).count(),
        'recent_patients': Patient.objects.order_by('-entry_date')[:10],
        'department_labels': department_labels,
        'department_values': department_values,
        'male_count': male_count,
        'female_count': female_count,
        'trend_labels': trend_labels,
        'trend_admits': trend_admits,
        'trend_discharges': trend_discharges,
    }
    return render(request, 'dashboard.html', context)
@login_required
def patient_database(request):
    query = request.GET.get('q', '')
    priority_filter = request.GET.get('priority', '')
    status_filter = request.GET.get('status', '')

    patients = Patient.objects.all().order_by('-entry_date')
    if query:
        patients = patients.filter(
            Q(mr_number__icontains=query) |
            Q(full_name__icontains=query) |
            Q(cnic__icontains=query) |
            Q(phone__icontains=query)
        )
    if priority_filter:
        patients = patients.filter(priority=priority_filter)
    if status_filter:
        patients = patients.filter(status=status_filter)

    return render(request, 'patient_database.html', {
        'patients': patients,
        'query': query,
        'priority_filter': priority_filter,
        'status_filter': status_filter,
    })
@login_required
def coming_soon(request):
    return render(request, 'coming_soon.html')

@login_required
def emergency_entry(request):
    if request.method == 'POST':
        mr_number = request.POST.get('mr_number', '').strip()
        patient = Patient.objects.filter(mr_number=mr_number).first() if mr_number else None

        if not patient:
            last = Patient.objects.order_by('-id').first()
            next_number = (last.id + 1) if last else 1
            mr_number = f"{next_number:06d}"
            patient = Patient(mr_number=mr_number)

        complaints = request.POST.getlist('complaint[]')
        onsets = request.POST.getlist('onset_time[]')
        mechanisms = request.POST.getlist('mechanism[]')
        complaint_lines = []
        for i in range(len(complaints)):
            if complaints[i].strip():
                line = complaints[i]
                if i < len(onsets) and onsets[i]:
                    line += f" (onset: {onsets[i]})"
                if i < len(mechanisms) and mechanisms[i]:
                    line += f" — {mechanisms[i]}"
                complaint_lines.append(line)

        if not complaint_lines:
            messages.error(request, "At least one chief complaint is required.")
            return redirect('emergency_entry')

        hpi_list = request.POST.getlist('hpi[]')
        pmh_list = request.POST.getlist('pmh[]')
        psh_list = request.POST.getlist('psh[]')

        patient.full_name = request.POST.get('full_name') or patient.full_name
        patient.cnic = request.POST.get('cnic') or patient.cnic
        patient.phone = request.POST.get('phone') or patient.phone
        patient.gender = request.POST.get('gender') or patient.gender
        patient.pregnancy_status = request.POST.get('pregnancy_status')
        patient.department = request.POST.get('department')

        patient.bp = request.POST.get('bp')
        patient.pulse = request.POST.get('pulse')
        patient.rr = request.POST.get('rr')
        patient.temp = request.POST.get('temp')
        patient.spo2 = request.POST.get('spo2')
        patient.gcs = request.POST.get('gcs')
        patient.priority = request.POST.get('priority', 'Stable')
        patient.status = 'active'

        patient.chief_complaints = " | ".join(complaint_lines)
        patient.history_present_illness = " | ".join([h for h in hpi_list if h.strip()])
        patient.past_medical_history = " | ".join([h for h in pmh_list if h.strip()])
        patient.past_surgical_history = " | ".join([h for h in psh_list if h.strip()])
        patient.allergies = request.POST.get('allergies_tags', '')
        patient.drug_history = request.POST.get('drug_tags', '')
        patient.family_history = request.POST.get('family_tags', '')

        patient.save()

        attachment_categories = ['lab_reports', 'radiology', 'medical_records', 'prescription', 'referral_letter', 'clinical_photos']
        for category in attachment_categories:
            f = request.FILES.get(category)
            if f:
                PatientAttachment.objects.create(
                    patient=patient,
                    category=category,
                    file=f,
                    remarks=request.POST.get(f'{category}_remarks', ''),
                )

        if 'go_to_clinical' in request.POST:
            return redirect(f"{reverse('clinical')}?mr={patient.mr_number}")
        return redirect('patient_database')

    attachment_fields = [
        ('lab_reports', 'Lab Reports'),
        ('radiology', 'Radiology Images'),
        ('medical_records', 'Medical Records'),
        ('prescription', 'Prescription'),
        ('referral_letter', 'Referral Letter'),
        ('clinical_photos', 'Clinical Photos'),
    ]
    prefill_mr = request.GET.get('mr', '')
    attachment_fields = [
        ('lab_reports', 'Lab Reports'),
        ('radiology', 'Radiology Images'),
        ('medical_records', 'Medical Records'),
        ('prescription', 'Prescription'),
        ('referral_letter', 'Referral Letter'),
        ('clinical_photos', 'Clinical Photos'),
    ]
    return render(request, 'emergency_entry.html', {'attachment_fields': attachment_fields, 'prefill_mr': prefill_mr})

from .models import ClinicalRecord

@login_required
def clinical_entry(request):
    if request.method == 'POST':
        mr_number = request.POST.get('mr_number', '').strip()
        patient = Patient.objects.filter(mr_number=mr_number).first()

        if not patient:
            messages.error(request, "No patient found with that MR number.")
            return redirect('clinical')

        if not request.POST.get('working_diagnosis', '').strip():
            messages.error(request, "Working diagnosis is required.")
            return redirect('clinical')

        record = ClinicalRecord.objects.create(
            patient=patient,
            pe_general=request.POST.get('pe_general'),
            pe_cardiovascular=request.POST.get('pe_cardiovascular'),
            pe_respiratory=request.POST.get('pe_respiratory'),
            pe_abdomen=request.POST.get('pe_abdomen'),
            pe_neurological=request.POST.get('pe_neurological'),
            pe_others=request.POST.get('pe_others'),
            co_blood_pressure='co_blood_pressure' in request.POST,
            co_hepatitis_bc='co_hepatitis_bc' in request.POST,
            co_heart_disease='co_heart_disease' in request.POST,
            co_asthma='co_asthma' in request.POST,
            co_diabetes='co_diabetes' in request.POST,
            co_renal_liver_disease='co_renal_liver_disease' in request.POST,
            co_stroke='co_stroke' in request.POST,
            co_cancer='co_cancer' in request.POST,
            comorbidity_notes=request.POST.get('comorbidity_notes'),
            working_diagnosis=request.POST.get('working_diagnosis'),
            differential_diagnosis=request.POST.get('differential_diagnosis'),
            tr_iv_line='tr_iv_line' in request.POST,
            tr_oxygen='tr_oxygen' in request.POST,
            tr_blood_products='tr_blood_products' in request.POST,
            tr_medications_administered=request.POST.get('tr_medications_administered'),
            tr_procedure_performed=request.POST.get('tr_procedure_performed'),
        )

        investigation_files = request.FILES.getlist('investigations')[:10]
        for f in investigation_files:
            PatientAttachment.objects.create(patient=patient, category='investigation', file=f)

        if 'go_to_discharge' in request.POST:
            return redirect(f"{reverse('discharge')}?mr={patient.mr_number}")
        return redirect('patient_view', mr_number=patient.mr_number)

    prefill_mr = request.GET.get('mr', '')
    records = ClinicalRecord.objects.select_related('patient').order_by('-created_at')[:20]
    return render(request, 'clinical.html', {'prefill_mr': prefill_mr, 'records': records})
from .models import TransferReceipt
import uuid

@login_required
def discharge(request):
    if request.method == 'POST':
        mr_number = request.POST.get('mr_number')
        patient = Patient.objects.filter(mr_number=mr_number).first()

        if not patient:
            messages.error(request, "No patient found with that MR number.")
            return redirect('discharge')

        transfer = TransferReceipt.objects.create(
            patient=patient,
            reason_specialist_care='reason_specialist_care' in request.POST,
            reason_icu_bed='reason_icu_bed' in request.POST,
            reason_surgery='reason_surgery' in request.POST,
            reason_advanced_imaging='reason_advanced_imaging' in request.POST,
            reason_higher_level_care='reason_higher_level_care' in request.POST,
            reason_other='reason_other' in request.POST,
            other_reason_details=request.POST.get('other_reason_details'),
            ambulance_number=request.POST.get('ambulance_number'),
            accompanying_staff=request.POST.get('accompanying_staff'),
            eta=request.POST.get('eta'),
            oxygen='oxygen' in request.POST,
            ventilator='ventilator' in request.POST,
            monitor='monitor' in request.POST,
            receiving_hospital_name=request.POST.get('receiving_hospital_name'),
            receiving_department=request.POST.get('receiving_department'),
            receiving_consultant=request.POST.get('receiving_consultant'),
            receiving_contact=request.POST.get('receiving_contact'),
            referring_doctor_name=request.POST.get('referring_doctor_name'),
            referring_doctor_pmdc=request.POST.get('referring_doctor_pmdc'),
            referring_doctor_designation=request.POST.get('referring_doctor_designation'),
            referring_doctor_contact=request.POST.get('referring_doctor_contact'),
            consent_details=request.POST.get('consent_details'),
            gps_location=request.POST.get('gps_location'),
        )

        if request.FILES.get('referring_doctor_signature'):
            transfer.referring_doctor_signature = request.FILES['referring_doctor_signature']
            transfer.save()

        attachment_categories = ['lab_reports', 'radiology', 'medical_records', 'prescription', 'referral_letter', 'clinical_photos']
        for category in attachment_categories:
            f = request.FILES.get(category)
            if f:
                PatientAttachment.objects.create(
                    patient=patient,
                    category=category,
                    file=f,
                    remarks=request.POST.get(f'{category}_remarks', ''),
                )

        patient.status = 'discharge'
        patient.save()
        return redirect('view_receipt', transfer_uuid=transfer.transfer_uuid)

    prefill_mr = request.GET.get('mr', '')
    attachment_fields = [
        ('lab_reports', 'Lab Reports'),
        ('radiology', 'Radiology Images'),
        ('medical_records', 'Medical Records'),
        ('prescription', 'Prescription'),
        ('referral_letter', 'Referral Letter'),
        ('clinical_photos', 'Clinical Photos'),
    ]
    return render(request, 'discharge.html', {'prefill_mr': prefill_mr, 'attachment_fields': attachment_fields})
from django.contrib.auth.models import User

from .models import UserProfile

@login_required
def user_management(request):
    for u in User.objects.filter(profile__isnull=True):
        UserProfile.objects.create(user=u)
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            email=request.POST.get('email'),
            password=request.POST.get('password'),
        )
        UserProfile.objects.create(
            user=user,
            role=request.POST.get('role', 'Staff'),
            qualification=request.POST.get('qualification'),
            designation=request.POST.get('designation'),
            contact_no=request.POST.get('contact_no'),
            department=request.POST.get('department'),
            profile_pic=request.FILES.get('profile_pic'),
        )
        messages.success(request, f"User {user.username} created.")
        return redirect('user_management')

    search_username = request.GET.get('username', '').strip()
    search_contact = request.GET.get('contact', '').strip()

    users = User.objects.all().order_by('id')
    if search_username:
        users = users.filter(username__icontains=search_username)
    if search_contact:
        users = users.filter(profile__contact_no__icontains=search_contact)

    return render(request, 'user_management.html', {
        'users': users,
        'search_username': search_username,
        'search_contact': search_contact,
    })


@login_required
def user_toggle_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('user_management')


@login_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user.email = request.POST.get('email')
        user.save()
        profile.role = request.POST.get('role', 'Staff')
        profile.qualification = request.POST.get('qualification')
        profile.designation = request.POST.get('designation')
        profile.contact_no = request.POST.get('contact_no')
        profile.department = request.POST.get('department')
        if request.FILES.get('profile_pic'):
            profile.profile_pic = request.FILES['profile_pic']
        profile.save()
        messages.success(request, f"User {user.username} updated.")
        return redirect('user_management')

    return render(request, 'user_edit.html', {'edit_user': user, 'profile': profile})


@login_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted.")
    return redirect('user_management')
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import io
from .models import TransferReceipt

@login_required
def view_receipt(request, transfer_uuid):
    transfer = TransferReceipt.objects.select_related('patient').get(transfer_uuid=transfer_uuid)
    html_string = render_to_string('receipt.html', {
        'transfer': transfer,
        'qr_code': transfer.qr_base64(request),
        'offline_qr_code': transfer.offline_qr_base64(),
    })
    return HttpResponse(html_string)

@login_required
def download_receipt(request, transfer_uuid):
    transfer = TransferReceipt.objects.select_related('patient').get(transfer_uuid=transfer_uuid)
    html_string = render_to_string('receipt.html', {
        'transfer': transfer,
        'qr_code': transfer.qr_base64(request),
        'offline_qr_code': transfer.offline_qr_base64(),
    })
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
    if pdf.err:
        return HttpResponse("Error generating PDF", status=500)
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transfer_{transfer.transfer_uuid}.pdf"'
    return response

from django.shortcuts import get_object_or_404
from django.contrib import messages






@login_required
def patient_view(request, mr_number):
    patient = get_object_or_404(Patient, mr_number=mr_number)
    return render(request, 'patient_view.html', {'patient': patient})


@login_required
def patient_edit(request, mr_number):
    patient = get_object_or_404(Patient, mr_number=mr_number)
    if request.method == 'POST':
        patient.full_name = request.POST.get('full_name')
        patient.cnic = request.POST.get('cnic')
        patient.phone = request.POST.get('phone')
        patient.gender = request.POST.get('gender')
        patient.blood_group = request.POST.get('blood_group')
        dob = request.POST.get('date_of_birth')
        if dob:
            patient.date_of_birth = dob
        patient.save()
        messages.success(request, f"Patient {patient.mr_number} added.")
        if 'go_to_emergency' in request.POST:
            return redirect(f"{reverse('emergency_entry')}?mr={patient.mr_number}")
        return redirect('patient_database')
    return render(request, 'patient_edit.html', {'patient': patient})


@login_required
def patient_delete(request, mr_number):
    patient = get_object_or_404(Patient, mr_number=mr_number)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, f"Patient {mr_number} deleted.")
    return redirect('patient_database')

@login_required
def add_patient(request):
    if request.method == 'POST':
        last = Patient.objects.order_by('-id').first()
        next_number = (last.id + 1) if last else 1
        mr_number = f"{next_number:06d}"

        # Repeatable Chief Complaints rows -> joined into one text block
        complaints = request.POST.getlist('complaint[]')
        onsets = request.POST.getlist('onset_time[]')
        mechanisms = request.POST.getlist('mechanism[]')
        complaint_lines = []
        for i in range(len(complaints)):
            if complaints[i].strip():
                line = complaints[i]
                if i < len(onsets) and onsets[i]:
                    line += f" (onset: {onsets[i]})"
                if i < len(mechanisms) and mechanisms[i]:
                    line += f" — {mechanisms[i]}"
                complaint_lines.append(line)

        # Repeatable Detailed History rows
        hpi_list = request.POST.getlist('hpi[]')
        pmh_list = request.POST.getlist('pmh[]')
        psh_list = request.POST.getlist('psh[]')

        patient = Patient.objects.create(
            mr_number=mr_number,
            full_name=request.POST.get('full_name'),
            cnic=request.POST.get('cnic'),
            phone=request.POST.get('phone'),
            gender=request.POST.get('gender'),
            pregnancy_status=request.POST.get('pregnancy_status'),
            bp=request.POST.get('bp'),
            pulse=request.POST.get('pulse'),
            rr=request.POST.get('rr'),
            temp=request.POST.get('temp'),
            spo2=request.POST.get('spo2'),
            gcs=request.POST.get('gcs'),
            chief_complaints=" | ".join(complaint_lines),
            priority=request.POST.get('priority', 'Stable'),
            history_present_illness=" | ".join([h for h in hpi_list if h.strip()]),
            past_medical_history=" | ".join([h for h in pmh_list if h.strip()]),
            past_surgical_history=" | ".join([h for h in psh_list if h.strip()]),
            allergies=request.POST.get('allergies_tags', ''),
            drug_history=request.POST.get('drug_tags', ''),
            family_history=request.POST.get('family_tags', ''),
            referring_doctor_name=request.POST.get('referring_doctor_name'),
            referring_doctor_designation=request.POST.get('referring_doctor_designation'),
            referring_doctor_contact=request.POST.get('referring_doctor_contact'),
            consent_details=request.POST.get('consent_details'),
            gps_location=request.POST.get('gps_location'),
        )

        if request.FILES.get('referring_doctor_signature'):
            patient.referring_doctor_signature = request.FILES['referring_doctor_signature']
            patient.save()

        # Attachments
        attachment_fields = {
            'lab_reports': 'lab_reports',
            'radiology': 'radiology',
            'medical_records': 'medical_records',
            'prescription': 'prescription',
            'referral_letter': 'referral_letter',
            'clinical_photos': 'clinical_photos',
        }
        for category, field_name in attachment_fields.items():
            f = request.FILES.get(field_name)
            if f:
                PatientAttachment.objects.create(
                    patient=patient,
                    category=category,
                    file=f,
                    remarks=request.POST.get(f'{field_name}_remarks', ''),
                )

        if 'go_to_clinical' in request.POST:
            return redirect('clinical')
        return redirect('patient_database')

    return render(request, 'add_patient.html')
from django.http import JsonResponse

@login_required
def patient_search(request):
    cnic = request.GET.get('cnic', '').strip()
    name = request.GET.get('name', '').strip()
    mr = request.GET.get('mr', '').strip()

    patient = None
    if mr:
        patient = Patient.objects.filter(mr_number=mr).first()
    elif cnic:
        patient = Patient.objects.filter(cnic=cnic).order_by('-entry_date').first()
    elif name:
        patient = Patient.objects.filter(full_name__icontains=name).order_by('-entry_date').first()

    if not patient:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'mr_number': patient.mr_number,
        'full_name': patient.full_name,
        'cnic': patient.cnic or '',
        'phone': patient.phone or '',
        'gender': patient.gender or '',
        'pregnancy_status': patient.pregnancy_status or '',
    })


def verify_transfer(request, transfer_uuid):
    transfer = get_object_or_404(TransferReceipt.objects.select_related('patient'), transfer_uuid=transfer_uuid)
    session_key = f'verified_{transfer_uuid}'

    if request.session.get(session_key):
        return render(request, 'verify_transfer_full.html', {'transfer': transfer})

    if request.method == 'POST':
        entered_pin = request.POST.get('pin', '').strip()
        if entered_pin == SystemSetting.get_verification_pin():
            request.session[session_key] = True
            return redirect('verify_transfer', transfer_uuid=transfer_uuid)
        messages.error(request, "Incorrect PIN.")

    return render(request, 'verify_transfer_pin.html', {'transfer': transfer})

from django.views.decorators.http import require_GET
from django.http import HttpResponse
@login_required
def change_verification_pin(request):
    if not request.user.is_superuser:
        messages.error(request, "Only admins can change the verification PIN.")
        return redirect('dashboard')

    if request.method == 'POST':
        new_pin = request.POST.get('new_pin', '').strip()
        if new_pin:
            setting, _ = SystemSetting.objects.get_or_create(key='verification_pin')
            setting.value = new_pin
            setting.save()
            messages.success(request, "Verification PIN updated.")
            return redirect('change_verification_pin')

    current_pin = SystemSetting.get_verification_pin()
    return render(request, 'change_pin.html', {'current_pin': current_pin})
@require_GET
def service_worker(request):
    return render(request, 'sw.js', content_type='application/javascript')

@login_required
def offline_receipt(request, local_id):
    return render(request, 'offline_receipt.html', {'local_id': local_id})

@login_required
def add_patient(request):
    last = Patient.objects.order_by('-id').first()
    next_number = (last.id + 1) if last else 1
    mr_number_preview = f"{next_number:06d}"

    if request.method == 'POST':
        patient = Patient.objects.create(
            mr_number=mr_number_preview,
            full_name=request.POST.get('full_name'),
            cnic=request.POST.get('cnic'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            gender=request.POST.get('gender'),
            blood_group=request.POST.get('blood_group'),
            pregnancy_status=request.POST.get('pregnancy_status'),
            date_of_birth=request.POST.get('date_of_birth') or None,
        )
        messages.success(request, f"Patient {patient.mr_number} added.")
        return redirect('patient_database')

    return render(request, 'add_patient.html', {'mr_number_preview': mr_number_preview})