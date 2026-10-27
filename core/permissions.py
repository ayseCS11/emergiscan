from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def is_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.role == 'Admin')


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "You don't have permission to do that. Admin access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper