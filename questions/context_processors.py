from .views import get_impersonated_user


def impersonation(request):
    return {'impersonation_user': get_impersonated_user(request)}
