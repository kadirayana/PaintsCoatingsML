"""
Paint Formulation AI - Dosya Sistemi Yöneticisi
===============================================
Excel ve CSV dosyalarıyla etkileşim kurar.
"""

import os
import openpyxl
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class FileSystemManager:
    """Dosya sistemi ve Excel işlemleri yöneticisi"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()

    def read_excel(self, file_path: str) -> List[Dict]:
        """Excel dosyasını okur ve liste-sözlük yapısına dönüştürür"""
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            
            headers = [cell.value for cell in sheet[1]]
            data = []
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row): continue # Boş satırları atla
                row_dict = {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
                data.append(row_dict)
                
            return data
        except Exception as e:
            logger.error(f"Excel okuma hatası: {e}")
            raise e

    def save_to_csv(self, data: List[Dict], file_path: str):
        """Veriyi CSV olarak kaydeder"""
        import csv
        if not data: return
        
        try:
            keys = data[0].keys()
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(data)
        except Exception as e:
            logger.error(f"CSV yazma hatası: {e}")
