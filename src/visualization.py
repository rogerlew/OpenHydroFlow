"""
Visualization module for water distribution modeling.
Handles creating visualizations and GeoJSON for web display.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import wntr
import geopandas as gpd
from shapely.geometry import Point, LineString

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DATA_DIR = Path("data/output")

class NetworkVisualizer:
    """Class to create visualizations of water distribution networks"""
    
    def __init__(self):
        """Initialize the NetworkVisualizer"""
        # Create output directory if it doesn't exist
        OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_network_geojson(self, inp_file):
        """
        Create GeoJSON representation of the network for web visualization
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
        
        Returns:
            dict: GeoJSON representation of the network
        """
        logger.info(f"Creating GeoJSON representation of network from {inp_file}...")
        
        try:
            # Load the water network model
            wn = wntr.network.WaterNetworkModel(str(inp_file))
            
            # Create GeoJSON features for nodes
            node_features = []
            
            # Process junctions
            for junction_name in wn.junction_name_list:
                junction = wn.get_node(junction_name)
                coords = junction.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [coords[0], coords[1]]
                    },
                    'properties': {
                        'id': junction_name,
                        'type': 'junction',
                        'elevation': junction.elevation,
                        'base_demand': junction.base_demand,
                        'name': junction.name if hasattr(junction, 'name') else junction_name
                    }
                }
                
                node_features.append(feature)
            
            # Process reservoirs
            for reservoir_name in wn.reservoir_name_list:
                reservoir = wn.get_node(reservoir_name)
                coords = reservoir.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [coords[0], coords[1]]
                    },
                    'properties': {
                        'id': reservoir_name,
                        'type': 'reservoir',
                        'base_head': reservoir.base_head,
                        'name': reservoir.name if hasattr(reservoir, 'name') else reservoir_name
                    }
                }
                
                node_features.append(feature)
            
            # Process tanks
            for tank_name in wn.tank_name_list:
                tank = wn.get_node(tank_name)
                coords = tank.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [coords[0], coords[1]]
                    },
                    'properties': {
                        'id': tank_name,
                        'type': 'tank',
                        'elevation': tank.elevation,
                        'init_level': tank.init_level,
                        'min_level': tank.min_level,
                        'max_level': tank.max_level,
                        'diameter': tank.diameter,
                        'name': tank.name if hasattr(tank, 'name') else tank_name
                    }
                }
                
                node_features.append(feature)
            
            # Create GeoJSON features for links
            link_features = []
            
            # Process pipes
            for pipe_name in wn.pipe_name_list:
                pipe = wn.get_link(pipe_name)
                
                # Get the start and end node coordinates
                start_node = wn.get_node(pipe.start_node_name)
                end_node = wn.get_node(pipe.end_node_name)
                
                start_coords = start_node.coordinates
                end_coords = end_node.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [start_coords[0], start_coords[1]],
                            [end_coords[0], end_coords[1]]
                        ]
                    },
                    'properties': {
                        'id': pipe_name,
                        'type': 'pipe',
                        'length': pipe.length,
                        'diameter': pipe.diameter,
                        'roughness': pipe.roughness,
                        'status': str(pipe.status),
                        'start_node': pipe.start_node_name,
                        'end_node': pipe.end_node_name,
                        'name': pipe.name if hasattr(pipe, 'name') else pipe_name
                    }
                }
                
                link_features.append(feature)
            
            # Process pumps
            for pump_name in wn.pump_name_list:
                pump = wn.get_link(pump_name)
                
                # Get the start and end node coordinates
                start_node = wn.get_node(pump.start_node_name)
                end_node = wn.get_node(pump.end_node_name)
                
                start_coords = start_node.coordinates
                end_coords = end_node.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [start_coords[0], start_coords[1]],
                            [end_coords[0], end_coords[1]]
                        ]
                    },
                    'properties': {
                        'id': pump_name,
                        'type': 'pump',
                        'start_node': pump.start_node_name,
                        'end_node': pump.end_node_name,
                        'name': pump.name if hasattr(pump, 'name') else pump_name
                    }
                }
                
                link_features.append(feature)
            
            # Process valves
            for valve_name in wn.valve_name_list:
                valve = wn.get_link(valve_name)
                
                # Get the start and end node coordinates
                start_node = wn.get_node(valve.start_node_name)
                end_node = wn.get_node(valve.end_node_name)
                
                start_coords = start_node.coordinates
                end_coords = end_node.coordinates
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [start_coords[0], start_coords[1]],
                            [end_coords[0], end_coords[1]]
                        ]
                    },
                    'properties': {
                        'id': valve_name,
                        'type': 'valve',
                        'valve_type': valve.valve_type,
                        'status': str(valve.status),
                        'start_node': valve.start_node_name,
                        'end_node': valve.end_node_name,
                        'name': valve.name if hasattr(valve, 'name') else valve_name
                    }
                }
                
                link_features.append(feature)
            
            # Combine all features
            geojson = {
                'nodes': {
                    'type': 'FeatureCollection',
                    'features': node_features
                },
                'links': {
                    'type': 'FeatureCollection',
                    'features': link_features
                }
            }
            
            # Save GeoJSON to file
            output_file = OUTPUT_DATA_DIR / "network.geojson"
            with open(output_file, 'w') as f:
                json.dump(geojson, f, indent=2)
            
            logger.info(f"GeoJSON representation saved to {output_file}")
            return geojson
            
        except Exception as e:
            logger.error(f"Error creating GeoJSON representation: {e}")
            return None
    
    def create_results_visualization(self, inp_file, results_file, output_file=None):
        """
        Create visualization data combining network and simulation results
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
            results_file (str or Path): Path to simulation results JSON
            output_file (str or Path, optional): Path to save visualization data
        
        Returns:
            dict: Visualization data
        """
        logger.info("Creating visualization data for simulation results...")
        
        try:
            # Load the water network model
            wn = wntr.network.WaterNetworkModel(str(inp_file))
            
            # Load simulation results
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Get network GeoJSON
            network_geojson = self.get_network_geojson(inp_file)
            
            if network_geojson is None:
                logger.error("Failed to create network GeoJSON")
                return None
            
            # Combine network GeoJSON with simulation results
            visualization_data = {
                'network': network_geojson,
                'results': results,
                'metadata': {
                    'duration': len(results['time_steps']),
                    'time_steps': results['time_steps']
                }
            }
            
            # Save visualization data to file if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(visualization_data, f, indent=2)
                
                logger.info(f"Visualization data saved to {output_file}")
            
            return visualization_data
            
        except Exception as e:
            logger.error(f"Error creating visualization data: {e}")
            return None
    
    def create_network_stats_charts(self, inp_file, output_prefix='network_stats'):
        """
        Create chart data for network statistics
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
            output_prefix (str): Prefix for output files
        
        Returns:
            dict: Chart data
        """
        logger.info("Creating network statistics charts...")
        
        try:
            # Load the water network model
            wn = wntr.network.WaterNetworkModel(str(inp_file))
            
            # Calculate pipe diameter distribution
            pipe_diameters = [wn.get_link(p).diameter * 1000 for p in wn.pipe_name_list]  # Convert to mm
            
            # Group diameters into ranges
            diameter_ranges = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 1000]
            diameter_labels = [f"{diameter_ranges[i]}-{diameter_ranges[i+1]}" for i in range(len(diameter_ranges)-1)]
            
            diameter_counts = [0] * (len(diameter_ranges) - 1)
            
            for diameter in pipe_diameters:
                for i in range(len(diameter_ranges) - 1):
                    if diameter_ranges[i] <= diameter < diameter_ranges[i+1]:
                        diameter_counts[i] += 1
                        break
            
            # Calculate pipe length distribution
            pipe_lengths = [wn.get_link(p).length for p in wn.pipe_name_list]
            
            # Group lengths into ranges (in meters)
            length_ranges = [0, 10, 50, 100, 200, 500, 1000, 5000]
            length_labels = [f"{length_ranges[i]}-{length_ranges[i+1]}" for i in range(len(length_ranges)-1)]
            
            length_counts = [0] * (len(length_ranges) - 1)
            
            for length in pipe_lengths:
                for i in range(len(length_ranges) - 1):
                    if length_ranges[i] <= length < length_ranges[i+1]:
                        length_counts[i] += 1
                        break
            
            # Calculate junction elevation distribution
            junction_elevations = [wn.get_node(j).elevation for j in wn.junction_name_list]
            
            # Calculate statistics
            elevation_min = min(junction_elevations) if junction_elevations else 0
            elevation_max = max(junction_elevations) if junction_elevations else 0
            
            # Group elevations into ranges
            range_size = max(1, (elevation_max - elevation_min) / 10)  # At least 1m range
            elevation_ranges = [elevation_min + i * range_size for i in range(11)]
            elevation_labels = [f"{int(elevation_ranges[i])}-{int(elevation_ranges[i+1])}" for i in range(len(elevation_ranges)-1)]
            
            elevation_counts = [0] * (len(elevation_ranges) - 1)
            
            for elevation in junction_elevations:
                for i in range(len(elevation_ranges) - 1):
                    if elevation_ranges[i] <= elevation < elevation_ranges[i+1]:
                        elevation_counts[i] += 1
                        break
            
            # Create chart data
            charts = {
                'diameter_distribution': {
                    'type': 'bar',
                    'labels': diameter_labels,
                    'datasets': [{
                        'label': 'Pipe Count',
                        'data': diameter_counts
                    }],
                    'title': 'Pipe Diameter Distribution (mm)'
                },
                'length_distribution': {
                    'type': 'bar',
                    'labels': length_labels,
                    'datasets': [{
                        'label': 'Pipe Count',
                        'data': length_counts
                    }],
                    'title': 'Pipe Length Distribution (m)'
                },
                'elevation_distribution': {
                    'type': 'bar',
                    'labels': elevation_labels,
                    'datasets': [{
                        'label': 'Junction Count',
                        'data': elevation_counts
                    }],
                    'title': 'Junction Elevation Distribution (m)'
                },
                'network_summary': {
                    'type': 'pie',
                    'labels': ['Junctions', 'Pipes', 'Reservoirs', 'Tanks', 'Valves', 'Pumps'],
                    'datasets': [{
                        'data': [
                            len(wn.junction_name_list),
                            len(wn.pipe_name_list),
                            len(wn.reservoir_name_list),
                            len(wn.tank_name_list),
                            len(wn.valve_name_list),
                            len(wn.pump_name_list)
                        ]
                    }],
                    'title': 'Network Components'
                }
            }
            
            # Save chart data to file
            output_file = OUTPUT_DATA_DIR / f"{output_prefix}.json"
            with open(output_file, 'w') as f:
                json.dump(charts, f, indent=2)
            
            logger.info(f"Network statistics charts saved to {output_file}")
            return charts
            
        except Exception as e:
            logger.error(f"Error creating network statistics charts: {e}")
            return None
    
    def create_results_charts(self, results_file, output_prefix='results_charts'):
        """
        Create chart data for simulation results
        
        Args:
            results_file (str or Path): Path to simulation results JSON
            output_prefix (str): Prefix for output files
        
        Returns:
            dict: Chart data
        """
        logger.info("Creating simulation results charts...")
        
        try:
            # Load simulation results
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Extract time steps
            time_steps = results['time_steps']
            
            # Create pressure chart data
            pressure_data = []
            
            # Select a subset of nodes for the chart to avoid overcrowding
            node_count = len(results['nodes']['pressure'])
            sample_size = min(10, node_count)  # At most 10 nodes in the chart
            
            # Select nodes at regular intervals
            sampled_nodes = list(results['nodes']['pressure'].keys())[::max(1, node_count // sample_size)][:sample_size]
            
            for node in sampled_nodes:
                pressure_data.append({
                    'label': node,
                    'data': results['nodes']['pressure'][node]
                })
            
            # Create flow chart data
            flow_data = []
            
            # Select a subset of links for the chart
            link_count = len(results['links']['flow'])
            sample_size = min(10, link_count)  # At most 10 links in the chart
            
            # Select links at regular intervals
            sampled_links = list(results['links']['flow'].keys())[::max(1, link_count // sample_size)][:sample_size]
            
            for link in sampled_links:
                flow_data.append({
                    'label': link,
                    'data': [abs(flow) for flow in results['links']['flow'][link]]  # Use absolute values for flow
                })
            
            # Create velocity chart data
            velocity_data = []
            
            for link in sampled_links:
                velocity_data.append({
                    'label': link,
                    'data': results['links']['velocity'][link]
                })
            
            # Create charts
            charts = {
                'pressure': {
                    'type': 'line',
                    'labels': time_steps,
                    'datasets': pressure_data,
                    'title': 'Junction Pressures Over Time',
                    'xlabel': 'Time (hours)',
                    'ylabel': 'Pressure (m)'
                },
                'flow': {
                    'type': 'line',
                    'labels': time_steps,
                    'datasets': flow_data,
                    'title': 'Pipe Flow Rates Over Time',
                    'xlabel': 'Time (hours)',
                    'ylabel': 'Flow Rate (m³/s)'
                },
                'velocity': {
                    'type': 'line',
                    'labels': time_steps,
                    'datasets': velocity_data,
                    'title': 'Pipe Velocities Over Time',
                    'xlabel': 'Time (hours)',
                    'ylabel': 'Velocity (m/s)'
                }
            }
            
            # Save chart data to file
            output_file = OUTPUT_DATA_DIR / f"{output_prefix}.json"
            with open(output_file, 'w') as f:
                json.dump(charts, f, indent=2)
            
            logger.info(f"Simulation results charts saved to {output_file}")
            return charts
            
        except Exception as e:
            logger.error(f"Error creating simulation results charts: {e}")
            return None