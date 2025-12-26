"""
Patient Report Parser - Step 2
Extracts bacteria abundance data from PDF microbiome reports.

Handles varying PDF formats from different labs using multiple extraction strategies.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

# PDF parsing libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logging.warning("pdfplumber not available. Install with: pip install pdfplumber")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logging.warning("PyPDF2 not available. Install with: pip install PyPDF2")


class PatientReportParser:
    """
    Flexible PDF parser for extracting bacteria abundance data from microbiome reports.
    
    Features:
    - Multi-strategy extraction (tables, text patterns, line parsing)
    - Handles varying PDF formats from different labs
    - Extracts genus or species level taxonomy
    - Focuses on relative abundance percentages
    - Smart column detection (patient data vs reference data)
    - Multiple timepoint support
    - Provides extraction confidence scores
    """
    
    # Keywords that indicate PATIENT data columns (priority columns)
    PATIENT_COLUMN_KEYWORDS = [
        'patient', 'your', 'sample', 'result', 'current', 'you',
        'first year', 'second year', 'third year', 'year 1', 'year 2', 'year 3',
        'visit 1', 'visit 2', 'baseline', 'follow-up', 'followup',
        'test 1', 'test 2', 'measurement', 'reading'
    ]
    
    # Keywords that indicate REFERENCE data columns (skip these)
    REFERENCE_COLUMN_KEYWORDS = [
        'maximum', 'minimum', 'max', 'min', 'average', 'mean', 'median',
        'healthy', 'normal', 'reference', 'control', 'typical', 'standard',
        'range', 'cohort', 'population'
    ]
    
    # Common bacteria genera in microbiome studies
    COMMON_GENERA = [
        'Bifidobacterium', 'Lactobacillus', 'Bacteroides', 'Prevotella', 
        'Faecalibacterium', 'Akkermansia', 'Escherichia', 'Streptococcus',
        'Clostridium', 'Ruminococcus', 'Roseburia', 'Enterococcus',
        'Blautia', 'Coprococcus', 'Dorea', 'Eubacterium', 'Alistipes',
        'Parabacteroides', 'Oscillospira', 'Sutterella', 'Collinsella',
        'Dialister', 'Veillonella', 'Megamonas', 'Phascolarctobacterium',
        'Actinomyces', 'Anaerostipes', 'Bilophila', 'Desulfovibrio',
        'Methanobrevibacter', 'Odoribacter', 'Barnesiella', 'Butyricicoccus',
        'Lactococcus', 'Leuconostoc', 'Pediococcus', 'Weissella'
    ]
    
    # Common bacterial phyla (higher taxonomic level)
    COMMON_PHYLA = [
        'Firmicutes', 'Actinobacteria', 'Bacteroidetes', 'Proteobacteria',
        'Verrucomicrobia', 'Fusobacteria', 'Cyanobacteria', 'Spirochaetes',
        'Lentisphaerae', 'Tenericutes'
    ]
    
    # Regex patterns for bacteria names
    BACTERIA_PATTERNS = [
        # Genus species (e.g., "Bifidobacterium longum")
        r'\b([A-Z][a-z]+)\s+([a-z]+)\b',
        # Genus only (e.g., "Bifidobacterium")
        r'\b([A-Z][a-z]+bacterium|[A-Z][a-z]+coccus|[A-Z][a-z]+bacter|[A-Z][a-z]+monas)\b',
        # Phyla names (e.g., "Firmicutes", "Bacteroidetes")
        r'\b([A-Z][a-z]+cetes|[A-Z][a-z]+bacteria|[A-Z][a-z]+microbia|[A-Z][a-z]+phaerae|[A-Z][a-z]+chaetes|[A-Z][a-z]+icutes)\b',
    ]
    
    # Regex patterns for percentages
    PERCENTAGE_PATTERNS = [
        r'(\d+\.?\d*)\s*%',           # 2.5%, 15.3%
        r'(\d+\.?\d*)\s*percent',     # 2.5 percent
        r'(\d+\.?\d*)%',              # 2.5%
    ]
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the patient report parser.
        
        Args:
            project_root: Root directory of the project
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.logger.info("Initialized PatientReportParser")
        self.logger.info(f"Project root: {self.project_root}")
        
        # Check available PDF libraries
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ImportError(
                "No PDF parsing library available. Install one of:\n"
                "  pip install pdfplumber\n"
                "  pip install PyPDF2"
            )
    
    def parse_report(self, pdf_path: str) -> pd.DataFrame:
        """
        Main method to parse a patient microbiome report PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DataFrame with columns:
                - bacteria_name: str
                - relative_abundance: float (0-100)
                - taxonomy_level: str ('phylum', 'genus', or 'species')
                - timepoint: str (e.g., 'First Year', 'Second Year', 'Patient', 'Unknown')
                - extraction_confidence: float (0-1)
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"PARSING PATIENT REPORT: {pdf_path.name}")
        self.logger.info(f"{'='*60}")
        
        # Try multiple extraction strategies
        results = []
        
        # Strategy 1: Table extraction with pdfplumber
        if PDFPLUMBER_AVAILABLE:
            self.logger.info("\n🔍 Strategy 1: Table extraction (pdfplumber)...")
            table_results = self._extract_from_tables(pdf_path)
            if not table_results.empty:
                results.append(('table', table_results))
                self.logger.info(f"   ✅ Found {len(table_results)} entries from tables")
            else:
                self.logger.info("   ⚠️  No data extracted from tables")
        
        # Strategy 2: Text pattern matching
        self.logger.info("\n🔍 Strategy 2: Text pattern matching...")
        text_results = self._extract_from_text_patterns(pdf_path)
        if not text_results.empty:
            results.append(('text', text_results))
            self.logger.info(f"   ✅ Found {len(text_results)} entries from text patterns")
        else:
            self.logger.info("   ⚠️  No data extracted from text patterns")
        
        # Strategy 3: Line-by-line parsing (fallback)
        self.logger.info("\n🔍 Strategy 3: Line-by-line parsing (fallback)...")
        line_results = self._extract_from_lines(pdf_path)
        if not line_results.empty:
            results.append(('line', line_results))
            self.logger.info(f"   ✅ Found {len(line_results)} entries from line parsing")
        else:
            self.logger.info("   ⚠️  No data extracted from line parsing")
        
        # Combine and deduplicate results
        if not results:
            self.logger.warning("\n⚠️  WARNING: No bacteria data extracted from PDF!")
            return pd.DataFrame(columns=[
                'bacteria_name', 'relative_abundance', 'taxonomy_level', 'timepoint', 'extraction_confidence'
            ])
        
        # Merge results with confidence scoring
        final_df = self._merge_and_deduplicate(results)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✅ EXTRACTION COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total bacteria extracted: {len(final_df)}")
        self.logger.info(f"Average confidence: {final_df['extraction_confidence'].mean():.2f}")
        
        return final_df
    
    def _extract_from_tables(self, pdf_path: Path) -> pd.DataFrame:
        """Extract bacteria data from PDF tables using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            return pd.DataFrame()
        
        all_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if not table:
                            continue
                        
                        # Strategy 1: Check for cells with \n-separated bacteria and values
                        bacteria_data = self._extract_from_multiline_cells(table)
                        if bacteria_data:
                            all_data.extend(bacteria_data)
                            continue
                        
                        # Strategy 2: Standard row-by-row extraction
                        for row in table:
                            if not row or len(row) < 2:
                                continue
                            
                            # Look for bacteria names and percentages in each row
                            bacteria_found = False
                            abundance_found = False
                            bacteria_name = None
                            abundance = None
                            
                            for cell in row:
                                if cell is None:
                                    continue
                                
                                cell = str(cell).strip()
                                
                                # Check if cell contains bacteria name
                                if not bacteria_found:
                                    bacteria_match = self._extract_bacteria_name(cell)
                                    if bacteria_match:
                                        bacteria_name = bacteria_match
                                        bacteria_found = True
                                
                                # Check if cell contains percentage
                                if not abundance_found:
                                    abundance_match = self._extract_percentage(cell)
                                    if abundance_match is not None:
                                        abundance = abundance_match
                                        abundance_found = True
                            
                            # If both found, add to results
                            if bacteria_found and abundance_found:
                                taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                                all_data.append({
                                    'bacteria_name': bacteria_name,
                                    'relative_abundance': abundance,
                                    'taxonomy_level': taxonomy_level,
                                    'timepoint': 'Unknown',  # Can't determine from standard extraction
                                    'extraction_confidence': 0.7  # Medium confidence - no header info
                                })
        
        except Exception as e:
            self.logger.error(f"Error extracting tables: {e}")
        
        return pd.DataFrame(all_data)
    
    def _extract_from_text_patterns(self, pdf_path: Path) -> pd.DataFrame:
        """Extract bacteria data using regex patterns on full text."""
        all_data = []
        
        # Extract text from PDF
        text = self._extract_pdf_text(pdf_path)
        if not text:
            return pd.DataFrame()
        
        # Split into lines for pattern matching
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for lines with both bacteria name and percentage
            bacteria_name = self._extract_bacteria_name(line)
            abundance = self._extract_percentage(line)
            
            if bacteria_name and abundance is not None:
                taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                all_data.append({
                    'bacteria_name': bacteria_name,
                    'relative_abundance': abundance,
                    'taxonomy_level': taxonomy_level,
                    'timepoint': 'Unknown',
                    'extraction_confidence': 0.6  # Medium confidence for pattern matching
                })
        
        return pd.DataFrame(all_data)
    
    def _extract_from_lines(self, pdf_path: Path) -> pd.DataFrame:
        """Fallback: Extract by searching for bacteria-percentage pairs in proximity."""
        all_data = []
        
        text = self._extract_pdf_text(pdf_path)
        if not text:
            return pd.DataFrame()
        
        lines = text.split('\n')
        
        # Look for bacteria names and percentages in adjacent lines
        for i in range(len(lines) - 1):
            line1 = lines[i].strip()
            line2 = lines[i + 1].strip()
            
            # Check if first line has bacteria and second has percentage
            bacteria_name = self._extract_bacteria_name(line1)
            abundance = self._extract_percentage(line2)
            
            if bacteria_name and abundance is not None:
                taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                all_data.append({
                    'bacteria_name': bacteria_name,
                    'relative_abundance': abundance,
                    'taxonomy_level': taxonomy_level,
                    'timepoint': 'Unknown',
                    'extraction_confidence': 0.5  # Lower confidence for proximity matching
                })
        
        return pd.DataFrame(all_data)
    
    def _extract_from_multiline_cells(self, table: List[List]) -> List[Dict]:
        """
        Extract bacteria from cells that contain multiple bacteria/values separated by newlines.
        
        Example cell format:
        'Firmicutes\\nActinobacteria\\nBacteroidetes' paired with '85.00\\n2.51\\n6.77'
        """
        results = []
        
        # First, identify column headers and their types
        headers = self._identify_table_headers(table)
        if not headers:
            return results
        
        bacteria_col_idx = headers.get('bacteria_column')
        patient_col_indices = headers.get('patient_columns', [])
        
        if bacteria_col_idx is None or not patient_col_indices:
            # Fallback to old logic if we can't identify columns
            return self._extract_from_multiline_cells_fallback(table)
        
        # Extract data from identified columns
        for row_idx, row in enumerate(table):
            if not row or row_idx <= headers.get('header_row_idx', 0):
                continue
            
            # Get bacteria cell
            if bacteria_col_idx >= len(row):
                continue
            
            bacteria_cell = row[bacteria_col_idx]
            if not bacteria_cell:
                continue
            
            bacteria_cell_str = str(bacteria_cell).strip()
            
            # Check for multiline bacteria names
            if '\n' in bacteria_cell_str:
                bacteria_lines = [line.strip() for line in bacteria_cell_str.split('\n') if line.strip()]
                
                # Extract from each patient column
                for patient_col_info in patient_col_indices:
                    col_idx = patient_col_info['index']
                    col_name = patient_col_info['name']
                    
                    if col_idx >= len(row):
                        continue
                    
                    abundance_cell = row[col_idx]
                    if not abundance_cell:
                        continue
                    
                    abundance_cell_str = str(abundance_cell).strip()
                    
                    if '\n' in abundance_cell_str:
                        abundance_lines = [line.strip() for line in abundance_cell_str.split('\n') if line.strip()]
                        
                        # Match bacteria with abundances
                        if len(bacteria_lines) == len(abundance_lines):
                            for bacteria_line, abundance_line in zip(bacteria_lines, abundance_lines):
                                bacteria_name = self._extract_bacteria_name(bacteria_line)
                                abundance = self._extract_float(abundance_line)
                                
                                if bacteria_name and abundance is not None:
                                    taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                                    results.append({
                                        'bacteria_name': bacteria_name,
                                        'relative_abundance': abundance,
                                        'taxonomy_level': taxonomy_level,
                                        'timepoint': col_name,
                                        'extraction_confidence': 0.90  # High confidence - structured with headers
                                    })
            else:
                # Single bacteria name in row
                bacteria_name = self._extract_bacteria_name(bacteria_cell_str)
                if not bacteria_name:
                    continue
                
                # Extract from each patient column
                for patient_col_info in patient_col_indices:
                    col_idx = patient_col_info['index']
                    col_name = patient_col_info['name']
                    
                    if col_idx >= len(row):
                        continue
                    
                    abundance_cell = row[col_idx]
                    if not abundance_cell:
                        continue
                    
                    abundance = self._extract_float(str(abundance_cell).strip())
                    
                    if abundance is not None:
                        taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                        results.append({
                            'bacteria_name': bacteria_name,
                            'relative_abundance': abundance,
                            'taxonomy_level': taxonomy_level,
                            'timepoint': col_name,
                            'extraction_confidence': 0.90
                        })
        
        return results
    
    def _identify_table_headers(self, table: List[List]) -> Dict:
        """
        Identify column headers and classify them as bacteria, patient data, or reference data.
        Handles multi-row headers where column names are split across multiple rows.
        
        Returns:
            Dict with:
                - bacteria_column: int (index of bacteria names column)
                - patient_columns: List[Dict] (indices and names of patient data columns)
                - reference_columns: List[int] (indices of reference data columns)
                - header_row_idx: int (which row contains headers)
        """
        result = {
            'bacteria_column': None,
            'patient_columns': [],
            'reference_columns': [],
            'header_row_idx': None
        }
        
        # Search first 5 rows for headers
        for row_idx, row in enumerate(table[:5]):
            if not row:
                continue
            
            # Check if this row looks like a header row
            header_score = 0
            for cell in row:
                if not cell:
                    continue
                cell_lower = str(cell).lower().strip()
                
                # Header indicators
                if any(keyword in cell_lower for keyword in ['bacteria', 'species', 'genus', 'organism', 'phyla', 'phylum']):
                    header_score += 3
                if any(keyword in cell_lower for keyword in ['abundance', 'relative', 'percentage', '%', 'patient', 'sample']):
                    header_score += 2
                if any(keyword in cell_lower for keyword in ['maximum', 'average', 'year', 'visit']):
                    header_score += 1
            
            # If this row has header-like content, analyze it
            if header_score >= 3:
                if result['header_row_idx'] is None:
                    result['header_row_idx'] = row_idx
                
                for col_idx, cell in enumerate(row):
                    if not cell:
                        continue
                    
                    cell_str = str(cell).strip()
                    cell_lower = cell_str.lower()
                    
                    # Identify bacteria column
                    if any(keyword in cell_lower for keyword in ['bacteria', 'species', 'genus', 'organism', 'phyla', 'phylum']):
                        if result['bacteria_column'] is None:
                            result['bacteria_column'] = col_idx
                        continue
                    
                    # Check if it's a patient data column
                    is_patient_col = False
                    for patient_keyword in self.PATIENT_COLUMN_KEYWORDS:
                        if patient_keyword in cell_lower:
                            is_patient_col = True
                            break
                    
                    # Check if it's a reference data column
                    is_reference_col = False
                    for ref_keyword in self.REFERENCE_COLUMN_KEYWORDS:
                        if ref_keyword in cell_lower:
                            is_reference_col = True
                            break
                    
                    # Prioritize patient columns
                    if is_patient_col and not is_reference_col:
                        # Check if we already have this column index from a previous row
                        existing = [c for c in result['patient_columns'] if c['index'] == col_idx]
                        if not existing:
                            result['patient_columns'].append({
                                'index': col_idx,
                                'name': cell_str
                            })
                    elif is_reference_col:
                        if col_idx not in result['reference_columns']:
                            result['reference_columns'].append(col_idx)
                    # If contains "%" or "abundance" but not reference, assume patient data
                    elif ('abundance' in cell_lower or '%' in cell_lower) and not is_reference_col:
                        # Could be a patient column without clear labeling
                        # Use heuristics: columns after reference columns are likely patient data
                        if len(result['reference_columns']) > 0:
                            existing = [c for c in result['patient_columns'] if c['index'] == col_idx]
                            if not existing:
                                result['patient_columns'].append({
                                    'index': col_idx,
                                    'name': cell_str or f'Column_{col_idx}'
                                })
        
        # If we found bacteria column but no patient columns, check the next row(s) for sub-headers
        if result['bacteria_column'] is not None and not result['patient_columns'] and result['header_row_idx'] is not None:
            next_row_idx = result['header_row_idx'] + 1
            if next_row_idx < len(table):
                next_row = table[next_row_idx]
                
                for col_idx, cell in enumerate(next_row):
                    if not cell or col_idx == result['bacteria_column']:
                        continue
                    
                    cell_str = str(cell).strip()
                    cell_lower = cell_str.lower()
                    
                    # Check if it's a patient data column
                    is_patient_col = False
                    for patient_keyword in self.PATIENT_COLUMN_KEYWORDS:
                        if patient_keyword in cell_lower:
                            is_patient_col = True
                            break
                    
                    # Check if it's a reference data column
                    is_reference_col = False
                    for ref_keyword in self.REFERENCE_COLUMN_KEYWORDS:
                        if ref_keyword in cell_lower:
                            is_reference_col = True
                            break
                    
                    if is_patient_col and not is_reference_col:
                        result['patient_columns'].append({
                            'index': col_idx,
                            'name': cell_str
                        })
                    elif is_reference_col:
                        if col_idx not in result['reference_columns']:
                            result['reference_columns'].append(col_idx)
        
        return result
    
    def _extract_from_multiline_cells_fallback(self, table: List[List]) -> List[Dict]:
        """
        Fallback extraction when we can't identify clear headers.
        Uses the old logic that picks the last numeric column.
        """
        results = []
        
        for row in table:
            if not row:
                continue
            
            # Look for cells with newline-separated content
            bacteria_cell = None
            abundance_cell = None
            
            for col_idx, cell in enumerate(row):
                if cell is None:
                    continue
                
                cell_str = str(cell).strip()
                
                # Check if cell contains multiple bacteria names
                if '\n' in cell_str:
                    lines = [line.strip() for line in cell_str.split('\n') if line.strip()]
                    
                    # Check if this looks like a bacteria list
                    bacteria_count = sum(1 for line in lines if self._extract_bacteria_name(line))
                    if bacteria_count >= 2:  # At least 2 bacteria names
                        bacteria_cell = lines
                        continue
                    
                    # Check if this looks like an abundance list (numbers/percentages)
                    number_count = sum(1 for line in lines if self._is_numeric(line))
                    if number_count >= 2:  # At least 2 numbers
                        # Prefer later columns (patient data usually comes after reference data)
                        abundance_cell = lines
            
            # If we found both bacteria and abundance lists with matching counts
            if bacteria_cell and abundance_cell and len(bacteria_cell) == len(abundance_cell):
                for bacteria_line, abundance_line in zip(bacteria_cell, abundance_cell):
                    bacteria_name = self._extract_bacteria_name(bacteria_line)
                    abundance = self._extract_float(abundance_line)
                    
                    if bacteria_name and abundance is not None:
                        taxonomy_level = self._determine_taxonomy_level(bacteria_name)
                        results.append({
                            'bacteria_name': bacteria_name,
                            'relative_abundance': abundance,
                            'taxonomy_level': taxonomy_level,
                            'timepoint': 'Unknown',
                            'extraction_confidence': 0.70  # Lower confidence without headers
                        })
        
        return results
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text contains a numeric value."""
        try:
            float(text.strip().replace('%', '').replace(',', ''))
            return True
        except ValueError:
            return False
    
    def _extract_float(self, text: str) -> Optional[float]:
        """Extract float value from text (handles percentages and plain numbers)."""
        try:
            # Remove common non-numeric characters
            cleaned = text.strip().replace('%', '').replace(',', '').replace(' ', '')
            value = float(cleaned)
            # Validate range for relative abundance
            if 0 <= value <= 100:
                return value
        except ValueError:
            pass
        return None
    
    def _determine_taxonomy_level(self, bacteria_name: str) -> str:
        """Determine the taxonomy level of a bacteria name."""
        if bacteria_name in self.COMMON_PHYLA:
            return 'phylum'
        elif ' ' in bacteria_name:
            return 'species'
        else:
            return 'genus'
    
    def _extract_bacteria_name(self, text: str) -> Optional[str]:
        """
        Extract bacteria name from text using regex patterns.
        
        Returns:
            Bacteria name (phylum, genus, or genus species) or None
        """
        if not text:
            return None
        
        # First check for common phyla
        text_clean = text.strip()
        if text_clean in self.COMMON_PHYLA:
            return text_clean
        
        # Try each pattern
        for pattern in self.BACTERIA_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Handle different match formats
                if isinstance(matches[0], tuple):
                    # Genus species pattern
                    genus, species = matches[0]
                    # Validate genus
                    if genus.capitalize() in self.COMMON_GENERA or genus.capitalize() in self.COMMON_PHYLA:
                        return f"{genus.capitalize()} {species.lower()}"
                    # Check if it ends with bacterial suffixes
                    if genus.endswith(('bacterium', 'coccus', 'bacter', 'monas', 'bacteria', 'cetes', 'microbia')):
                        return f"{genus.capitalize()} {species.lower()}"
                else:
                    # Single word pattern
                    name = matches[0]
                    name_cap = name.capitalize()
                    
                    # Check against known lists
                    if name_cap in self.COMMON_GENERA or name_cap in self.COMMON_PHYLA:
                        return name_cap
                    
                    # Check if it ends with bacterial suffixes
                    if name.endswith(('bacterium', 'coccus', 'bacter', 'monas', 'bacteria', 'cetes', 'microbia', 'phaerae', 'chaetes', 'icutes')):
                        return name_cap
        
        return None
    
    def _extract_percentage(self, text: str) -> Optional[float]:
        """
        Extract percentage value from text.
        
        Returns:
            Float value (0-100) or None
        """
        if not text:
            return None
        
        for pattern in self.PERCENTAGE_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    value = float(matches[0])
                    # Validate range (should be 0-100 for relative abundance)
                    if 0 <= value <= 100:
                        return value
                except ValueError:
                    continue
        
        return None
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract all text from PDF using available libraries."""
        text = ""
        
        # Try pdfplumber first (better text extraction)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text
            except Exception as e:
                self.logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text
            except Exception as e:
                self.logger.warning(f"PyPDF2 extraction failed: {e}")
        
        return text
    
    def _merge_and_deduplicate(self, results: List[Tuple[str, pd.DataFrame]]) -> pd.DataFrame:
        """
        Merge results from multiple strategies and remove duplicates.
        
        For duplicates with same bacteria+timepoint, keep the entry with highest confidence.
        """
        if not results:
            return pd.DataFrame()
        
        # Combine all results
        all_dfs = [df for strategy, df in results]
        combined = pd.concat(all_dfs, ignore_index=True)
        
        if combined.empty:
            return combined
        
        # Deduplicate: keep highest confidence for each bacteria+timepoint combination
        combined = combined.sort_values('extraction_confidence', ascending=False)
        combined = combined.drop_duplicates(subset=['bacteria_name', 'timepoint'], keep='first')
        
        # Sort by timepoint and abundance
        combined = combined.sort_values(['timepoint', 'relative_abundance'], ascending=[True, False])
        combined = combined.reset_index(drop=True)
        
        return combined
    
    def save_results(self, df: pd.DataFrame, output_path: str):
        """Save extracted data to CSV/Excel."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == '.csv':
            df.to_csv(output_path, index=False)
        elif output_path.suffix in ['.xlsx', '.xls']:
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported file format: {output_path.suffix}")
        
        self.logger.info(f"✅ Saved results to: {output_path}")
    
    def print_summary(self, df: pd.DataFrame):
        """Print extraction summary."""
        if df.empty:
            print("\n⚠️  No bacteria data extracted")
            return
        
        print("\n" + "="*60)
        print("BACTERIA EXTRACTION SUMMARY")
        print("="*60)
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total entries: {len(df)}")
        print(f"   Unique bacteria: {df['bacteria_name'].nunique()}")
        print(f"   Timepoints: {df['timepoint'].nunique()}")
        print(f"   Phylum-level: {(df['taxonomy_level'] == 'phylum').sum()}")
        print(f"   Genus-level: {(df['taxonomy_level'] == 'genus').sum()}")
        print(f"   Species-level: {(df['taxonomy_level'] == 'species').sum()}")
        print(f"   Average confidence: {df['extraction_confidence'].mean():.2%}")
        
        print(f"\n📅 Data by Timepoint:")
        for timepoint in df['timepoint'].unique():
            count = len(df[df['timepoint'] == timepoint])
            total_abundance = df[df['timepoint'] == timepoint]['relative_abundance'].sum()
            print(f"   {timepoint}: {count} bacteria (total abundance: {total_abundance:.2f}%)")
        
        print(f"\n🦠 Top 10 Most Abundant Bacteria (across all timepoints):")
        # Group by bacteria and show max abundance across timepoints
        top_bacteria = df.groupby('bacteria_name').agg({
            'relative_abundance': 'max',
            'taxonomy_level': 'first',
            'extraction_confidence': 'first'
        }).nlargest(10, 'relative_abundance')
        
        for bacteria, row in top_bacteria.iterrows():
            print(f"   {bacteria}: {row['relative_abundance']:.2f}% [{row['taxonomy_level']}, confidence: {row['extraction_confidence']:.2f}]")
        
        print(f"\n📈 Abundance Distribution:")
        print(f"   Total abundance captured: {df['relative_abundance'].sum():.2f}%")
        print(f"   Mean abundance: {df['relative_abundance'].mean():.2f}%")
        print(f"   Median abundance: {df['relative_abundance'].median():.2f}%")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    # Example usage
    parser = PatientReportParser()
    
    # Test with sample PDF
    # df = parser.parse_report("path/to/patient_report.pdf")
    # parser.print_summary(df)
    # parser.save_results(df, "output/patient_bacteria.csv")
