from agents.models import Agent
from .models import Member, MemberAssignment
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password



class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'first_name',
            'last_name',
            'other_names',
            'gender',
            'date_of_birth',
            'phone',
            'email',
            'address',
            'photo',
            'next_of_kin',
            'next_of_kin_phone',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'other_names': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '08012345678'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'next_of_kin': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'next_of_kin_phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()

        queryset = Member.objects.filter(phone=phone)

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                'A member with this phone number already exists.'
            )

        return phone





class MemberCreateForm(MemberForm):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter login username'
        })
    )

    password1 = forms.CharField(
        label='Initial Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set initial password'
        })
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        User = get_user_model()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                'This username is already in use.'
            )

        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        User = get_user_model()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'This email already has an account.'
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                self.add_error(
                    'password2',
                    'Passwords do not match.'
                )
            else:
                user = get_user_model()(
                    username=cleaned_data.get('username'),
                    email=cleaned_data.get('email')
                )
                try:
                    validate_password(password1, user)
                except forms.ValidationError as error:
                    self.add_error('password1', error)

        return cleaned_data




class MemberAssignmentForm(forms.ModelForm):

    class Meta:
        model = MemberAssignment
        fields = ['member', 'agent', 'notes']

        widgets = {
            'member': forms.Select(attrs={
                'class': 'form-select'
            }),
            'agent': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional assignment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['member'].queryset = Member.objects.filter(
            status=Member.Status.ACTIVE
        ).order_by('first_name', 'last_name')

        self.fields['agent'].queryset = Agent.objects.filter(
            status=Agent.Status.ACTIVE,
            user__is_active=True
        ).select_related('user').order_by('user__first_name')

        self.fields['member'].label_from_instance = (
            lambda member: f'{member.member_no} - {member.full_name}'
        )

        self.fields['agent'].label_from_instance = (
            lambda agent: f'{agent.agent_no} - {agent.full_name}'
        )

    def clean_member(self):
        member = self.cleaned_data['member']

        existing = MemberAssignment.objects.filter(
            member=member,
            is_active=True
        )

        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                'This member already has an assigned agent. '
                'Use the transfer option instead.'
            )

        return member


class MemberTransferForm(forms.ModelForm):

    class Meta:
        model = MemberAssignment
        fields = ['agent', 'notes']

        widgets = {
            'agent': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for transferring this member'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['agent'].queryset = Agent.objects.filter(
            status=Agent.Status.ACTIVE,
            user__is_active=True
        ).select_related('user')

        self.fields['agent'].label_from_instance = (
            lambda agent: f'{agent.agent_no} - {agent.full_name}'
        )

    def clean_agent(self):
        agent = self.cleaned_data['agent']

        if self.instance.pk and agent.pk == self.instance.agent_id:
            raise forms.ValidationError(
                'Select a different agent for the transfer.'
            )

        return agent


