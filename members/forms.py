from agents.models import Agent
from .models import Member, MemberAssignment
from django import forms
from .models import Member


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


