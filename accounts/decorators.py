from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):

    def decorator(view_func):

        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            user = request.user

            if user.is_superuser or user.role in roles:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                "You do not have permission to access this page."
            )

            return redirect('accounts:dashboard')

        return wrapper

    return decorator