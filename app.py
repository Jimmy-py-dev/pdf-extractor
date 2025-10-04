from flask import Flask, request, render_template, jsonify, send_file
import os
import tempfile
import uuid
from pathlib import Path
import logging
import io

# Import your PDF extractor
from pdf_extractor import PDFExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize your PDF extractor
extractor = PDFExtractor()

@app.route('/')
def index():
    """Main page with the upload form"""
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_pdf():
    """
    Handle PDF upload and extraction
    """
    # Check if file was uploaded
    if 'pdf' not in request.files:
        logger.error("No file uploaded")
        return jsonify({'error': 'No file uploaded'}), 400
    
    pdf_file = request.files['pdf']
    
    # Check if file was selected
    if pdf_file.filename == '':
        logger.error("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file is a PDF
    if not pdf_file.filename.lower().endswith('.pdf'):
        logger.error(f"Invalid file type: {pdf_file.filename}")
        return jsonify({'error': 'Please upload a PDF file'}), 400
    
    # Generate unique filename for security
    unique_filename = f"{uuid.uuid4().hex}_{pdf_file.filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    logger.info(f"Processing file: {pdf_file.filename}")
    
    try:
        # Save uploaded file to permanent location
        pdf_file.save(file_path)
        logger.info(f"File saved to: {file_path}")
        
        # Verify file was saved correctly
        if not os.path.exists(file_path):
            logger.error("File was not saved properly")
            return jsonify({'error': 'File upload failed'}), 500
        
        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("Uploaded file is empty")
            return jsonify({'error': 'Uploaded file is empty'}), 400
        
        # Extract data using your PDF extractor
        logger.info("Starting text extraction...")
        text = extractor.extract_text(file_path)
        
        logger.info("Starting table extraction...")
        tables = extractor.extract_tables(file_path)
        
        logger.info(f"Extraction completed - Text: {len(text)} chars, Tables: {len(tables)}")
        
        # Prepare response
        response_data = {
            'success': True,
            'text': text,
            'tables': tables,
            'text_length': len(text),
            'table_count': len(tables),
            'extraction_mode': extractor.get_extraction_mode()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
    
    finally:
        # Always clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup failed: {cleanup_error}")

@app.route('/export', methods=['POST'])
def export_data():
    """
    Export table data to Excel or CSV format using your DataExporter
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        table_index = data.get('table_index')
        format_type = data.get('format')
        tables = data.get('tables', [])
        
        if table_index is None or format_type is None:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        if not tables or table_index >= len(tables):
            return jsonify({'error': 'Invalid table index'}), 400
        
        table_data = tables[table_index]
        
        # Use your data_exporter to export the table
        if format_type == 'excel':
            excel_data = extractor.data_exporter.export_table(table_data, 'excel')
            return send_file(
                io.BytesIO(excel_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'table_{table_index + 1}.xlsx'
            )
        
        elif format_type == 'csv':
            csv_data = extractor.data_exporter.export_table(table_data, 'csv')
            return send_file(
                io.BytesIO(csv_data.encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'table_{table_index + 1}.csv'
            )
        
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/export_all', methods=['POST'])
def export_all_tables():
    """
    Export all tables to a single Excel file with multiple sheets using your DataExporter
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        tables = data.get('tables', [])
        
        if not tables:
            return jsonify({'error': 'No tables to export'}), 400
        
        # Create a dictionary of tables for multi-sheet export
        tables_dict = {}
        for i, table in enumerate(tables):
            tables_dict[f'Table_{i + 1}'] = table
        
        # Use your data_exporter to export all tables
        excel_data = extractor.data_exporter.export_multiple_tables(tables_dict)
        
        return send_file(
            io.BytesIO(excel_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='all_tables.xlsx'
        )
            
    except Exception as e:
        logger.error(f"Export all error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'PDF Extractor API'})

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

if __name__ == '__main__':
    # Get port from environment variable (for production)
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("Starting PDF Extractor Web Demo...")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"Access the demo at: http://localhost:{port}")
    
    app.run(
        host='0.0.0.0',  # Important for production
        port=port,
        debug=False  # Set to False in production
    )