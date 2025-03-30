from typing import Dict, List
from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import BaseTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv
import pandas as pd
from decimal import Decimal
import re
from datetime import datetime
import json

load_dotenv()

class AnalysisTool(BaseTool):
    name: str = "analysis_tool"
    description: str = "Analyzes financial data from multiple sources and provides comprehensive insights"
    
    def _extract_financial_data(self, text: str) -> Dict:
        """Extract financial information from text using regex patterns."""
        # Initialize financial data structure
        financial_data = {
            "transactions": [],
            "balances": [],
            "categories": set()
        }
        
        # Regular expressions for different financial patterns
        patterns = {
            "amount": r'\$[\d,]+\.?\d*',
            "date": r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            "category": r'(?:payment|deposit|withdrawal|transfer|salary|rent|utilities|groceries|shopping|entertainment)',
        }
        
        # Find all amounts in the text
        amounts = re.finditer(patterns["amount"], text, re.IGNORECASE)
        dates = re.finditer(patterns["date"], text)
        categories = re.finditer(patterns["category"], text, re.IGNORECASE)
        
        # Extract transactions
        lines = text.split('\n')
        for line in lines:
            transaction = {}
            
            # Find amount in line
            amount_match = re.search(patterns["amount"], line)
            if amount_match:
                amount_str = amount_match.group().replace('$', '').replace(',', '')
                transaction["amount"] = float(amount_str)
                
                # Determine if income or expense based on context
                if any(word in line.lower() for word in ['deposit', 'credit', 'salary', 'income']):
                    transaction["type"] = "income"
                else:
                    transaction["type"] = "expense"
            
            # Find date in line
            date_match = re.search(patterns["date"], line)
            if date_match:
                transaction["date"] = date_match.group()
            
            # Find category in line
            category_match = re.search(patterns["category"], line, re.IGNORECASE)
            if category_match:
                category = category_match.group().lower()
                transaction["category"] = category
                financial_data["categories"].add(category)
            
            if transaction:
                financial_data["transactions"].append(transaction)
        
        return financial_data

    def _analyze_transactions(self, transactions: List[Dict]) -> Dict:
        """Analyze transactions to generate financial insights."""
        analysis = {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net_cash_flow": 0.0,
            "expense_by_category": {},
            "income_by_category": {},
            "monthly_summary": {},
            "insights": []
        }
        
        for transaction in transactions:
            amount = transaction.get("amount", 0)
            category = transaction.get("category", "uncategorized")
            trans_type = transaction.get("type", "expense")
            
            if trans_type == "income":
                analysis["total_income"] += amount
                if category not in analysis["income_by_category"]:
                    analysis["income_by_category"][category] = 0
                analysis["income_by_category"][category] += amount
            else:
                analysis["total_expenses"] += amount
                if category not in analysis["expense_by_category"]:
                    analysis["expense_by_category"][category] = 0
                analysis["expense_by_category"][category] += amount
        
        # Calculate net cash flow
        analysis["net_cash_flow"] = analysis["total_income"] - analysis["total_expenses"]
        
        # Generate insights
        analysis["insights"] = self._generate_insights(analysis)
        
        return analysis
    
    def _generate_insights(self, analysis: Dict) -> List[str]:
        """Generate insights based on the financial analysis."""
        insights = []
        
        # Overall financial health
        if analysis["net_cash_flow"] > 0:
            insights.append(f"Positive net cash flow of ${analysis['net_cash_flow']:.2f}")
        else:
            insights.append(f"Negative net cash flow of ${abs(analysis['net_cash_flow']):.2f}")
        
        # Income insights
        insights.append(f"Total income: ${analysis['total_income']:.2f}")
        if analysis["income_by_category"]:
            top_income = max(analysis["income_by_category"].items(), key=lambda x: x[1])
            insights.append(f"Main income source: {top_income[0]} (${top_income[1]:.2f})")
        
        # Expense insights
        insights.append(f"Total expenses: ${analysis['total_expenses']:.2f}")
        if analysis["expense_by_category"]:
            top_expense = max(analysis["expense_by_category"].items(), key=lambda x: x[1])
            insights.append(f"Largest expense category: {top_expense[0]} (${top_expense[1]:.2f})")
        
        # Savings rate
        if analysis["total_income"] > 0:
            savings_rate = (analysis["net_cash_flow"] / analysis["total_income"]) * 100
            insights.append(f"Savings rate: {savings_rate:.1f}%")
        
        return insights
    
    def _run(self, input: str) -> Dict:
        """Analyze financial data from multiple sources."""
        try:
            # Parse the input data
            data = eval(input)  # Convert string representation back to dict
            
            all_transactions = []
            all_categories = set()
            
            # Process PDF data
            if data.get("pdf_data"):
                for pdf_data in data["pdf_data"]:
                    if isinstance(pdf_data, dict) and "data" in pdf_data:
                        # Extract insights from PDF analysis
                        insights = pdf_data["data"].get("insights", {})
                        if isinstance(insights, dict):
                            # Extract transactions from the insights
                            transactions = insights.get("transactions", [])
                            if transactions:
                                all_transactions.extend(transactions)
                            
                            # Extract categories from the insights
                            categories = insights.get("summary", {}).get("categories", {})
                            if categories:
                                all_categories.update(categories.keys())
                        
                        # Also try to extract from raw text if available
                        raw_text = pdf_data["data"]["output"].get("raw_text", "")
                        if raw_text:
                            financial_data = self._extract_financial_data(raw_text)
                            all_transactions.extend(financial_data["transactions"])
                            all_categories.update(financial_data["categories"])
            
            # Process structured data
            if data.get("data_data"):
                for data_item in data["data_data"]:
                    if isinstance(data_item, dict) and "data" in data_item:
                        # Assuming structured data is in a similar format
                        financial_data = self._extract_financial_data(str(data_item["data"]))
                        all_transactions.extend(financial_data["transactions"])
                        all_categories.update(financial_data["categories"])
            
            # Perform comprehensive analysis
            analysis = self._analyze_transactions(all_transactions)
            
            return {
                "summary": "Comprehensive Financial Analysis",
                "details": {
                    "transactions": all_transactions,
                    "categories": list(all_categories),
                    "analysis": analysis
                }
            }
            
        except Exception as e:
            raise Exception(f"Error analyzing data: {str(e)}")

class AnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4-turbo-preview",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a financial analysis expert. Your task is to analyze financial data from multiple sources "
                "and provide comprehensive insights. Focus on:\n"
                "1. Income and expense patterns\n"
                "2. Financial trends and anomalies\n"
                "3. Key metrics and ratios\n"
                "4. Recommendations for improvement\n"
                "Use the analysis_tool to process the data and generate insights."
            )),
            HumanMessage(content="Please analyze the following financial data:\n\n{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        self.tool = AnalysisTool()
        
    def analyze_data(self, data: Dict) -> Dict:
        """Analyze financial data from multiple sources."""
        try:
            # First, analyze the data directly using the tool
            result = self.tool._run(str(data))
            
            # Then, let the agent provide additional insights
            agent_result = self.llm.invoke(
                self.prompt.format_messages(input=str(data))
            )
            
            # Ensure the result has the expected structure
            if isinstance(result, dict):
                analysis_data = result
            else:
                analysis_data = {
                    "summary": "Financial Analysis",
                    "details": {
                        "transactions": [],
                        "categories": [],
                        "analysis": {
                            "total_income": 0.0,
                            "total_expenses": 0.0,
                            "net_cash_flow": 0.0,
                            "expense_by_category": {},
                            "income_by_category": {},
                            "monthly_summary": {},
                            "insights": []
                        }
                    }
                }
            
            return {
                "status": "success",
                "data": {
                    "output": analysis_data,
                    "insights": agent_result.content
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def analyze_combined_data(self, pdf_data: Dict, csv_data: Dict) -> Dict:
        """Analyze combined data from PDF and CSV sources."""
        try:
            # Combine data from different sources
            combined_data = {
                "pdf_analysis": pdf_data.get("analysis", ""),
                "data_analysis": csv_data.get("analysis", ""),
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            result = self.llm.invoke(
                self.prompt.format_messages(input=f"Please perform a comprehensive financial analysis using the following data:\n"
                        f"PDF Analysis: {combined_data['pdf_analysis']}\n"
                        f"Data Analysis: {combined_data['data_analysis']}\n"
                        f"Provide key insights, trends, and recommendations.")
            )
            
            return {
                "status": "success",
                "analysis": result.content,
                "combined_data": combined_data
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 