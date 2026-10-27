from .permissions import is_admin


def role_flags(request):
    return {'is_admin_user': is_admin(request.user)}