import PyPDF2
import argparse

def pdf_to_text(pdf_path, output_path=None):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_path (str, optional): Path to save the extracted text. If None, prints to console.
    
    Returns:
        str: The extracted text content
    """
    # Open the PDF file in binary mode
    with open(pdf_path, 'rb') as file:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Get the number of pages
        num_pages = len(pdf_reader.pages)
        
        # Extract text from each page
        text = ""
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        # If output path is provided, save to file
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(text)
            print(f"Text extracted and saved to {output_path}")
        else:
            print(text)
            
        return text

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract text from a PDF file')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-o', '--output', help='Path to save the extracted text')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the function
    pdf_to_text(args.pdf_path, args.output)