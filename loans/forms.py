from django import forms
from .models import Loan


class LoanApplicationForm(forms.ModelForm):

    REPAYMENT_PERIODS = [
        (1, '1 month'),
        (2, '2 months'),
        (3, '3 months'),
        (6, '6 months'),
        (9, '9 months'),
        (12, '12 months'),
    ]

    repayment_months = forms.TypedChoiceField(
        choices=REPAYMENT_PERIODS,
        coerce=int,
        label='Repayment Period',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Loan
        fields = ['requested_amount', 'repayment_months', 'notes']

        widgets = {
            'requested_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter loan amount',
                'min': '1',
                'step': '0.01',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for requesting this loan',
            }),
        }

    def __init__(self, *args, eligibility=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.eligibility = eligibility or {}

        # Store the eligibility figures on the loan application.
        self.instance.verified_contributions = self.eligibility.get(
            'verified_contributions', 0
        )
        self.instance.eligibility_percentage = self.eligibility.get(
            'eligibility_percentage', 25
        )
        self.instance.eligible_amount = self.eligibility.get(
            'eligible_amount', 0
        )

    def clean_requested_amount(self):
        amount = self.cleaned_data['requested_amount']
        eligible_amount = self.eligibility.get('eligible_amount', 0)

        if amount <= 0:
            raise forms.ValidationError(
                'Loan amount must be greater than zero.'
            )

        if amount > eligible_amount:
            raise forms.ValidationError(
                'Your requested amount exceeds your eligible loan amount.'
            )

        return amount


from decimal import Decimal
from django import forms
from .models import Loan


class LoanApprovalForm(forms.Form):
    approved_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        })
    )

    repayment_months = forms.TypedChoiceField(
        choices=[
            (1, '1 month'),
            (2, '2 months'),
            (3, '3 months'),
            (6, '6 months'),
            (9, '9 months'),
            (12, '12 months'),
        ],
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    interest_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.01'),
        initial=Decimal('10.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        })
    )


class LoanRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Reason for rejection',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
        })
    )