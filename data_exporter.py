import pandas as pd
import io
import logging
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class DataExporter:
    """
    Simple data exporter - converts table data to export formats without data cleaning
    """
    
    def __init__(self):
        self.supported_formats = ['excel', 'csv']
        logger.info("✅ DataExporter initialized")
    
    def export_table(self, table_data: List[List[str]], format_type: str, 
                    filename: str = None) -> Union[bytes, str]:
        """
        Export table to requested format - raw data only
        
        Args:
            table_data: List of lists (rows × columns)
            format_type: 'excel', 'csv'
            filename: Optional output filename
            
        Returns:
            File data for download
        """
        if format_type not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format_type}. Supported: {self.supported_formats}")
        
        logger.info(f"Exporting table to {format_type}: {len(table_data)} rows")
        
        # Convert to pandas DataFrame with raw data
        df = self._table_list_to_dataframe(table_data)
        
        if format_type == 'excel':
            return self._to_excel(df, filename)
        elif format_type == 'csv':
            return self._to_csv(df, filename)
    
    def export_multiple_tables(self, tables_data: Dict[str, List[List[str]]], 
                              filename: str = "exported_tables") -> bytes:
        """
        Export multiple tables to Excel with multiple sheets - raw data only
        """
        logger.info(f"Exporting {len(tables_data)} tables to multi-sheet Excel")
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, table_data in tables_data.items():
                df = self._table_list_to_dataframe(table_data)
                clean_sheet_name = self._clean_sheet_name(sheet_name)
                df.to_excel(writer, sheet_name=clean_sheet_name, index=False)
        
        output.seek(0)
        return output.getvalue()
    
    def _table_list_to_dataframe(self, table_data: List[List[str]]) -> pd.DataFrame:
        """
        Convert list of lists to pandas DataFrame - no data cleaning
        """
        if not table_data:
            return pd.DataFrame()
        
        logger.info(f"Converting table data: {len(table_data)} rows, {len(table_data[0])} columns")
        
        # Use raw data as-is, no cleaning
        return pd.DataFrame(table_data)
    
    def _to_excel(self, df: pd.DataFrame, filename: str = None) -> bytes:
        """
        Convert DataFrame to Excel file - raw data only
        """
        logger.info(f"Converting DataFrame to Excel: {df.shape}")
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet_name = filename or 'Sheet1'
            clean_sheet_name = self._clean_sheet_name(sheet_name)
            df.to_excel(writer, sheet_name=clean_sheet_name, index=False)
        
        output.seek(0)
        excel_data = output.getvalue()
        logger.info(f"Excel file generated: {len(excel_data)} bytes")
        return excel_data
    
    def _to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Convert DataFrame to CSV - raw data only
        """
        logger.info(f"Converting DataFrame to CSV: {df.shape}")
        
        csv_data = df.to_csv(index=False, encoding='utf-8')
        logger.info(f"CSV data generated: {len(csv_data)} characters")
        return csv_data
    
    def _clean_sheet_name(self, sheet_name: str, max_length: int = 31) -> str:
        """
        Clean sheet name for Excel compatibility
        """
        # Remove invalid characters
        import re
        cleaned = re.sub(r'[\\/*?\[\]:]', '', sheet_name)
        
        # Truncate to max length
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        # Ensure not empty
        if not cleaned.strip():
            cleaned = "Sheet1"
        
        return cleaned
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return self.supported_formats.copy()
    