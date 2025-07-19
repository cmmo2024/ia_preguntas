# core/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def user_has_plan(plan_required='premium'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            try:
                profile = request.user.userprofile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=request.user)

            # Si requiere premium y el usuario no lo tiene
            if plan_required == 'premium' and profile.plan != 'premium':
                messages.warning(request, "⚠️ Esta función requiere un plan Premium.")
                return redirect('profile')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator