from django import forms
from django.utils import timezone

from .models import Collection
from contributions.models import PlanEnrollment
from members.models import MemberAssignment


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = [
            'enrollment',
            'assignment',
            'amount',
            'payment_method',
            'transaction_reference',
            'collection_date',
            'notes',
        ]
        widgets = {
            'enrollment': forms.Select(attrs={'class': 'form-select'}),
            'assignment': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank transfer reference',
            }),
            'collection_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional collection notes',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        self.fields['enrollment'].queryset = (
            PlanEnrollment.objects
            .filter(
                status=PlanEnrollment.Status.ACTIVE,
                member__status='ACTIVE',
            )
            .select_related('member', 'plan')
            .order_by('member__first_name')
        )

        self.fields['assignment'].queryset = (
            MemberAssignment.objects
            .filter(
                is_active=True,
                agent__status='ACTIVE',
                agent__user__is_active=True,
            )
            .select_related('member', 'agent__user')
            .order_by('member__first_name')
        )

        self.fields['enrollment'].label_from_instance = (
            lambda obj: (
                f'{obj.member.member_no} - {obj.member.full_name} '
                f'({obj.plan.name})'
            )
        )

        self.fields['assignment'].label_from_instance = (
            lambda obj: f'{obj.agent.agent_no} - {obj.agent.full_name}'
        )

        # An agent can only collect for members assigned to that agent.
        if user and user.role == 'AGENT':
            self.fields['assignment'].queryset = (
                self.fields['assignment'].queryset.filter(
                    agent__user=user
                )
            )
            self.fields['enrollment'].queryset = (
                self.fields['enrollment'].queryset.filter(
                    member__assignments__agent__user=user,
                    member__assignments__is_active=True,
                ).distinct()
            )

        self.fields['collection_date'].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()

        enrollment = cleaned_data.get('enrollment')
        assignment = cleaned_data.get('assignment')
        payment_method = cleaned_data.get('payment_method')
        transaction_reference = cleaned_data.get('transaction_reference')

        if enrollment and assignment:
            if enrollment.member_id != assignment.member_id:
                self.add_error(
                    'assignment',
                    'This agent is not assigned to the selected member.'
                )

        if (
            payment_method == Collection.PaymentMethod.BANK_TRANSFER
            and not transaction_reference
        ):
            self.add_error(
                'transaction_reference',
                'Enter the bank transfer reference.'
            )

        return cleaned_data


class CollectionRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Reason for rejection',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this payment is being rejected.',
        }),
    )