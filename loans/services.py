from decimal import Decimal
from django.db.models import Sum

from wallets.models import WalletTransaction
from loans.models import Loan


LOAN_ELIGIBILITY_PERCENTAGE = Decimal('25.00')


def calculate_loan_eligibility(member):
    """
    Calculate loan eligibility using 25% of verified contributions.

    Existing outstanding loans are deducted from the
    member's borrowing limit.
    """

    # Total contributions credited to the member's wallet
    verified_contributions = (
        WalletTransaction.objects.filter(
            wallet__member=member,
            transaction_type=WalletTransaction.TransactionType.CREDIT,
            collection__isnull=False,
            collection__status='VERIFIED',
        ).aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )

    # Maximum borrowing limit
    maximum_loan = (
        verified_contributions
        * LOAN_ELIGIBILITY_PERCENTAGE
        / Decimal('100')
    ).quantize(Decimal('0.01'))

    # Outstanding balances on previous loans
    outstanding_loans = Decimal('0.00')

    previous_loans = Loan.objects.filter(
        member=member,
        status__in=[
            Loan.Status.DISBURSED,
            Loan.Status.APPROVED,
        ]
    )

    for loan in previous_loans:
        outstanding_loans += loan.outstanding_balance

    eligible_amount = max(
        maximum_loan - outstanding_loans,
        Decimal('0.00')
    )

    return {
        'verified_contributions': verified_contributions,
        'eligibility_percentage': LOAN_ELIGIBILITY_PERCENTAGE,
        'maximum_loan': maximum_loan,
        'outstanding_loans': outstanding_loans,
        'eligible_amount': eligible_amount,
    }