"""
Data collection module for water distribution modeling.
Handles fetching data from various APIs and sources for Madison, WI.
"""

import os
import logging
import requests
import pandas as pd
import geopandas as gpd
import dataretrieval.nwis as nwis
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
MADISON_WI_BBOX = (-89.5417, 43.0233, -89.2349, 43.1710)  # (min_lon, min_lat, max_lon, max_lat)
RAW_DATA_DIR = Path("data/raw")
USGS_SITES_URL = "https://waterservices.usgs.gov/nwis/site/"

class DataCollector:
    """Class to collect water data from various sources for Madison, WI"""
    
    def __init__(self):
        """Initialize the DataCollector"""
        # Create data directories if they don't exist
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # API keys (from .env file or environment variables)
        self.epa_api_key = os.getenv("EPA_API_KEY", "")
        self.usgs_api_key = os.getenv("USGS_API_KEY", "")
        
        # Verify API keys are available
        if not self.epa_api_key:
            logger.warning("EPA API key not found. Some data collection may be limited.")
        if not self.usgs_api_key:
            logger.warning("USGS API key not found. Some data collection may be limited.")
    
    def fetch_madison_water_gis(self):
        """
        Fetch Madison, WI water infrastructure GIS data from the city's open data portal
        """
        logger.info("Fetching Madison water infrastructure GIS data...")
        
        # Madison open data portal for water infrastructure
        # Main water mains data
        water_mains_url = "https://data-cityofmadison.opendata.arcgis.com/datasets/cityofmadison::water-mains.geojson"
        # Water hydrants data
        hydrants_url = "https://data-cityofmadison.opendata.arcgis.com/datasets/cityofmadison::fire-hydrants.geojson"
        # Water pressure zones
        pressure_zones_url = "https://data-cityofmadison.opendata.arcgis.com/datasets/cityofmadison::water-pressure-zones.geojson"
        
        try:
            # Download water mains
            logger.info("Downloading water mains data...")
            water_mains = gpd.read_file(water_mains_url)
            water_mains.to_file(RAW_DATA_DIR / "madison_water_mains.geojson", driver="GeoJSON")
            
            # Download hydrants
            logger.info("Downloading hydrants data...")
            hydrants = gpd.read_file(hydrants_url)
            hydrants.to_file(RAW_DATA_DIR / "madison_hydrants.geojson", driver="GeoJSON")
            
            # Download pressure zones
            logger.info("Downloading pressure zones data...")
            pressure_zones = gpd.read_file(pressure_zones_url)
            pressure_zones.to_file(RAW_DATA_DIR / "madison_pressure_zones.geojson", driver="GeoJSON")
            
            logger.info("Madison GIS data downloaded successfully.")
            return {
                "water_mains": water_mains,
                "hydrants": hydrants,
                "pressure_zones": pressure_zones
            }
            
        except Exception as e:
            logger.error(f"Error downloading Madison GIS data: {e}")
            return None
    
    def fetch_usgs_water_data(self, days=30):
        """
        Fetch USGS water data for streams and groundwater in the Madison area
        
        Args:
            days (int): Number of days of data to retrieve
        
        Returns:
            dict: Dictionary of dataframes containing the water data
        """
        logger.info(f"Fetching USGS water data for the past {days} days...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for USGS API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        try:
            # Get sites in the Madison area
            site_params = {
                "format": "rdb",
                "bBox": f"{MADISON_WI_BBOX[0]},{MADISON_WI_BBOX[1]},{MADISON_WI_BBOX[2]},{MADISON_WI_BBOX[3]}",
                "siteType": "ST,GW",  # Stream and Groundwater sites
                "hasDataTypeCd": "dv",  # Sites with daily values
                "siteStatus": "active"
            }
            
            # Use dataretrieval package for USGS data
            logger.info("Identifying USGS water monitoring sites in Madison area...")
            site_data = nwis.get_record(site_params, "site")
            
            if site_data is None or site_data.empty:
                logger.warning("No USGS sites found in the Madison area.")
                return None
            
            # Save sites to file
            site_data.to_csv(RAW_DATA_DIR / "madison_usgs_sites.csv", index=False)
            
            # Get site codes
            site_codes = site_data['site_no'].tolist()
            
            # Get streamflow data for stream sites
            stream_sites = site_data[site_data['site_tp_cd'] == 'ST']['site_no'].tolist()
            groundwater_sites = site_data[site_data['site_tp_cd'] == 'GW']['site_no'].tolist()
            
            data_dict = {}
            
            # Get streamflow data
            if stream_sites:
                logger.info(f"Retrieving streamflow data for {len(stream_sites)} sites...")
                streamflow_data = nwis.get_dv(
                    sites=stream_sites,
                    start=start_str,
                    end=end_str,
                    parameterCd='00060'  # Discharge (ft³/s)
                )
                
                if streamflow_data is not None and not streamflow_data.empty:
                    streamflow_data.to_csv(RAW_DATA_DIR / "madison_streamflow_data.csv")
                    data_dict['streamflow'] = streamflow_data
            
            # Get groundwater level data
            if groundwater_sites:
                logger.info(f"Retrieving groundwater data for {len(groundwater_sites)} sites...")
                groundwater_data = nwis.get_dv(
                    sites=groundwater_sites,
                    start=start_str,
                    end=end_str,
                    parameterCd='72019'  # Depth to water level (ft below land surface)
                )
                
                if groundwater_data is not None and not groundwater_data.empty:
                    groundwater_data.to_csv(RAW_DATA_DIR / "madison_groundwater_data.csv")
                    data_dict['groundwater'] = groundwater_data
            
            logger.info("USGS water data retrieved successfully.")
            return data_dict
            
        except Exception as e:
            logger.error(f"Error fetching USGS water data: {e}")
            return None
    
    def fetch_epa_water_quality(self):
        """
        Fetch EPA water quality data for Madison, WI
        
        Returns:
            pd.DataFrame: Dataframe containing EPA water quality data
        """
        logger.info("Fetching EPA water quality data...")
        
        # EPA ECHO API endpoint for facility information
        epa_api_url = "https://enviro.epa.gov/enviro/efservice/SDW_WATER_SYSTEM/PRIMACY_AGENCY_CODE/WI/CITY_NAME/MADISON/JSON"
        
        try:
            # Fetch water system data
            response = requests.get(epa_api_url)
            response.raise_for_status()
            
            # Convert to dataframe
            water_systems = pd.DataFrame(response.json())
            
            # Save to file
            water_systems.to_csv(RAW_DATA_DIR / "madison_epa_water_systems.csv", index=False)
            
            # Get detailed water quality data if available
            if not water_systems.empty and 'PWSID' in water_systems.columns:
                # Get water quality data for each system
                quality_data_list = []
                
                for pwsid in water_systems['PWSID'].unique():
                    # EPA SDWIS water quality data endpoint
                    quality_url = f"https://enviro.epa.gov/enviro/efservice/SDWIS_VIOLATION/PWSID/{pwsid}/JSON"
                    
                    try:
                        quality_response = requests.get(quality_url)
                        quality_response.raise_for_status()
                        
                        # Add to list if data is available
                        quality_data = quality_response.json()
                        if quality_data:
                            quality_df = pd.DataFrame(quality_data)
                            quality_data_list.append(quality_df)
                    
                    except Exception as e:
                        logger.warning(f"Could not fetch quality data for system {pwsid}: {e}")
                
                # Combine all quality data
                if quality_data_list:
                    all_quality_data = pd.concat(quality_data_list, ignore_index=True)
                    all_quality_data.to_csv(RAW_DATA_DIR / "madison_epa_quality_data.csv", index=False)
                    logger.info("EPA water quality data retrieved successfully.")
                    return all_quality_data
                else:
                    logger.info("No water quality violation data found.")
                    return water_systems
            
            logger.info("EPA water system data retrieved successfully.")
            return water_systems
            
        except Exception as e:
            logger.error(f"Error fetching EPA water quality data: {e}")
            return None
    
    def fetch_elevation_data(self):
        """
        Fetch elevation data for Madison area from USGS National Map API
        
        Returns:
            str: Path to downloaded elevation data file
        """
        logger.info("Fetching elevation data for Madison area...")
        
        # USGS National Map API for 3DEP elevation data
        # Using the 1/3 arc-second (~10m) resolution DEM
        usgs_dem_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
        
        params = {
            "bbox": f"{MADISON_WI_BBOX[0]},{MADISON_WI_BBOX[1]},{MADISON_WI_BBOX[2]},{MADISON_WI_BBOX[3]}",
            "datasets": "Digital Elevation Model (DEM) 1/3 arc-second",
            "outputFormat": "JSON",
            "prodFormats": "GeoTIFF"
        }
        
        try:
            # Get available DEM datasets
            response = requests.get(usgs_dem_url, params=params)
            response.raise_for_status()
            
            items = response.json().get('items', [])
            
            if not items:
                logger.warning("No elevation data found for Madison area")
                return None
            
            # Take the first available DEM
            download_url = items[0].get('downloadURL')
            
            if not download_url:
                logger.warning("No download URL found for elevation data")
                return None
            
            # Download the DEM file
            dem_response = requests.get(download_url, stream=True)
            dem_response.raise_for_status()
            
            # Save the DEM file
            output_path = RAW_DATA_DIR / "madison_elevation.tif"
            with open(output_path, 'wb') as f:
                for chunk in dem_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Elevation data downloaded successfully to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error fetching elevation data: {e}")
            return None
    
    def fetch_all_data(self):
        """
        Fetch all required data for the Madison water distribution model
        
        Returns:
            dict: Dictionary containing all fetched data
        """
        logger.info("Starting complete data collection for Madison, WI...")
        
        data = {}
        
        # Fetch GIS data
        data['gis'] = self.fetch_madison_water_gis()
        
        # Fetch USGS water data
        data['usgs'] = self.fetch_usgs_water_data(days=30)
        
        # Fetch EPA water quality data
        data['epa'] = self.fetch_epa_water_quality()
        
        # Fetch elevation data
        data['elevation'] = self.fetch_elevation_data()
        
        logger.info("Data collection complete.")
        return data

if __name__ == "__main__":
    # If run as a script, collect all data
    collector = DataCollector()
    data = collector.fetch_all_data()