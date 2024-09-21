import os
import re
from enum import Enum, auto
from PyPDF2 import PdfReader
from typing import List


class TransactionType(Enum):
    DEDUCTION = auto()
    DEPOSIT = auto()
    CHECK = auto()
    

class ParserState(Enum):
    START = auto()
    FIND_TOTALS = auto()
    FIND_DEPOSITS = auto()
    READ_DEPOSITS = auto()
    FIND_CHECK_TRANSACTIONS = auto()
    READ_CHECK_TRANSACTIONS = auto()
    FIND_DEBIT_TRANSACTIONS = auto()
    READ_DEBIT_TRANSACTIONS = auto()
    READ_BANKING_DEDUCTIONS = auto()
    READ_ONLINE_DEDUCTIONS = auto()
    READ_OTHER_DEDUCTIONS = auto()
    PAGE_BREAK_DEBIT = auto()
    PAGE_BREAK_DEPOSITS = auto()
    PAGE_BREAK_ONLINE = auto()
    DONE = auto()

class BankTransaction:
    def __init__(self, date: str, type: TransactionType, amount: float, description: str):
        self.date = date
        self.type = type
        self.amount = amount
        self.description = description
    
    def __repr__(self):
        return f"Transaction(date='{self.date}', type={self.type}, amount={self.amount}, description='{self.description}')"

class BankStatement:
    def __init__(self, entries: List[BankTransaction], date: str):
        self.entries = entries
        self.date = date
        
    def append(self, target):
        if isinstance(target, BankTransaction):
            self.entries.append(target)

def parse_transaction_text(data: list):
    if not data:
        return []
    
    transactions: List[BankTransaction] = []
    total_deductions = 0.0
    total_deposits = 0.0
    state = ParserState.START
    
    for line in data:
        # print('LINE: ' + line)
        if re.search('Daily Balance Detail', line):
            state = ParserState.DONE
            break
        
        match state:
            case ParserState.START:
                if line == 'balance':
                    state = ParserState.FIND_TOTALS
            
            case ParserState.FIND_TOTALS:
                tokenized = [float(l.replace(',', '')) for l in line.split()]
                if not total_deductions and len(tokenized) == 4:
                    total_deposits = tokenized[1]
                    total_deductions = tokenized[2]
                    state = ParserState.FIND_DEPOSITS
            
            case ParserState.FIND_DEPOSITS:
                if re.search('Deposits and Other Additions There were', line):
                    state = ParserState.READ_DEPOSITS
            
            case ParserState.READ_DEPOSITS:
                if re.search('continued on next page', line):
                    state = ParserState.PAGE_BREAK_DEPOSITS
                elif re.search('Checks and Substitute Checks', line):
                    state = ParserState.READ_CHECK_TRANSACTIONS
                else:
                    record(transactions, TransactionType.DEPOSIT, line)
            
            # TODO what happens when we have more than one or two checks?
            case ParserState.READ_CHECK_TRANSACTIONS:
                if re.search('Gap in check sequence', line):
                    state = ParserState.FIND_DEBIT_TRANSACTIONS
                check_pattern = r'\d+ \d+\.\d{2} \d{2}/\d{2}'
                if re.search(check_pattern, line):
                    record(transactions, TransactionType.CHECK, line)
            
            case ParserState.FIND_DEBIT_TRANSACTIONS:
                if re.search('Banking/Debit Card Withdrawals and Purchases There were', line):
                    state = ParserState.READ_DEBIT_TRANSACTIONS
            
            case ParserState.READ_DEBIT_TRANSACTIONS:
                if re.search('continued on next page', line):
                    state = ParserState.PAGE_BREAK_DEBIT
                elif re.search('Banking Deductions totaling', line):
                    state = ParserState.READ_ONLINE_DEDUCTIONS
                else:
                    record(transactions, TransactionType.DEDUCTION, line)
            
            case ParserState.READ_ONLINE_DEDUCTIONS:
                if re.search('Other Deductions There were', line):
                    state = ParserState.READ_OTHER_DEDUCTIONS
                elif re.search('continued on next page', line):
                    state = ParserState.PAGE_BREAK_ONLINE
                else:
                    record(transactions, TransactionType.DEDUCTION, line)
            
            case ParserState.READ_OTHER_DEDUCTIONS:
                    record(transactions, TransactionType.DEDUCTION, line)
            
            case ParserState.PAGE_BREAK_DEPOSITS:
                if re.search('Date Amount Description', line):
                    state = ParserState.READ_DEPOSITS
            
            case ParserState.PAGE_BREAK_DEBIT:
                if re.search('Date Amount Description', line):
                    state = ParserState.READ_DEBIT_TRANSACTIONS
            
            case ParserState.PAGE_BREAK_ONLINE:
                if re.search('Date Amount Description', line):
                    state = ParserState.READ_ONLINE_DEDUCTIONS      
    
    # Parsing and validation
    sum_of_deductions = round(sum([float(t.amount) for t in transactions if t.type in (TransactionType.CHECK, TransactionType.DEDUCTION)]), 2)
    sum_of_deposits = round(sum([float(t.amount) for t in transactions if t.type == TransactionType.DEPOSIT]), 2)
    if sum_of_deductions != total_deductions:
        print(f'\033[93mDEDUCTION ERROR; EXPECTED {total_deductions}, GOT: {sum_of_deductions}\033[0m')
    else:
        print(f'\033[92mDEDUCTIONS MATCH!\033[0m {total_deductions} == {sum_of_deductions}')
    if sum_of_deposits != total_deposits:
        print(f'\033[93mDEPOSIT ERROR; EXPECTED {total_deposits}, GOT: {sum_of_deposits}\033[0m')
    else:
        print(f'\033[92mDEPOSITS MATCH!\033[0m {total_deposits} == {sum_of_deposits}')
    return transactions

def record(ledger: List[BankTransaction], type: TransactionType, entry: str):
    if not entry or len(entry) <= 0:
        return    
    match (type):
        case TransactionType.CHECK:
            if len(split := entry.split()) < 4:
                return
            for i in range(0, len(split), 4):
                check_num = split[i]
                amount = round(float(split[i+1].replace(',', '')), 2)
                date = split[i+2]
                reference = split[i+3]
                ledger.append(BankTransaction(date, type, amount, f'Check number: {check_num} [ref:{reference}]'))
        
        case TransactionType.DEDUCTION | TransactionType.DEPOSIT:
            pattern = re.compile(r'^\d{2}/\d{2} ')
            if pattern.match(entry):
                tokens = entry.split(maxsplit=2)
                if len(tokens) >= 3:
                    date = tokens[0]
                    amount = round(float(tokens[1].replace(',', '')), 2)
                    description = tokens[2]
                    ledger.append(BankTransaction(date, type, amount, description))
            elif len(ledger) > 1:
                ledger[-1].description += ' ' + entry

##############################################################################
##############################################################################
##############################################################################

def load_text_file_to_list(file_name):
    try:
        with open(file_name, 'r') as file:
            content = file.readlines()
            return [line.strip() for line in content]
    except FileNotFoundError:
        print(f"File {file_name} not found.")
        return []

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    try:
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None

def _dbg_convert_pdfs_to_text_files():
    # Get all PDF files in the current directory
    pdf_files = [f for f in os.listdir() if f.lower().endswith('.pdf')]
    
    # Process each PDF file
    for pdf_file in pdf_files:
        text = extract_text_from_pdf(pdf_file)
        if text:
            # Create a text file with the same name as the PDF
            txt_file_name = os.path.splitext(pdf_file)[0] + ".txt"
            with open(txt_file_name, 'w', encoding='utf-8') as txt_file:
                txt_file.write(text)
            print(f"Extracted text from {pdf_file} to {txt_file_name}")
        else:
            print(f"Failed to extract text from {pdf_file}")

# DEBUG
jun = load_text_file_to_list('jun.txt')
jul = load_text_file_to_list('jul.txt')
pjun = parse_transaction_text(jun)
pjul = parse_transaction_text(jul)