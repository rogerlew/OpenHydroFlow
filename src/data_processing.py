"""
src/data_processing.py
Data processing module for water distribution modeling.
Handles cleaning, transforming, and preparing data for EPANET modeling.
"""

import os
import re
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, LineString
import networkx as nx
# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
OUTPUT_DATA_DIR = Path("data/output")

class DataProcessor:
    """Class to process water data for EPANET modeling"""
    
    def __init__(self):
        """Initialize the DataProcessor"""
        # Create data directories if they don't exist
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check if raw data directory exists
        if not RAW_DATA_DIR.exists():
            logger.error(f"Raw data directory {RAW_DATA_DIR} does not exist!")
            raise FileNotFoundError(f"Raw data directory {RAW_DATA_DIR} does not exist!")
    
    def clean_water_mains(self, subset_area=None):
        """
        Clean and prepare water mains data for network modeling
        
        Args:
            subset_area (gpd.GeoDataFrame, optional): Area to subset data to
        
        Returns:
            gpd.GeoDataFrame: Cleaned water mains
        """
        logger.info("Cleaning water mains data...")
        
        try:
            # Load water mains data
            water_mains_path = RAW_DATA_DIR / "madison_water_mains.geojson"
            
            if not water_mains_path.exists():
                logger.error(f"Water mains file {water_mains_path} not found!")
                return None
            
            water_mains = gpd.read_file(water_mains_path)
            print(water_mains.columns)
            # Initial data exploration
            logger.info(f"Original water mains data: {len(water_mains)} rows")
            
            # Ensure coordinate reference system is consistent with the CRS84 specified in the original file
            # CRS84 is equivalent to EPSG:4326 with lon/lat order
            if water_mains.crs.name != "WGS 84":
                water_mains = water_mains.to_crs("EPSG:4326")
            
            # Clean data
            # 1. Remove mains with invalid geometries
            water_mains = water_mains[water_mains.geometry.is_valid]
            
            # 2. Ensure all geometries are LineStrings
            water_mains = water_mains[water_mains.geometry.type == "LineString"]
            
            # 3. Ensure diameter and length are present
            # These are already present in the sample data, but adding checks for robustness
            if 'diameter_mm' not in water_mains.columns:
                # Use a default method if diameter is missing
                water_mains['diameter_mm'] = 100  # Default to 100mm
                logger.warning("No diameter information found. Using default 100mm.")
            
            if 'length_m' not in water_mains.columns:
                # Calculate length in a projected CRS
                water_mains_proj = water_mains.to_crs("EPSG:3857")  # Web Mercator projection
                water_mains['length_m'] = water_mains_proj.geometry.length
                logger.info("Calculated pipe lengths using Web Mercator projection.")
            
            # 4. Ensure roughness is present
            if 'roughness' not in water_mains.columns:
                # Use a default roughness or calculate based on a method
                water_mains['roughness'] = 100  # Default Hazen-Williams C coefficient
                logger.warning("No roughness information found. Using default C=100.")
            
            # 5. Subset to area of interest if provided
            if subset_area is not None:
                # Ensure subset_area is in the same CRS
                if subset_area.crs != water_mains.crs:
                    subset_area = subset_area.to_crs(water_mains.crs)
                
                # Spatial subset
                water_mains = gpd.overlay(water_mains, subset_area, how='intersection')
            
            # 6. Create unique ID for each pipe if not already present
            if 'pipe_id' not in water_mains.columns:
                # Use the existing 'id' column if present, otherwise generate new IDs
                if 'id' in water_mains.columns:
                    water_mains['pipe_id'] = water_mains['id']
                else:
                    water_mains['pipe_id'] = [f'p{i}' for i in range(1, len(water_mains) + 1)]
            
            # 7. Extract start and end points for each pipe
            # These will become junctions in the EPANET model
            water_mains['start_point'] = water_mains.geometry.apply(lambda x: Point(x.coords[0]))
            water_mains['end_point'] = water_mains.geometry.apply(lambda x: Point(x.coords[-1]))
            
            # 8. Save processed data
            output_path = PROCESSED_DATA_DIR / "processed_water_mains.geojson"
            water_mains.to_parquet(output_path, driver="GeoJSON")
            
            logger.info(f"Water mains data processed: {len(water_mains)} valid pipes")
            return water_mains
            
        except Exception as e:
            logger.error(f"Error processing water mains data: {e}")
            return None

    def _assign_pipe_roughness(self, water_mains):
        """
        Assign Hazen-Williams roughness coefficients based on pipe material and age
        
        Args:
            water_mains (gpd.GeoDataFrame): Water mains data
        
        Returns:
            pd.Series: Series with roughness coefficients
        """
        # Default roughness value (cast iron, older)
        default_roughness = 100

        # Initialize roughness series with default value
        roughness = pd.Series(default_roughness, index=water_mains.index)

        # Check if 'material' column exists
        if 'material' not in water_mains.columns:
            return roughness  # Return default roughness if material column is missing

        # Define roughness coefficients by material and condition
        material_roughness = {
            'CAST IRON': 100,
            'CAST IRON (CIP)': 100,
            'DUCTILE IRON': 140,
            'DUCTILE IRON (DIP)': 140,
            'PVC': 150,
            'HDPE': 150,
            'CONCRETE': 120,
            'STEEL': 135,
            'COPPER': 135,
            'GALVANIZED IRON': 120
        }

        # Adjust for pipe age if year_installed is available
        current_year = 2024

        for material, base_c in material_roughness.items():
            # Find pipes of this material (case insensitive)
            mask = water_mains['material'].str.upper().str.contains(material, na=False)

            if mask.any():
                # Set base roughness for this material
                roughness[mask] = base_c

                # Adjust for age if 'year_installed' column is available
                if 'year_installed' in water_mains.columns:
                    age_mask = mask & (~water_mains['year_installed'].isna())

                    if age_mask.any():
                        ages = current_year - water_mains.loc[age_mask, 'year_installed']

                        # Decrease roughness with age (simplistic model)
                        very_old = ages > 70
                        if very_old.any():
                            roughness.loc[age_mask & very_old] *= 0.7

                        older = (ages > 40) & (ages <= 70)
                        if older.any():
                            roughness.loc[age_mask & older] *= 0.85

                        middle = (ages > 20) & (ages <= 40)
                        if middle.any():
                            roughness.loc[age_mask & middle] *= 0.95

        return roughness

    
    def process_hydrants(self):
        """
        Process hydrants data
        
        Returns:
            gpd.GeoDataFrame: Processed hydrants
        """
        logger.info("Processing hydrants data...")
        
        try:
            # Load hydrants data
            hydrants_path = RAW_DATA_DIR / "madison_hydrants.geojson"
            
            if not hydrants_path.exists():
                logger.error(f"Hydrants file {hydrants_path} not found!")
                return None
            
            hydrants = gpd.read_file(hydrants_path)
            
            # Ensure coordinate reference system is consistent
            if hydrants.crs != "EPSG:4326":
                hydrants = hydrants.to_crs("EPSG:4326")
            
            # Create unique ID for each hydrant
            hydrants['hydrant_id'] = [f'h{i}' for i in range(1, len(hydrants) + 1)]
            
            # Save processed data
            output_path = PROCESSED_DATA_DIR / "processed_hydrants.geojson"
            hydrants.to_file(output_path, driver="GeoJSON")
            
            logger.info(f"Hydrants data processed: {len(hydrants)} hydrants")
            return hydrants
            
        except Exception as e:
            logger.error(f"Error processing hydrants data: {e}")
            return None
    
    def process_pressure_zones(self):
        """
        Process pressure zones data
        
        Returns:
            gpd.GeoDataFrame: Processed pressure zones
        """
        logger.info("Processing pressure zones data...")
        
        try:
            # Load pressure zones data
            pressure_path = RAW_DATA_DIR / "madison_pressure_zones.geojson"
            
            if not pressure_path.exists():
                logger.error(f"Pressure zones file {pressure_path} not found!")
                return None
            
            pressure_zones = gpd.read_file(pressure_path)
            
            # Ensure coordinate reference system is consistent
            if pressure_zones.crs != "EPSG:4326":
                pressure_zones = pressure_zones.to_crs("EPSG:4326")
            
            # Extract relevant information for water modeling
            # Assuming there are columns for zone name, pressure, etc.
            
            # Save processed data
            output_path = PROCESSED_DATA_DIR / "processed_pressure_zones.geojson"
            pressure_zones.to_file(output_path, driver="GeoJSON")
            
            logger.info(f"Pressure zones data processed: {len(pressure_zones)} zones")
            return pressure_zones
            
        except Exception as e:
            logger.error(f"Error processing pressure zones data: {e}")
            return None
    
    def extract_elevation_data(self, points_gdf):
        """
        Extract elevation values for a set of points
        
        Args:
            points_gdf (gpd.GeoDataFrame): GeoDataFrame of points
        
        Returns:
            pd.Series: Series with elevation values
        """
        logger.info("Extracting elevation data for points...")
        
        elevation_path = RAW_DATA_DIR / "madison_elevation.tif"
        
        if not elevation_path.exists():
            logger.error(f"Elevation file {elevation_path} not found!")
            return None
        
        try:
            # Ensure points are in the same CRS as the raster
            with rasterio.open(elevation_path) as src:
                if points_gdf.crs != src.crs:
                    points_gdf = points_gdf.to_crs(src.crs)
                
                # Sample raster at point locations
                elevations = []
                
                for idx, point in points_gdf.iterrows():
                    # Sample the raster at the point location
                    x, y = point.geometry.x, point.geometry.y
                    
                    # Get the sample value
                    sample = list(src.sample([(x, y)]))[0]
                    
                    # Check for nodata values
                    if sample[0] == src.nodata:
                        elevations.append(np.nan)
                    else:
                        elevations.append(float(sample[0]))
            
            logger.info(f"Extracted elevation data for {len(elevations)} points")
            return pd.Series(elevations, index=points_gdf.index)
            
        except Exception as e:
            logger.error(f"Error extracting elevation data: {e}")
            return None
    
    def create_epanet_network_data(self, water_mains=None, subset_region=None):
        """
        Create data for EPANET network model
        
        Args:
            water_mains (gpd.GeoDataFrame, optional): Processed water mains data
            subset_region (gpd.GeoDataFrame, optional): Region to subset the network to
        
        Returns:
            dict: Dictionary with processed network data for EPANET
        """
        logger.info("Creating EPANET network data...")
        
        try:
            # Load processed water mains if not provided
            if water_mains is None:
                water_mains_path = PROCESSED_DATA_DIR / "processed_water_mains.geojson"
                
                if not water_mains_path.exists():
                    logger.error(f"Processed water mains file {water_mains_path} not found!")
                    return None
                
                water_mains = gpd.read_file(water_mains_path)
            
            # Apply spatial subset if provided
            if subset_region is not None:
                # Ensure subset_region is in the same CRS
                if subset_region.crs != water_mains.crs:
                    subset_region = subset_region.to_crs(water_mains.crs)
                
                # Spatial subset
                water_mains = gpd.overlay(water_mains, subset_region, how='intersection')
            
            # Extract unique junction points from pipe start and end points
            start_points = gpd.GeoDataFrame(
                geometry=water_mains['start_point'],
                crs=water_mains.crs
            )
            
            end_points = gpd.GeoDataFrame(
                geometry=water_mains['end_point'],
                crs=water_mains.crs
            )
            
            # Combine all points
            all_points = pd.concat([start_points, end_points])
            
            # Remove duplicate points (within a small tolerance)
            # Using a spatial index for efficiency
            unique_points = []
            seen_coords = set()
            
            for idx, point in all_points.iterrows():
                # Round coordinates to handle floating point precision issues
                # Using 6 decimal places (approximately 10 cm precision)
                rounded_coords = (round(point.geometry.x, 6), round(point.geometry.y, 6))
                
                if rounded_coords not in seen_coords:
                    seen_coords.add(rounded_coords)
                    unique_points.append(point)
            
            junctions = gpd.GeoDataFrame(
                geometry=[p.geometry for p in unique_points],
                crs=water_mains.crs
            )
            
            # Create junction IDs
            junctions['junction_id'] = [f'J{i}' for i in range(1, len(junctions) + 1)]
            
            # Try to extract elevation data if available
            try:
                elevations = self.extract_elevation_data(junctions)
                if elevations is not None:
                    junctions['elevation'] = elevations
                else:
                    # Default elevation if extraction failed
                    junctions['elevation'] = 250.0
            except Exception as e:
                logger.warning(f"Could not extract elevation data: {e}")
                junctions['elevation'] = 250.0
            
            # Assign base demands (will be updated with real data if available)
            junctions['base_demand'] = 0.01  # Default base demand (m³/s)
            
            # Create pipe connections
            connections = []
            
            for idx, pipe in water_mains.iterrows():
                # Find start junction
                start_x, start_y = round(pipe.start_point.x, 6), round(pipe.start_point.y, 6)
                end_x, end_y = round(pipe.end_point.x, 6), round(pipe.end_point.y, 6)
                
                # Find the corresponding junction indices
                start_junction = None
                end_junction = None
                
                for j_idx, junction in junctions.iterrows():
                    j_x, j_y = round(junction.geometry.x, 6), round(junction.geometry.y, 6)
                    
                    if (j_x, j_y) == (start_x, start_y):
                        start_junction = junction['junction_id']
                    
                    if (j_x, j_y) == (end_x, end_y):
                        end_junction = junction['junction_id']
                    
                    if start_junction is not None and end_junction is not None:
                        break
                
                if start_junction is not None and end_junction is not None and start_junction != end_junction:
                    connections.append({
                        'pipe_id': pipe['pipe_id'],
                        'start_junction': start_junction,
                        'end_junction': end_junction,
                        'length': pipe['length_m'],
                        'diameter': pipe['diameter_mm'] / 1000.0 if 'diameter_mm' in pipe else 0.2,  # Convert mm to m
                        'roughness': pipe['roughness'] if 'roughness' in pipe else 100.0
                    })
            
            # Create network graph for connectivity analysis
            G = nx.Graph()
            
            # Add junctions as nodes
            for _, junction in junctions.iterrows():
                G.add_node(junction['junction_id'], 
                          pos=(junction.geometry.x, junction.geometry.y),
                          elevation=junction['elevation'],
                          demand=junction['base_demand'])
            
            # Add pipes as edges
            for conn in connections:
                G.add_edge(conn['start_junction'], 
                          conn['end_junction'], 
                          pipe_id=conn['pipe_id'],
                          length=conn['length'],
                          diameter=conn['diameter'],
                          roughness=conn['roughness'])
            
            # Identify isolated subnetworks
            subnetworks = list(nx.connected_components(G))
            
            # Keep only the largest subnetwork
            if len(subnetworks) > 1:
                logger.warning(f"Found {len(subnetworks)} disconnected subnetworks. Keeping only the largest one.")
                
                # Sort subnetworks by size (largest first)
                subnetworks.sort(key=len, reverse=True)
                
                largest_subnetwork = subnetworks[0]
                
                # Filter junctions to keep only those in the largest subnetwork
                junctions = junctions[junctions['junction_id'].isin(largest_subnetwork)]
                
                # Filter connections to keep only those in the largest subnetwork
                connections = [
                    conn for conn in connections 
                    if conn['start_junction'] in largest_subnetwork and conn['end_junction'] in largest_subnetwork
                ]
            
            # Create a simple water source (reservoir)
            # Find the junction with highest elevation to place the reservoir
            if len(junctions) > 0:
                highest_junction = junctions.loc[junctions['elevation'].idxmax()]
                reservoir = {
                    'reservoir_id': 'R1',
                    'junction_id': highest_junction['junction_id'],
                    'head': highest_junction['elevation'] + 50.0  # Add 50m of head
                }
            else:
                reservoir = None
            
            # Save processed network data
            network_data = {
                'junctions': junctions,
                'connections': connections,
                'reservoir': reservoir
            }
            
            # Save to file
            junctions.to_file(PROCESSED_DATA_DIR / "epanet_junctions.geojson", driver="GeoJSON")
            
            # Save connections as CSV
            pd.DataFrame(connections).to_csv(PROCESSED_DATA_DIR / "epanet_pipes.csv", index=False)
            
            # Save reservoir as JSON
            if reservoir:
                import json
                with open(PROCESSED_DATA_DIR / "epanet_reservoir.json", 'w') as f:
                    json.dump(reservoir, f)
            
            logger.info(f"EPANET network data created with {len(junctions)} junctions and {len(connections)} pipes")
            return network_data
            
        except Exception as e:
            logger.error(f"Error creating EPANET network data: {e}")
            return None
    
    def process_all_data(self, subset_area=None):
        """
        Process all water distribution data
        
        Args:
            subset_area (gpd.GeoDataFrame, optional): Area to subset data to
        
        Returns:
            dict: Dictionary with all processed data
        """
        logger.info("Processing all water distribution data...")
        
        try:
            # Process water mains
            water_mains = self.clean_water_mains(subset_area)
            
            if water_mains is None:
                logger.error("Failed to process water mains data")
                return None
            
            # Process hydrants
            hydrants = self.process_hydrants()
            
            # Process pressure zones
            pressure_zones = self.process_pressure_zones()
            
            # Create EPANET network data
            network_data = self.create_epanet_network_data(water_mains, subset_area)
            
            if network_data is None:
                logger.error("Failed to create EPANET network data")
                return None
            
            # Combine all processed data
            processed_data = {
                'water_mains': water_mains,
                'hydrants': hydrants,
                'pressure_zones': pressure_zones,
                'network_data': network_data
            }
            
            logger.info("All water distribution data processed successfully")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing all data: {e}")
            return None
    
    def create_subset_area(self, center_point, radius_km):
        """
        Create a circular subset area around a center point
        
        Args:
            center_point (tuple): Center point coordinates (longitude, latitude)
            radius_km (float): Radius in kilometers
        
        Returns:
            gpd.GeoDataFrame: GeoDataFrame with the subset area
        """
        try:
            # Create a point geometry
            center = Point(center_point)
            
            # Create a GeoDataFrame with the center point
            gdf = gpd.GeoDataFrame(geometry=[center], crs="EPSG:4326")
            
            # Convert to a projected CRS for accurate buffer
            gdf_proj = gdf.to_crs("EPSG:3857")
            
            # Create buffer in meters
            radius_m = radius_km * 1000
            gdf_proj['geometry'] = gdf_proj.buffer(radius_m)
            
            # Convert back to WGS84
            subset_area = gdf_proj.to_crs("EPSG:4326")
            
            return subset_area
            
        except Exception as e:
            logger.error(f"Error creating subset area: {e}")
            return None


if __name__ == "__main__":
    # If run as a script, process all data
    processor = DataProcessor()
    
    # Create a subset area around downtown Madison
    downtown_madison = (-89.3837, 43.0731)  # Longitude, Latitude
    subset_area = processor.create_subset_area(downtown_madison, radius_km=3.0)
    
    # Process all data
    processed_data = processor.process_all_data(subset_area)