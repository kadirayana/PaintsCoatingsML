"""
Paint Formulation AI - Dosya Sistemi Yöneticisi
===============================================
Excel ve CSV dosya okuma/yazma işlemleri
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class FileSystemManager:
    """Excel ve CSV dosya işlemleri yöneticisi"""
    
    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xls', '.csv']
    
    def read_excel(self, file_path: str, sheet_name: str = None) -> List[Dict]:
        """
        Excel dosyasını oku
        
        Args:
            file_path: Dosya yolu
            sheet_name: Sayfa adı (opsiyonel)
            
        Returns:
            Satırlar listesi (her satır bir dict)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.csv':
            return self.read_csv(file_path)
        
        try:
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            
            # Sayfa seç
            if sheet_name:
                ws = wb[sheet_name]
            else:
                ws = wb.active
            
            # Başlıkları al
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            
            headers = [str(cell).strip() if cell else f"Column_{i}" for i, cell in enumerate(rows[0])]
            
            # Verileri oku
            data = []
            for row in rows[1:]:
                if any(cell is not None for cell in row):
                    row_dict = {}
                    for i, cell in enumerate(row):
                        if i < len(headers):
                            row_dict[headers[i]] = self._convert_cell_value(cell)
                    data.append(row_dict)
            
            wb.close()
            logger.info(f"Excel okundu: {file_path} ({len(data)} satır)")
            return data
            
        except ImportError:
            logger.error("openpyxl kütüphanesi bulunamadı")
            raise ImportError("Excel okumak için openpyxl gerekli: pip install openpyxl")
        except Exception as e:
            logger.error(f"Excel okuma hatası: {e}")
            raise
    
    def read_csv(self, file_path: str, encoding: str = 'utf-8') -> List[Dict]:
        """
        CSV dosyasını oku
        
        Args:
            file_path: Dosya yolu
            encoding: Karakter kodlaması
            
        Returns:
            Satırlar listesi
        """
        import csv
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
        data = []
        encodings_to_try = [encoding, 'utf-8-sig', 'latin-1', 'cp1254']  # Türkçe için cp1254
        
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc, newline='') as f:
                    # Ayırıcıyı otomatik tespit et
                    sample = f.read(1024)
                    f.seek(0)
                    
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample)
                    except csv.Error:
                        dialect = csv.excel
                    
                    reader = csv.DictReader(f, dialect=dialect)
                    data = [row for row in reader]
                    
                logger.info(f"CSV okundu: {file_path} ({len(data)} satır)")
                return data
                
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Dosya kodlaması tespit edilemedi: {file_path}")
    
    def write_excel(self, data: List[Dict], file_path: str, sheet_name: str = "Veri") -> bool:
        """
        Excel dosyasına yaz
        
        Args:
            data: Yazılacak veriler
            file_path: Dosya yolu
            sheet_name: Sayfa adı
            
        Returns:
            Başarı durumu
        """
        if not data:
            logger.warning("Yazılacak veri yok")
            return False
        
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name
            
            # Başlıkları yaz
            headers = list(data[0].keys())
            header_font = Font(bold=True)
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal='center')
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Verileri yaz
            for row_idx, row_data in enumerate(data, 2):
                for col_idx, header in enumerate(headers, 1):
                    ws.cell(row=row_idx, column=col_idx, value=row_data.get(header, ''))
            
            # Sütun genişliklerini ayarla
            for col_idx, header in enumerate(headers, 1):
                max_length = len(str(header))
                for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                    for cell in row:
                        try:
                            cell_length = len(str(cell.value)) if cell.value else 0
                            max_length = max(max_length, cell_length)
                        except:
                            pass
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = min(max_length + 2, 50)
            
            wb.save(file_path)
            logger.info(f"Excel yazıldı: {file_path}")
            return True
            
        except ImportError:
            raise ImportError("Excel yazmak için openpyxl gerekli: pip install openpyxl")
        except Exception as e:
            logger.error(f"Excel yazma hatası: {e}")
            raise
    
    def write_csv(self, data: List[Dict], file_path: str, encoding: str = 'utf-8-sig') -> bool:
        """
        CSV dosyasına yaz
        
        Args:
            data: Yazılacak veriler
            file_path: Dosya yolu
            encoding: Karakter kodlaması
            
        Returns:
            Başarı durumu
        """
        import csv
        
        if not data:
            logger.warning("Yazılacak veri yok")
            return False
        
        try:
            headers = list(data[0].keys())
            
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"CSV yazıldı: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"CSV yazma hatası: {e}")
            raise
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """
        Excel dosyasındaki sayfa isimlerini getir
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Sayfa isimleri listesi
        """
        try:
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheet_names = wb.sheetnames
            wb.close()
            
            return sheet_names
            
        except ImportError:
            raise ImportError("Excel için openpyxl gerekli: pip install openpyxl")
        except Exception as e:
            logger.error(f"Sayfa ismi okuma hatası: {e}")
            raise
    
    def validate_file(self, file_path: str) -> Dict:
        """
        Dosyayı doğrula
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Doğrulama sonucu
        """
        result = {
            'valid': False,
            'file_exists': False,
            'extension_valid': False,
            'readable': False,
            'row_count': 0,
            'column_count': 0,
            'columns': [],
            'message': ''
        }
        
        # Dosya var mı?
        if not os.path.exists(file_path):
            result['message'] = "Dosya bulunamadı"
            return result
        
        result['file_exists'] = True
        
        # Uzantı geçerli mi?
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            result['message'] = f"Desteklenmeyen dosya formatı: {ext}"
            return result
        
        result['extension_valid'] = True
        
        # Okunabilir mi?
        try:
            data = self.read_excel(file_path) if ext != '.csv' else self.read_csv(file_path)
            result['readable'] = True
            result['row_count'] = len(data)
            
            if data:
                result['columns'] = list(data[0].keys())
                result['column_count'] = len(result['columns'])
            
            result['valid'] = True
            result['message'] = "Dosya geçerli"
            
        except Exception as e:
            result['message'] = f"Dosya okuma hatası: {str(e)}"
        
        return result
    
    def create_template(self, template_path: str, columns: List[str], sample_data: List[Dict] = None) -> bool:
        """
        Excel şablonu oluştur
        
        Args:
            template_path: Şablon dosya yolu
            columns: Sütun isimleri
            sample_data: Örnek veriler (opsiyonel)
            
        Returns:
            Başarı durumu
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.comments import Comment
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Veri Girişi"
            
            # Stiller
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal='center', vertical='center')
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Başlıkları yaz
            for col, header in enumerate(columns, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
                
                # Sütun genişliği
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = max(len(header) + 5, 15)
            
            # Örnek veri varsa ekle
            if sample_data:
                for row_idx, row_data in enumerate(sample_data, 2):
                    for col_idx, header in enumerate(columns, 1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(header, ''))
                        cell.border = thin_border
            
            # Talimatlar sayfası
            ws_instructions = wb.create_sheet(title="Talimatlar")
            instructions = [
                "BOYA FORMÜLASYONU VERİ GİRİŞ ŞABLONU",
                "",
                "Kullanım Talimatları:",
                "1. 'Veri Girişi' sayfasına verilerinizi girin",
                "2. Başlık satırını değiştirmeyin",
                "3. Her satır bir formülasyon/deneme kaydı olmalıdır",
                "4. Sayısal değerler için nokta (.) kullanın (örn: 1.5)",
                "5. Tarihler için GG.AA.YYYY formatını kullanın",
                "",
                f"Şablon oluşturma tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ]
            
            for row, text in enumerate(instructions, 1):
                ws_instructions.cell(row=row, column=1, value=text)
            
            ws_instructions.column_dimensions['A'].width = 60
            
            wb.save(template_path)
            logger.info(f"Şablon oluşturuldu: {template_path}")
            return True
            
        except Exception as e:
            logger.error(f"Şablon oluşturma hatası: {e}")
            raise
    
    @staticmethod
    def _convert_cell_value(value: Any) -> Any:
        """Hücre değerini uygun tipe dönüştür"""
        if value is None:
            return None
        
        # Datetime kontrolü
        if isinstance(value, datetime):
            return value.isoformat()
        
        # String ise boşlukları temizle
        if isinstance(value, str):
            return value.strip()
        
        return value
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict:
        """
        Dosya bilgilerini getir
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Dosya bilgileri
        """
        if not os.path.exists(file_path):
            return {'exists': False}
        
        stat = os.stat(file_path)
        
        return {
            'exists': True,
            'name': os.path.basename(file_path),
            'directory': os.path.dirname(file_path),
            'extension': os.path.splitext(file_path)[1],
            'size_bytes': stat.st_size,
            'size_formatted': FileSystemManager._format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Boyutu okunabilir formata dönüştür"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
