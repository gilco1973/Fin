# Financial Analysis System with OpenAI Agents

This system uses OpenAI Agents SDK to perform financial analysis using multiple specialized agents:

1. PDF Reader Agent: Extracts and analyzes financial information from PDF documents
2. Data Reader Agent: Processes financial data from CSV and Excel files
3. Analysis Agent: Performs comprehensive financial analysis using data from other agents
4. Report Generator Agent: Creates detailed PDF reports of the analysis

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

Run the main script:
```bash
python main.py
```

## Project Structure

- `agents/`: Contains all specialized agents
  - `pdf_reader.py`: PDF document processing agent
  - `data_reader.py`: CSV/Excel data processing agent
  - `analysis_agent.py`: Financial analysis agent
  - `report_generator.py`: PDF report generation agent
- `utils/`: Utility functions and helpers
- `main.py`: Main script to orchestrate the agents 