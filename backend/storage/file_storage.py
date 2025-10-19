"""Local file storage utilities for claims reasoner."""

import shutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FileStorage:
    """
    Local file storage manager for policy documents, uploads, and sample cases.
    
    Provides methods for:
    - Managing directory structure
    - Saving/loading uploads by case_id
    - Listing policy documents
    - Managing sample cases
    """
    
    def __init__(
        self,
        policy_dir: str = "data/policies",
        sample_cases_dir: str = "data/sample_cases",
        uploads_dir: str = "data/uploads"
    ):
        """
        Initialize FileStorage.
        
        Args:
            policy_dir: Directory for policy PDF documents
            sample_cases_dir: Directory for sample test cases
            uploads_dir: Directory for temporary uploads
        """
        self.policy_dir = Path(policy_dir)
        self.sample_cases_dir = Path(sample_cases_dir)
        self.uploads_dir = Path(uploads_dir)
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        logger.info(
            f"Initialized FileStorage: "
            f"policy_dir={self.policy_dir}, "
            f"uploads_dir={self.uploads_dir}"
        )
    
    def _ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for directory in [self.policy_dir, self.sample_cases_dir, self.uploads_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    # Policy document methods
    
    def list_policy_documents(self, extension: str = ".pdf") -> List[Path]:
        """
        List all policy documents in the policy directory.
        
        Args:
            extension: File extension to filter (default: .pdf)
            
        Returns:
            List of Path objects for policy documents
        """
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory does not exist: {self.policy_dir}")
            return []
        
        policy_files = list(self.policy_dir.glob(f"*{extension}"))
        logger.info(f"Found {len(policy_files)} policy documents in {self.policy_dir}")
        
        return policy_files
    
    def get_policy_path(self, filename: str) -> Path:
        """
        Get full path for a policy document.
        
        Args:
            filename: Policy document filename
            
        Returns:
            Path object for the policy document
        """
        return self.policy_dir / filename
    
    def policy_exists(self, filename: str) -> bool:
        """
        Check if a policy document exists.
        
        Args:
            filename: Policy document filename
            
        Returns:
            True if policy exists, False otherwise
        """
        return (self.policy_dir / filename).exists()
    
    # Upload management methods
    
    def save_upload(
        self,
        case_id: str,
        filename: str,
        content: bytes,
        category: str = "general"
    ) -> Path:
        """
        Save an uploaded file for a specific case.
        
        Args:
            case_id: Unique case identifier
            filename: Original filename
            content: File content as bytes
            category: File category (e.g., "photos", "invoices", "fnol")
            
        Returns:
            Path where file was saved
            
        Raises:
            IOError: If file cannot be saved
        """
        # Create case directory structure
        case_dir = self.uploads_dir / case_id / category
        case_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = case_dir / filename
        
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Saved upload: {file_path} ({len(content)} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save upload {filename}: {str(e)}")
            raise IOError(f"Failed to save upload: {str(e)}") from e
    
    def load_upload(self, case_id: str, filename: str, category: str = "general") -> bytes:
        """
        Load an uploaded file for a specific case.
        
        Args:
            case_id: Unique case identifier
            filename: Filename to load
            category: File category
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        file_path = self.uploads_dir / case_id / category / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Upload not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.debug(f"Loaded upload: {file_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Failed to load upload {filename}: {str(e)}")
            raise IOError(f"Failed to load upload: {str(e)}") from e
    
    def list_uploads(
        self,
        case_id: str,
        category: Optional[str] = None
    ) -> List[Tuple[str, Path]]:
        """
        List all uploads for a specific case.
        
        Args:
            case_id: Unique case identifier
            category: Optional category filter
            
        Returns:
            List of tuples (filename, full_path)
        """
        case_dir = self.uploads_dir / case_id
        
        if not case_dir.exists():
            logger.warning(f"Case directory does not exist: {case_dir}")
            return []
        
        uploads = []
        
        if category:
            # List files in specific category
            category_dir = case_dir / category
            if category_dir.exists():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        uploads.append((file_path.name, file_path))
        else:
            # List all files in all categories
            for category_dir in case_dir.iterdir():
                if category_dir.is_dir():
                    for file_path in category_dir.iterdir():
                        if file_path.is_file():
                            uploads.append((file_path.name, file_path))
        
        logger.debug(f"Found {len(uploads)} uploads for case {case_id}")
        return uploads
    
    def delete_case_uploads(self, case_id: str) -> bool:
        """
        Delete all uploads for a specific case.
        
        Args:
            case_id: Unique case identifier
            
        Returns:
            True if deletion successful, False if case doesn't exist
        """
        case_dir = self.uploads_dir / case_id
        
        if not case_dir.exists():
            logger.warning(f"Case directory does not exist: {case_dir}")
            return False
        
        try:
            shutil.rmtree(case_dir)
            logger.info(f"Deleted uploads for case {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete case uploads: {str(e)}")
            return False
    
    def get_case_dir(self, case_id: str) -> Path:
        """
        Get the directory path for a specific case.
        
        Args:
            case_id: Unique case identifier
            
        Returns:
            Path object for the case directory
        """
        return self.uploads_dir / case_id
    
    # Sample cases methods
    
    def list_sample_cases(self) -> List[str]:
        """
        List all available sample cases.
        
        Returns:
            List of sample case directory names
        """
        if not self.sample_cases_dir.exists():
            logger.warning(f"Sample cases directory does not exist: {self.sample_cases_dir}")
            return []
        
        sample_cases = [
            d.name for d in self.sample_cases_dir.iterdir()
            if d.is_dir()
        ]
        
        logger.info(f"Found {len(sample_cases)} sample cases")
        return sample_cases
    
    def get_sample_case_path(self, case_name: str) -> Path:
        """
        Get the directory path for a sample case.
        
        Args:
            case_name: Sample case name
            
        Returns:
            Path object for the sample case directory
        """
        return self.sample_cases_dir / case_name
    
    def load_sample_case_files(
        self,
        case_name: str
    ) -> Dict[str, List[Tuple[str, bytes]]]:
        """
        Load all files from a sample case.
        
        Args:
            case_name: Sample case name
            
        Returns:
            Dict with keys for different file categories:
                - 'fnol': List of (filename, content) tuples
                - 'photos': List of (filename, content) tuples
                - 'invoices': List of (filename, content) tuples
                
        Raises:
            FileNotFoundError: If sample case doesn't exist
        """
        case_path = self.get_sample_case_path(case_name)
        
        if not case_path.exists():
            raise FileNotFoundError(f"Sample case not found: {case_name}")
        
        result = {
            'fnol': [],
            'photos': [],
            'invoices': []
        }
        
        # Load FNOL files
        fnol_dir = case_path / "fnol"
        if fnol_dir.exists():
            for file_path in fnol_dir.iterdir():
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        result['fnol'].append((file_path.name, f.read()))
        
        # Load photos
        photos_dir = case_path / "photos"
        if photos_dir.exists():
            for file_path in photos_dir.iterdir():
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        result['photos'].append((file_path.name, f.read()))
        
        # Load invoices
        invoices_dir = case_path / "invoices"
        if invoices_dir.exists():
            for file_path in invoices_dir.iterdir():
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        result['invoices'].append((file_path.name, f.read()))
        
        logger.info(
            f"Loaded sample case '{case_name}': "
            f"fnol={len(result['fnol'])}, "
            f"photos={len(result['photos'])}, "
            f"invoices={len(result['invoices'])}"
        )
        
        return result
    
    # Utility methods
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about file storage.
        
        Returns:
            Dict with storage statistics
        """
        def get_dir_size(path: Path) -> int:
            """Calculate total size of directory in bytes."""
            total = 0
            if path.exists():
                for item in path.rglob('*'):
                    if item.is_file():
                        total += item.stat().st_size
            return total
        
        def count_files(path: Path) -> int:
            """Count total files in directory."""
            if not path.exists():
                return 0
            return sum(1 for item in path.rglob('*') if item.is_file())
        
        return {
            'policy_dir': {
                'path': str(self.policy_dir),
                'exists': self.policy_dir.exists(),
                'file_count': count_files(self.policy_dir),
                'size_bytes': get_dir_size(self.policy_dir)
            },
            'uploads_dir': {
                'path': str(self.uploads_dir),
                'exists': self.uploads_dir.exists(),
                'file_count': count_files(self.uploads_dir),
                'size_bytes': get_dir_size(self.uploads_dir),
                'case_count': len(list(self.uploads_dir.iterdir())) if self.uploads_dir.exists() else 0
            },
            'sample_cases_dir': {
                'path': str(self.sample_cases_dir),
                'exists': self.sample_cases_dir.exists(),
                'case_count': len(self.list_sample_cases())
            }
        }
    
    def cleanup_old_uploads(self, days: int = 7) -> int:
        """
        Delete uploads older than specified number of days.
        
        Args:
            days: Number of days to keep uploads
            
        Returns:
            Number of cases deleted
        """
        import time
        
        if not self.uploads_dir.exists():
            return 0
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for case_dir in self.uploads_dir.iterdir():
            if case_dir.is_dir():
                # Check modification time
                if case_dir.stat().st_mtime < cutoff_time:
                    try:
                        shutil.rmtree(case_dir)
                        deleted_count += 1
                        logger.info(f"Deleted old case uploads: {case_dir.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete {case_dir.name}: {str(e)}")
        
        logger.info(f"Cleanup completed: deleted {deleted_count} old case uploads")
        return deleted_count
