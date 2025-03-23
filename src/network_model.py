"""
Network model module for water distribution modeling.
Direct implementation of EPANET functionality without relying on WNTR.
"""

import os
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
import networkx as nx
from shapely.geometry import Point, LineString
import subprocess
import tempfile
import json
import platform

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROCESSED_DATA_DIR = Path("data/processed")
OUTPUT_DATA_DIR = Path("data/output")

# Path to EPANET executable - modify this based on installation
if platform.system() == "Windows":
    EPANET_PATH = Path("epanet") / "epanet2.exe"
else:
    EPANET_PATH = Path("epanet") / "epanet2"

class NetworkBuilder:
    """Class to build water network models from processed GIS data"""
    
    def __init__(self):
        """Initialize the NetworkBuilder"""
        # Create output directory if it doesn't exist
        OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def build_from_gis(self, mains_file, hydrants_file=None, pressure_zones_file=None):
        """
        Build network model from GIS data
        
        Args:
            mains_file (str or Path): Path to processed water mains GeoJSON
            hydrants_file (str or Path, optional): Path to processed hydrants GeoJSON
            pressure_zones_file (str or Path, optional): Path to processed pressure zones GeoJSON
        
        Returns:
            dict: Dictionary containing network model data
        """
        logger.info("Building network model from GIS data...")
        
        try:
            # Load water mains data
            water_mains = gpd.read_file(mains_file)
            
            # Load hydrants data if available
            hydrants = None
            if hydrants_file and Path(hydrants_file).exists():
                hydrants = gpd.read_file(hydrants_file)
            
            # Load pressure zones data if available
            pressure_zones = None
            if pressure_zones_file and Path(pressure_zones_file).exists():
                pressure_zones = gpd.read_file(pressure_zones_file)
            
            # Create a network graph from the water mains
            G = self._create_network_graph(water_mains)
            
            # Add elevation data if available
            G = self._add_elevation_data(G)
            
            # Add default demands to junctions
            G = self._add_junction_demands(G)
            
            # Add hydrants if available
            if hydrants is not None:
                G = self._add_hydrants_to_network(G, hydrants)
            
            # Add reservoirs and tanks based on pressure zones
            if pressure_zones is not None:
                G = self._add_reservoirs_and_tanks(G, pressure_zones)
            else:
                # If no pressure zones data, add a default source
                G = self._add_default_water_source(G)
            
            # Generate INP file
            inp_file = OUTPUT_DATA_DIR / "madison_network.inp"
            self._create_inp_file(G, inp_file)
            
            # Create network model dictionary
            network_model = {
                'graph': G,
                'inp_file': str(inp_file),
                'junctions': list(filter(lambda n: G.nodes[n].get('type') == 'junction', G.nodes())),
                'pipes': list(filter(lambda e: G.edges[e].get('type') == 'pipe', G.edges())),
                'reservoirs': list(filter(lambda n: G.nodes[n].get('type') == 'reservoir', G.nodes())),
                'tanks': list(filter(lambda n: G.nodes[n].get('type') == 'tank', G.nodes()))
            }
            
            logger.info(f"Network model built with {len(network_model['junctions'])} junctions and {len(network_model['pipes'])} pipes")
            return network_model
            
        except Exception as e:
            logger.error(f"Error building network model: {e}")
            return None
    
    def _create_network_graph(self, water_mains):
        """
        Create a NetworkX graph from water mains data
        
        Args:
            water_mains (gpd.GeoDataFrame): Processed water mains data
        
        Returns:
            nx.Graph: Network graph
        """
        logger.info("Creating network graph from water mains...")
        
        # Create an empty graph
        G = nx.Graph()
        
        # Extract unique junction points from pipe endpoints
        junctions = {}
        
        # Process each pipe
        for idx, pipe in water_mains.iterrows():
            # Get pipe geometry
            if 'geometry' not in pipe:
                continue
                
            # Get pipe endpoints
            if 'start_point' in pipe and 'end_point' in pipe:
                start_point = pipe.start_point
                end_point = pipe.end_point
            else:
                # Extract endpoints from LineString geometry
                if pipe.geometry.geom_type != 'LineString':
                    continue
                    
                start_point = Point(pipe.geometry.coords[0])
                end_point = Point(pipe.geometry.coords[-1])
            
            # Create junction IDs based on coordinates (rounded to handle floating point issues)
            start_coord = (round(start_point.x, 6), round(start_point.y, 6))
            end_coord = (round(end_point.x, 6), round(end_point.y, 6))
            
            # Generate unique IDs for junctions
            if start_coord not in junctions:
                junctions[start_coord] = f"J{len(junctions) + 1}"
            
            if end_coord not in junctions:
                junctions[end_coord] = f"J{len(junctions) + 1}"
            
            start_junction_id = junctions[start_coord]
            end_junction_id = junctions[end_coord]
            
            # Add junctions to the graph
            if start_junction_id not in G:
                G.add_node(start_junction_id, 
                         type='junction',
                         x=start_point.x,
                         y=start_point.y,
                         elevation=250.0,  # Default elevation
                         demand=0.01)      # Default demand
            
            if end_junction_id not in G:
                G.add_node(end_junction_id, 
                         type='junction',
                         x=end_point.x,
                         y=end_point.y,
                         elevation=250.0,  # Default elevation
                         demand=0.01)      # Default demand
            
            # Skip self-loops
            if start_junction_id == end_junction_id:
                continue
            
            # Create pipe ID
            pipe_id = f"P{idx + 1}" if 'pipe_id' not in pipe else pipe['pipe_id']
            
            # Get pipe properties
            length = pipe['length_m'] if 'length_m' in pipe else 100.0
            
            # Diameter in mm, convert to m
            if 'diameter_mm' in pipe:
                diameter = pipe['diameter_mm'] / 1000.0  # Convert mm to m
            elif 'diameter' in pipe:
                diameter = pipe['diameter'] / 1000.0 if pipe['diameter'] > 10 else pipe['diameter']
            else:
                diameter = 0.2  # Default diameter (200 mm)
            
            # Roughness coefficient
            roughness = pipe['roughness'] if 'roughness' in pipe else 100.0
            
            # Add the pipe as an edge in the graph
            G.add_edge(start_junction_id, end_junction_id,
                     id=pipe_id,
                     type='pipe',
                     length=length,
                     diameter=diameter,
                     roughness=roughness,
                     status='OPEN')
        
        logger.info(f"Created network graph with {len(G.nodes)} junctions and {len(G.edges)} pipes")
        return G
    
    def _add_elevation_data(self, G):
        """
        Add elevation data to junctions if available
        
        Args:
            G (nx.Graph): Network graph
        
        Returns:
            nx.Graph: Updated network graph
        """
        # Check if processed elevation data exists
        elevation_file = PROCESSED_DATA_DIR / "junction_elevations.csv"
        
        if elevation_file.exists():
            try:
                # Load elevation data
                elevation_df = pd.read_csv(elevation_file)
                
                # Update junction elevations
                for _, row in elevation_df.iterrows():
                    junction_id = row['junction_id']
                    elevation = row['elevation']
                    
                    if junction_id in G.nodes:
                        G.nodes[junction_id]['elevation'] = elevation
                
                logger.info(f"Added elevation data to {len(elevation_df)} junctions")
            except Exception as e:
                logger.warning(f"Error loading elevation data: {e}")
        
        return G
    
    def _add_junction_demands(self, G):
        """
        Add demand data to junctions if available, or use a default pattern
        
        Args:
            G (nx.Graph): Network graph
        
        Returns:
            nx.Graph: Updated network graph
        """
        # Check if processed demand data exists
        demand_file = PROCESSED_DATA_DIR / "junction_demands.csv"
        
        if demand_file.exists():
            try:
                # Load demand data
                demand_df = pd.read_csv(demand_file)
                
                # Update junction demands
                for _, row in demand_df.iterrows():
                    junction_id = row['junction_id']
                    demand = row['demand']
                    
                    if junction_id in G.nodes:
                        G.nodes[junction_id]['demand'] = demand
                
                logger.info(f"Added demand data to {len(demand_df)} junctions")
            except Exception as e:
                logger.warning(f"Error loading demand data: {e}")
        else:
            # Assign default demands based on a simple formula
            # More peripheral nodes get higher demand
            
            # Find the center of the network
            x_coords = [G.nodes[n]['x'] for n in G.nodes()]
            y_coords = [G.nodes[n]['y'] for n in G.nodes()]
            
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            
            # Calculate demands based on distance from center
            for node in G.nodes():
                x = G.nodes[node]['x']
                y = G.nodes[node]['y']
                
                # Calculate distance from center
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                
                # Normalize distance to range [0, 1]
                max_distance = ((max(x_coords) - min(x_coords)) ** 2 + (max(y_coords) - min(y_coords)) ** 2) ** 0.5 / 2
                normalized_distance = distance / max_distance if max_distance > 0 else 0
                
                # Calculate demand based on distance (more peripheral nodes have higher demand)
                # Base demand between 0.01 and 0.05
                demand = 0.01 + normalized_distance * 0.04
                
                G.nodes[node]['demand'] = demand
            
            logger.info(f"Added default demands to {len(G.nodes)} junctions")
        
        return G
    
    def _add_hydrants_to_network(self, G, hydrants):
        """
        Add hydrants to the network
        
        Args:
            G (nx.Graph): Network graph
            hydrants (gpd.GeoDataFrame): Processed hydrants data
        
        Returns:
            nx.Graph: Updated network graph
        """
        logger.info("Adding hydrants to network model...")
        
        # Create spatial index for the junctions
        junction_points = []
        junction_ids = []
        
        for node in G.nodes():
            if G.nodes[node]['type'] == 'junction':
                x = G.nodes[node]['x']
                y = G.nodes[node]['y']
                junction_points.append((x, y))
                junction_ids.append(node)
        
        # Process each hydrant
        hydrant_count = 0
        for idx, hydrant in hydrants.iterrows():
            # Get hydrant coordinates
            if hydrant.geometry.geom_type != 'Point':
                continue
                
            x, y = hydrant.geometry.x, hydrant.geometry.y
            
            # Find nearest junction
            distances = [((x - jx) ** 2 + (y - jy) ** 2) ** 0.5 for jx, jy in junction_points]
            nearest_idx = np.argmin(distances)
            nearest_junction = junction_ids[nearest_idx]
            
            # Generate unique hydrant ID
            hydrant_id = f"H{idx + 1}" if 'hydrant_id' not in hydrant else hydrant['hydrant_id']
            
            # Add the hydrant as a node
            G.add_node(hydrant_id,
                     type='hydrant',
                     x=x,
                     y=y,
                     elevation=G.nodes[nearest_junction]['elevation'],  # Same elevation as nearest junction
                     demand=0.0)  # Hydrants have zero base demand
            
            # Add a pipe connecting the hydrant to the nearest junction
            pipe_id = f"HP{idx + 1}"
            
            G.add_edge(nearest_junction, hydrant_id,
                     id=pipe_id,
                     type='pipe',
                     length=10.0,  # Short 10-meter connection
                     diameter=0.1,  # 100 mm diameter
                     roughness=100.0,
                     status='OPEN')
            
            hydrant_count += 1
        
        logger.info(f"Added {hydrant_count} hydrants to the network model")
        return G
    
    def _add_reservoirs_and_tanks(self, G, pressure_zones):
        """
        Add reservoirs and tanks based on pressure zones
        
        Args:
            G (nx.Graph): Network graph
            pressure_zones (gpd.GeoDataFrame): Processed pressure zones data
        
        Returns:
            nx.Graph: Updated network graph
        """
        logger.info("Adding reservoirs and tanks based on pressure zones...")
        
        # Extract junction coordinates
        junction_coords = {}
        for node in G.nodes():
            if G.nodes[node]['type'] == 'junction':
                x = G.nodes[node]['x']
                y = G.nodes[node]['y']
                junction_coords[node] = Point(x, y)
        
        # Add reservoirs and tanks for each pressure zone
        reservoir_count = 0
        tank_count = 0
        
        for idx, zone in pressure_zones.iterrows():
            zone_id = f'Z{idx+1}' if 'ZONE_ID' not in pressure_zones.columns else zone['ZONE_ID']
            
            # Find junctions within this zone
            junctions_in_zone = []
            for node, point in junction_coords.items():
                if zone.geometry.contains(point):
                    junctions_in_zone.append(node)
            
            if not junctions_in_zone:
                logger.warning(f"No junctions found in pressure zone {zone_id}. Skipping...")
                continue
            
            # For the primary zone (or first zone), add a reservoir
            if idx == 0 or ('PRIMARY' in zone and zone['PRIMARY']):
                # Create a reservoir ID
                reservoir_id = f'R{zone_id}'
                
                # Choose a junction to connect the reservoir to
                # Ideally the highest elevation junction
                elevations = [G.nodes[node]['elevation'] for node in junctions_in_zone]
                highest_idx = np.argmax(elevations)
                connection_junction = junctions_in_zone[highest_idx]
                
                # Determine base head based on pressure zone data
                base_head = 300.0  # Default head in meters
                if 'HEAD' in zone:
                    base_head = zone['HEAD']
                elif 'PRESSURE' in zone:
                    # Convert pressure to head (pressure in psi, head in meters)
                    base_head = zone['PRESSURE'] * 0.703  # psi to meters of head
                
                # Add the reservoir
                G.add_node(reservoir_id,
                         type='reservoir',
                         x=G.nodes[connection_junction]['x'],
                         y=G.nodes[connection_junction]['y'],
                         head=base_head)
                
                # Add a pipe connecting the reservoir to the junction
                pipe_id = f'RP{idx+1}'
                
                G.add_edge(reservoir_id, connection_junction,
                         id=pipe_id,
                         type='pipe',
                         length=10.0,  # Short 10-meter connection
                         diameter=0.3,  # 300 mm diameter for main feed
                         roughness=120.0,
                         status='OPEN')
                
                reservoir_count += 1
            else:
                # Add a tank for secondary zones
                tank_id = f'T{zone_id}'
                
                # Choose a junction to connect the tank to
                # For simplicity, use the first junction
                connection_junction = junctions_in_zone[0]
                
                # Determine tank parameters
                max_level = 10.0  # Default max level in meters
                diameter = 20.0  # Default diameter in meters
                
                # Use pressure zone information if available
                if 'MAX_LEVEL' in zone:
                    max_level = zone['MAX_LEVEL']
                
                initial_level = max_level * 0.7  # Start at 70% full
                min_level = 0.1  # Minimum level
                
                # Add the tank
                G.add_node(tank_id,
                         type='tank',
                         x=G.nodes[connection_junction]['x'],
                         y=G.nodes[connection_junction]['y'],
                         elevation=G.nodes[connection_junction]['elevation'],
                         init_level=initial_level,
                         min_level=min_level,
                         max_level=max_level,
                         diameter=diameter)
                
                # Add a pipe connecting the tank to the junction
                pipe_id = f'TP{idx+1}'
                
                G.add_edge(tank_id, connection_junction,
                         id=pipe_id,
                         type='pipe',
                         length=10.0,  # Short 10-meter connection
                         diameter=0.2,  # 200 mm diameter
                         roughness=120.0,
                         status='OPEN')
                
                tank_count += 1
        
        logger.info(f"Added {reservoir_count} reservoirs and {tank_count} tanks to the network model")
        return G
    
    def _add_default_water_source(self, G):
        """
        Add a default water source (reservoir)
        
        Args:
            G (nx.Graph): Network graph
        
        Returns:
            nx.Graph: Updated network graph
        """
        logger.info("Adding default water source...")
        
        # Find the highest elevation junction
        junction_elevations = {node: G.nodes[node]['elevation'] 
                              for node in G.nodes() 
                              if G.nodes[node]['type'] == 'junction'}
        
        if not junction_elevations:
            logger.error("No junctions found in the network. Cannot add water source.")
            return G
        
        highest_junction = max(junction_elevations, key=junction_elevations.get)
        highest_elevation = junction_elevations[highest_junction]
        
        # Add a reservoir
        reservoir_id = 'R1'
        
        G.add_node(reservoir_id,
                 type='reservoir',
                 x=G.nodes[highest_junction]['x'],
                 y=G.nodes[highest_junction]['y'],
                 head=highest_elevation + 50.0)  # Add 50 meters of head
        
        # Add a pipe connecting the reservoir to the junction
        G.add_edge(reservoir_id, highest_junction,
                 id='RP1',
                 type='pipe',
                 length=10.0,  # Short 10-meter connection
                 diameter=0.3,  # 300 mm diameter for main feed
                 roughness=120.0,
                 status='OPEN')
        
        logger.info("Added default water source (reservoir)")
        return G
    
    def _create_inp_file(self, G, output_file):
        """
        Create an EPANET INP file from the network graph
        
        Args:
            G (nx.Graph): Network graph
            output_file (str or Path): Path to save the INP file
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Creating EPANET INP file: {output_file}")
        
        try:
            with open(output_file, 'w') as f:
                # Write [TITLE] section
                f.write("[TITLE]\n")
                f.write(";Generated by HydroFlow\n")
                f.write("\n")
                
                # Write [JUNCTIONS] section
                f.write("[JUNCTIONS]\n")
                f.write(";ID              Elev        Demand      Pattern         \n")
                f.write(";-------------- ------------ ------------ ----------------\n")
                
                for node in G.nodes():
                    if G.nodes[node]['type'] == 'junction':
                        elevation = G.nodes[node]['elevation']
                        demand = G.nodes[node]['demand']
                        
                        f.write(f"{node:<16} {elevation:<12.2f} {demand:<12.6f} ;\n")
                
                f.write("\n")
                
                # Write [RESERVOIRS] section
                f.write("[RESERVOIRS]\n")
                f.write(";ID              Head        Pattern         \n")
                f.write(";-------------- ------------ ----------------\n")
                
                for node in G.nodes():
                    if G.nodes[node]['type'] == 'reservoir':
                        head = G.nodes[node]['head']
                        
                        f.write(f"{node:<16} {head:<12.2f} ;\n")
                
                f.write("\n")
                
                # Write [TANKS] section
                f.write("[TANKS]\n")
                f.write(";ID              Elevation   InitLevel   MinLevel    MaxLevel    Diameter    MinVol      VolCurve\n")
                f.write(";-------------- ------------ ------------ ------------ ------------ ------------ ------------ ----------------\n")
                
                for node in G.nodes():
                    if G.nodes[node]['type'] == 'tank':
                        elevation = G.nodes[node]['elevation']
                        init_level = G.nodes[node]['init_level']
                        min_level = G.nodes[node]['min_level']
                        max_level = G.nodes[node]['max_level']
                        diameter = G.nodes[node]['diameter']
                        
                        f.write(f"{node:<16} {elevation:<12.2f} {init_level:<12.2f} {min_level:<12.2f} {max_level:<12.2f} {diameter:<12.2f} 0.0          ;\n")
                
                f.write("\n")
                
                # Write [PIPES] section
                f.write("[PIPES]\n")
                f.write(";ID              Node1           Node2           Length      Diameter    Roughness   MinorLoss   Status\n")
                f.write(";-------------- ---------------- ---------------- ----------- ----------- ----------- ----------- ----------------\n")
                
                for u, v, data in G.edges(data=True):
                    if data['type'] == 'pipe':
                        pipe_id = data['id']
                        length = data['length']
                        diameter = data['diameter']
                        roughness = data['roughness']
                        status = data['status']
                        
                        f.write(f"{pipe_id:<16} {u:<16} {v:<16} {length:<11.2f} {diameter*1000:<11.2f} {roughness:<11.2f} 0.0         {status}\n")
                
                f.write("\n")
                
                # Write [PATTERNS] section
                f.write("[PATTERNS]\n")
                f.write(";ID              Multipliers\n")
                f.write(";-------------- ----------------\n")
                f.write(";Daily demand pattern\n")
                f.write("1                0.5         0.4         0.4         0.4         0.5         0.7\n")
                f.write("1                0.9         1.2         1.3         1.2         1.1         1.0\n")
                f.write("1                1.0         1.1         1.2         1.3         1.4         1.2\n")
                f.write("1                1.1         1.0         0.9         0.8         0.7         0.6\n")
                f.write("\n")
                
                # Write [OPTIONS] section
                f.write("[OPTIONS]\n")
                f.write("UNITS              LPS\n")
                f.write("HEADLOSS           H-W\n")
                f.write("SPECIFIC GRAVITY   1.0\n")
                f.write("VISCOSITY          1.0\n")
                f.write("TRIALS             40\n")
                f.write("ACCURACY           0.001\n")
                f.write("PATTERN            1\n")
                f.write("DEMAND MULTIPLIER  1.0\n")
                f.write("EMITTER EXPONENT   0.5\n")
                f.write("QUALITY            NONE\n")
                f.write("DIFFUSIVITY        1.0\n")
                f.write("TOLERANCE          0.01\n")
                f.write("\n")
                
                # Write [TIMES] section
                f.write("[TIMES]\n")
                f.write("DURATION           24:00\n")
                f.write("HYDRAULIC TIMESTEP 1:00\n")
                f.write("QUALITY TIMESTEP   0:05\n")
                f.write("PATTERN TIMESTEP   1:00\n")
                f.write("PATTERN START      0:00\n")
                f.write("REPORT TIMESTEP    1:00\n")
                f.write("REPORT START       0:00\n")
                f.write("START CLOCKTIME    0:00\n")
                f.write("STATISTIC          NONE\n")
                f.write("\n")
                
                # Write [REPORT] section
                f.write("[REPORT]\n")
                f.write("PAGESIZE           0\n")
                f.write("STATUS             YES\n")
                f.write("SUMMARY            YES\n")
                f.write("ENERGY             NO\n")
                f.write("NODES              ALL\n")
                f.write("LINKS              ALL\n")
                f.write("\n")
                
                # Write [END] section
                f.write("[END]\n")
            
            logger.info(f"EPANET INP file created successfully: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating EPANET INP file: {e}")
            return False
    
    def get_network_stats(self, network_model):
        """
        Generate statistics about the network model
        
        Args:
            network_model (dict): Network model dictionary
        
        Returns:
            dict: Dictionary of network statistics
        """
        try:
            G = network_model['graph']
            
            # Count components
            junctions = [n for n in G.nodes() if G.nodes[n].get('type') == 'junction']
            reservoirs = [n for n in G.nodes() if G.nodes[n].get('type') == 'reservoir']
            tanks = [n for n in G.nodes() if G.nodes[n].get('type') == 'tank']
            pipes = [e for e in G.edges() if G.edges[e].get('type') == 'pipe']
            
            # Calculate total pipe length
            total_pipe_length = sum(G.edges[e]['length'] for e in pipes)
            
            # Calculate average pipe diameter
            avg_diameter = np.mean([G.edges[e]['diameter'] for e in pipes]) * 1000  # Convert to mm
            
            # Calculate total demand
            total_demand = sum(G.nodes[n]['demand'] for n in junctions)
            
            # Create statistics dictionary
            stats = {
                'junctions': len(junctions),
                'reservoirs': len(reservoirs),
                'tanks': len(tanks),
                'pipes': len(pipes),
                'total_pipe_length': total_pipe_length,
                'avg_pipe_diameter': avg_diameter,
                'total_demand': total_demand
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating network statistics: {e}")
            return {}
    
    def save_network(self, network_model, output_file):
        """
        Save network model to file
        
        Args:
            network_model (dict): Network model dictionary
            output_file (str or Path): Path to save the network model
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert the NetworkX graph to a serializable format
            G = network_model['graph']
            
            # Export node data
            nodes_data = []
            for node, data in G.nodes(data=True):
                node_data = {'id': node}
                node_data.update(data)
                nodes_data.append(node_data)
            
            # Export edge data
            edges_data = []
            for u, v, data in G.edges(data=True):
                edge_data = {'source': u, 'target': v}
                edge_data.update(data)
                edges_data.append(edge_data)
            
            # Create serializable network model
            serializable_model = {
                'nodes': nodes_data,
                'edges': edges_data,
                'inp_file': network_model['inp_file'],
                'junctions': network_model['junctions'],
                'pipes': network_model['pipes'],
                'reservoirs': network_model['reservoirs'],
                'tanks': network_model['tanks']
            }
            
            # Save to file
            with open(output_file, 'w') as f:
                json.dump(serializable_model, f, indent=2)
            
            logger.info(f"Network model saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving network model: {e}")
            return False
    
    def load_network(self, input_file):
        """
        Load network model from file
        
        Args:
            input_file (str or Path): Path to network model file
        
        Returns:
            dict: Network model dictionary
        """
        try:
            # Load serialized network model
            with open(input_file, 'r') as f:
                serialized_model = json.load(f)
            
            # Create a new graph
            G = nx.Graph()
            
            # Add nodes
            for node_data in serialized_model['nodes']:
                node_id = node_data.pop('id')
                G.add_node(node_id, **node_data)
            
            # Add edges
            for edge_data in serialized_model['edges']:
                source = edge_data.pop('source')
                target = edge_data.pop('target')
                G.add_edge(source, target, **edge_data)
            
            # Recreate the network model dictionary
            network_model = {
                'graph': G,
                'inp_file': serialized_model['inp_file'],
                'junctions': serialized_model['junctions'],
                'pipes': serialized_model['pipes'],
                'reservoirs': serialized_model['reservoirs'],
                'tanks': serialized_model['tanks']
            }
            
            logger.info(f"Network model loaded from {input_file}")
            return network_model
            
        except Exception as e:
            logger.error(f"Error loading network model: {e}")
            return None