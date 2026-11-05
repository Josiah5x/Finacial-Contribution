from django import forms
from django.core.exceptions import ValidationError

from .models import Expense, ExpenseCategory


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Transportation',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'title',
            'category',
            'description',
            'amount',
            'expense_date',
            'paid_to',
            'receipt',
            'notes',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter expense title',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'expense_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'paid_to': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Beneficiary or supplier',
            }),
            'receipt': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(
            is_active=True
        ).order_by('name')


class ExpensePaymentForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['payment_method', 'notes']
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }


class ExpenseRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Reason for rejection',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this expense is being rejected',
        })
    )