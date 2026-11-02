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


from django import forms
from members.models import Member
from .models import ContributionPlan, PlanEnrollment


class PlanEnrollmentForm(forms.ModelForm):

    class Meta:
        model = PlanEnrollment
        fields = [
            'member',
            'plan',
            'start_date',
            'end_date',
            'notes',
        ]

        widgets = {
            'member': forms.Select(attrs={
                'class': 'form-select'
            }),
            'plan': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional enrolment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['member'].queryset = Member.objects.filter(
            status=Member.Status.ACTIVE
        ).order_by('first_name', 'last_name')

        self.fields['plan'].queryset = ContributionPlan.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['member'].label_from_instance = (
            lambda member: f'{member.member_no} - {member.full_name}'
        )

        self.fields['plan'].label_from_instance = (
            lambda plan: f'{plan.name} - ₦{plan.amount:,.2f} ({plan.get_frequency_display()})'
        )


    