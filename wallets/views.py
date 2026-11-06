from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from decimal import Decimal
from django.shortcuts import render, get_object_or_404

from accounts.decorators import role_required
from django.shortcuts import render, redirect

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from members.models import Member
from .models import Wallet, WalletTransaction

User = get_user_model()




@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def wallet_list(request):

    wallets = Wallet.objects.select_related('member').all()

    # Members can only see their own wallet.
    if request.user.role == User.Role.MEMBER:
        wallets = wallets.filter(member__user=request.user)

    search = request.GET.get('q', '').strip()

    if search and request.user.role != User.Role.MEMBER:
        wallets = wallets.filter(
            Q(member__member_no__icontains=search)
            | Q(member__first_name__icontains=search)
            | Q(member__last_name__icontains=search)
            | Q(member__phone__icontains=search)
        )

    paginator = Paginator(wallets, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'wallets': page_obj.object_list,
        'page_obj': page_obj,
        'search': search,
    }

    return render(request, 'wallets/wallet_list.html', context)


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def wallet_detail(request, pk):

    wallet = get_object_or_404(
        Wallet.objects.select_related('member'),
        pk=pk,
    )

    # Prevent members from accessing another member's wallet.
    if (
        request.user.role == User.Role.MEMBER
        and wallet.member.user_id != request.user.id
    ):
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.error(request, 'You cannot access this wallet.')
        return redirect('wallets:wallet_list')

    transactions = wallet.transactions.select_related(
        'created_by',
        'collection',
    ).all()

    paginator = Paginator(transactions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'wallet': wallet,
        'transactions': page_obj.object_list,
        'page_obj': page_obj,
    }

    return render(request, 'wallets/wallet_detail.html', context)

# ////////////////////////////
@login_required
def member_transactions(request):
    if request.user.role != 'MEMBER':
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        return redirect('dashboard')

    wallet = Wallet.objects.filter(member=member).first()

    if not wallet:
        transactions = WalletTransaction.objects.none()
    else:
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')

    transaction_type = request.GET.get('type', '')

    if transaction_type in ['CREDIT', 'DEBIT']:
        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    paginator = Paginator(transactions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'member': member,
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
        'transaction_type': transaction_type,
    }

    return render(
        request,
        'wallets/member_transactions.html',
        context
    )


@login_required
def member_wallet(request):
    if request.user.role != User.Role.MEMBER:
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        return redirect('member_dashboard')

    wallet = Wallet.objects.filter(member=member).first()

    if not wallet:
        return render(request, 'wallets/member_wallet.html', {
            'wallet': None,
            'member': member,
        })

    return redirect('wallets:wallet_detail', pk=wallet.pk)


@login_required
def member_statement(request):
    if request.user.role != User.Role.MEMBER:
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        messages.error(request, "Member profile not found.")
        return redirect('member_dashboard')

    wallet = Wallet.objects.filter(member=member).first()

    if not wallet:
        return render(request, 'wallets/member_statement.html', {
            'member': member,
            'wallet': None,
            'transactions': [],
        })

    today = timezone.localdate()
    start_date = parse_date(request.GET.get('start_date', '')) or today.replace(day=1)
    end_date = parse_date(request.GET.get('end_date', '')) or today

    if start_date > end_date:
        messages.error(request, "Start date cannot be after end date.")
        start_date = today.replace(day=1)
        end_date = today

    # Transactions before the selected period
    previous_transaction = wallet.transactions.filter(
        created_at__date__lt=start_date
    ).order_by('-created_at').first()

    opening_balance = (
        previous_transaction.balance_after
        if previous_transaction
        else Decimal('0.00')
    )

    # Transactions within the selected period
    transactions = wallet.transactions.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by('created_at')

    totals = transactions.aggregate(
        total_credits=Sum(
            'amount',
            filter=Q(transaction_type=WalletTransaction.TransactionType.CREDIT)
        ),
        total_debits=Sum(
            'amount',
            filter=Q(transaction_type=WalletTransaction.TransactionType.DEBIT)
        ),
    )

    total_credits = totals['total_credits'] or Decimal('0.00')
    total_debits = totals['total_debits'] or Decimal('0.00')

    last_transaction = transactions.order_by('-created_at').first()

    closing_balance = (
        last_transaction.balance_after
        if last_transaction
        else opening_balance
    )

    context = {
        'member': member,
        'wallet': wallet,
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'today': today,
    }

    return render(request, 'wallets/member_statement.html', context)



@login_required
def member_statement_pdf(request):
    if request.user.role != User.Role.MEMBER:
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        messages.error(request, "Member profile not found.")
        return redirect('member_dashboard')

    wallet = Wallet.objects.filter(member=member).first()

    if not wallet:
        messages.error(request, "Your wallet is not available.")
        return redirect('member_dashboard')

    today = timezone.localdate()

    start_date = (
        parse_date(request.GET.get('start_date', ''))
        or today.replace(day=1)
    )

    end_date = (
        parse_date(request.GET.get('end_date', ''))
        or today
    )

    if start_date > end_date:
        messages.error(request, "Invalid statement date range.")
        return redirect('wallets:member_statement')

    transactions = wallet.transactions.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).order_by('created_at', 'pk')

    previous_transaction = wallet.transactions.filter(
        created_at__date__lt=start_date
    ).order_by('-created_at', '-pk').first()

    opening_balance = (
        previous_transaction.balance_after
        if previous_transaction
        else Decimal('0.00')
    )

    total_credits = Decimal('0.00')
    total_debits = Decimal('0.00')

    for transaction in transactions:
        if transaction.transaction_type == WalletTransaction.TransactionType.CREDIT:
            total_credits += transaction.amount
        else:
            total_debits += transaction.amount

    last_transaction = transactions.order_by(
        '-created_at', '-pk'
    ).first()

    closing_balance = (
        last_transaction.balance_after
        if last_transaction
        else opening_balance
    )

    # Create PDF in memory
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CompanyTitle',
        parent=styles['Title'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#08264b'),
        alignment=TA_CENTER,
        spaceAfter=5,
    ))

    styles.add(ParagraphStyle(
        name='StatementTitle',
        parent=styles['Heading2'],
        fontSize=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0758d8'),
        spaceAfter=15,
    ))

    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
    ))

    elements = []

    # Header
    elements.append(Paragraph(
        "DAILYCOLLECT",
        styles['CompanyTitle']
    ))

    elements.append(Paragraph(
        "MEMBER CONTRIBUTION STATEMENT",
        styles['StatementTitle']
    ))

    elements.append(Paragraph(
        f"<b>Member Name:</b> {member.full_name}",
        styles['Normal']
    ))

    elements.append(Paragraph(
        f"<b>Member Number:</b> {member.member_no}",
        styles['Normal']
    ))

    elements.append(Paragraph(
        f"<b>Statement Period:</b> "
        f"{start_date.strftime('%d %b %Y')} - "
        f"{end_date.strftime('%d %b %Y')}",
        styles['Normal']
    ))

    elements.append(Spacer(1, 12))

    # Financial summary
    summary_data = [
        ['Opening Balance', 'Total Contributions',
         'Total Withdrawals', 'Closing Balance'],

        [
            f"NGN {opening_balance:,.2f}",
            f"NGN {total_credits:,.2f}",
            f"NGN {total_debits:,.2f}",
            f"NGN {closing_balance:,.2f}",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[65 * mm, 65 * mm, 65 * mm, 65 * mm],
    )

    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor('#08264b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('BACKGROUND', (0, 1), (-1, 1),
         colors.HexColor('#f1f5f9')),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Transaction table
    transaction_data = [[
        'Date',
        'Reference',
        'Description',
        'Type',
        'Credit (NGN)',
        'Debit (NGN)',
        'Balance (NGN)',
    ]]

    for transaction in transactions:
        is_credit = (
            transaction.transaction_type
            == WalletTransaction.TransactionType.CREDIT
        )

        transaction_data.append([
            transaction.created_at.strftime('%d %b %Y'),
            transaction.reference or '-',
            Paragraph(
                transaction.description or '-',
                styles['SmallText']
            ),
            'Credit' if is_credit else 'Debit',
            f"{transaction.amount:,.2f}" if is_credit else '-',
            '-' if is_credit else f"{transaction.amount:,.2f}",
            f"{transaction.balance_after:,.2f}",
        ])

    if not transactions.exists():
        transaction_data.append([
            'No transactions found',
            '', '', '', '', '', ''
        ])

    transaction_table = Table(
        transaction_data,
        repeatRows=1,
        colWidths=[
            28 * mm,
            35 * mm,
            62 * mm,
            22 * mm,
            35 * mm,
            35 * mm,
            35 * mm,
        ],
    )

    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor('#0758d8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4,
         colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor('#f8fafc'),
        ]),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))

    elements.append(transaction_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "This statement is computer-generated by DailyCollect.",
        styles['SmallText']
    ))

    elements.append(Paragraph(
        f"Generated on: {today.strftime('%d %B %Y')}",
        styles['SmallText']
    ))

    # Generate PDF
    document.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="DailyCollect-Statement-'
        f'{member.member_no}.pdf"'
    )

    return response


