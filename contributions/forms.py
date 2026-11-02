from django import forms
from .models import ContributionPlan


class ContributionPlanForm(forms.ModelForm):

    class Meta:
        model = ContributionPlan
        fields = [
            'name',
            'code',
            'description',
            'frequency',
            'amount',
            'collection_weekday',
            'collection_day',
            'duration_days',
            'is_active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Standard Daily Savings'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. DAILY001'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this contribution plan'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
                'placeholder': 'Enter contribution amount'
            }),
            'collection_weekday': forms.Select(attrs={
                'class': 'form-select'
            }),
            'collection_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '28'
            }),
            'duration_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Leave blank for ongoing plan'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()