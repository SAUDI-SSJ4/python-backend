import os
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import json


class EncryptionConfig:
    """
    AES-128 Encryption Configuration for HLS streaming
    """
    
    # Encryption settings
    KEY_SIZE = 16  # 128 bits for AES-128
    IV_SIZE = 16   # Initialization Vector size
    ALGORITHM = "AES-128"
    
    # Key management
    KEY_EXPIRY_HOURS = 24
    KEY_ROTATION_ENABLED = True
    KEY_ROTATION_INTERVAL_HOURS = 24
    
    # Storage settings
    KEY_STORAGE_DIR = "keys"
    KEY_FILE_PREFIX = "hls_key_"
    KEY_INFO_SUFFIX = ".keyinfo"
    
    # Security settings
    SALT_SIZE = 32
    HASH_ITERATIONS = 100000
    HASH_ALGORITHM = "sha256"
    
    def __init__(self):
        self.key_storage_path = Path(self.KEY_STORAGE_DIR)
        self.key_storage_path.mkdir(exist_ok=True)
    
    def generate_key(self, session_id: str) -> Dict[str, str]:
        """
        Generate new AES-128 key for session
        """
        # Generate random key
        key_bytes = secrets.token_bytes(self.KEY_SIZE)
        key_hex = key_bytes.hex()
        
        # Generate key ID
        key_id = hashlib.sha256(f"{session_id}:{key_hex}".encode()).hexdigest()[:16]
        
        # Create key data
        key_data = {
            "key_id": key_id,
            "key": key_hex,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=self.KEY_EXPIRY_HOURS)).isoformat(),
            "algorithm": self.ALGORITHM
        }
        
        # Store key
        self._store_key(key_data)
        
        return key_data
    
    def _store_key(self, key_data: Dict[str, str]) -> None:
        """
        Store key data to file system
        """
        key_id = key_data["key_id"]
        key_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.key"
        keyinfo_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}{self.KEY_INFO_SUFFIX}"
        
        # Write key file
        with open(key_file, "wb") as f:
            f.write(bytes.fromhex(key_data["key"]))
        
        # Write keyinfo file
        keyinfo_content = f"{key_file.name}\n{key_file}\n"
        with open(keyinfo_file, "w") as f:
            f.write(keyinfo_content)
        
        # Store metadata
        metadata_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.json"
        with open(metadata_file, "w") as f:
            json.dump(key_data, f, indent=2)
    
    def get_key(self, key_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve key data by key ID
        """
        metadata_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, "r") as f:
                key_data = json.load(f)
            
            # Check if key is expired
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.now() > expires_at:
                self._delete_key(key_id)
                return None
            
            return key_data
        except Exception:
            return None
    
    def _delete_key(self, key_id: str) -> None:
        """
        Delete key and related files
        """
        try:
            # Delete key file
            key_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.key"
            if key_file.exists():
                key_file.unlink()
            
            # Delete keyinfo file
            keyinfo_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}{self.KEY_INFO_SUFFIX}"
            if keyinfo_file.exists():
                keyinfo_file.unlink()
            
            # Delete metadata file
            metadata_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
        except Exception:
            pass
    
    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys and return count of deleted keys
        """
        deleted_count = 0
        
        for metadata_file in self.key_storage_path.glob(f"{self.KEY_FILE_PREFIX}*.json"):
            try:
                with open(metadata_file, "r") as f:
                    key_data = json.load(f)
                
                expires_at = datetime.fromisoformat(key_data["expires_at"])
                if datetime.now() > expires_at:
                    key_id = key_data["key_id"]
                    self._delete_key(key_id)
                    deleted_count += 1
            except Exception:
                continue
        
        return deleted_count
    
    def get_key_file_path(self, key_id: str) -> Optional[Path]:
        """
        Get key file path for FFmpeg
        """
        key_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}.key"
        return key_file if key_file.exists() else None
    
    def get_keyinfo_file_path(self, key_id: str) -> Optional[Path]:
        """
        Get keyinfo file path for FFmpeg
        """
        keyinfo_file = self.key_storage_path / f"{self.KEY_FILE_PREFIX}{key_id}{self.KEY_INFO_SUFFIX}"
        return keyinfo_file if keyinfo_file.exists() else None
    
    def validate_key_access(self, key_id: str, session_id: str, video_id: str) -> bool:
        """
        Validate if key can be accessed by session
        """
        key_data = self.get_key(key_id)
        if not key_data:
            return False
        
        # Check session match
        if key_data.get("session_id") != session_id:
            return False
        
        # Check if not expired
        expires_at = datetime.fromisoformat(key_data["expires_at"])
        if datetime.now() > expires_at:
            return False
        
        return True
    
    def get_key_statistics(self) -> Dict[str, int]:
        """
        Get key storage statistics
        """
        total_keys = 0
        active_keys = 0
        expired_keys = 0
        
        for metadata_file in self.key_storage_path.glob(f"{self.KEY_FILE_PREFIX}*.json"):
            total_keys += 1
            try:
                with open(metadata_file, "r") as f:
                    key_data = json.load(f)
                
                expires_at = datetime.fromisoformat(key_data["expires_at"])
                if datetime.now() > expires_at:
                    expired_keys += 1
                else:
                    active_keys += 1
            except Exception:
                expired_keys += 1
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys
        }


# Global encryption configuration instance
encryption_config = EncryptionConfig()


def get_encryption_config() -> EncryptionConfig:
    """Get encryption configuration instance"""
    return encryption_config


def generate_session_key(session_id: str) -> Dict[str, str]:
    """Generate new session key"""
    return encryption_config.generate_key(session_id)


def validate_key_access(key_id: str, session_id: str, video_id: str) -> bool:
    """Validate key access"""
    return encryption_config.validate_key_access(key_id, session_id, video_id)


def cleanup_expired_keys() -> int:
    """Clean up expired keys"""
    return encryption_config.cleanup_expired_keys() 