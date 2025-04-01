"""
Data collection module for water distribution modeling.
Handles fetching data from various APIs and sources for Madison, WI.
The open data API documentation is available here 
https://data-cityofmadison.opendata.arcgis.com/datasets/cityofmadison::water-main-breaks/about
For API go here: https://data-cityofmadison.opendata.arcgis.com/datasets/cityofmadison::water-main-breaks/api
"""

import os
import logging
import requests
import pandas as pd
import geopandas as gpd
import dataretrieval.nwis as nwis
import time
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from shapely.geometry import Point, LineString, Polygon  # Added the missing imports

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
        # Note: These are optional and not required for basic functionality
        self.epa_api_key = os.getenv("EPA_API_KEY", "")
        self.usgs_api_key = os.getenv("USGS_API_KEY", "")

        # Log API key status (as info, not warnings)
        if not self.epa_api_key:
            logger.info("EPA API key not provided. Using public access endpoints.")
        if not self.usgs_api_key:
            logger.info("USGS API key not provided. Using public access endpoints.")
    
    def fetch_madison_water_gis(self):
        """
        Fetch Madison, WI water infrastructure GIS data from the city's open data portal
        """
        logger.info("Fetching Madison water infrastructure GIS data...")
        
        # Request fields that align with the data processing pipeline expectations
        water_main_breaks_url = "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/5/query?outFields=OBJECTID,pipe_type,pipe_mslink,pipe_size,MainID,AssetNumber,FacilityID,pipe_depth_ft&where=1%3D1&f=geojson"
        
        results = {}
        
        # Try to download water main breaks data
        try:
            logger.info(f"Downloading water main breaks from: {water_main_breaks_url}")
            
            # Directly use geopandas to read the GeoJSON URL
            water_mains = gpd.read_file(water_main_breaks_url)
            
            if not water_mains.empty:
                # Map field names to what the pipeline expects
                if 'pipe_size' in water_mains.columns:
                    water_mains['diameter_mm'] = water_mains['pipe_size'] * 25.4  # Convert inches to mm if needed
                
                # Add required fields that might be missing
                if 'length_m' not in water_mains.columns:
                    # Approximate length from geometry if available
                    try:
                        # Create a temporary projected version for accurate measurements
                        water_mains_proj = water_mains.to_crs("EPSG:3857")  # Web Mercator
                        water_mains['length_m'] = water_mains_proj.geometry.length
                    except Exception:
                        # Default length if calculation fails
                        water_mains['length_m'] = 100.0
                
                # Add roughness coefficient based on pipe_type if available
                if 'roughness' not in water_mains.columns:
                    water_mains['roughness'] = 100.0  # Default roughness
                    
                    # Map pipe types to roughness values if pipe_type exists
                    if 'pipe_type' in water_mains.columns:
                        pipe_type_map = {
                            'CAST IRON': 100.0,
                            'DUCTILE IRON': 140.0,
                            'PVC': 150.0,
                            'HDPE': 150.0,
                            'CONCRETE': 120.0,
                            'STEEL': 135.0
                        }
                        # Apply mapping where possible
                        for pipe_type, roughness in pipe_type_map.items():
                            mask = water_mains['pipe_type'].str.contains(pipe_type, case=False, na=False)
                            water_mains.loc[mask, 'roughness'] = roughness
                
                # Save to file
                water_mains.to_file(RAW_DATA_DIR / "madison_water_mains.geojson", driver="GeoJSON")
                results["water_mains"] = water_mains
                logger.info(f"Successfully downloaded {len(water_mains)} water main records")
            else:
                logger.warning("Received empty dataset for water mains")
        except Exception as e:
            logger.warning(f"Failed to download water mains: {e}")
        
        # Fallback to sample data if needed
        if "water_mains" not in results:
            logger.warning("Falling back to sample data for water mains")
            sample_data = self._create_sample_gis_data()
            if "water_mains" in sample_data:
                results["water_mains"] = sample_data["water_mains"]
                results["water_mains"].to_file(RAW_DATA_DIR / "madison_water_mains.geojson", driver="GeoJSON")
                logger.info(f"Created {len(results['water_mains'])} sample water main records")
        
        # Similarly use sample data for hydrants and pressure zones for now
        sample_data = self._create_sample_gis_data()
        
        if "hydrants" not in results:
            results["hydrants"] = sample_data["hydrants"]
            results["hydrants"].to_file(RAW_DATA_DIR / "madison_hydrants.geojson", driver="GeoJSON")
            logger.info(f"Using sample data for hydrants: {len(results['hydrants'])} records")
        
        if "pressure_zones" not in results:
            results["pressure_zones"] = sample_data["pressure_zones"]
            results["pressure_zones"].to_file(RAW_DATA_DIR / "madison_pressure_zones.geojson", driver="GeoJSON")
            logger.info(f"Using sample data for pressure zones: {len(results['pressure_zones'])} records")
        
        logger.info(f"Madison GIS data available: {', '.join(results.keys())}")
        return results
        
    def _create_sample_gis_data(self):
        """
        Create sample GIS data as a fallback when real data cannot be downloaded
        
        Returns:
            dict: Dictionary of sample GeoDataFrames
        """
        logger.info("Creating sample GIS data for Madison, WI...")
        
        # Center of Madison, WI
        center_x, center_y = -89.4012, 43.0731
        
        # Create sample water mains (lines)
        lines = []
        for i in range(10):
            # Create a grid of lines
            x1 = center_x - 0.05 + (i % 3) * 0.025
            y1 = center_y - 0.05 + (i // 3) * 0.025
            x2 = x1 + 0.02
            y2 = y1 + 0.02
            lines.append(LineString([(x1, y1), (x2, y2)]))
        
        water_mains = gpd.GeoDataFrame(
            {
                'id': [f'M{i}' for i in range(len(lines))],
                'diameter_mm': [100 + i * 50 for i in range(len(lines))],
                'length_m': [1000 + i * 100 for i in range(len(lines))],
                'roughness': [100 for _ in range(len(lines))]
            },
            geometry=lines,
            crs='EPSG:4326'
        )
        water_mains.to_file(RAW_DATA_DIR / "madison_water_mains.geojson", driver="GeoJSON")
        
        # Create sample hydrants (points)
        points = []
        for i in range(8):
            # Create points near the lines
            x = center_x - 0.04 + (i % 4) * 0.025
            y = center_y - 0.04 + (i // 4) * 0.025
            points.append(Point(x, y))
        
        hydrants = gpd.GeoDataFrame(
            {
                'id': [f'H{i}' for i in range(len(points))],
                'status': ['Active' for _ in range(len(points))]
            },
            geometry=points,
            crs='EPSG:4326'
        )
        hydrants.to_file(RAW_DATA_DIR / "madison_hydrants.geojson", driver="GeoJSON")
        
        # Create sample pressure zones (polygons)
        from shapely.geometry import Polygon
        polygons = []
        for i in range(2):
            # Create two pressure zones
            x_min = center_x - 0.06 + i * 0.03
            y_min = center_y - 0.06
            x_max = x_min + 0.06
            y_max = y_min + 0.12
            polygons.append(Polygon([
                (x_min, y_min), (x_max, y_min), 
                (x_max, y_max), (x_min, y_max), (x_min, y_min)
            ]))
        
        pressure_zones = gpd.GeoDataFrame(
            {
                'id': [f'Z{i}' for i in range(len(polygons))],
                'name': [f'Zone {i+1}' for i in range(len(polygons))],
                'pressure': [40 + i * 10 for i in range(len(polygons))]
            },
            geometry=polygons,
            crs='EPSG:4326'
        )
        pressure_zones.to_file(RAW_DATA_DIR / "madison_pressure_zones.geojson", driver="GeoJSON")
        
        return {
            "water_mains": water_mains,
            "hydrants": hydrants,
            "pressure_zones": pressure_zones
        }
    
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
            # Get sites in the Madison area - FIXED: Removed 'format' parameter 
            site_params = {
                "bBox": f"{MADISON_WI_BBOX[0]},{MADISON_WI_BBOX[1]},{MADISON_WI_BBOX[2]},{MADISON_WI_BBOX[3]}",
                "siteType": "ST,GW",  # Stream and Groundwater sites
                "hasDataTypeCd": "dv",  # Sites with daily values
                "siteStatus": "active"
            }
            
            # Use dataretrieval package for USGS data - FIXED: Changed method call
            logger.info("Identifying USGS water monitoring sites in Madison area...")
            try:
                # First try the updated API method
                site_data = nwis.get_record(None, "site", **site_params)
            except Exception as e:
                logger.warning(f"First method failed: {e}")
                # Fall back to alternative method if needed
                try:
                    site_data = nwis.get_info(state="WI")
                    logger.info("Used fallback method to get site data.")
                except Exception as e2:
                    logger.error(f"Fallback method also failed: {e2}")
                    # Create sample data as a last resort
                    site_data = self._create_sample_site_data()
                    logger.info("Created sample site data as fallback.")
            
            if site_data is None or site_data.empty:
                logger.warning("No USGS sites found in the Madison area.")
                site_data = self._create_sample_site_data()
                logger.info("Created sample site data as fallback.")
            
            # Save sites to file
            site_data.to_csv(RAW_DATA_DIR / "madison_usgs_sites.csv", index=False)
            
            # Extract site codes
            if 'site_no' in site_data.columns:
                site_codes = site_data['site_no'].tolist()
            elif 'site_no' in site_data.columns:
                site_codes = site_data['site_no'].tolist()
            else:
                # Use fallback site codes if column names are different
                site_codes = [str(i) for i in range(5430500, 5430510)]
            
            # Get streamflow data for stream sites (if available)
            try:
                # Use a subset of sites for testing
                test_sites = site_codes[:3]
                logger.info(f"Retrieving streamflow data for test sites: {test_sites}")
                
                try:
                    # Try to get streamflow data
                    streamflow_data = nwis.get_dv(
                        sites=test_sites,
                        start=start_str,
                        end=end_str,
                        parameterCd='00060'  # Discharge (ft³/s)
                    )
                    
                    if streamflow_data is not None and not streamflow_data.empty:
                        streamflow_data.to_csv(RAW_DATA_DIR / "madison_streamflow_data.csv")
                        return {"streamflow": streamflow_data}
                except Exception as se:
                    logger.warning(f"Error getting streamflow data: {se}")
                    
                # Create sample data if no data is available
                streamflow_data = self._create_sample_streamflow_data(site_codes, start_date, end_date)
                streamflow_data.to_csv(RAW_DATA_DIR / "madison_streamflow_data.csv")
                return {"streamflow": streamflow_data}
                
            except Exception as e:
                logger.error(f"Error retrieving USGS water data: {e}")
                # Create sample data as fallback
                streamflow_data = self._create_sample_streamflow_data(site_codes, start_date, end_date)
                streamflow_data.to_csv(RAW_DATA_DIR / "madison_streamflow_data.csv")
                return {"streamflow": streamflow_data}
            
        except Exception as e:
            logger.error(f"Error fetching USGS water data: {e}")
            # Create and return sample data
            site_data = self._create_sample_site_data()
            site_data.to_csv(RAW_DATA_DIR / "madison_usgs_sites.csv", index=False)
            
            site_codes = [str(i) for i in range(5430500, 5430510)]
            streamflow_data = self._create_sample_streamflow_data(site_codes, start_date, end_date)
            streamflow_data.to_csv(RAW_DATA_DIR / "madison_streamflow_data.csv")
            
            return {"streamflow": streamflow_data}
    
    def _create_sample_site_data(self):
        """Create sample USGS site data as a fallback"""
        logger.info("Creating sample USGS site data for Madison, WI...")
        
        # Center of Madison, WI
        center_x, center_y = -89.4012, 43.0731
        
        # Create sample sites
        sites = []
        for i in range(10):
            site_no = str(5430500 + i)
            x = center_x - 0.05 + (i % 5) * 0.02
            y = center_y - 0.05 + (i // 5) * 0.02
            site_type = 'ST' if i % 3 != 0 else 'GW'  # Mix of stream and groundwater sites
            sites.append({
                'site_no': site_no,
                'station_nm': f'Sample Site {i+1}',
                'dec_long_va': x,
                'dec_lat_va': y,
                'site_tp_cd': site_type,
                'state_cd': '55',  # Wisconsin
                'county_cd': '025'  # Dane County
            })
        
        return pd.DataFrame(sites)
    
    def _create_sample_streamflow_data(self, site_codes, start_date, end_date):
        """Create sample streamflow data as a fallback"""
        logger.info("Creating sample streamflow data...")
        
        # Create a date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Create sample data for each site
        data_list = []
        
        for site_no in site_codes[:5]:  # Use first 5 sites
            # Create random but realistic streamflow values
            import random
            import numpy as np
            
            # Base flow with seasonal pattern
            base_flow = 50 + 30 * np.sin(np.linspace(0, 2*np.pi, len(date_range)))
            
            # Add random variations
            flows = [max(1, bf + random.normalvariate(0, 10)) for bf in base_flow]
            
            for i, date in enumerate(date_range):
                data_list.append({
                    'site_no': site_no,
                    'datetime': date,
                    'value': flows[i],
                    'parameter_cd': '00060',
                    'qualifier_cd': '',
                    'agency_cd': 'USGS'
                })
        
        return pd.DataFrame(data_list)
    
    def fetch_epa_water_quality(self):
        """
        Fetch EPA water quality data for Madison, WI
        
        Returns:
            pd.DataFrame: Dataframe containing EPA water quality data
        """
        logger.info("Fetching EPA water quality data...")
        
        # FIXED: Corrected EPA ECHO API endpoint URL
        epa_api_urls = [
            "https://enviro.epa.gov/efservice/SDW_WATER_SYSTEM/PRIMACY_AGENCY_CODE/WI/CITY_NAME/MADISON/JSON",
            "https://enviro.epa.gov/enviro/efservice/SDW_WATER_SYSTEM/PRIMACY_AGENCY_CODE/WI/CITY_NAME/MADISON/JSON"
        ]
        
        try:
            # Try multiple endpoints with retry
            max_retries = 3
            water_systems = None
            
            for url in epa_api_urls:
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        logger.info(f"Trying to fetch EPA data from: {url}")
                        response = requests.get(url, timeout=30)
                        response.raise_for_status()
                        
                        # Check if response is valid JSON
                        if not response.text.strip():
                            logger.warning(f"Empty response from EPA API at {url}")
                            raise ValueError("Empty response from EPA API")
                            
                        # Try to parse JSON
                        data = response.json()
                        water_systems = pd.DataFrame(data)
                        logger.info(f"Successfully retrieved EPA data from {url}")
                        break
                        
                    except (requests.exceptions.RequestException, ValueError) as e:
                        retry_count += 1
                        logger.warning(f"EPA API request failed (attempt {retry_count}/{max_retries}): {e}")
                        if retry_count >= max_retries:
                            logger.error(f"All attempts failed for {url}")
                        time.sleep(1 * retry_count)  # Backoff
                
                if water_systems is not None:
                    break
            
            # If all API attempts fail, create sample data
            if water_systems is None:
                logger.warning("All EPA API requests failed. Creating sample data.")
                water_systems = self._create_sample_water_quality_data()
            
            # Save to file
            water_systems.to_csv(RAW_DATA_DIR / "madison_epa_water_systems.csv", index=False)
            
            # Get detailed water quality data if available
            if not water_systems.empty and 'PWSID' in water_systems.columns:
                # For real data, we'd process violations here
                pass  # Simplified for this example
            
            logger.info("EPA water system data retrieved/created successfully.")
            return water_systems
            
        except Exception as e:
            logger.error(f"Error in EPA water quality data retrieval: {e}")
            # Create sample data as fallback
            water_systems = self._create_sample_water_quality_data()
            water_systems.to_csv(RAW_DATA_DIR / "madison_epa_water_systems.csv", index=False)
            return water_systems
    
    def _create_sample_water_quality_data(self):
        """Create sample water quality data as a fallback"""
        logger.info("Creating sample EPA water quality data for Madison, WI...")
        
        # Create sample water systems
        systems = []
        for i in range(3):
            pwsid = f"WI5502{i+1:03d}"
            systems.append({
                'PWSID': pwsid,
                'PWS_NAME': f'MADISON WATER UTILITY {i+1}',
                'CITY_NAME': 'MADISON',
                'STATE_CODE': 'WI',
                'SOURCE_WATER': 'GW',  # Ground Water
                'POPULATION_SERVED_COUNT': 250000 - i*10000,
                'PRIMARY_SOURCE_CODE': 'GW',
                'PRIMARY_SOURCE': 'Ground water',
                'EPA_REGION': '05'
            })
        
        return pd.DataFrame(systems)
    
    def fetch_elevation_data(self):
        """
        Fetch elevation data for Madison area from USGS National Map API
        
        Returns:
            str: Path to downloaded elevation data file
        """
        logger.info("Fetching elevation data for Madison area...")
        
        # Try multiple resolution options
        datasets = [
            "Digital Elevation Model (DEM) 1/3 arc-second",
            "Digital Elevation Model (DEM) 1 arc-second",
            "Digital Elevation Model (DEM) 1 meter"
        ]
        
        # Slightly expanded bounding box for better results
        expanded_bbox = (
            MADISON_WI_BBOX[0] - 0.05,  # Expand west
            MADISON_WI_BBOX[1] - 0.05,  # Expand south
            MADISON_WI_BBOX[2] + 0.05,  # Expand east
            MADISON_WI_BBOX[3] + 0.05   # Expand north
        )
        
        output_path = RAW_DATA_DIR / "madison_elevation.tif"
        
        for dataset in datasets:
            try:
                # USGS National Map API for elevation data
                usgs_dem_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
                
                params = {
                    "bbox": f"{expanded_bbox[0]},{expanded_bbox[1]},{expanded_bbox[2]},{expanded_bbox[3]}",
                    "datasets": dataset,
                    "outputFormat": "JSON",
                    "prodFormats": "GeoTIFF"
                }
                
                # Get available DEM datasets
                logger.info(f"Trying dataset: {dataset}")
                response = requests.get(usgs_dem_url, params=params, timeout=30)
                response.raise_for_status()
                
                items = response.json().get('items', [])
                
                if items:
                    # Found data, download it
                    download_url = items[0].get('downloadURL')
                    
                    if download_url:
                        # Download the DEM file
                        dem_response = requests.get(download_url, stream=True, timeout=60)
                        dem_response.raise_for_status()
                        
                        # Save the DEM file
                        with open(output_path, 'wb') as f:
                            for chunk in dem_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        logger.info(f"Elevation data downloaded successfully using dataset: {dataset}")
                        return str(output_path)
                else:
                    logger.warning(f"No elevation data found for dataset: {dataset}")
            
            except Exception as e:
                logger.warning(f"Error fetching elevation data for dataset {dataset}: {e}")
        
        # If all attempts failed, create a simple sample elevation model
        logger.warning("Could not download elevation data from any source. Creating sample elevation data.")
        try:
            self._create_sample_elevation_data(output_path)
            logger.info("Created sample elevation data as fallback.")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to create sample elevation data: {e}")
            return None
    
    def _create_sample_elevation_data(self, output_path):
        """Create a simple sample elevation raster as fallback"""
        try:
            # Check if rasterio is available
            import rasterio
            import numpy as np
            from rasterio.transform import from_origin
            
            # Define raster properties
            width, height = 100, 100
            
            # Create a simple elevation model (hill in the middle)
            x = np.linspace(-4, 4, width)
            y = np.linspace(-4, 4, height)
            xx, yy = np.meshgrid(x, y)
            # Create a hill
            z = 250 + 50 * np.exp(-0.1 * (xx**2 + yy**2))
            
            # Define geotransform
            west, north = MADISON_WI_BBOX[0], MADISON_WI_BBOX[3]
            pixel_width = (MADISON_WI_BBOX[2] - MADISON_WI_BBOX[0]) / width
            pixel_height = (MADISON_WI_BBOX[3] - MADISON_WI_BBOX[1]) / height
            transform = from_origin(west, north, pixel_width, pixel_height)
            
            # Create GeoTiff
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,
                dtype=z.dtype,
                crs='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs',
                transform=transform,
            ) as dst:
                dst.write(z, 1)
            
            return True
        
        except ImportError:
            # If rasterio is not available, create a very simple text file
            logger.warning("Rasterio not available. Creating placeholder elevation file.")
            with open(output_path, 'w') as f:
                f.write("This is a placeholder for elevation data.\n")
                f.write(f"Bounding box: {MADISON_WI_BBOX}\n")
                f.write("Install rasterio for proper sample raster creation.")
            return True
    
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