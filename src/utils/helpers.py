"""
Utility Helper Functions

Common utility functions used throughout the ML pipeline.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if it doesn't"""
    try:
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Directory ensured: {path}")
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        raise


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        else:
            logger.warning(f"Config file not found: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """Save configuration to JSON file"""
    try:
        ensure_directory(os.path.dirname(config_path))
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2, default=str)
        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {e}")
        return False


def generate_timestamp() -> str:
    """Generate timestamp string"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> bool:
    """Validate DataFrame structure and content"""
    try:
        if df.empty:
            logger.warning("DataFrame is empty")
            return False

        if required_columns:
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False

        # Check for infinite values
        if np.isinf(df.select_dtypes(include=[np.number])).any().any():
            logger.warning("DataFrame contains infinite values")

        # Check for null values
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            logger.info(f"Null value counts:\n{null_counts[null_counts > 0]}")

        return True

    except Exception as e:
        logger.error(f"Error validating DataFrame: {e}")
        return False


def sample_dataframe(
    df: pd.DataFrame, sample_size: int = 1000, random_state: int = 42
) -> pd.DataFrame:
    """Sample DataFrame for testing/development"""
    try:
        if len(df) <= sample_size:
            return df

        sampled_df = df.sample(n=sample_size, random_state=random_state)
        logger.info(f"Sampled DataFrame: {len(sampled_df)} rows from {len(df)} total")
        return sampled_df

    except Exception as e:
        logger.error(f"Error sampling DataFrame: {e}")
        return df


def calculate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate basic statistics for DataFrame"""
    try:
        stats = {
            "shape": df.shape,
            "memory_usage": df.memory_usage(deep=True).sum(),
            "dtypes": df.dtypes.to_dict(),
            "null_counts": df.isnull().sum().to_dict(),
            "unique_counts": df.nunique().to_dict(),
        }

        # Numerical statistics
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        if len(numerical_cols) > 0:
            stats["numerical_stats"] = df[numerical_cols].describe().to_dict()

        # Categorical statistics
        categorical_cols = df.select_dtypes(include=["object"]).columns
        if len(categorical_cols) > 0:
            stats["categorical_stats"] = {}
            for col in categorical_cols:
                stats["categorical_stats"][col] = (
                    df[col].value_counts().head(10).to_dict()
                )

        return stats

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return {}


def save_dataframe(df: pd.DataFrame, filepath: str, format: str = "auto") -> bool:
    """Save DataFrame to file"""
    try:
        ensure_directory(os.path.dirname(filepath))

        if format == "auto":
            if filepath.endswith(".csv"):
                format = "csv"
            elif filepath.endswith(".json"):
                format = "json"
            elif filepath.endswith(".parquet"):
                format = "parquet"
            elif filepath.endswith(".pkl"):
                format = "pickle"
            else:
                format = "csv"

        if format == "csv":
            df.to_csv(filepath, index=False)
        elif format == "json":
            df.to_json(filepath, orient="records", indent=2)
        elif format == "parquet":
            df.to_parquet(filepath, index=False)
        elif format == "pickle":
            df.to_pickle(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"DataFrame saved to {filepath} in {format} format")
        return True

    except Exception as e:
        logger.error(f"Error saving DataFrame to {filepath}: {e}")
        return False


def load_dataframe(filepath: str, format: str = "auto") -> pd.DataFrame:
    """Load DataFrame from file"""
    try:
        if format == "auto":
            if filepath.endswith(".csv"):
                format = "csv"
            elif filepath.endswith(".json"):
                format = "json"
            elif filepath.endswith(".parquet"):
                format = "parquet"
            elif filepath.endswith(".pkl"):
                format = "pickle"
            else:
                format = "csv"

        if format == "csv":
            df = pd.read_csv(filepath)
        elif format == "json":
            df = pd.read_json(filepath)
        elif format == "parquet":
            df = pd.read_parquet(filepath)
        elif format == "pickle":
            df = pd.read_pickle(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"DataFrame loaded from {filepath}. Shape: {df.shape}")
        return df

    except Exception as e:
        logger.error(f"Error loading DataFrame from {filepath}: {e}")
        raise


def create_backup(filepath: str, backup_dir: str = "backups") -> str:
    """Create backup of a file"""
    try:
        if not os.path.exists(filepath):
            logger.warning(f"File not found for backup: {filepath}")
            return ""

        ensure_directory(backup_dir)
        timestamp = generate_timestamp()
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)

        backup_path = os.path.join(backup_dir, f"{name}_{timestamp}{ext}")

        # Copy file
        import shutil

        shutil.copy2(filepath, backup_path)

        logger.info(f"Backup created: {backup_path}")
        return backup_path

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return ""


def cleanup_old_files(
    directory: str, pattern: str = "*", max_age_days: int = 30
) -> int:
    """Clean up old files in directory"""
    try:
        import glob
        import time

        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600

        files_to_remove = []
        for filepath in glob.glob(os.path.join(directory, pattern)):
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    files_to_remove.append(filepath)

        removed_count = 0
        for filepath in files_to_remove:
            try:
                os.remove(filepath)
                removed_count += 1
                logger.debug(f"Removed old file: {filepath}")
            except Exception as e:
                logger.warning(f"Could not remove file {filepath}: {e}")

        logger.info(f"Cleanup completed. Removed {removed_count} old files")
        return removed_count

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 0


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        import psutil

        info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage("/").percent,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        }

        return info

    except ImportError:
        logger.warning("psutil not available, limited system info")
        return {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {}


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """Setup logging configuration"""
    try:
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            ensure_directory(os.path.dirname(log_file))
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        logger.info(f"Logging setup completed. Level: {log_level}")

    except Exception as e:
        print(f"Error setting up logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(level=getattr(logging, log_level.upper()))
