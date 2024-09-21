from PyPDF4 import PdfReader
import tabula
import os
import re


def get_pdfs(directory):
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf") \
            and filename.startswith("Statement"):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

def extract_pdf_data(pdfs):
    book = []
    for file in pdfs:
        reader = PdfReader(file)
        combined_text = ""
        for page in reader.pages:
            combined_text += page.extract_text()
        book.append(combined_text)
    return book
        

def extract_transactions(page_text):
    transactions = []
    lines = page_text.split('\n')
    in_transactions = False
    continued_next_page = False
    for line in lines:
        if 'Online and Electronic Banking Deductions' in line:
            print('Found last section')
            break  # End transactions section
        if 'continued on next page' in line:
            print('Found end of page')
            continued_next_page = True
            continue  # Skip to next line
        if 'Date Amount Description' in line:
            print('Found transaction section')
            in_transactions = True
            continue  # Skip to next line (avoiding header)
        if in_transactions:
            if continued_next_page and 'Date Amount Description' in line:
                print('This part is strange to me')
                continued_next_page = False
                continue  # Skip header line on continued page
            # Use regex to match lines starting with a date and a decimal value
            match = re.match(r'^\d{1,2}/\d{1,2} \d+\.\d+', line)
            if not match:
                continue  # Ignore the line if it doesn't match the expected format
            print(f'ADDING TRANSACTION: {line}')
            transactions.append(line)
    return transactions

def _test(pdf_path):
    tables = tabula.read_pdf(pdf_path, pages='all', lattice=True)
    structured_text = []
    for df in tables:
        structured_text.append(df.to_string(index=False))
    return structured_text
_path = 'C:\\Users\\Matt\\source\\repos\\pncreader\\Statement_Jan_24_2024.pdf'
pdfs = get_pdfs("C:\\Users\\Matt\\source\\repos\\pncreader")
book = extract_pdf_data(pdfs)
trans = extract_transactions(book[0])

