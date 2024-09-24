import itertools
import logging
import os
import re
from enum import Enum, auto
from pypdf import PdfReader
from typing import List, Tuple

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)

log = logging.getLogger(__name__)

class TransactionType(Enum):
    DEDUCTION = auto()
    DEPOSIT = auto()
    CHECK = auto()

class Transaction:
    def __init__(self, date: str, type: TransactionType, amount: float, description: str):
        self.date = date
        self.type = type
        self.amount = amount
        self.description = description
    
    def __repr__(self):
        return f"Transaction(date='{self.date}', type={self.type}, amount={self.amount}, description='{self.description}')"
    
    def __eq__(self, other):
        if isinstance(other, Transaction):
            return (self.date == other.date and 
                    self.type == other.type and 
                    self.amount == other.amount and 
                    self.description == other.description)
        return False
    
    def __hash__(self):
        return hash((self.date, self.type, self.amount, self.description))

class Statement:
    def __init__(self, entries: List[Transaction], date: str):
        self.entries = entries
        self.date = date
        
    def append(self, target):
        if isinstance(target, Transaction):
            self.entries.append(target)

def parse_transaction_text(data: list):
    if not data:
        log.warning('No data provided to parse!')
        return []
    
    transactions: List[Transaction] = []
    trans_type: TransactionType = None
    total_deductions = 0.0
    total_deposits = 0.0
    
    check_pattern = re.compile(r'\d+ \d+\.\d{2} \d{2}/\d{2}')
    trans_pattern = re.compile(r'^\d{2}/\d{2} (\d{1,3}(,\d{3})*|\d*)\.\d{2} ')
    totals_pattern = re.compile(r'^(\d{1,3}(?:,\d{3})*\.\d{2}-?)(?: (\d{1,3}(?:,\d{3})*\.\d{2}-?)){3}$')
    
    # When processing transactions, if the next line contains any of these markers,
    # it's probably not part of the previous transaction description
    reserved: Tuple[str] = (
        'Deposits And Other Additions',
        'Checks and Substitute Checks',
        'Gap in check sequence',
        'Daily Balance Detail',
    )
    
    # This is just to easily get the next line while processing; two iters, one ahead by an item
    head, tail = itertools.tee(data)
    next(tail)
    
    log.info('Begin processing data...')
    for line, next_line in zip(head, tail):
        if not total_deductions and totals_pattern.match(line):
            totals = []
            for l in line.split():
                total = l.replace(',','')
                if l.endswith('-'):
                    total = '-' + l[:-1]
                totals.append(float(total))
            total_deposits = totals[1]
            total_deductions = totals[2]
        
        if not total_deductions or not total_deposits:
            log.warning('Could not parse total deduction amount. Possibly corrupted PDF file!')
            break
        
        if re.search('Deposits and Other Additions', line):
            log.info('Totals found,')
            trans_type = TransactionType.DEPOSIT
        elif re.search('Checks and Substitute Checks', line):
            log.info('End deposit section, begin check lookup...')
            trans_type = TransactionType.CHECK
        elif re.search('Gap in check sequence', line):
            log.info('End check section, begin transaction lookup...')
            trans_type = TransactionType.DEDUCTION
        elif re.search('Daily Balance Detail', line):
            log.info('Processing complete!')
            break
        
        # Processing the transaction
        if trans_type == TransactionType.CHECK and check_pattern.match(line):
            log.info('Processing checks...')
            tokens = line.split()
            for i in range(0, len(tokens), 4):
                check_num = tokens[i]
                amount = round(float(tokens[i+1].replace(',', '')), 2)
                date = tokens[i+2]
                reference = tokens[i+3]
                description = f'Check number: {check_num} [ref:{reference}]'
                transactions.append(Transaction(date, trans_type, amount, description))
        elif trans_type in (TransactionType.DEDUCTION, TransactionType.DEPOSIT) and trans_pattern.match(line):
            log.info(f'Found transaction ID{len(transactions)}')
            tokens = line.split()
            date = tokens[0]
            amount = round(float(tokens[1].replace(',', '')), 2)
            description = ' '.join(tokens[2:])
            if not trans_pattern.match(next_line):
                found = False
                for r in reserved:
                    if re.search(r, next_line):
                        found = True
                if not found:
                    description += ' ' + next_line
            transactions.append(Transaction(date, trans_type, amount, description))
    
    # Amount validation
    sum_of_deductions = round(sum([float(t.amount) for t in transactions if t.type in (TransactionType.CHECK, TransactionType.DEDUCTION)]), 2)
    sum_of_deposits = round(sum([float(t.amount) for t in transactions if t.type == TransactionType.DEPOSIT]), 2)
    if sum_of_deductions != total_deductions:   
        log.fatal(f'\033[93mERROR; DEDUCTIONS TOTAL EXPECTED {total_deductions}, GOT: {sum_of_deductions}\033[0m')
    else:
        log.info(f'\033[92mDeduction totals match!\033[0m found in PDF: {total_deductions}, total of found deposits: {sum_of_deductions}')
    if sum_of_deposits != total_deposits:
        log.fatal(f'\033[93mERROR; DEPOSIT TOTAL EXPECTED {total_deposits}, GOT: {sum_of_deposits}\033[0m')
    else:
        log.info(f'\033[92mDeposit totals match!\033[0m found in PDF: {total_deposits}, total of found deposits: {sum_of_deposits}')
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
        log.exception(f"Error reading {pdf_path}: {e}")
        return None

def _dbg_convert_pdfs_to_text_files():
    # Get all PNC Statement PDFs in the current directory
    
    statement_pattern = re.compile(r'^Statement_[A-Za-z]{3}_(\d{1,2})_(\d{4})\.pdf$')
    
    pdf_files = [f for f in os.listdir() if statement_pattern.match(f)]
    
    if not pdf_files:
        log.fatal('Could not find any PNC Statements. Ensure they are in this format: Statement_Mmm_DD_YYYY.pdf')
        return
    
    # Process each PDF file
    for pdf_file in pdf_files:
        text = extract_text_from_pdf(pdf_file)
        if text:
            # Create a text file with the same name as the PDF
            txt_file_name = os.path.splitext(pdf_file)[0] + ".txt"
            with open(txt_file_name, 'w', encoding='utf-8') as txt_file:
                txt_file.write(text)
            log.info(f"Extracted text from {pdf_file}, exported to {txt_file_name}")
        else:
            log.exception(f"Failed to extract text from {pdf_file}")
