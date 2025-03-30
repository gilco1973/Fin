from typing import Dict, List
from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.tools import BaseTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import json
import re

load_dotenv()

class PDFReaderTool(BaseTool):
    name: str = "pdf_reader"
    description: str = "Reads and extracts financial information from PDF documents"
    
    def _extract_financial_data(self, text: str) -> Dict:
        """Extract financial information from text using regex patterns."""
        # Initialize financial data structure
        financial_data = {
            "transactions": [],
            "balances": [],
            "categories": set(),
            "statement_period": {"start_date": "", "end_date": ""},
            "account_info": {"account_number": "", "holder_name": ""},
            "balance_info": {
                "previous_balance": 0,
                "payments": 0,
                "other_credits": 0,
                "purchases": 0,
                "cash_advances": 0,
                "fees": 0,
                "interest": 0,
                "new_balance": 0
            },
            "sections": {
                "account_summary": [],
                "payments_credits": [],
                "transactions": []
            }
        }
        
        # Regular expressions for different financial patterns
        patterns = {
            "amount": r'\$[\d,]+\.?\d*|\d+\.\d{2}',
            "date": r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\w{3}\s+\d{1,2}',
            "category": r'(?:payment|deposit|withdrawal|transfer|salary|rent|utilities|groceries|shopping|entertainment|dining|transportation|housing|subscription|insurance|healthcare|education|travel|gifts|charity)',
            "balance": r'(?:balance|total|amount due|payment due).*?(?:\$[\d,]+\.?\d*|\d+\.\d{2})',
            "account": r'(?:account|acct|card).*?(?:\d{4}|\d{10,})',
            "holder": r'(?:holder|name|cardholder):\s*([A-Za-z\s]+)',
            "period": r'(?:period|statement|from).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            "credit_card": r'(?:credit card|visa|mastercard|amex|discover|capital one)',
            "transaction_line": r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+([A-Za-z0-9\s\-\.,&\'*]+?)(?:\s+\$[\d,]+\.?\d*|\s+\d+\.\d{2})*\s+(\$[\d,]+\.?\d*|\d+\.\d{2})',
            "payment": r'(?:payment|credit|refund|credit adjustment)',
            "credit_card_payment": r'(?:payment received|payment credited|payment posted|mobile payment|payment auth)',
            "section_header": r'(?:Account Summary|Payments, Credits and Adjustments|Transactions)'
        }
        
        # Determine if this is a credit card statement
        is_credit_card = bool(re.search(patterns["credit_card"], text, re.IGNORECASE))
        
        # Extract statement period
        period_match = re.search(patterns["period"], text, re.IGNORECASE)
        if period_match:
            financial_data["statement_period"]["start_date"] = period_match.group(1)
            financial_data["statement_period"]["end_date"] = period_match.group(2)
        
        # Extract account information
        account_match = re.search(patterns["account"], text, re.IGNORECASE)
        if account_match:
            financial_data["account_info"]["account_number"] = account_match.group()
        
        holder_match = re.search(patterns["holder"], text, re.IGNORECASE)
        if holder_match:
            financial_data["account_info"]["holder_name"] = holder_match.group(1).strip()
        
        # Process text by sections
        current_section = None
        lines = text.split('\n')
        for line in lines:
            # Check for section headers
            section_match = re.search(patterns["section_header"], line, re.IGNORECASE)
            if section_match:
                section_name = section_match.group().lower()
                # Map section names to internal keys
                if "account summary" in section_name:
                    current_section = "account_summary"
                elif "payments" in section_name:
                    current_section = "payments_credits"
                elif "transactions" in section_name:
                    current_section = "transactions"
                continue
            
            # Skip empty lines and headers
            if not line.strip() or any(header in line.lower() for header in ['date', 'description', 'amount', 'balance']):
                continue
            
            # Skip summary lines that contain percentages or specific patterns
            if '%' in line or any(pattern in line.lower() for pattern in [
                'purchases', 'cash advances', 'fees', 'interest',
                'ses', 'ces', 'p $0.00', 'other $',
                'credit limit', 'exchange rate', 'minimum payment',
                'available credit', 'cash advance limit'
            ]):
                continue

            # Skip lines that contain only amounts and no merchant/transaction information
            if re.match(r'^[\s\$]*[\d,]+\.?\d*[\s\$]*$', line.strip()):
                continue
            
            # Handle Account Summary section
            if current_section == "account_summary":
                line_lower = line.lower()
                # Skip percentage lines and summary headers
                if '%' in line or any(word in line_lower for word in ['purchases', 'cash advances', 'fees', 'interest']):
                    continue
                    
                if "previous balance" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["previous_balance"] = float(amount_str)
                elif "payments" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        if amount_str.startswith('-'):
                            amount_str = amount_str[1:]
                        financial_data["balance_info"]["payments"] = float(amount_str)
                elif "other credits" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["other_credits"] = float(amount_str)
                elif "purchases" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["purchases"] = float(amount_str)
                elif "cash advances" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["cash_advances"] = float(amount_str)
                elif "fees" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["fees"] = float(amount_str)
                elif "interest" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["interest"] = float(amount_str)
                elif "new balance" in line_lower:
                    amount_match = re.search(patterns["amount"], line)
                    if amount_match:
                        amount_str = amount_match.group().replace('$', '').replace(',', '')
                        financial_data["balance_info"]["new_balance"] = float(amount_str)
                continue
                
            transaction = {
                "type": "expense",  # Default type for credit card
                "amount": 0.0,
                "date": "",
                "category": "other",
                "description": line.strip(),
                "is_recurring": False
            }
            
            # Try to match transaction line pattern first
            trans_match = re.search(patterns["transaction_line"], line)
            if trans_match:
                # Skip if this is a summary line
                if any(pattern in line.lower() for pattern in ['ses', 'ces', 'p $0.00', 'other $']):
                    continue
                    
                # Extract date, description, and amount
                transaction["date"] = trans_match.group(1)  # Transaction date
                post_date = trans_match.group(2)  # Post date (we'll ignore this)
                transaction["description"] = trans_match.group(3).strip()  # Description without dates or amounts
                amount_str = trans_match.group(4).replace('$', '').replace(',', '')  # Only use the final amount
                
                # Skip if description is empty or contains only amounts
                if not transaction["description"] or re.match(r'^[\s\$]*[\d,]+\.?\d*[\s\$]*$', transaction["description"]):
                    continue
                    
                # Handle negative amounts (payments)
                if amount_str.startswith('-'):
                    amount_str = amount_str[1:]
                    transaction["amount"] = float(amount_str)
                else:
                    transaction["amount"] = float(amount_str)
            else:
                # Fall back to individual pattern matching
                amount_match = re.search(patterns["amount"], line)
                if amount_match:
                    amount_str = amount_match.group().replace('$', '').replace(',', '')
                    # Handle negative amounts (payments)
                    if amount_str.startswith('-'):
                        amount_str = amount_str[1:]
                        transaction["amount"] = float(amount_str)
                    else:
                        transaction["amount"] = float(amount_str)
                
                date_match = re.search(patterns["date"], line)
                if date_match:
                    transaction["date"] = date_match.group()
            
            # Handle transaction types based on section
            if is_credit_card:
                if current_section == "payments_credits":
                    transaction["type"] = "payment"  # Payments reduce the balance
                    transaction["category"] = "payment"
                    # Add to balance_info
                    financial_data["balance_info"]["payments"] += transaction["amount"]
                elif current_section == "transactions":
                    transaction["type"] = "expense"  # Regular transactions are expenses
                    # Add to balance_info
                    financial_data["balance_info"]["purchases"] += transaction["amount"]
                    # Categorize transactions
                    if "amazon" in transaction["description"].lower():
                        transaction["category"] = "shopping"
                    elif "restaurant" in transaction["description"].lower() or "cafe" in transaction["description"].lower():
                        transaction["category"] = "dining"
                    elif "apple.com" in transaction["description"].lower():
                        transaction["category"] = "subscription"
                    elif "godaddy" in transaction["description"].lower():
                        transaction["category"] = "business"
                    elif "garage" in transaction["description"].lower():
                        transaction["category"] = "parking"
                    elif "wegmans" in transaction["description"].lower():
                        transaction["category"] = "groceries"
            
            # Check for recurring transactions
            if any(word in line.lower() for word in ['monthly', 'subscription', 'recurring', 'automatic', 'membership']):
                transaction["is_recurring"] = True
            
            # Additional validation for transaction lines
            if trans_match:
                # Skip if this looks like a metadata line
                desc_lower = trans_match.group(3).lower()
                if any(pattern in desc_lower for pattern in [
                    'credit limit',
                    'exchange rate',
                    'minimum payment',
                    'available credit',
                    'cash advance limit',
                    'payment due',
                    'credit available'
                ]):
                    continue
            
            if transaction["amount"] > 0:  # Only add transaction if we found an amount
                financial_data["transactions"].append(transaction)
                # Add to appropriate section
                if current_section and current_section in financial_data["sections"]:
                    financial_data["sections"][current_section].append(transaction)
        
        # Calculate net change for credit card statements
        if is_credit_card:
            balance_info = financial_data["balance_info"]
            balance_info["net_change"] = (
                balance_info["previous_balance"] +
                balance_info["payments"] +
                balance_info["other_credits"] +
                balance_info["purchases"] +
                balance_info["cash_advances"] +
                balance_info["fees"] +
                balance_info["interest"] -
                balance_info["new_balance"]
            )
        
        return financial_data

    def _run(self, file_path: str) -> Dict:
        """Read a PDF file and extract its content."""
        try:
            # Remove any quotes from the file path
            file_path = file_path.strip("'\"")
            
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                # Extract financial information
                financial_data = self._extract_financial_data(text_content)
                
                # Calculate summary statistics
                total_income = sum(t["amount"] for t in financial_data["transactions"] if t["type"] == "income")
                total_expenses = sum(t["amount"] for t in financial_data["transactions"] if t["type"] == "expense")
                
                # Group transactions by category
                income_by_category = {}
                expense_by_category = {}
                recurring_items = []
                
                for t in financial_data["transactions"]:
                    if t["type"] == "income":
                        if t["category"] not in income_by_category:
                            income_by_category[t["category"]] = 0
                        income_by_category[t["category"]] += t["amount"]
                    else:
                        if t["category"] not in expense_by_category:
                            expense_by_category[t["category"]] = 0
                        expense_by_category[t["category"]] += t["amount"]
                    
                    if t["is_recurring"]:
                        recurring_items.append(f"{t['category']}: {t['amount']}")
                
                # Return structured data
                return {
                    "raw_text": text_content,
                    "metadata": {
                        "num_pages": len(pdf_reader.pages),
                        "file_name": os.path.basename(file_path)
                    },
                    "analysis": {
                        "statement_period": financial_data["statement_period"],
                        "account_info": financial_data["account_info"],
                        "balance_info": financial_data["balance_info"],
                        "transactions": financial_data["transactions"],
                        "balances": financial_data["balances"],
                        "categories": list(financial_data["categories"]),
                        "summary": {
                            "total_income": total_income,
                            "total_expenses": total_expenses,
                            "net_cash_flow": total_income - total_expenses,
                            "income_by_category": income_by_category,
                            "expense_by_category": expense_by_category,
                            "recurring_items": recurring_items
                        }
                    }
                }
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")

    def _arun(self, file_path: str) -> Dict:
        """Async version of _run."""
        raise NotImplementedError("Async version not implemented")

class PDFReaderAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4-turbo-preview",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a financial document analyzer specialized in extracting and analyzing information from bank statements "
                "and financial documents. Your task is to analyze the provided document content, which may be one of several "
                "related statements, and extract relevant financial information.\n\n"
                "Important: Each document you analyze is part of a larger set of financial statements. Your analysis should:\n"
                "1. Extract all financial information from the current document\n"
                "2. Be prepared for this data to be combined with other statements\n"
                "3. Note any references to previous or future statements\n"
                "4. Identify recurring transactions or patterns that might span multiple statements\n\n"
                "Extract the following information:\n"
                "1. Account information (account numbers, holder names)\n"
                "2. Transaction details (dates, amounts, descriptions)\n"
                "3. Balance information (opening, closing, changes)\n"
                "4. Income sources and expense categories\n"
                "5. Any fees, interest, or special transactions\n"
                "6. Statement period and any cross-references\n\n"
                "Provide a structured analysis that can be used for financial reporting and combined with other statements. "
                "Format your response as a JSON object with the following structure:\n"
                "{\n"
                '  "statement_period": { "start_date": "", "end_date": "" },\n'
                '  "account_info": { "account_number": "", "holder_name": "" },\n'
                '  "balance_info": { "opening": 0, "closing": 0, "change": 0 },\n'
                '  "transactions": [\n'
                '    { "date": "", "description": "", "amount": 0, "type": "income|expense", "category": "", "is_recurring": false }\n'
                "  ],\n"
                '  "summary": {\n'
                '    "total_income": 0,\n'
                '    "total_expenses": 0,\n'
                '    "net_change": 0,\n'
                '    "categories": { "category_name": amount },\n'
                '    "recurring_items": ["item1", "item2"]\n'
                "  },\n"
                '  "cross_references": {\n'
                '    "previous_statement": { "date": "", "balance": 0 },\n'
                '    "next_statement": { "date": "", "balance": 0 }\n'
                "  },\n"
                '  "insights": [\n'
                '    "insight1",\n'
                '    "insight2"\n'
                "  ]\n"
                "}"
            )),
            HumanMessage(content=(
                "Please analyze the following document content, keeping in mind this may be one of several related statements:\n\n"
                "{input}\n\n"
                "Focus on identifying:\n"
                "- Statement period and cross-references to other statements\n"
                "- Transaction patterns and recurring items\n"
                "- Income sources and their frequency\n"
                "- Expense categories and their patterns\n"
                "- Balance changes and their relationship to other statements\n"
                "- Important dates, amounts, and any unusual transactions"
            ))
        ])
        
    def analyze_pdf(self, file_path: str) -> Dict:
        """Analyze a PDF file using the agent."""
        try:
            # First, read the PDF content directly
            tool = PDFReaderTool()
            pdf_data = tool._run(file_path)
            
            # Extract text content for analysis
            text_content = pdf_data.get("raw_text", "")
            if not text_content:
                raise Exception("No text content extracted from PDF")
            
            # Let the model analyze the content
            result = self.llm.invoke(
                self.prompt.format_messages(input=text_content)
            )
            
            # Parse the response
            try:
                analysis = json.loads(result.content)
            except json.JSONDecodeError:
                analysis = {"error": "Failed to parse analysis as JSON"}
            
            # Combine the raw data with the analysis
            return {
                "status": "success",
                "data": {
                    "output": pdf_data,
                    "insights": analysis
                }
            }
        except Exception as e:
            print(f"Error analyzing PDF {file_path}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }