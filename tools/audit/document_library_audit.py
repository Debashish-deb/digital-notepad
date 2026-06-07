#!/usr/bin/env python3
"""
Comprehensive Document Library Audit Script for OMEIA Digital Notepad

This script performs a complete audit of the document library including:
- File discovery across all roots
- Metadata extraction
- Category/taxonomy analysis
- File type coverage
- UI/database/filesystem reconciliation
- Duplicate detection
- Report generation

Run with: python tools/audit/document_library_audit.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import mimetypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tools/audit/audit_log.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
LOGGER = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports" / "document_library_audit"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Cache directory for expensive operations
CACHE_DIR = PROJECT_ROOT / "tools" / "audit" / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class FileCategory(Enum):
    """Scientific/lab document categories"""
    PROTOCOL = "protocol"
    SOP = "sop"
    WET_LAB_OPERATION = "wet_lab_operation"
    INVENTORY = "inventory"
    REAGENT_LIST = "reagent_list"
    ANTIBODY_PANEL = "antibody_panel"
    MARKER_PANEL = "marker_panel"
    SAMPLE_PREPARATION = "sample_preparation"
    ORGANOID_WORK = "organoid_work"
    TISSUE_FIXATION = "tissue_fixation"
    FFPE = "ffpe"
    FROZEN_TISSUE = "frozen_tissue"
    PATIENT_SAMPLE = "patient_sample"
    OMENTUM = "omentum"
    ADNEXA = "adnexa"
    OTHER_ANATOMICAL_SITE = "other_anatomical_site"
    CYCIF = "cycif"
    TCYCIF = "tcycif"
    IMMUNOFLUORESCENCE = "immunofluorescence"
    MICROSCOPY = "microscopy"
    IMAGE_ANALYSIS = "image_analysis"
    SEGMENTATION = "segmentation"
    QUANTIFICATION = "quantification"
    QC = "qc"
    SLIDES = "slides"
    SECTIONS = "sections"
    ORDER_FORMS = "order_forms"
    SCRNA_SEQ = "scrna_seq"
    SEQUENCING = "sequencing"
    BIOINFORMATICS = "bioinformatics"
    COMPUTATIONAL_NOTEBOOK = "computational_notebook"
    DATABASE_EXPORT = "database_export"
    SPREADSHEET_TRACKER = "spreadsheet_tracker"
    ARCHIVE_OLD_PROTOCOL = "archive_old_protocol"
    ADMINISTRATIVE_DOCUMENT = "administrative_document"
    UNKNOWN = "unknown"


@dataclass
class FileMetadata:
    """Complete metadata for a single file"""
    # Basic identity
    document_id: Optional[str] = None
    file_id: Optional[str] = None
    display_name: Optional[str] = None
    original_filename: Optional[str] = None
    normalized_filename: Optional[str] = None
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    detected_file_type: Optional[str] = None
    file_size_bytes: int = 0
    human_readable_size: str = ""
    full_path: Optional[str] = None
    project_relative_path: Optional[str] = None
    parent_folder: Optional[str] = None
    folder_depth: int = 0
    source_root: Optional[str] = None
    exists_on_disk: bool = False
    referenced_by_ui: bool = False
    referenced_by_database: bool = False
    orphaned_on_disk: bool = False
    ui_references_missing_file: bool = False
    
    # Dates
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    accessed_date: Optional[str] = None
    upload_date: Optional[str] = None
    indexed_date: Optional[str] = None
    preview_generated_date: Optional[str] = None
    
    # Current organization
    main_page_module: Optional[str] = None
    main_inside_page_tab: Optional[str] = None
    secondary_tab: Optional[str] = None
    tertiary_tab: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    nested_category_path: Optional[str] = None
    folder_derived_category: Optional[str] = None
    database_category: Optional[str] = None
    ui_category: Optional[str] = None
    tag_list: List[str] = field(default_factory=list)
    section_label: Optional[str] = None
    count_group_shown_in_ui: Optional[str] = None
    route_page_where_appears: Optional[str] = None
    api_endpoint_where_appears: Optional[str] = None
    source_registry_database_table: Optional[str] = None
    
    # Document structure
    page_count: Optional[int] = None
    slide_count: Optional[int] = None
    sheet_count: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    number_of_frames: Optional[int] = None
    ome_tiff_metadata: Optional[Dict] = None
    number_of_series: Optional[int] = None
    number_of_channels: Optional[int] = None
    pyramid_levels: Optional[int] = None
    physical_pixel_size: Optional[str] = None
    z_c_t_dimensions: Optional[str] = None
    video_duration: Optional[str] = None
    audio_duration: Optional[str] = None
    notebook_cell_count: Optional[int] = None
    markdown_heading_count: Optional[int] = None
    json_yaml_top_level_keys: List[str] = field(default_factory=list)
    
    # Text/content extraction
    extractable_text: bool = False
    text_extraction_method: Optional[str] = None
    extraction_success: bool = False
    word_count: int = 0
    character_count: int = 0
    detected_language: Optional[str] = None
    extracted_title: Optional[str] = None
    first_heading: Optional[str] = None
    first_500_chars: Optional[str] = None
    top_repeated_keywords: List[str] = field(default_factory=list)
    scientific_lab_terms_detected: List[str] = field(default_factory=list)
    sample_ids_detected: List[str] = field(default_factory=list)
    patient_site_terms_detected: List[str] = field(default_factory=list)
    assay_terms_detected: List[str] = field(default_factory=list)
    marker_names_detected: List[str] = field(default_factory=list)
    protocol_terms_detected: List[str] = field(default_factory=list)
    inventory_terms_detected: List[str] = field(default_factory=list)
    order_shipping_terms_detected: List[str] = field(default_factory=list)
    owner_author: Optional[str] = None
    document_version: Optional[str] = None
    
    # Scientific/lab classification
    scientific_category: Optional[str] = None
    
    # Duplicate and quality checks
    checksum_sha256: Optional[str] = None
    quick_hash: Optional[str] = None
    exact_duplicate: bool = False
    near_duplicate_filename: bool = False
    near_duplicate_title: bool = False
    near_duplicate_first_page_text: bool = False
    duplicate_group_id: Optional[str] = None
    duplicate_reason: Optional[str] = None
    possible_obsolete_version: bool = False
    possible_newer_version: bool = False
    bad_filename: bool = False
    missing_category: bool = False
    missing_preview: bool = False
    missing_metadata: bool = False
    cannot_parse: bool = False
    parse_error_message: Optional[str] = None


class DocumentLibraryAuditor:
    """Main auditor class for comprehensive document library analysis"""
    
    def __init__(self, project_root: Path, reports_dir: Path):
        self.project_root = project_root
        self.reports_dir = reports_dir
        self.cache_dir = CACHE_DIR
        
        # Data structures
        self.all_files: List[FileMetadata] = []
        self.category_tree: Dict = {}
        self.file_type_distribution: Dict[str, int] = defaultdict(int)
        self.ui_files: Set[str] = set()
        self.database_files: Set[str] = set()
        self.filesystem_files: Set[str] = set()
        
        # Potential file roots to scan
        self.file_roots: List[Path] = []
        
        # Progress tracking
        self.progress_file = self.cache_dir / "audit_progress.json"
        self.load_progress()
    
    def load_progress(self):
        """Load previous progress if exists"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    LOGGER.info(f"Loaded previous progress from {self.progress_file}")
                    return progress
            except Exception as e:
                LOGGER.warning(f"Could not load progress file: {e}")
        return {}
    
    def save_progress(self, progress: Dict):
        """Save current progress"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            LOGGER.warning(f"Could not save progress: {e}")
    
    def discover_file_roots(self):
        """Discover all potential file roots in the project"""
        LOGGER.info("Phase 1: Discovering file roots...")
        
        potential_roots = [
            self.project_root / "uploads",
            self.project_root / "documents",
            self.project_root / "data",
            self.project_root / "static",
            self.project_root / "public",
            self.project_root / "storage",
            self.project_root / "files",
            self.project_root / "lab_files",
            self.project_root / "registry",
            self.project_root / "wet_lab",
            self.project_root / "protocols",
            self.project_root / "inventories",
            self.project_root / "imaging",
            self.project_root / "previews",
            self.project_root / "extracted",
            self.project_root / "generated",
            self.project_root / "notebooks",
            self.project_root / "database",
            self.project_root / "assets",
            self.project_root / "media",
            self.project_root / "projects",
            self.project_root / "docs",
            self.project_root / "app_skeleton" / "data",
            self.project_root / "app_skeleton" / "storage",
        ]
        
        # Also check for environment variables
        env_roots = [
            os.getenv("DOCUMENTS_ROOT"),
            os.getenv("FILES_ROOT"),
            os.getenv("STORAGE_ROOT"),
            os.getenv("PROJECTS_ROOT"),
            os.getenv("DATABASE_ROOT"),
        ]
        
        for env_root in env_roots:
            if env_root:
                potential_roots.append(Path(env_root))
        
        # Filter to existing directories
        for root in potential_roots:
            if root and root.exists() and root.is_dir():
                self.file_roots.append(root)
                LOGGER.info(f"Found file root: {root}")
        
        LOGGER.info(f"Total file roots discovered: {len(self.file_roots)}")
        return self.file_roots
    
    def walk_filesystem(self):
        """Walk all file roots and collect file metadata"""
        LOGGER.info("Phase 2: Walking filesystem to discover files...")
        
        total_files = 0
        for root in self.file_roots:
            LOGGER.info(f"Scanning root: {root}")
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    try:
                        metadata = self.extract_file_metadata(file_path, root)
                        self.all_files.append(metadata)
                        self.filesystem_files.add(str(file_path))
                        total_files += 1
                        
                        if total_files % 100 == 0:
                            LOGGER.info(f"Processed {total_files} files...")
                    except Exception as e:
                        LOGGER.warning(f"Error processing {file_path}: {e}")
        
        LOGGER.info(f"Total files discovered: {total_files}")
        return self.all_files
    
    def extract_file_metadata(self, file_path: Path, root: Path) -> FileMetadata:
        """Extract basic metadata from a file"""
        stat = file_path.stat()
        size_bytes = stat.st_size
        
        # Human-readable size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        
        extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Calculate quick hash for large files
        quick_hash = self.calculate_quick_hash(file_path)
        
        # Calculate SHA256 for smaller files
        checksum = None
        if size_bytes < 50 * 1024 * 1024:  # < 50MB
            checksum = self.calculate_sha256(file_path)
        
        # Detect scientific category from filename/path
        scientific_category = self.detect_scientific_category(file_path)
        
        return FileMetadata(
            original_filename=file_path.name,
            normalized_filename=self.normalize_filename(file_path.name),
            extension=extension,
            mime_type=mime_type,
            detected_file_type=self.detect_file_type(extension),
            file_size_bytes=size_bytes,
            human_readable_size=size_str,
            full_path=str(file_path),
            project_relative_path=str(file_path.relative_to(root)),
            parent_folder=str(file_path.parent.name),
            folder_depth=len(file_path.relative_to(root).parts),
            source_root=str(root),
            exists_on_disk=True,
            created_date=datetime.fromtimestamp(stat.st_ctime).isoformat() if stat.st_ctime else None,
            modified_date=datetime.fromtimestamp(stat.st_mtime).isoformat() if stat.st_mtime else None,
            quick_hash=quick_hash,
            checksum_sha256=checksum,
            scientific_category=scientific_category,
        )
    
    def normalize_filename(self, filename: str) -> str:
        """Normalize filename for comparison"""
        return re.sub(r'[^\w\-_.]', '_', filename.lower())
    
    def calculate_quick_hash(self, file_path: Path, chunk_size: 8192) -> str:
        """Calculate quick hash from first and last chunks"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read first chunk
                first_chunk = f.read(chunk_size)
                hasher.update(first_chunk)
                
                # Read last chunk if file is larger
                if file_path.stat().st_size > chunk_size * 2:
                    f.seek(-chunk_size, 2)
                    last_chunk = f.read(chunk_size)
                    hasher.update(last_chunk)
            
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def calculate_sha256(self, file_path: Path) -> str:
        """Calculate full SHA256 hash"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def detect_file_type(self, extension: str) -> str:
        """Detect file type from extension"""
        extension = extension.lower()
        
        type_map = {
            # Documents
            '.pdf': 'PDF',
            '.docx': 'DOCX',
            '.doc': 'DOC',
            '.rtf': 'RTF',
            '.txt': 'TXT',
            '.md': 'Markdown',
            '.html': 'HTML',
            '.xml': 'XML',
            '.tex': 'LaTeX',
            
            # Spreadsheets
            '.xlsx': 'XLSX',
            '.xls': 'XLS',
            '.csv': 'CSV',
            '.tsv': 'TSV',
            '.ods': 'ODS',
            
            # Presentations
            '.pptx': 'PPTX',
            '.ppt': 'PPT',
            
            # Images
            '.png': 'PNG',
            '.jpg': 'JPG',
            '.jpeg': 'JPG',
            '.webp': 'WEBP',
            '.svg': 'SVG',
            '.bmp': 'BMP',
            '.gif': 'GIF',
            '.tiff': 'TIFF',
            '.tif': 'TIFF',
            '.ome.tif': 'OME-TIFF',
            '.ome.tiff': 'OME-TIFF',
            
            # Scientific data
            '.czi': 'CZI',
            '.nd2': 'ND2',
            '.lif': 'LIF',
            '.svs': 'SVS',
            '.scn': 'SCN',
            '.qptiff': 'QPTIFF',
            '.h5': 'H5',
            '.hdf5': 'HDF5',
            '.h5ad': 'H5AD',
            '.zarr': 'Zarr',
            '.loom': 'Loom',
            '.fastq': 'FASTQ',
            '.bam': 'BAM',
            '.sam': 'SAM',
            '.vcf': 'VCF',
            '.gtf': 'GTF',
            '.gff': 'GFF',
            '.bed': 'BED',
            '.fcs': 'FCS',
            
            # Code and notebooks
            '.py': 'Python',
            '.r': 'R',
            '.rmd': 'RMarkdown',
            '.ipynb': 'Jupyter',
            '.js': 'JavaScript',
            '.jsx': 'JSX',
            '.ts': 'TypeScript',
            '.tsx': 'TSX',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.sql': 'SQL',
            
            # Archives
            '.zip': 'ZIP',
            '.tar': 'TAR',
            '.gz': 'GZ',
            '.tgz': 'TGZ',
            '.7z': '7Z',
            '.rar': 'RAR',
            
            # Media
            '.mp4': 'MP4',
            '.mov': 'MOV',
            '.avi': 'AVI',
            '.wav': 'WAV',
            '.mp3': 'MP3',
            
            # Reference
            '.bib': 'BibTeX',
            '.ris': 'RIS',
            '.enw': 'EndNote',
        }
        
        return type_map.get(extension, 'Unknown')
    
    def detect_scientific_category(self, file_path: Path) -> str:
        """Detect scientific category from filename and path"""
        path_lower = str(file_path).lower()
        filename_lower = file_path.name.lower()
        
        # Protocol/SOP detection
        if any(term in path_lower for term in ['protocol', 'sop', 'standard operating']):
            if 'wet' in path_lower or 'lab' in path_lower:
                return FileCategory.WET_LAB_OPERATION.value
            return FileCategory.PROTOCOL.value
        
        # Inventory detection
        if any(term in path_lower for term in ['inventory', 'stock', 'reagent', 'antibody', 'marker']):
            if 'antibody' in path_lower or 'marker' in path_lower:
                if 'panel' in path_lower:
                    return FileCategory.MARKER_PANEL.value
                return FileCategory.ANTIBODY_PANEL.value
            return FileCategory.INVENTORY.value
        
        # Sample preparation
        if any(term in path_lower for term in ['sample prep', 'preparation', 'extraction']):
            return FileCategory.SAMPLE_PREPARATION.value
        
        # Tissue types
        if 'omentum' in path_lower:
            return FileCategory.OMENTUM.value
        if 'adnexa' in path_lower:
            return FileCategory.ADNEXA.value
        if 'ffpe' in path_lower:
            return FileCategory.FFPE.value
        if 'frozen' in path_lower:
            return FileCategory.FROZEN_TISSUE.value
        
        # Imaging/CyCIF
        if 'cycif' in path_lower or 'tcycif' in path_lower:
            if 'tcycif' in path_lower:
                return FileCategory.TCYCIF.value
            return FileCategory.CYCIF.value
        
        # Microscopy
        if any(term in path_lower for term in ['microscopy', 'image', 'slide', 'section']):
            if 'qc' in path_lower:
                return FileCategory.QC.value
            if 'slide' in path_lower:
                return FileCategory.SLIDES.value
            if 'section' in path_lower:
                return FileCategory.SECTIONS.value
            return FileCategory.MICROSCOPY.value
        
        # Sequencing
        if any(term in path_lower for term in ['scrna', 'single cell', 'rna seq', 'sequencing']):
            return FileCategory.SCRNA_SEQ.value
        
        # Bioinformatics
        if any(term in path_lower for term in ['bioinfo', 'analysis', 'pipeline', 'workflow']):
            return FileCategory.BIOINFORMATICS.value
        
        # Orders
        if any(term in path_lower for term in ['order', 'purchase', 'shipping', 'courier']):
            return FileCategory.ORDER_FORMS.value
        
        # Administrative
        if any(term in path_lower for term in ['admin', 'meeting', 'report', 'invoice']):
            return FileCategory.ADMINISTRATIVE_DOCUMENT.value
        
        # Notebooks
        if file_path.suffix in ['.ipynb', '.rmd']:
            return FileCategory.COMPUTATIONAL_NOTEBOOK.value
        
        # Spreadsheets
        if file_path.suffix in ['.xlsx', '.xls', '.csv']:
            if 'tracker' in path_lower or 'log' in path_lower:
                return FileCategory.SPREADSHEET_TRACKER.value
            return FileCategory.DATABASE_EXPORT.value
        
        return FileCategory.UNKNOWN.value
    
    def analyze_file_type_distribution(self):
        """Analyze distribution of file types"""
        LOGGER.info("Phase 3: Analyzing file type distribution...")
        
        for file_meta in self.all_files:
            file_type = file_meta.detected_file_type or 'Unknown'
            self.file_type_distribution[file_type] += 1
        
        LOGGER.info(f"File types found: {len(self.file_type_distribution)}")
        return self.file_type_distribution
    
    def detect_duplicates(self):
        """Detect duplicate files"""
        LOGGER.info("Phase 4: Detecting duplicate files...")
        
        # Group by SHA256
        sha256_groups: Dict[str, List[FileMetadata]] = defaultdict(list)
        for file_meta in self.all_files:
            if file_meta.checksum_sha256:
                sha256_groups[file_meta.checksum_sha256].append(file_meta)
        
        # Mark exact duplicates
        for sha256, files in sha256_groups.items():
            if len(files) > 1:
                for file_meta in files:
                    file_meta.exact_duplicate = True
                    file_meta.duplicate_group_id = sha256
                    file_meta.duplicate_reason = "exact_sha256_match"
        
        # Group by quick hash for large files
        quick_hash_groups: Dict[str, List[FileMetadata]] = defaultdict(list)
        for file_meta in self.all_files:
            if file_meta.quick_hash and not file_meta.checksum_sha256:
                quick_hash_groups[file_meta.quick_hash].append(file_meta)
        
        for quick_hash, files in quick_hash_groups.items():
            if len(files) > 1:
                for file_meta in files:
                    file_meta.near_duplicate_filename = True
                    file_meta.duplicate_group_id = quick_hash
                    file_meta.duplicate_reason = "quick_hash_match"
        
        duplicate_count = sum(1 for f in self.all_files if f.exact_duplicate)
        LOGGER.info(f"Found {duplicate_count} exact duplicates")
        
        return self.all_files
    
    def generate_reports(self):
        """Generate all audit reports"""
        LOGGER.info("Phase 5: Generating audit reports...")
        
        # 1. document_inventory.csv
        self.generate_csv_inventory()
        
        # 2. document_inventory.json
        self.generate_json_inventory()
        
        # 3. category_tree.json
        self.generate_category_tree()
        
        # 4. category_summary.csv
        self.generate_category_summary()
        
        # 5. file_type_summary.md
        self.generate_file_type_summary()
        
        # 6. duplicate_candidates.md
        self.generate_duplicate_report()
        
        # 7. audit_summary.md
        self.generate_audit_summary()
        
        LOGGER.info(f"All reports generated in {self.reports_dir}")
    
    def generate_csv_inventory(self):
        """Generate CSV inventory of all files"""
        output_file = self.reports_dir / "document_inventory.csv"
        
        fieldnames = [
            'document_id', 'original_filename', 'extension', 'detected_file_type',
            'file_size_bytes', 'human_readable_size', 'full_path', 'project_relative_path',
            'parent_folder', 'folder_depth', 'source_root', 'exists_on_disk',
            'created_date', 'modified_date', 'category', 'subcategory',
            'scientific_category', 'extractable_text', 'word_count', 'character_count',
            'checksum_sha256', 'quick_hash', 'exact_duplicate', 'duplicate_reason',
            'page_count', 'sheet_count', 'image_width', 'image_height',
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for file_meta in self.all_files:
                row = {k: getattr(file_meta, k) for k in fieldnames}
                writer.writerow(row)
        
        LOGGER.info(f"Generated CSV inventory: {output_file}")
    
    def generate_json_inventory(self):
        """Generate JSON inventory"""
        output_file = self.reports_dir / "document_inventory.json"
        
        inventory = [asdict(f) for f in self.all_files]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, default=str)
        
        LOGGER.info(f"Generated JSON inventory: {output_file}")
    
    def generate_category_tree(self):
        """Generate category tree from discovered categories"""
        output_file = self.reports_dir / "category_tree.json"
        
        # Build tree from scientific categories
        category_tree = {
            "scientific_categories": {},
            "file_types": {},
            "folder_structure": {},
        }
        
        # Group by scientific category
        for file_meta in self.all_files:
            sci_cat = file_meta.scientific_category or "unknown"
            if sci_cat not in category_tree["scientific_categories"]:
                category_tree["scientific_categories"][sci_cat] = {
                    "count": 0,
                    "total_size": 0,
                    "file_types": defaultdict(int),
                    "examples": []
                }
            
            category_tree["scientific_categories"][sci_cat]["count"] += 1
            category_tree["scientific_categories"][sci_cat]["total_size"] += file_meta.file_size_bytes
            category_tree["scientific_categories"][sci_cat]["file_types"][file_meta.detected_file_type or "unknown"] += 1
            
            if len(category_tree["scientific_categories"][sci_cat]["examples"]) < 5:
                category_tree["scientific_categories"][sci_cat]["examples"].append(file_meta.original_filename)
        
        # Convert defaultdicts to regular dicts
        for cat in category_tree["scientific_categories"].values():
            cat["file_types"] = dict(cat["file_types"])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(category_tree, f, indent=2, default=str)
        
        LOGGER.info(f"Generated category tree: {output_file}")
    
    def generate_category_summary(self):
        """Generate category summary CSV"""
        output_file = self.reports_dir / "category_summary.csv"
        
        fieldnames = [
            'category', 'file_count', 'total_size_bytes', 'avg_size_bytes',
            'file_types', 'example_files'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Get categories from category tree
            category_tree_file = self.reports_dir / "category_tree.json"
            if category_tree_file.exists():
                with open(category_tree_file, 'r') as f:
                    category_tree = json.load(f)
                
                for category, data in category_tree["scientific_categories"].items():
                    writer.writerow({
                        'category': category,
                        'file_count': data["count"],
                        'total_size_bytes': data["total_size"],
                        'avg_size_bytes': data["total_size"] // data["count"] if data["count"] > 0 else 0,
                        'file_types': json.dumps(data["file_types"]),
                        'example_files': json.dumps(data["examples"])
                    })
        
        LOGGER.info(f"Generated category summary: {output_file}")
    
    def generate_file_type_summary(self):
        """Generate file type summary markdown"""
        output_file = self.reports_dir / "file_type_summary.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# File Type Distribution Summary\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Total Files:** {len(self.all_files)}\n\n")
            
            f.write("## File Type Counts\n\n")
            f.write("| File Type | Count | Percentage |\n")
            f.write("|-----------|-------|------------|\n")
            
            total_files = len(self.all_files)
            sorted_types = sorted(self.file_type_distribution.items(), key=lambda x: x[1], reverse=True)
            
            for file_type, count in sorted_types:
                percentage = (count / total_files * 100) if total_files > 0 else 0
                f.write(f"| {file_type} | {count} | {percentage:.1f}% |\n")
        
        LOGGER.info(f"Generated file type summary: {output_file}")
    
    def generate_duplicate_report(self):
        """Generate duplicate candidates report"""
        output_file = self.reports_dir / "duplicate_candidates.md"
        
        duplicates = [f for f in self.all_files if f.exact_duplicate or f.near_duplicate_filename]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Duplicate Candidates Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Total Duplicate Candidates:** {len(duplicates)}\n\n")
            
            # Group by duplicate group
            groups = defaultdict(list)
            for dup in duplicates:
                if dup.duplicate_group_id:
                    groups[dup.duplicate_group_id].append(dup)
            
            f.write("## Duplicate Groups\n\n")
            for group_id, files in groups.items():
                f.write(f"### Group: {group_id}\n")
                f.write(f"**Reason:** {files[0].duplicate_reason}\n")
                f.write(f"**Count:** {len(files)}\n\n")
                for file_meta in files:
                    f.write(f"- {file_meta.full_path} ({file_meta.human_readable_size})\n")
                f.write("\n")
        
        LOGGER.info(f"Generated duplicate report: {output_file}")
    
    def generate_audit_summary(self):
        """Generate final audit summary"""
        output_file = self.reports_dir / "audit_summary.md"
        
        total_files = len(self.all_files)
        total_size = sum(f.file_size_bytes for f in self.all_files)
        duplicate_count = sum(1 for f in self.all_files if f.exact_duplicate)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Document Library Audit Summary\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Project Root:** {self.project_root}\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Files Found:** {total_files}\n")
            f.write(f"- **Total Size:** {total_size / (1024**3):.2f} GB\n")
            f.write(f"- **File Roots Scanned:** {len(self.file_roots)}\n")
            f.write(f"- **File Types Detected:** {len(self.file_type_distribution)}\n")
            f.write(f"- **Exact Duplicates:** {duplicate_count}\n")
            f.write(f"- **Scientific Categories:** {len(set(f.scientific_category for f in self.all_files))}\n\n")
            
            f.write("## Top 10 File Types\n\n")
            sorted_types = sorted(self.file_type_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            for file_type, count in sorted_types:
                f.write(f"- {file_type}: {count}\n")
            
            f.write("\n## Top 10 Largest Files\n\n")
            sorted_by_size = sorted(self.all_files, key=lambda x: x.file_size_bytes, reverse=True)[:10]
            for file_meta in sorted_by_size:
                f.write(f"- {file_meta.original_filename}: {file_meta.human_readable_size}\n")
            
            f.write("\n## Reports Generated\n\n")
            f.write("1. document_inventory.csv - Complete file inventory\n")
            f.write("2. document_inventory.json - Structured inventory\n")
            f.write("3. category_tree.json - Category hierarchy\n")
            f.write("4. category_summary.csv - Category statistics\n")
            f.write("5. file_type_summary.md - File type distribution\n")
            f.write("6. duplicate_candidates.md - Duplicate analysis\n")
            f.write("7. audit_summary.md - This summary\n")
        
        LOGGER.info(f"Generated audit summary: {output_file}")
    
    def run_full_audit(self):
        """Run the complete audit process"""
        LOGGER.info("=" * 80)
        LOGGER.info("Starting Comprehensive Document Library Audit")
        LOGGER.info("=" * 80)
        
        start_time = datetime.now()
        
        # Phase 1: Discover file roots
        self.discover_file_roots()
        
        # Phase 2: Walk filesystem
        self.walk_filesystem()
        
        # Phase 3: Analyze file types
        self.analyze_file_type_distribution()
        
        # Phase 4: Detect duplicates
        self.detect_duplicates()
        
        # Phase 5: Generate reports
        self.generate_reports()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        LOGGER.info("=" * 80)
        LOGGER.info(f"Audit completed in {duration}")
        LOGGER.info(f"Reports saved to: {self.reports_dir}")
        LOGGER.info("=" * 80)
        
        # Print final summary
        print("\n" + "=" * 80)
        print("AUDIT COMPLETE - FINAL SUMMARY")
        print("=" * 80)
        print(f"Total files found: {len(self.all_files)}")
        print(f"Total size: {sum(f.file_size_bytes for f in self.all_files) / (1024**3):.2f} GB")
        print(f"File types: {len(self.file_type_distribution)}")
        print(f"Exact duplicates: {sum(1 for f in self.all_files if f.exact_duplicate)}")
        print(f"Reports directory: {self.reports_dir}")
        print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Comprehensive Document Library Audit")
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(PROJECT_ROOT),
        help="Project root directory"
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=str(REPORTS_DIR),
        help="Reports output directory"
    )
    
    args = parser.parse_args()
    
    auditor = DocumentLibraryAuditor(
        project_root=Path(args.project_root),
        reports_dir=Path(args.reports_dir)
    )
    
    auditor.run_full_audit()


if __name__ == "__main__":
    main()
