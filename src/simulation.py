"""
Simulation module for water distribution modeling.
Direct implementation of EPANET functionality without relying on WNTR.
"""

import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess
import tempfile
import json
import platform
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DATA_DIR = Path("data/output")

# Path to EPANET executable - modify this based on installation
if platform.system() == "Windows":
    EPANET_PATH = Path("epanet") / "epanet2.exe"
else:
    EPANET_PATH = Path("epanet") / "epanet2"

class EPANETSimulator:
    """Class to run hydraulic simulations on water network models"""
    
    def __init__(self):
        """Initialize the EPANETSimulator"""
        # Create output directory if it doesn't exist
        OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check if EPANET executable exists
        if not EPANET_PATH.exists():
            logger.warning(f"EPANET executable not found at {EPANET_PATH}. Will use direct calculation.")
    
    def run_simulation(self, inp_file, duration_hours=24, report_time_step=1):
        """
        Run hydraulic simulation on a water network model
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
            duration_hours (int): Simulation duration in hours
            report_time_step (int): Time step for reporting results in hours
        
        Returns:
            dict: Dictionary of simulation results
        """
        logger.info(f"Running hydraulic simulation for {duration_hours} hours...")
        
        try:
            # Create output and report files
            out_file = Path(str(inp_file).replace('.inp', '.out'))
            report_file = Path(str(inp_file).replace('.inp', '.rpt'))
            
            # Check if EPANET executable exists and run simulation
            if EPANET_PATH.exists():
                logger.info(f"Running EPANET simulation using {EPANET_PATH}...")
                
                # Run EPANET command line
                cmd = [str(EPANET_PATH), str(inp_file), str(report_file), str(out_file)]
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    logger.error(f"EPANET simulation failed: {process.stderr}")
                    return None
                
                # Parse EPANET output file
                results = self._parse_epanet_output(report_file)
                
            else:
                logger.info("EPANET executable not found. Using built-in simple hydraulic calculator...")
                
                # Use simple built-in hydraulic calculator
                results = self._run_simple_hydraulic_simulation(inp_file, duration_hours, report_time_step)
            
            # Save results to file
            results_file = OUTPUT_DATA_DIR / "simulation_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Simulation completed successfully. Results saved to {results_file}")
            return results
            
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return None
    
    def _parse_epanet_output(self, report_file):
        """
        Parse EPANET report file to extract simulation results
        
        Args:
            report_file (str or Path): Path to EPANET report file
        
        Returns:
            dict: Dictionary of simulation results
        """
        logger.info(f"Parsing EPANET report file: {report_file}")
        
        try:
            # Initialize results dictionary
            results = {
                'time_steps': [],
                'nodes': {'pressure': {}, 'head': {}, 'demand': {}},
                'links': {'flow': {}, 'velocity': {}, 'headloss': {}}
            }
            
            # Read report file
            with open(report_file, 'r') as f:
                lines = f.readlines()
            
            # Extract results
            section = None
            time_step = None
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Check for section headers
                if line.startswith('Page '):
                    section = None
                elif 'Node Results' in line:
                    section = 'nodes'
                elif 'Link Results' in line:
                    section = 'links'
                
                # Check for time step
                if line.startswith('Time: '):
                    # Extract time (format: "Time: HH:MM:SS")
                    time_str = line.split(':', 1)[1].strip()
                    time_step = time_str
                    
                    if time_step not in results['time_steps']:
                        results['time_steps'].append(time_step)
                
                # Process node results
                if section == 'nodes' and time_step and ' Junction ' in line:
                    parts = line.split()
                    
                    if len(parts) >= 5:
                        node_id = parts[1]
                        demand = float(parts[2])
                        head = float(parts[3])
                        pressure = float(parts[4])
                        
                        # Initialize node data if not exists
                        if node_id not in results['nodes']['pressure']:
                            results['nodes']['pressure'][node_id] = []
                            results['nodes']['head'][node_id] = []
                            results['nodes']['demand'][node_id] = []
                        
                        # Add data for this time step
                        results['nodes']['pressure'][node_id].append(pressure)
                        results['nodes']['head'][node_id].append(head)
                        results['nodes']['demand'][node_id].append(demand)
                
                # Process link results
                if section == 'links' and time_step and ' Pipe ' in line:
                    parts = line.split()
                    
                    if len(parts) >= 5:
                        link_id = parts[1]
                        flow = float(parts[2])
                        velocity = float(parts[3])
                        headloss = float(parts[4])
                        
                        # Initialize link data if not exists
                        if link_id not in results['links']['flow']:
                            results['links']['flow'][link_id] = []
                            results['links']['velocity'][link_id] = []
                            results['links']['headloss'][link_id] = []
                        
                        # Add data for this time step
                        results['links']['flow'][link_id].append(flow)
                        results['links']['velocity'][link_id].append(velocity)
                        results['links']['headloss'][link_id].append(headloss)
            
            # Add statistics to results
            results['stats'] = self._calculate_statistics(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing EPANET report file: {e}")
            return None
    
    def _run_simple_hydraulic_simulation(self, inp_file, duration_hours, report_time_step):
        """
        Run a simplified hydraulic simulation using built-in calculator
        
        Args:
            inp_file (str or Path): Path to EPANET INP file
            duration_hours (int): Simulation duration in hours
            report_time_step (int): Time step for reporting results in hours
        
        Returns:
            dict: Dictionary of simulation results
        """
        logger.info("Running simplified hydraulic simulation...")
        
        try:
            # Parse INP file to get network structure
            network = self._parse_inp_file(inp_file)
            
            if not network:
                logger.error("Failed to parse INP file")
                return None
            
            # Generate time steps
            time_steps = []
            for hour in range(0, duration_hours + 1, report_time_step):
                time_steps.append(f"{hour}:00")
            
            # Initialize results dictionary
            results = {
                'time_steps': time_steps,
                'nodes': {'pressure': {}, 'head': {}, 'demand': {}},
                'links': {'flow': {}, 'velocity': {}, 'headloss': {}}
            }
            
            # Get nodes and links
            junctions = network['junctions']
            pipes = network['pipes']
            reservoirs = network['reservoirs']
            
            # Simple demand pattern (24-hour pattern, repeating)
            pattern = [0.5, 0.4, 0.4, 0.4, 0.5, 0.7, 
                       0.9, 1.2, 1.3, 1.2, 1.1, 1.0,
                       1.0, 1.1, 1.2, 1.3, 1.4, 1.2,
                       1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
            
            # Simulate each time step
            for t, time_step in enumerate(time_steps):
                # Get demand multiplier for this hour
                hour = t % 24
                demand_multiplier = pattern[hour]
                
                # Calculate flows and pressures
                flows, pressures = self._calculate_flows_and_pressures(network, demand_multiplier)
                
                # Store results for this time step
                for junction in junctions:
                    junction_id = junction['id']
                    
                    # Initialize node data if not exists
                    if junction_id not in results['nodes']['pressure']:
                        results['nodes']['pressure'][junction_id] = []
                        results['nodes']['head'][junction_id] = []
                        results['nodes']['demand'][junction_id] = []
                    
                    # Add pressure and demand data
                    pressure = pressures.get(junction_id, 0.0)
                    demand = junction['demand'] * demand_multiplier
                    head = junction['elevation'] + pressure
                    
                    results['nodes']['pressure'][junction_id].append(pressure)
                    results['nodes']['head'][junction_id].append(head)
                    results['nodes']['demand'][junction_id].append(demand)
                
                for pipe in pipes:
                    pipe_id = pipe['id']
                    
                    # Initialize link data if not exists
                    if pipe_id not in results['links']['flow']:
                        results['links']['flow'][pipe_id] = []
                        results['links']['velocity'][pipe_id] = []
                        results['links']['headloss'][pipe_id] = []
                    
                    # Add flow and velocity data
                    flow = flows.get(pipe_id, 0.0)
                    velocity = abs(flow) / (np.pi * (pipe['diameter'] / 2) ** 2) if pipe['diameter'] > 0 else 0.0
                    
                    # Calculate headloss using Hazen-Williams formula
                    if abs(flow) > 0 and pipe['length'] > 0 and pipe['diameter'] > 0:
                        # Hazen-Williams headloss formula
                        # h = 10.67 * L * (Q^1.85) / (C^1.85 * D^4.87)
                        # where L is length (m), Q is flow (m³/s), C is roughness, D is diameter (m)
                        headloss = 10.67 * pipe['length'] * (abs(flow) ** 1.85) / \
                                  ((pipe['roughness'] ** 1.85) * (pipe['diameter'] ** 4.87))
                    else:
                        headloss = 0.0
                    
                    results['links']['flow'][pipe_id].append(flow)
                    results['links']['velocity'][pipe_id].append(velocity)
                    results['links']['headloss'][pipe_id].append(headloss)
            
            # Add statistics to results
            results['stats'] = self._calculate_statistics(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in simplified hydraulic simulation: {e}")
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
                'pumps': []
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
            
            return network
            
        except Exception as e:
            logger.error(f"Error parsing INP file: {e}")
            return None
    
    def _calculate_flows_and_pressures(self, network, demand_multiplier):
        """
        Calculate flows and pressures using a simplified hydraulic model
        
        Args:
            network (dict): Network structure
            demand_multiplier (float): Demand pattern multiplier
        
        Returns:
            tuple: (flows, pressures) dictionaries
        """
        # Simplified hydraulic calculation
        # This is a very basic approximation and not a full hydraulic solver
        
        # Initialize flows and pressures
        flows = {}
        pressures = {}
        
        # Get source pressure from reservoirs
        source_pressure = 0.0
        if network['reservoirs']:
            # Use the first reservoir's head
            source_pressure = network['reservoirs'][0]['head']
        
        # Calculate total demand
        total_demand = sum(junction['demand'] * demand_multiplier for junction in network['junctions'])
        
        # Distribute flow based on demand proportion
        for pipe in network['pipes']:
            # Find the junction at the end of the pipe
            end_junction = None
            for junction in network['junctions']:
                if junction['id'] == pipe['node2']:
                    end_junction = junction
                    break
            
            if end_junction:
                # Calculate flow based on demand proportion
                proportion = end_junction['demand'] * demand_multiplier / total_demand if total_demand > 0 else 0
                flows[pipe['id']] = proportion * total_demand
            else:
                flows[pipe['id']] = 0.0
        
        # Calculate pressures based on distance from source and flow
        for junction in network['junctions']:
            # Find the shortest path to a source (simplified)
            min_headloss = float('inf')
            
            for pipe in network['pipes']:
                if pipe['node2'] == junction['id'] or pipe['node1'] == junction['id']:
                    # Simple head loss calculation
                    flow = abs(flows.get(pipe['id'], 0.0))
                    
                    if flow > 0 and pipe['diameter'] > 0:
                        # Simplified headloss formula
                        headloss = 10.67 * pipe['length'] * (flow ** 1.85) / \
                                 ((pipe['roughness'] ** 1.85) * (pipe['diameter'] ** 4.87))
                    else:
                        headloss = 0.0
                    
                    min_headloss = min(min_headloss, headloss)
            
            # Set pressure (source pressure minus head loss, minus elevation difference)
            if min_headloss != float('inf'):
                pressure = source_pressure - min_headloss - junction['elevation']
                pressures[junction['id']] = max(0.0, pressure)  # Pressure can't be negative
            else:
                pressures[junction['id']] = 0.0
        
        return flows, pressures
    
    def _calculate_statistics(self, results):
        """
        Calculate statistics from simulation results
        
        Args:
            results (dict): Simulation results
        
        Returns:
            dict: Statistics dictionary
        """
        stats = {
            'duration_hours': len(results['time_steps']),
            'pressure': {
                'min': None,
                'max': None,
                'avg': None
            },
            'flow': {
                'min': None,
                'max': None,
                'avg': None
            },
            'velocity': {
                'min': None,
                'max': None,
                'avg': None
            }
        }
        
        # Calculate pressure statistics
        all_pressures = []
        for pressures in results['nodes']['pressure'].values():
            all_pressures.extend(pressures)
        
        if all_pressures:
            stats['pressure']['min'] = min(all_pressures)
            stats['pressure']['max'] = max(all_pressures)
            stats['pressure']['avg'] = sum(all_pressures) / len(all_pressures)
        
        # Calculate flow statistics
        all_flows = []
        for flows in results['links']['flow'].values():
            all_flows.extend([abs(flow) for flow in flows])
        
        if all_flows:
            stats['flow']['min'] = min(all_flows)
            stats['flow']['max'] = max(all_flows)
            stats['flow']['avg'] = sum(all_flows) / len(all_flows)
        
        # Calculate velocity statistics
        all_velocities = []
        for velocities in results['links']['velocity'].values():
            all_velocities.extend(velocities)
        
        if all_velocities:
            stats['velocity']['min'] = min(all_velocities)
            stats['velocity']['max'] = max(all_velocities)
            stats['velocity']['avg'] = sum(all_velocities) / len(all_velocities)
        
        return stats
    
    def get_result_stats(self, results):
        """
        Get statistics from simulation results
        
        Args:
            results (dict): Simulation results
        
        Returns:
            dict: Statistics dictionary
        """
        if 'stats' in results:
            return results['stats']
        else:
            return self._calculate_statistics(results)
    
    def save_results(self, results, output_file):
        """
        Save simulation results to file
        
        Args:
            results (dict): Simulation results
            output_file (str or Path): Path to save results
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Simulation results saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving simulation results: {e}")
            return False