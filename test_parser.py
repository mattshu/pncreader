import pytest
from parser import parse_transaction_text, Transaction, TransactionType

@pytest.fixture
def sample_data():
    return [
        "Virtual Wallet With Performance Spend",
        "StatementPNC Bank",
        "For the period 07/24/2024 to08/22/2024 Number of enclosures: 0",
        " PNC Bank Online Banking at pnc.com",
        "PNC accepts Telecommunications Relay Service",
        "(TRS) calls.",
        "balance",
        "146.84 205.00 1,805.55 5.50-",
        "Total for this Period Total Year to Date",
        "Total Overdraft Fees .00 72.00",
        "Total NSF/OD Refunds .00 72.00",
        "Deposits and Other Additions There were 2 Deposits and Other",
        "07/25 200.00 ATM Deposit 123 Street Rd Town",
        "ST",
        "Deposits and Other Additions continued on next pagePage 1 of ",
        "5Virtual Wallet With Performance Spend Statement",
        "08/22 5.00 Other Fin Inst ATM Surcharge Reimb",
        "Checks and Substitute Checks",
        "156 200.00 07/24 012345678 157 500.00 08/05 9876543210",
        "* Gap in check sequence There were 2 checks listed totaling",
        "07/29 5.00 1234 Debit Card Purchase Wendell 155",
        "Town ST",
        "07/29 1,100.55 1234 Debit Card Purchase Wm Supercenter",
        "#1234",
        "Banking/Debit Card Withdrawals and Purchases continued on next pagePage 2 of ",
        "5Virtual Wallet With Performance Spend Statement",
        "Daily Balance Detail",
        "Member FDIC",
        " Equal Housing LenderPage 5 of",
        "5",
    ]

@pytest.fixture
def expected_transactions():
    return [
        Transaction(date="07/25", type=TransactionType.DEPOSIT, amount=200.00, description="ATM Deposit 123 Street Rd Town ST"),
        Transaction(date="08/22", type=TransactionType.DEPOSIT, amount=5.00, description="Other Fin Inst ATM Surcharge Reimb"),
        Transaction(date="07/24", type=TransactionType.CHECK, amount=200.00, description="Check number: 156 [ref:012345678]"),
        Transaction(date="08/05", type=TransactionType.CHECK, amount=500.00, description="Check number: 157 [ref:9876543210]"),
        Transaction(date="07/29", type=TransactionType.DEDUCTION, amount=5.00, description="1234 Debit Card Purchase Wendell 155 Town ST"),
        Transaction(date="07/29", type=TransactionType.DEDUCTION, amount=1100.55, description="1234 Debit Card Purchase Wm Supercenter #1234"),
    ]

def test_parse_transaction_text(sample_data, expected_transactions):
    transactions = parse_transaction_text(sample_data)
    assert sorted(transactions, key=lambda x: (x.amount)) == sorted(expected_transactions, key=lambda x: (x.amount))

def test_total_deductions(sample_data):
    transactions = parse_transaction_text(sample_data)
    total_deductions = sum(t.amount for t in transactions if t.type in (TransactionType.CHECK, TransactionType.DEDUCTION))
    assert total_deductions == 1805.55

def test_total_deposits(sample_data):
    transactions = parse_transaction_text(sample_data)
    total_deposits = sum(t.amount for t in transactions if t.type == TransactionType.DEPOSIT)
    assert total_deposits == 205.00

def test_empty_data():
    transactions = parse_transaction_text([])
    assert transactions == []
