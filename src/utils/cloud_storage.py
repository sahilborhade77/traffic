import logging
import shutil
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class CloudStorage:
    """
    Mock Cloud Storage Integration (S3 / Google Cloud Storage / Azure Blob).
    Handles off-site backup of violation evidence and e-challans.
    """
    
    def __init__(self, bucket_name: str = 'traffic-intelligence-backup'):
        self.bucket_name = bucket_name
        self.cloud_mock_dir = Path('cloud_storage_mock') / bucket_name
        self.cloud_mock_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CloudStorage initialized: Bucket={bucket_name}")

    def upload_file(self, local_path: str, remote_folder: str = 'evidence') -> str:
        """
        Uploads a file to the (mock) cloud storage.
        """
        if not os.path.exists(local_path):
            logger.error(f"File not found for upload: {local_path}")
            return ""
            
        filename = os.path.basename(local_path)
        dest_dir = self.cloud_mock_dir / remote_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / filename
        
        # Simulate upload (copy)
        shutil.copy2(local_path, dest_path)
        
        cloud_url = f"https://storage.googleapis.com/{self.bucket_name}/{remote_folder}/{filename}"
        logger.info(f"✅ Cloud Backup Success: {local_path} -> {cloud_url}")
        
        return cloud_url

    def sync_daily_challans(self):
        """
        Example method to sync all challans generated today.
        """
        today_str = datetime.now().strftime("%Y%m%d")
        challan_dir = Path('output/challans')
        
        if not challan_dir.exists():
            return
            
        count = 0
        for pdf in challan_dir.glob(f"*_{today_str}_*.pdf"):
            self.upload_file(str(pdf), remote_folder='challans')
            count += 1
            
        if count > 0:
            logger.info(f"Synced {count} challans to cloud.")
