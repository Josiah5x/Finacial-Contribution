
from django import forms
from django.db.models import Q

from .models import Withdrawal
from members.models import Member


class WithdrawalRequestForm(forms.ModelForm):

    class Meta:
        model = Withdrawal
        fields = ['amount', 'reason']

        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter withdrawal amount',
                'min': '0.01',
                'step': '0.01',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for withdrawal',
            }),
        }


class WithdrawalPaymentForm(forms.ModelForm):

    class Meta:
        model = Withdrawal
        fields = ['payment_method', 'payment_reference', 'notes']

        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank transaction reference (if applicable)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        method = cleaned_data.get('payment_method')
        reference = cleaned_data.get('payment_reference', '').strip()

        if method == Withdrawal.PaymentMethod.BANK_TRANSFER and not reference:
            self.add_error(
                'payment_reference',
                'Enter the bank transfer reference.'
            )

        return cleaned_data


class WithdrawalRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Reason for rejection',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this request is rejected',
        })
    )
