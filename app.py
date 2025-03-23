"""
Flask application for EPANET Water Distribution Model
"""

import os
import json
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import project modules
from src.data_collection import DataCollector
from src.data_processing import DataProcessor
from src.network_model import NetworkBuilder
from src.simulation import EPANETSimulator
from src.visualization import NetworkVisualizer

# Try to import and set up EPANET if possible
try:
    from src.epanet_util import setup_epanet
    setup_epanet()
    logger.info("EPANET command-line tool setup successful")
except ImportError:
    logger.warning("EPANET utility module not found. Hydraulic simulations will use simplified calculations")
except Exception as e:
    logger.warning(f"Could not set up EPANET: {e}")
    logger.warning("Hydraulic simulations will use simplified calculations")

# Initialize Flask app
app = Flask(__name__)

# Data paths
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
OUTPUT_DATA_DIR = Path("data/output")

# Create directories if they don't exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Initialize components
data_collector = DataCollector()
data_processor = DataProcessor()
network_builder = NetworkBuilder()
simulator = EPANETSimulator()
visualizer = NetworkVisualizer()

# Global variable to store the current simulation state
current_simulation = None

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@app.route('/collect-data', methods=['POST'])
def collect_data():
    """API endpoint to collect water distribution data"""
    try:
        # Get optional parameters from request
        params = request.get_json() or {}
        
        # Check if data already exists to avoid re-downloading
        if RAW_DATA_DIR.exists() and any(RAW_DATA_DIR.iterdir()):
            logger.info("Using existing data files")
            # List existing files
            files = list(RAW_DATA_DIR.glob('*'))
            return jsonify({
                'status': 'success',
                'message': 'Using existing data files',
                'files': [str(f.name) for f in files]
            })
        
        # Collect data
        logger.info("Starting data collection")
        result = data_collector.fetch_all_data()
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Failed to collect data'
            }), 500
        
        # List files that were collected
        files = list(RAW_DATA_DIR.glob('*'))
        
        return jsonify({
            'status': 'success',
            'message': 'Data collected successfully',
            'files': [str(f.name) for f in files]
        })
    
    except Exception as e:
        logger.error(f"Error in data collection: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/process-data', methods=['POST'])
def process_data():
    """API endpoint to process collected data"""
    try:
        # Get optional parameters from request
        params = request.get_json() or {}
        subset_area = params.get('subset_area', None)
        
        # Process water mains
        logger.info("Processing water mains")
        water_mains = data_processor.clean_water_mains(subset_area)
        
        if water_mains is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to process water mains data'
            }), 500
        
        # Process hydrants
        logger.info("Processing hydrants")
        hydrants = data_processor.process_hydrants()
        
        # Process pressure zones
        logger.info("Processing pressure zones")
        pressure_zones = data_processor.process_pressure_zones()
        
        # List processed files
        files = list(PROCESSED_DATA_DIR.glob('*'))
        
        return jsonify({
            'status': 'success',
            'message': 'Data processed successfully',
            'stats': {
                'water_mains': len(water_mains) if water_mains is not None else 0,
                'hydrants': len(hydrants) if hydrants is not None else 0,
                'pressure_zones': len(pressure_zones) if pressure_zones is not None else 0
            },
            'files': [str(f.name) for f in files]
        })
    
    except Exception as e:
        logger.error(f"Error in data processing: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/build-network', methods=['POST'])
def build_network():
    """API endpoint to build network model"""
    try:
        # Get optional parameters from request
        params = request.get_json() or {}
        
        # Check if required processed data exists
        required_files = ["processed_water_mains.geojson"]
        missing_files = [f for f in required_files if not (PROCESSED_DATA_DIR / f).exists()]
        
        if missing_files:
            return jsonify({
                'status': 'error',
                'message': f'Missing required processed data: {", ".join(missing_files)}'
            }), 400
        
        # Build network model
        logger.info("Building network model")
        network = network_builder.build_from_gis(
            mains_file=PROCESSED_DATA_DIR / "processed_water_mains.geojson",
            hydrants_file=PROCESSED_DATA_DIR / "processed_hydrants.geojson" if (PROCESSED_DATA_DIR / "processed_hydrants.geojson").exists() else None,
            pressure_zones_file=PROCESSED_DATA_DIR / "processed_pressure_zones.geojson" if (PROCESSED_DATA_DIR / "processed_pressure_zones.geojson").exists() else None
        )
        
        if network is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to build network model'
            }), 500
        
        # Save network to file
        model_file = OUTPUT_DATA_DIR / "network_model.json"
        inp_file = OUTPUT_DATA_DIR / "madison_network.inp"
        network_builder.save_network(network, model_file)
        
        # Generate network statistics
        stats = network_builder.get_network_stats(network)
        
        return jsonify({
            'status': 'success',
            'message': 'Network model built successfully',
            'stats': stats,
            'inp_file': str(inp_file),
            'model_file': str(model_file)
        })
    
    except Exception as e:
        logger.error(f"Error in network building: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/run-simulation', methods=['POST'])
def run_simulation():
    """API endpoint to run hydraulic simulation"""
    global current_simulation
    
    try:
        # Get parameters from request
        params = request.get_json() or {}
        duration = params.get('duration', 24)  # Default 24-hour simulation
        time_step = params.get('time_step', 1)  # Default 1-hour time step
        
        # Check if network file exists
        inp_file = OUTPUT_DATA_DIR / "madison_network.inp"
        if not inp_file.exists():
            return jsonify({
                'status': 'error',
                'message': 'Network model file not found'
            }), 400
        
        # Run simulation
        logger.info(f"Running hydraulic simulation for {duration} hours")
        results = simulator.run_simulation(
            inp_file=inp_file,
            duration_hours=duration,
            report_time_step=time_step
        )
        
        if results is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to run simulation'
            }), 500
        
        # Store current simulation results
        current_simulation = {
            'results': results,
            'duration': duration,
            'time_step': time_step
        }
        
        # Save results to file
        results_file = OUTPUT_DATA_DIR / "simulation_results.json"
        simulator.save_results(results, results_file)
        
        # Generate result statistics
        stats = simulator.get_result_stats(results)
        
        return jsonify({
            'status': 'success',
            'message': 'Simulation completed successfully',
            'stats': stats,
            'results_file': str(results_file)
        })
    
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/visualize-network', methods=['GET'])
def visualize_network():
    """API endpoint to get visualization data for the network"""
    try:
        # Check if network file exists
        inp_file = OUTPUT_DATA_DIR / "madison_network.inp"
        if not inp_file.exists():
            return jsonify({
                'status': 'error',
                'message': 'Network model file not found'
            }), 400
        
        # Get network visualization data
        vis_data = visualizer.get_network_geojson(inp_file)
        
        if vis_data is None:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate visualization data'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': vis_data
        })
    
    except Exception as e:
        logger.error(f"Error in visualization: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/visualization-results', methods=['GET'])
def visualization_results():
    """API endpoint to get simulation results for visualization"""
    try:
        # Check if simulation results exist
        results_file = OUTPUT_DATA_DIR / "simulation_results.json"
        if not results_file.exists():
            return jsonify({
                'status': 'error',
                'message': 'Simulation results not found'
            }), 400
        
        # Load results from file
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        return jsonify({
            'status': 'success',
            'data': results
        })
    
    except Exception as e:
        logger.error(f"Error loading simulation results: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/data/<path:filename>')
def serve_data(filename):
    """Serve data files"""
    # Determine which directory to serve from based on the filename
    if filename.startswith('raw/'):
        return send_from_directory('data', filename)
    elif filename.startswith('processed/'):
        return send_from_directory('data', filename)
    elif filename.startswith('output/'):
        return send_from_directory('data', filename)
    else:
        return jsonify({
            'status': 'error',
            'message': 'Invalid file path'
        }), 400

@app.route('/scenarios', methods=['GET'])
def list_scenarios():
    """List available simulation scenarios"""
    try:
        # Get list of scenario files
        scenario_files = list(Path('scenarios').glob('*.json')) if Path('scenarios').exists() else []
        
        scenarios = []
        for file in scenario_files:
            with open(file, 'r') as f:
                scenario = json.load(f)
                scenarios.append({
                    'id': file.stem,
                    'name': scenario.get('name', file.stem),
                    'description': scenario.get('description', '')
                })
        
        return jsonify({
            'status': 'success',
            'scenarios': scenarios
        })
    
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/scenarios/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """Get a specific simulation scenario"""
    try:
        scenario_file = Path(f'scenarios/{scenario_id}.json')
        
        if not scenario_file.exists():
            return jsonify({
                'status': 'error',
                'message': f'Scenario {scenario_id} not found'
            }), 404
        
        with open(scenario_file, 'r') as f:
            scenario = json.load(f)
        
        return jsonify({
            'status': 'success',
            'scenario': scenario
        })
    
    except Exception as e:
        logger.error(f"Error getting scenario: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/scenarios', methods=['POST'])
def create_scenario():
    """Create a new simulation scenario"""
    try:
        # Get scenario data from request
        scenario = request.get_json()
        
        if not scenario:
            return jsonify({
                'status': 'error',
                'message': 'No scenario data provided'
            }), 400
        
        # Create scenarios directory if it doesn't exist
        scenarios_dir = Path('scenarios')
        scenarios_dir.mkdir(exist_ok=True)
        
        # Generate a unique ID for the scenario
        import uuid
        scenario_id = str(uuid.uuid4())[:8]
        
        # Add metadata
        if 'name' not in scenario:
            scenario['name'] = f'Scenario {scenario_id}'
        
        if 'created_at' not in scenario:
            from datetime import datetime
            scenario['created_at'] = datetime.now().isoformat()
        
        # Save scenario to file
        scenario_file = scenarios_dir / f'{scenario_id}.json'
        with open(scenario_file, 'w') as f:
            json.dump(scenario, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'message': 'Scenario created successfully',
            'scenario_id': scenario_id
        })
    
    except Exception as e:
        logger.error(f"Error creating scenario: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a file"""
    try:
        # Determine which directory to serve from based on the filename
        if filename.startswith('raw/'):
            return send_from_directory('data', filename, as_attachment=True)
        elif filename.startswith('processed/'):
            return send_from_directory('data', filename, as_attachment=True)
        elif filename.startswith('output/'):
            return send_from_directory('data', filename, as_attachment=True)
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid file path'
            }), 400
    
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

"""
Fixed version of the API status endpoint for app.py
"""

@app.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint to check application status"""
    try:
        # Check if EPANET executable exists
        epanet_installed = False
        try:
            from src.epanet_util import EPANET_PATH
            epanet_installed = EPANET_PATH.exists()
        except:
            pass

        # Use file existence to determine status
        status = {
            'application': 'HydroFlow',
            'status': 'running',
            'data_collected': any(RAW_DATA_DIR.iterdir()) if RAW_DATA_DIR.exists() else False,
            'data_processed': any(PROCESSED_DATA_DIR.iterdir()) if PROCESSED_DATA_DIR.exists() else False,
            'network_built': (OUTPUT_DATA_DIR / "madison_network.inp").exists(),
            'simulation_run': (OUTPUT_DATA_DIR / "simulation_results.json").exists() or current_simulation is not None,
            'epanet_installed': epanet_installed,
            'hydraulic_engine': 'EPANET CLI' if epanet_installed else 'Built-in Simplified Model'
        }
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error checking application status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500
        
if __name__ == '__main__':
    # Run the Flask application in debug mode
    app.run(debug=True, host='0.0.0.0', port=5000)