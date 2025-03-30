from typing import Dict, List
import pandas as pd
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

load_dotenv()

class DataReaderTool(BaseTool):
    name: str = "data_reader"
    description: str = "Reads and analyzes financial data from CSV and Excel files"
    
    def _run(self, file_path: str) -> Dict:
        """Read a CSV or Excel file and extract its content."""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return {"content": "Unsupported file format", "status": "error"}
            
            # Convert DataFrame to string representation
            data_summary = df.describe().to_string()
            return {
                "content": data_summary,
                "columns": df.columns.tolist(),
                "shape": df.shape,
                "status": "success"
            }
        except Exception as e:
            return {"content": str(e), "status": "error"}

class DataReaderAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4-turbo-preview",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.tools = [DataReaderTool()]
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a financial data analyzer. Extract and analyze financial information from CSV and Excel files."),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True
        )
    
    def analyze_data(self, file_path: str) -> Dict:
        """Analyze a CSV or Excel file and extract financial information."""
        try:
            result = self.agent_executor.invoke({
                "input": f"Please analyze this data file at {file_path} and extract key financial information. "
                        f"Focus on financial metrics, trends, and patterns in the data."
            })
            return {
                "status": "success",
                "analysis": result["output"],
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "file_path": file_path
            } 