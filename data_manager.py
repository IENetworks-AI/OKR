#!/usr/bin/env python3
"""
Data Manager - Comprehensive Data Upload/Download Utility
Handles real data management with multiple format support
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import shutil
import argparse
from typing import Dict, List, Any, Optional
import hashlib
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, base_dir: str = "data"):
        """Initialize Data Manager with base directory"""
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.final_dir = self.base_dir / "final"
        self.backup_dir = self.base_dir / "backup"
        
        # Create directories
        self._create_directories()
        
        # Supported file formats
        self.supported_formats = {
            '.csv': self._read_csv,
            '.json': self._read_json,
            '.xlsx': self._read_excel,
            '.parquet': self._read_parquet,
            '.pickle': self._read_pickle,
            '.h5': self._read_hdf,
            '.xml': self._read_xml,
            '.yaml': self._read_yaml,
            '.yml': self._read_yaml
        }
        
        # Supported write formats
        self.write_formats = {
            '.csv': self._write_csv,
            '.json': self._write_json,
            '.xlsx': self._write_excel,
            '.parquet': self._write_parquet,
            '.pickle': self._write_pickle,
            '.h5': self._write_hdf
        }
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [self.raw_dir, self.processed_dir, self.final_dir, self.backup_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive file information"""
        stat = file_path.stat()
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return {
            'name': file_path.name,
            'path': str(file_path),
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash': file_hash,
            'mime_type': mime_type,
            'extension': file_path.suffix.lower()
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        """Read CSV file with smart encoding detection"""
        try:
            # Try UTF-8 first
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Try latin-1
                return pd.read_csv(file_path, encoding='latin-1')
            except UnicodeDecodeError:
                # Try with error handling
                return pd.read_csv(file_path, encoding='utf-8', errors='replace')
    
    def _read_json(self, file_path: Path) -> pd.DataFrame:
        """Read JSON file"""
        try:
            return pd.read_json(file_path)
        except Exception as e:
            # Try reading as JSON lines
            try:
                return pd.read_json(file_path, lines=True)
            except:
                raise ValueError(f"Cannot read JSON file: {e}")
    
    def _read_excel(self, file_path: Path) -> pd.DataFrame:
        """Read Excel file"""
        try:
            return pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Cannot read Excel file: {e}")
    
    def _read_parquet(self, file_path: Path) -> pd.DataFrame:
        """Read Parquet file"""
        try:
            return pd.read_parquet(file_path)
        except Exception as e:
            raise ValueError(f"Cannot read Parquet file: {e}")
    
    def _read_pickle(self, file_path: Path) -> pd.DataFrame:
        """Read Pickle file"""
        try:
            return pd.read_pickle(file_path)
        except Exception as e:
            raise ValueError(f"Cannot read Pickle file: {e}")
    
    def _read_hdf(self, file_path: Path) -> pd.DataFrame:
        """Read HDF file"""
        try:
            return pd.read_hdf(file_path)
        except Exception as e:
            raise ValueError(f"Cannot read HDF file: {e}")
    
    def _read_xml(self, file_path: Path) -> pd.DataFrame:
        """Read XML file"""
        try:
            return pd.read_xml(file_path)
        except Exception as e:
            raise ValueError(f"Cannot read XML file: {e}")
    
    def _read_yaml(self, file_path: Path) -> pd.DataFrame:
        """Read YAML file"""
        try:
            import yaml
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            return pd.DataFrame(data)
        except Exception as e:
            raise ValueError(f"Cannot read YAML file: {e}")
    
    def _write_csv(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write CSV file"""
        data.to_csv(file_path, index=False, **kwargs)
    
    def _write_json(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write JSON file"""
        data.to_json(file_path, orient='records', indent=2, **kwargs)
    
    def _write_excel(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write Excel file"""
        data.to_excel(file_path, index=False, **kwargs)
    
    def _write_parquet(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write Parquet file"""
        data.to_parquet(file_path, index=False, **kwargs)
    
    def _write_pickle(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write Pickle file"""
        data.to_pickle(file_path, **kwargs)
    
    def _write_hdf(self, data: pd.DataFrame, file_path: Path, **kwargs):
        """Write HDF file"""
        data.to_hdf(file_path, key='data', mode='w', **kwargs)
    
    def upload_data(self, source_path: str, target_folder: str = "raw", 
                   target_name: Optional[str] = None) -> Dict[str, Any]:
        """Upload data file to specified folder"""
        try:
            source_path = Path(source_path)
            
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            # Determine target folder
            if target_folder == "raw":
                target_dir = self.raw_dir
            elif target_folder == "processed":
                target_dir = self.processed_dir
            elif target_folder == "final":
                target_dir = self.final_dir
            else:
                raise ValueError(f"Invalid target folder: {target_folder}")
            
            # Determine target filename
            if target_name is None:
                target_name = source_path.name
            
            target_path = target_dir / target_name
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Get file info
            file_info = self._get_file_info(target_path)
            
            logger.info(f"Data uploaded successfully: {target_path}")
            return {
                'status': 'success',
                'message': 'Data uploaded successfully',
                'file_info': file_info
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def download_data(self, filename: str, source_folder: str = "raw", 
                     target_path: Optional[str] = None) -> Dict[str, Any]:
        """Download data file from specified folder"""
        try:
            # Determine source folder
            if source_folder == "raw":
                source_dir = self.raw_dir
            elif source_folder == "processed":
                source_dir = self.processed_dir
            elif source_folder == "final":
                source_dir = self.final_dir
            else:
                raise ValueError(f"Invalid source folder: {source_folder}")
            
            source_path = source_dir / filename
            
            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {source_path}")
            
            # Determine target path
            if target_path is None:
                target_path = f"./downloaded_{filename}"
            
            target_path = Path(target_path)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Get file info
            file_info = self._get_file_info(source_path)
            
            logger.info(f"Data downloaded successfully: {target_path}")
            return {
                'status': 'success',
                'message': 'Data downloaded successfully',
                'file_info': file_info,
                'target_path': str(target_path)
            }
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def read_data(self, filename: str, folder: str = "raw") -> pd.DataFrame:
        """Read data file from specified folder"""
        try:
            # Determine folder
            if folder == "raw":
                source_dir = self.raw_dir
            elif folder == "processed":
                source_dir = self.processed_dir
            elif folder == "final":
                source_dir = self.final_dir
            else:
                raise ValueError(f"Invalid folder: {folder}")
            
            file_path = source_dir / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file extension
            extension = file_path.suffix.lower()
            
            if extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {extension}")
            
            # Read file
            data = self.supported_formats[extension](file_path)
            
            logger.info(f"Data read successfully: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Read failed: {e}")
            raise
    
    def write_data(self, data: pd.DataFrame, filename: str, folder: str = "processed", 
                   format: Optional[str] = None) -> str:
        """Write data to specified folder"""
        try:
            # Determine folder
            if folder == "raw":
                target_dir = self.raw_dir
            elif folder == "processed":
                target_dir = self.processed_dir
            elif folder == "final":
                target_dir = self.final_dir
            else:
                raise ValueError(f"Invalid folder: {folder}")
            
            # Determine format
            if format is None:
                format = Path(filename).suffix.lower()
            
            if format not in self.write_formats:
                raise ValueError(f"Unsupported write format: {format}")
            
            # Ensure filename has correct extension
            if not filename.endswith(format):
                filename = f"{filename}{format}"
            
            target_path = target_dir / filename
            
            # Write file
            self.write_formats[format](data, target_path)
            
            logger.info(f"Data written successfully: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"Write failed: {e}")
            raise
    
    def list_files(self, folder: str = "raw") -> List[Dict[str, Any]]:
        """List all files in specified folder with details"""
        try:
            # Determine folder
            if folder == "raw":
                source_dir = self.raw_dir
            elif folder == "processed":
                source_dir = self.processed_dir
            elif folder == "final":
                source_dir = self.final_dir
            else:
                raise ValueError(f"Invalid folder: {folder}")
            
            files = []
            for file_path in source_dir.iterdir():
                if file_path.is_file():
                    file_info = self._get_file_info(file_path)
                    files.append(file_info)
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []
    
    def backup_data(self, folder: str = "raw", backup_name: Optional[str] = None) -> str:
        """Create backup of specified folder"""
        try:
            # Determine source folder
            if folder == "raw":
                source_dir = self.raw_dir
            elif folder == "processed":
                source_dir = self.processed_dir
            elif folder == "final":
                source_dir = self.final_dir
            else:
                raise ValueError(f"Invalid folder: {folder}")
            
            # Create backup name
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{folder}_backup_{timestamp}.zip"
            
            backup_path = self.backup_dir / backup_name
            
            # Create zip backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
    
    def restore_backup(self, backup_path: str, target_folder: str = "raw") -> bool:
        """Restore data from backup"""
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Determine target folder
            if target_folder == "raw":
                target_dir = self.raw_dir
            elif target_folder == "processed":
                target_dir = self.processed_dir
            elif target_folder == "final":
                target_dir = self.final_dir
            else:
                raise ValueError(f"Invalid target folder: {target_folder}")
            
            # Clear target directory
            shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            logger.info(f"Backup restored successfully to {target_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def get_data_summary(self, folder: str = "raw") -> Dict[str, Any]:
        """Get comprehensive summary of data in specified folder"""
        try:
            files = self.list_files(folder)
            
            if not files:
                return {
                    'folder': folder,
                    'total_files': 0,
                    'total_size_mb': 0,
                    'file_types': {},
                    'summary': 'No files found'
                }
            
            # Calculate totals
            total_size_mb = sum(f['size_mb'] for f in files)
            file_types = {}
            
            for file_info in files:
                ext = file_info['extension']
                if ext not in file_types:
                    file_types[ext] = {'count': 0, 'total_size_mb': 0}
                file_types[ext]['count'] += 1
                file_types[ext]['total_size_mb'] += file_info['size_mb']
            
            # Get sample data for analysis
            sample_data = None
            if files:
                try:
                    sample_file = files[0]
                    sample_data = self.read_data(sample_file['name'], folder)
                except:
                    pass
            
            summary = {
                'folder': folder,
                'total_files': len(files),
                'total_size_mb': round(total_size_mb, 2),
                'file_types': file_types,
                'last_modified': max(f['modified'] for f in files),
                'sample_data_shape': sample_data.shape if sample_data is not None else None,
                'sample_data_columns': list(sample_data.columns) if sample_data is not None else None
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Get summary failed: {e}")
            return {
                'folder': folder,
                'error': str(e)
            }

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Data Manager - Upload/Download Utility")
    parser.add_argument('action', choices=['upload', 'download', 'list', 'read', 'write', 'backup', 'restore', 'summary'],
                       help='Action to perform')
    parser.add_argument('--source', help='Source file or folder')
    parser.add_argument('--target', help='Target file or folder')
    parser.add_argument('--folder', default='raw', choices=['raw', 'processed', 'final'],
                       help='Folder to operate on')
    parser.add_argument('--format', help='File format for write operations')
    parser.add_argument('--backup-name', help='Name for backup file')
    
    args = parser.parse_args()
    
    # Initialize data manager
    dm = DataManager()
    
    try:
        if args.action == 'upload':
            if not args.source:
                print("Error: --source is required for upload")
                return 1
            
            result = dm.upload_data(args.source, args.folder, args.target)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'download':
            if not args.source:
                print("Error: --source (filename) is required for download")
                return 1
            
            result = dm.download_data(args.source, args.folder, args.target)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'list':
            files = dm.list_files(args.folder)
            print(f"Files in {args.folder} folder:")
            for file_info in files:
                print(f"  {file_info['name']} ({file_info['size_mb']} MB) - {file_info['modified']}")
            
        elif args.action == 'read':
            if not args.source:
                print("Error: --source (filename) is required for read")
                return 1
            
            data = dm.read_data(args.source, args.folder)
            print(f"Data shape: {data.shape}")
            print(f"Columns: {list(data.columns)}")
            print("\nFirst 5 rows:")
            print(data.head())
            
        elif args.action == 'write':
            if not args.source:
                print("Error: --source (filename) is required for write")
                return 1
            
            # Generate sample data for demonstration
            sample_data = pd.DataFrame({
                'id': range(1, 101),
                'name': [f'Item_{i}' for i in range(1, 101)],
                'value': np.random.randn(100),
                'category': np.random.choice(['A', 'B', 'C'], 100)
            })
            
            result_path = dm.write_data(sample_data, args.source, args.folder, args.format)
            print(f"Data written to: {result_path}")
            
        elif args.action == 'backup':
            result_path = dm.backup_data(args.folder, args.backup_name)
            print(f"Backup created: {result_path}")
            
        elif args.action == 'restore':
            if not args.source:
                print("Error: --source (backup path) is required for restore")
                return 1
            
            success = dm.restore_backup(args.source, args.folder)
            if success:
                print(f"Backup restored to {args.folder} folder")
            else:
                print("Restore failed")
                return 1
                
        elif args.action == 'summary':
            summary = dm.get_data_summary(args.folder)
            print(json.dumps(summary, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())