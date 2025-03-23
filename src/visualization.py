"""
Visualization module for water distribution modeling.
Direct implementation without relying on WNTR.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
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
        logger.info(f"Creating GeoJSON representation of network from {inp_file}")
        
        try:
            # Try to load network model JSON file first (if it exists)
            model_file = Path(str(inp_file).replace('.inp', '.json'))
            if model_file.exists():
                return self._create_geojson_from_model_file(model_file)
            
            # Otherwise parse the INP file directly
            return self._create_geojson_from_inp_file(inp_file)
        
        except Exception as e:
            logger.error(f"Error creating GeoJSON representation: {e}")
            return None
    
    def _create_geojson_from_model_file(self, model_file):
        """
        Create GeoJSON representation from a network model JSON file
        
        Args:
            model_file (str or Path): Path to network model JSON file
        
        Returns:
            dict: GeoJSON representation of the network
        """
        logger.info(f"Creating GeoJSON from model file: {model_file}")
        
        try:
            # Load the network model
            with open(model_file, 'r') as f:
                network_model = json.load(f)
            
            # Initialize GeoJSON collections
            node_features = []
            link_features = []
            
            # Process nodes
            for node in network_model.get('nodes', []):
                # Skip if no coordinates
                if 'x' not in node or 'y' not in node:
                    continue
                
                # Create GeoJSON geometry
                geometry = {
                    'type': 'Point',
                    'coordinates': [node['x'], node['y']]
                }
                
                # Create feature properties
                properties = {k: v for k, v in node.items() if k not in ['x', 'y']}
                
                # Create feature
                feature = {
                    'type': 'Feature',
                    'geometry': geometry,
                    'properties': properties
                }
                
                node_features.append(feature)
            
            # Process edges
            for edge in network_model.get('edges', []):
                # Skip if missing source or target
                if 'source' not in edge or 'target' not in edge:
                    continue
                
                # Find source and target nodes
                source_node = None
                target_node = None
                
                for node in network_model.get('nodes', []):
                    if 'id' in node:
                        if node['id'] == edge['source']:
                            source_node = node
                        elif node['id'] == edge['target']:
                            target_node = node
                
                # Skip if nodes not found
                if source_node is None or target_node is None:
                    continue
                
                # Create GeoJSON geometry
                geometry = {
                    'type': 'LineString',
                    'coordinates': [
                        [source_node['x'], source_node['y']],
                        [target_node['x'], target_node['y']]
                    ]
                }
                
                # Create feature properties
                properties = {k: v for k, v in edge.items() if k not in ['source', 'target']}
                properties['start_node'] = edge['source']
                properties['end_node'] = edge['target']
                
                # Create feature
                feature = {
                    'type': 'Feature',
                    'geometry': geometry,
                    'properties': properties
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
            logger.error(f"Error creating GeoJSON from model file: {e}")
            return None
    
    def _create_geojson_from_inp_file(self, inp_file):
        """
        Create GeoJSON representation by parsing an EPANET INP file
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
        
        Returns:
            dict: GeoJSON representation of the network
        """
        logger.info(f"Creating GeoJSON from INP file: {inp_file}")
        
        try:
            # Parse the INP file
            network = self._parse_inp_file(inp_file)
            
            # Initialize GeoJSON collections
            node_features = []
            link_features = []
            
            # Process junctions
            for junction in network.get('junctions', []):
                # Skip if no coordinates
                if 'x' not in junction or 'y' not in junction:
                    continue
                
                # Create GeoJSON feature for junction
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [junction['x'], junction['y']]
                    },
                    'properties': {
                        'id': junction['id'],
                        'type': 'junction',
                        'elevation': junction.get('elevation', 0.0),
                        'demand': junction.get('demand', 0.0),
                        'name': junction.get('name', junction['id'])
                    }
                }
                
                node_features.append(feature)
            
            # Process reservoirs
            for reservoir in network.get('reservoirs', []):
                # Skip if no coordinates
                if 'x' not in reservoir or 'y' not in reservoir:
                    continue
                
                # Create GeoJSON feature for reservoir
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [reservoir['x'], reservoir['y']]
                    },
                    'properties': {
                        'id': reservoir['id'],
                        'type': 'reservoir',
                        'head': reservoir.get('head', 0.0),
                        'name': reservoir.get('name', reservoir['id'])
                    }
                }
                
                node_features.append(feature)
            
            # Process tanks
            for tank in network.get('tanks', []):
                # Skip if no coordinates
                if 'x' not in tank or 'y' not in tank:
                    continue
                
                # Create GeoJSON feature for tank
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [tank['x'], tank['y']]
                    },
                    'properties': {
                        'id': tank['id'],
                        'type': 'tank',
                        'elevation': tank.get('elevation', 0.0),
                        'init_level': tank.get('init_level', 0.0),
                        'min_level': tank.get('min_level', 0.0),
                        'max_level': tank.get('max_level', 0.0),
                        'diameter': tank.get('diameter', 0.0),
                        'name': tank.get('name', tank['id'])
                    }
                }
                
                node_features.append(feature)
            
            # Process pipes
            for pipe in network.get('pipes', []):
                # Find source and target nodes
                source_node = None
                target_node = None
                
                for node in node_features:
                    if node['properties']['id'] == pipe['node1']:
                        source_node = node
                    elif node['properties']['id'] == pipe['node2']:
                        target_node = node
                
                # Skip if nodes not found
                if source_node is None or target_node is None:
                    continue
                
                # Get coordinates
                source_coords = source_node['geometry']['coordinates']
                target_coords = target_node['geometry']['coordinates']
                
                # Create GeoJSON feature for pipe
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [source_coords, target_coords]
                    },
                    'properties': {
                        'id': pipe['id'],
                        'type': 'pipe',
                        'length': pipe.get('length', 0.0),
                        'diameter': pipe.get('diameter', 0.0),
                        'roughness': pipe.get('roughness', 0.0),
                        'status': pipe.get('status', 'OPEN'),
                        'start_node': pipe['node1'],
                        'end_node': pipe['node2'],
                        'name': pipe.get('name', pipe['id'])
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
            logger.error(f"Error creating GeoJSON from INP file: {e}")
            return None
    
    def _parse_inp_file(self, inp_file):
        """
        Parse EPANET INP file to extract network structure
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
        
        Returns:
            dict: Dictionary containing network structure
        """
        logger.info(f"Parsing EPANET INP file: {inp_file}")
        
        try:
            # Initialize network dictionary
            network = {
                'junctions': [],
                'reservoirs': [],
                'tanks': [],
                'pipes': [],
                'valves': [],
                'pumps': [],
                'coordinates': {}  # Store node coordinates
            }
            
            # Read INP file
            with open(inp_file, 'r') as f:
                lines = f.readlines()
            
            # Parse sections
            section = None
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith(';'):
                    continue
                
                # Check for section headers
                if line.startswith('['):
                    section = line.strip('[]').lower()
                    continue
                
                # Process sections
                if section == 'junctions':
                    parts = line.split()
                    if len(parts) >= 3:
                        junction = {
                            'id': parts[0],
                            'elevation': float(parts[1]),
                            'demand': float(parts[2]),
                            'pattern': parts[3] if len(parts) > 3 and not parts[3].startswith(';') else None
                        }
                        network['junctions'].append(junction)
                
                elif section == 'reservoirs':
                    parts = line.split()
                    if len(parts) >= 2:
                        reservoir = {
                            'id': parts[0],
                            'head': float(parts[1]),
                            'pattern': parts[2] if len(parts) > 2 and not parts[2].startswith(';') else None
                        }
                        network['reservoirs'].append(reservoir)
                
                elif section == 'tanks':
                    parts = line.split()
                    if len(parts) >= 7:
                        tank = {
                            'id': parts[0],
                            'elevation': float(parts[1]),
                            'init_level': float(parts[2]),
                            'min_level': float(parts[3]),
                            'max_level': float(parts[4]),
                            'diameter': float(parts[5]),
                            'min_volume': float(parts[6]),
                            'volume_curve': parts[7] if len(parts) > 7 and not parts[7].startswith(';') else None
                        }
                        network['tanks'].append(tank)
                
                elif section == 'pipes':
                    parts = line.split()
                    if len(parts) >= 8:
                        pipe = {
                            'id': parts[0],
                            'node1': parts[1],
                            'node2': parts[2],
                            'length': float(parts[3]),
                            'diameter': float(parts[4]) / 1000.0,  # Convert from mm to m
                            'roughness': float(parts[5]),
                            'minor_loss': float(parts[6]),
                            'status': parts[7]
                        }
                        network['pipes'].append(pipe)
                
                elif section == 'coordinates':
                    parts = line.split()
                    if len(parts) >= 3:
                        node_id = parts[0]
                        x = float(parts[1])
                        y = float(parts[2])
                        network['coordinates'][node_id] = {'x': x, 'y': y}
            
            # Add coordinates to nodes
            for node_type in ['junctions', 'reservoirs', 'tanks']:
                for node in network[node_type]:
                    if node['id'] in network['coordinates']:
                        node['x'] = network['coordinates'][node['id']]['x']
                        node['y'] = network['coordinates'][node['id']]['y']
            
            return network
            
        except Exception as e:
            logger.error(f"Error parsing INP file: {e}")
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
            # Get network GeoJSON
            network_geojson = self.get_network_geojson(inp_file)
            
            if network_geojson is None:
                logger.error("Failed to create network GeoJSON")
                return None
            
            # Load simulation results
            with open(results_file, 'r') as f:
                results = json.load(f)
            
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
            # Parse INP file
            network = self._parse_inp_file(inp_file)
            
            if network is None:
                logger.error("Failed to parse INP file")
                return None
            
            # Calculate pipe diameter distribution
            pipe_diameters = [pipe['diameter'] * 1000 for pipe in network['pipes']]  # Convert to mm
            
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
            pipe_lengths = [pipe['length'] for pipe in network['pipes']]
            
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
            junction_elevations = [junction['elevation'] for junction in network['junctions']]
            
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
                    'labels': ['Junctions', 'Pipes', 'Reservoirs', 'Tanks'],
                    'datasets': [{
                        'data': [
                            len(network['junctions']),
                            len(network['pipes']),
                            len(network['reservoirs']),
                            len(network['tanks'])
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