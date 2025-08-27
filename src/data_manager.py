#!/usr/bin/env python3
"""
Real Data Manager
Handles file uploads, downloads, and data operations with proper folder management
"""

import os
import shutil
import json
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime
import zipfile
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataManager:
    """Manages real data operations including upload, download, and processing"""
    
    def __init__(self, workspace_root: str = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).parent.parent
        else:
            self.workspace_root = Path(workspace_root)
            
        # Set up directory structure
        self.data_root = self.workspace_root / "data"
        self.raw_dir = self.data_root / "raw"
        self.processed_dir = self.data_root / "processed"
        self.models_dir = self.data_root / "models"
        self.archive_dir = self.data_root / "archive"
        self.uploads_dir = self.data_root / "uploads"
        self.downloads_dir = self.data_root / "downloads"
        
        # Create all directories
        for directory in [self.raw_dir, self.processed_dir, self.models_dir, 
                         self.archive_dir, self.uploads_dir, self.downloads_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Data manager initialized with root: {self.workspace_root}")
    
    def upload_file(self, file_path: str, file_data: bytes, 
                   destination: str = "raw") -> Dict[str, Any]:
        """
        Upload file to specified destination
        
        Args:
            file_path: Original file path/name
            file_data: File content as bytes
            destination: Destination folder (raw, processed, uploads)
            
        Returns:
            Dict with upload status and file info
        """
        try:
            # Determine destination directory
            if destination == "raw":
                dest_dir = self.raw_dir
            elif destination == "processed":
                dest_dir = self.processed_dir
            elif destination == "uploads":
                dest_dir = self.uploads_dir
            else:
                dest_dir = self.uploads_dir
                
            # Create secure filename
            filename = os.path.basename(file_path)
            safe_filename = self._make_safe_filename(filename)
            
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(safe_filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            
            dest_path = dest_dir / unique_filename
            
            # Write file
            with open(dest_path, 'wb') as f:
                f.write(file_data)
                
            file_info = {
                "status": "success",
                "original_name": filename,
                "saved_name": unique_filename,
                "path": str(dest_path),
                "size": len(file_data),
                "destination": destination,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"File uploaded successfully: {unique_filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def download_file(self, filename: str, source: str = "processed") -> Optional[bytes]:
        """
        Download file from specified source
        
        Args:
            filename: Name of file to download
            source: Source folder (raw, processed, models, archive)
            
        Returns:
            File content as bytes or None if not found
        """
        try:
            # Determine source directory
            if source == "raw":
                src_dir = self.raw_dir
            elif source == "processed":
                src_dir = self.processed_dir
            elif source == "models":
                src_dir = self.models_dir
            elif source == "archive":
                src_dir = self.archive_dir
            else:
                src_dir = self.processed_dir
                
            file_path = src_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
                
            with open(file_path, 'rb') as f:
                content = f.read()
                
            logger.info(f"File downloaded: {filename}")
            return content
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def list_files(self, directory: str = "all") -> Dict[str, List[Dict]]:
        """
        List files in specified directory or all directories
        
        Args:
            directory: Directory to list (raw, processed, models, archive, all)
            
        Returns:
            Dict with file listings
        """
        try:
            result = {}
            
            directories = {
                "raw": self.raw_dir,
                "processed": self.processed_dir,
                "models": self.models_dir,
                "archive": self.archive_dir,
                "uploads": self.uploads_dir,
                "downloads": self.downloads_dir
            }
            
            if directory == "all":
                dirs_to_list = directories.items()
            elif directory in directories:
                dirs_to_list = [(directory, directories[directory])]
            else:
                return {"error": f"Unknown directory: {directory}"}
            
            for dir_name, dir_path in dirs_to_list:
                files = []
                if dir_path.exists():
                    for file_path in dir_path.iterdir():
                        if file_path.is_file():
                            stat = file_path.stat()
                            files.append({
                                "name": file_path.name,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "extension": file_path.suffix
                            })
                
                result[dir_name] = sorted(files, key=lambda x: x["modified"], reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {"error": str(e)}
    
    def create_sample_data(self, num_samples: int = 1000) -> str:
        """
        Create sample OKR data and save to raw directory
        
        Args:
            num_samples: Number of sample records to generate
            
        Returns:
            Path to created file
        """
        try:
            logger.info(f"Creating sample data with {num_samples} records")
            
            # Generate sample data
            np.random.seed(42)
            
            departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations']
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            objective_types = ['Revenue', 'Efficiency', 'Quality', 'Growth', 'Innovation']
            priorities = ['High', 'Medium', 'Low']
            
            data = []
            for i in range(num_samples):
                record = {
                    'id': i + 1,
                    'department': np.random.choice(departments),
                    'quarter': np.random.choice(quarters),
                    'year': np.random.choice([2023, 2024]),
                    'objective_type': np.random.choice(objective_types),
                    'objective_title': f"Objective {i + 1}",
                    'key_result_1': f"KR1 for objective {i + 1}",
                    'key_result_2': f"KR2 for objective {i + 1}",
                    'key_result_3': f"KR3 for objective {i + 1}",
                    'team_size': np.random.randint(1, 21),
                    'budget': np.random.uniform(1000, 100000),
                    'timeline_days': np.random.randint(30, 365),
                    'priority': np.random.choice(priorities),
                    'progress_percentage': np.random.uniform(0, 100),
                    'success_score': np.random.uniform(0, 10),
                    'created_date': datetime.now().strftime("%Y-%m-%d"),
                    'updated_date': datetime.now().strftime("%Y-%m-%d")
                }
                data.append(record)
            
            # Save as CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"sample_okr_data_{timestamp}.csv"
            csv_path = self.raw_dir / csv_filename
            
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False)
            
            # Also save as JSON
            json_filename = f"sample_okr_data_{timestamp}.json"
            json_path = self.raw_dir / json_filename
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Sample data created: {csv_filename} and {json_filename}")
            return str(csv_path)
            
        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            raise
    
    def process_uploaded_file(self, filename: str) -> Dict[str, Any]:
        """
        Process an uploaded file and move it to processed directory
        
        Args:
            filename: Name of file to process
            
        Returns:
            Processing result
        """
        try:
            # Find file in uploads or raw directory
            file_path = None
            for directory in [self.uploads_dir, self.raw_dir]:
                potential_path = directory / filename
                if potential_path.exists():
                    file_path = potential_path
                    break
            
            if file_path is None:
                return {"status": "error", "message": f"File not found: {filename}"}
            
            # Process based on file type
            if filename.endswith('.csv'):
                result = self._process_csv_file(file_path)
            elif filename.endswith('.json'):
                result = self._process_json_file(file_path)
            else:
                # Copy as-is for other file types
                result = self._copy_file_to_processed(file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _process_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """Process CSV file"""
        try:
            # Read and validate CSV
            df = pd.read_csv(file_path)
            
            # Basic data cleaning
            df = df.dropna()  # Remove rows with missing values
            
            # Save processed version
            processed_name = f"processed_{file_path.name}"
            processed_path = self.processed_dir / processed_name
            df.to_csv(processed_path, index=False)
            
            return {
                "status": "success",
                "original_file": str(file_path),
                "processed_file": str(processed_path),
                "rows_original": len(pd.read_csv(file_path)),
                "rows_processed": len(df),
                "columns": list(df.columns)
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            return {"status": "error", "message": str(e)}
    
    def _process_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Process JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame for processing
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                return {"status": "error", "message": "Invalid JSON format"}
            
            # Basic data cleaning
            df = df.dropna()
            
            # Save as processed CSV
            processed_name = f"processed_{file_path.stem}.csv"
            processed_path = self.processed_dir / processed_name
            df.to_csv(processed_path, index=False)
            
            return {
                "status": "success",
                "original_file": str(file_path),
                "processed_file": str(processed_path),
                "rows_processed": len(df),
                "columns": list(df.columns)
            }
            
        except Exception as e:
            logger.error(f"Error processing JSON file: {e}")
            return {"status": "error", "message": str(e)}
    
    def _copy_file_to_processed(self, file_path: Path) -> Dict[str, Any]:
        """Copy file to processed directory"""
        try:
            processed_name = f"processed_{file_path.name}"
            processed_path = self.processed_dir / processed_name
            shutil.copy2(file_path, processed_path)
            
            return {
                "status": "success",
                "original_file": str(file_path),
                "processed_file": str(processed_path)
            }
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_data_package(self, package_type: str = "all") -> Optional[str]:
        """
        Create a ZIP package of data files
        
        Args:
            package_type: Type of package (raw, processed, models, all)
            
        Returns:
            Path to created ZIP file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"data_package_{package_type}_{timestamp}.zip"
            zip_path = self.downloads_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if package_type == "all":
                    directories = [
                        ("raw", self.raw_dir),
                        ("processed", self.processed_dir),
                        ("models", self.models_dir)
                    ]
                elif package_type == "raw":
                    directories = [("raw", self.raw_dir)]
                elif package_type == "processed":
                    directories = [("processed", self.processed_dir)]
                elif package_type == "models":
                    directories = [("models", self.models_dir)]
                else:
                    return None
                
                for dir_name, dir_path in directories:
                    if dir_path.exists():
                        for file_path in dir_path.rglob("*"):
                            if file_path.is_file():
                                arcname = f"{dir_name}/{file_path.relative_to(dir_path)}"
                                zipf.write(file_path, arcname)
            
            logger.info(f"Data package created: {zip_filename}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Error creating data package: {e}")
            return None
    
    def _make_safe_filename(self, filename: str) -> str:
        """Make filename safe for filesystem"""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        safe_filename = filename
        for char in unsafe_chars:
            safe_filename = safe_filename.replace(char, '_')
        
        # Limit length
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:255-len(ext)] + ext
            
        return safe_filename
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of all data directories"""
        try:
            summary = {
                "directories": {},
                "total_files": 0,
                "total_size": 0,
                "timestamp": datetime.now().isoformat()
            }
            
            directories = {
                "raw": self.raw_dir,
                "processed": self.processed_dir,
                "models": self.models_dir,
                "archive": self.archive_dir,
                "uploads": self.uploads_dir,
                "downloads": self.downloads_dir
            }
            
            for dir_name, dir_path in directories.items():
                if dir_path.exists():
                    files = list(dir_path.rglob("*"))
                    file_count = len([f for f in files if f.is_file()])
                    total_size = sum(f.stat().st_size for f in files if f.is_file())
                    
                    summary["directories"][dir_name] = {
                        "path": str(dir_path),
                        "files": file_count,
                        "size": total_size,
                        "size_mb": round(total_size / 1024 / 1024, 2)
                    }
                    
                    summary["total_files"] += file_count
                    summary["total_size"] += total_size
                else:
                    summary["directories"][dir_name] = {
                        "path": str(dir_path),
                        "files": 0,
                        "size": 0,
                        "size_mb": 0
                    }
            
            summary["total_size_mb"] = round(summary["total_size"] / 1024 / 1024, 2)
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {"error": str(e)}

def main():
    """Test the data manager"""
    manager = RealDataManager()
    
    # Create sample data
    sample_file = manager.create_sample_data(100)
    print(f"Created sample data: {sample_file}")
    
    # List files
    files = manager.list_files("all")
    print("File listing:", json.dumps(files, indent=2))
    
    # Get summary
    summary = manager.get_data_summary()
    print("Data summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()