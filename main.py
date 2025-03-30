import os
import argparse
from agents.pdf_reader import PDFReaderAgent
from agents.data_reader import DataReaderAgent
from agents.analysis_agent import AnalysisAgent
from agents.report_generator import ReportGeneratorAgent
import json
from datetime import datetime

def process_files(input_path: str, output_dir: str) -> None:
    """Process PDF files and generate a combined report."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize tools
        pdf_reader = PDFReaderAgent()
        report_generator = ReportGeneratorAgent()
        
        # Get list of PDF files from both CC and Bank directories
        pdf_files = []
        
        # Process CC directory
        cc_dir = os.path.join(input_path, "CC")
        if os.path.exists(cc_dir):
            cc_files = [os.path.join(cc_dir, f) for f in os.listdir(cc_dir) if f.lower().endswith('.pdf')]
            pdf_files.extend(cc_files)
        
        # Process Bank directory
        bank_dir = os.path.join(input_path, "Bank")
        if os.path.exists(bank_dir):
            bank_files = [os.path.join(bank_dir, f) for f in os.listdir(bank_dir) if f.lower().endswith('.pdf')]
            pdf_files.extend(bank_files)
        
        if not pdf_files:
            print(f"No PDF files found in {input_path}/CC or {input_path}/Bank")
            return
        
        # Sort files by date (newest first)
        pdf_files.sort(reverse=True)
        
        # Process each PDF file
        analyses = []
        for pdf_file in pdf_files:
            print(f"\nProcessing PDF file: {pdf_file}")
            try:
                # Read and analyze PDF
                result = pdf_reader.analyze_pdf(pdf_file)
                if result["status"] == "success":
                    analyses.append(result["data"])
                else:
                    print(f"Error processing {pdf_file}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
                continue
        
        if not analyses:
            print("No valid analyses to combine.")
            return
        
        print("\nPerforming combined analysis...")
        
        # Generate timestamp for output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"financial_report_{timestamp}.pdf")
        
        print("\nGenerating report...")
        report_result = report_generator.generate_report(analyses, output_file)
        
        if report_result["status"] == "success":
            print(f"\nAnalysis complete! Report generated at: {output_file}")
        else:
            print(f"\nError generating report: {report_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error in process_files: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Process financial documents and generate analysis report")
    parser.add_argument("--input", required=True, help="Input directory containing PDF and data files")
    parser.add_argument("--output", required=True, help="Output directory for generated reports")
    args = parser.parse_args()
    
    process_files(args.input, args.output)

if __name__ == "__main__":
    main() 