import itertools
import os
import re
from enum import Enum, auto
from PyPDF2 import PdfReader
from typing import List


class TransactionType(Enum):
    DEDUCTION = auto()
    DEPOSIT = auto()
    CHECK = auto()
    

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
    trans_type: TransactionType = None
    total_deductions = 0.0
    total_deposits = 0.0
    
    check_pattern = re.compile(r'\d+ \d+\.\d{2} \d{2}/\d{2}')
    trans_pattern = re.compile(r'^\d{2}/\d{2} (\d{1,3}(,\d{3})*|\d*)\.\d{2} ')
    totals_pattern = re.compile(r'^(\d{1,3}(?:,\d{3})*\.\d{2}-?)(?: (\d{1,3}(?:,\d{3})*\.\d{2}-?)){3}$')
    
    tail, head = itertools.tee(data)
    next(head)
    
    for line, next_line in zip(tail, head):
        if not total_deductions and totals_pattern.match(line):
            totals = []
            for l in line.split():
                total = l.replace(',','')
                if l.endswith('-'):
                    total = '-' + l[:-1]
                totals.append(float(total))
            total_deposits = totals[1]
            total_deductions = totals[2]
        elif re.search('Deposits and Other Additions There were', line):
            trans_type = TransactionType.DEPOSIT
        elif re.search('Checks and Substitute Checks', line):
            trans_type = TransactionType.CHECK
        elif re.search('Gap in check sequence', line):
            trans_type = TransactionType.DEDUCTION
        elif re.search('Daily Balance Detail', line):
            # Done 
            break
        
        # Processing the transaction
        if trans_type == TransactionType.CHECK and check_pattern.match(line):
            tokens = line.split()
            for i in range(0, len(tokens), 4):
                check_num = tokens[i]
                amount = round(float(tokens[i+1].replace(',', '')), 2)
                date = tokens[i+2]
                reference = tokens[i+3]
                transactions.append(BankTransaction(date, trans_type, amount, f'Check number: {check_num} [ref:{reference}]'))
        elif trans_type in (TransactionType.DEDUCTION, TransactionType.DEPOSIT) and trans_pattern.match(line):
            tokens = line.split()
            date = tokens[0]
            amount = round(float(tokens[1].replace(',', '')), 2)
            description = ' '.join(tokens[2:])
            if not trans_pattern.match(next_line):
                description += ' ' + next_line
            transactions.append(BankTransaction(date, trans_type, amount, description))
    
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
aug = load_text_file_to_list('aug.txt')
pjun = parse_transaction_text(jun)
pjul = parse_transaction_text(jul)
paug = parse_transaction_text(aug)
from pprint import pprint
pp =  lambda v: pprint(v)
