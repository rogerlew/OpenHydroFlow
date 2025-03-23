"""
EPANET utility module for downloading and setting up the EPANET command-line tool.
"""

import os
import logging
import platform
import requests
import zipfile
import tarfile
from pathlib import Path
import shutil
import stat

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
EPANET_DIR = Path("epanet")

# EPANET download URLs
EPANET_WINDOWS_URL = "https://github.com/OpenWaterAnalytics/EPANET/releases/download/v2.2/epanet2.2_win32.zip"
EPANET_LINUX_URL = "https://github.com/OpenWaterAnalytics/EPANET/releases/download/v2.2/epanet2.2_linux.tar.gz"
EPANET_MAC_URL = "https://github.com/OpenWaterAnalytics/EPANET/releases/download/v2.2/epanet2.2_mac.tar.gz"

def setup_epanet():
    """
    Download and set up EPANET command-line tool
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Setting up EPANET command-line tool...")
    
    try:
        # Create EPANET directory if it doesn't exist
        EPANET_DIR.mkdir(exist_ok=True)
        
        # Determine platform and download URL
        system = platform.system()
        
        if system == "Windows":
            url = EPANET_WINDOWS_URL
            executable_name = "epanet2.exe"
        elif system == "Linux":
            url = EPANET_LINUX_URL
            executable_name = "epanet2"
        elif system == "Darwin":  # macOS
            url = EPANET_MAC_URL
            executable_name = "epanet2"
        else:
            logger.error(f"Unsupported platform: {system}")
            return False
        
        # Check if executable already exists
        executable_path = EPANET_DIR / executable_name
        
        if executable_path.exists():
            logger.info(f"EPANET executable already exists at {executable_path}")
            return True
        
        # Download EPANET
        logger.info(f"Downloading EPANET from {url}...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save the downloaded file
        download_path = EPANET_DIR / "epanet.download"
        
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract the archive
        logger.info(f"Extracting EPANET...")
        
        if system == "Windows":
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(EPANET_DIR)
        else:
            with tarfile.open(download_path, 'r:gz') as tar_ref:
                tar_ref.extractall(EPANET_DIR)
        
        # Find the executable in the extracted files
        for root, dirs, files in os.walk(EPANET_DIR):
            for file in files:
                if file.lower() == executable_name.lower():
                    # Copy the executable to the EPANET directory
                    source_path = Path(root) / file
                    shutil.copy2(source_path, executable_path)
                    
                    # Make the file executable on Unix-like systems
                    if system != "Windows":
                        executable_path.chmod(executable_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    
                    logger.info(f"EPANET executable setup at {executable_path}")
                    
                    # Clean up
                    download_path.unlink()
                    
                    return True
        
        logger.error(f"EPANET executable not found in the downloaded archive")
        return False
        
    except Exception as e:
        logger.error(f"Error setting up EPANET: {e}")
        return False

if __name__ == "__main__":
    setup_epanet()