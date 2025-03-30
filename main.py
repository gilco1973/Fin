import os
import argparse
from agents.pdf_reader import PDFReaderAgent
from agents.data_reader import DataReaderAgent
from agents.analysis_agent import AnalysisAgent
from agents.report_generator import ReportGeneratorAgent
import json
from datetime import datetime

def process_files(input_path: str, output_dir: str) -> None:
    """Process PDF files and generate a report."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize tools and agents
    pdf_reader = PDFReaderAgent()
    report_generator = ReportGeneratorAgent()
    
    # List to store analysis results
    analyses = []
    
    # Handle both directory and single file inputs
    if os.path.isdir(input_path):
        # Process all PDF files in directory
        for file in os.listdir(input_path):
            if file.endswith('.pdf'):
                file_path = os.path.join(input_path, file)
                try:
                    print(f"\nProcessing PDF file: {file_path}")
                    result = pdf_reader.analyze_pdf(file_path)
                    if result["status"] == "success":
                        analyses.append(result["data"])
                    else:
                        print(f"Error processing {file}: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")
    else:
        # Process single PDF file
        if input_path.endswith('.pdf'):
            try:
                print(f"\nProcessing PDF file: {input_path}")
                result = pdf_reader.analyze_pdf(input_path)
                if result["status"] == "success":
                    analyses.append(result["data"])
                else:
                    print(f"Error processing file: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error processing file: {str(e)}")
        else:
            print("Error: Input file must be a PDF file")
            return
    
    if not analyses:
        print("No files were successfully processed")
        return
    
    print("\nPerforming combined analysis...")
    
    # Generate report
    try:
        print("\nGenerating report...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"financial_report_{timestamp}.pdf")
        report_generator.generate_report(analyses, report_path)
        print(f"\nAnalysis complete! Report generated at: {report_path}")
    except Exception as e:
        print(f"Error generating report: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Process financial documents and generate analysis report")
    parser.add_argument("--input", required=True, help="Input directory containing PDF and data files")
    parser.add_argument("--output", required=True, help="Output directory for generated reports")
    args = parser.parse_args()
    
    process_files(args.input, args.output)

if __name__ == "__main__":
    main() 