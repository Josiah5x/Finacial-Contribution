from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.messages import get_messages

from .models import User
from .forms import LoginForm, CreateUserForm, UpdateUserForm
from .decorators import role_required


from django.contrib.auth import get_user_model
from django.db import transaction

from members.models import Member


from django.core.exceptions import ValidationError

from .forms import (
    LoginForm,
    CreateUserForm,
    UpdateUserForm,
    MemberRegistrationForm,
    EmailOTPVerifyForm,
)

from .services import generate_email_otp, verify_email_otp

User = get_user_model()




class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('accounts:dashboard') # Simplest approach



@login_required
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have logged out successfully.')
        return redirect('accounts:login')

    return redirect('dashboard')


@role_required('ADMIN', 'MANAGER')
def user_list(request):

    users = User.objects.all().order_by('-date_joined')

    return render(request, 'accounts/user_list.html', {
        'users': users,
    })


@role_required('ADMIN', 'MANAGER')
def user_create(request):

    form = CreateUserForm()

    if request.user.role == 'MANAGER':
        form.fields['role'].choices = [
            choice for choice in form.fields['role'].choices
            if choice[0] not in ['ADMIN']
        ]

    if request.method == 'POST':
        form = CreateUserForm(request.POST)

        if request.user.role == 'MANAGER':
            form.fields['role'].choices = [
                choice for choice in form.fields['role'].choices
                if choice[0] not in ['ADMIN']
            ]

        if form.is_valid():
            user = form.save()

            messages.success(
                request,
                f'{user.username} was created successfully.'
            )

            return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Create New User',
    })


@role_required('ADMIN', 'MANAGER')
def user_update(request, pk):

    user = get_object_or_404(User, pk=pk)

    if request.user.role == 'MANAGER' and user.role == 'ADMIN':
        messages.error(request, 'You cannot modify an administrator.')
        return redirect('accounts:user_list')

    form = UpdateUserForm(instance=user)

    if request.user.role == 'MANAGER':
        form.fields['role'].choices = [
            choice for choice in form.fields['role'].choices
            if choice[0] not in ['ADMIN']
        ]

    if request.method == 'POST':
        form = UpdateUserForm(request.POST, instance=user)

        if request.user.role == 'MANAGER':
            form.fields['role'].choices = [
                choice for choice in form.fields['role'].choices
                if choice[0] not in ['ADMIN']
            ]

        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Update User',
    })


from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        # Save the new password and update the user's session.
        response = super().form_valid(form)

        # Allow the user to access the dashboard after changing password.
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=['must_change_password'])

        return response


from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, 'dashboard/index.html')




def member_register(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()

            try:
                with transaction.atomic():

                    # Create inactive user account.
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=email,
                        phone=form.cleaned_data['phone'],
                        password=form.cleaned_data['password1'],
                        role=User.Role.MEMBER,
                        is_active=False
                    )

                    # Create pending member profile.
                    Member.objects.create(
                        user=user,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        phone=user.phone,
                        email=user.email,
                        status=Member.Status.PENDING
                    )

                    # Send the HTML verification email.
                    generate_email_otp(email)

                # Remember the email for the verification page.
                request.session['pending_verification_email'] = email

                messages.success(
                    request,
                    'Registration submitted! Check your email for your verification code.'
                )

                return redirect('accounts:verify_email')

            except ValidationError as error:
                form.add_error(None, error)

            except Exception:
                messages.error(
                    request,
                    'We could not send your verification email. Please try again.'
                )

    else:
        form = MemberRegistrationForm()

    return render(
        request,
        'accounts/member_register.html',
        {'form': form}
    )


def verify_email(request):

    email = request.session.get('pending_verification_email')

    if not email:
        messages.error(
            request,
            'Please register before verifying your email.'
        )
        return redirect('accounts:register')

    if request.method == 'POST':
        form = EmailOTPVerifyForm(request.POST)

        if form.is_valid():
            try:
                verified = verify_email_otp(
                    email,
                    form.cleaned_data['otp']
                )

                if verified:

                    # Clear previous registration messages.
                    storage = get_messages(request)
                    for message in storage:
                        pass

                    request.session.pop(
                        'pending_verification_email',
                        None
                    )

                    messages.success(
                        request,
                        'Email verified successfully! Your account is awaiting administrator approval.'
                    )

                    return redirect('accounts:login')

                form.add_error(
                    'otp',
                    'Invalid or expired verification code.'
                )

            except ValidationError as error:
                form.add_error('otp', error)

    else:
        form = EmailOTPVerifyForm()

    return render(
        request,
        'accounts/verify_email.html',
        {
            'form': form,
            'email': email,
        }
    )



@login_required
def profile(request):
    member = None

    if request.user.role == User.Role.MEMBER:
        member = Member.objects.filter(user=request.user).first()

    return render(request, 'accounts/profile.html', {
        'member': member,
    })



