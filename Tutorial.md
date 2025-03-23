# HydroFlow: Water Distribution Modeling Tutorial

I'll walk you through how HydroFlow works for water distribution modeling using EPANET principles. This tutorial will focus on the hydraulic modeling aspects rather than software development.

## Project Overview

HydroFlow is a water distribution modeling application that simulates how water flows through a municipal pipe network. It models pipes, junctions, tanks, reservoirs, and other components to predict pressure, flow rates, and water quality throughout a system.

## Core Workflow

### 1. Data Collection

The first phase involves gathering all the necessary data to build an accurate water distribution model:

- **GIS Data**: The application collects geographic information system (GIS) data for Madison, WI's water infrastructure from their open data portal, including:

  - Water mains (pipes)
  - Fire hydrants
  - Pressure zones

- **Elevation Data**: Elevation data is crucial for accurate hydraulic modeling since water pressure is affected by height. The app fetches this from the USGS National Map API.

- **Water Quality Data**: Information about water quality from EPA's Safe Drinking Water Information System.

- **USGS Water Data**: Real-world flow measurements from the USGS National Water Information System help calibrate the model.

### 2. Data Processing

Raw data needs preprocessing to be useful for hydraulic modeling:

- **Pipe Cleaning**: Extracts key properties like:

  - Diameter (mm)
  - Length (m)
  - Material type (cast iron, PVC, etc.)
  - Age/installation year
  - Hazen-Williams roughness coefficient (calculated based on material and age)

- **Junction Creation**: Identifies where pipes connect and creates network junctions.

- **Elevation Assignment**: Assigns elevation values to each junction.

- **Demand Allocation**: Assigns water demand values to junctions based on their location in the network.

### 3. Network Modeling

This phase builds the water distribution network model:

- **Graph Creation**: Builds a mathematical graph where:

  - Nodes represent junctions, tanks, and reservoirs
  - Edges represent pipes, valves, and pumps

- **Component Definition**:

  - **Junctions**: Connection points with elevation and demand properties
  - **Pipes**: Links with diameter, length, and roughness properties
  - **Reservoirs**: Water sources with constant head (pressure)
  - **Tanks**: Storage with variable volume
  - **Pumps/Valves**: Special links that add energy or control flow

- **INP File Generation**: Creates an EPANET-compatible INP file with all network components, including:
  - [JUNCTIONS] section with elevation and demand data
  - [PIPES] section with connectivity, diameter, length, and roughness
  - [RESERVOIRS] and [TANKS] sections for water sources and storage
  - [OPTIONS] section with calculation parameters
  - [TIMES] section for simulation duration and time steps

### 4. Hydraulic Simulation

The heart of the system - simulating water flow through the network:

- **Simulation Methods**:

  1. **EPANET Command-line Tool**: For accurate results, the app can download and use the actual EPANET engine
  2. **Built-in Simulator**: A simplified calculator that applies hydraulic principles directly

- **Key Calculations**:

  - **Mass Conservation**: Ensuring the flow into each junction equals the flow out
  - **Energy Conservation**: Computing head (energy) loss in closed loops
  - **Headloss Formula**: Using Hazen-Williams formula to calculate friction losses:
    ```
    h = 10.67 * L * (Q^1.85) / (C^1.85 * D^4.87)
    ```
    Where:
    - h = head loss (m)
    - L = pipe length (m)
    - Q = flow rate (m³/s)
    - C = roughness coefficient
    - D = pipe diameter (m)

- **Time-stepping**: The simulation runs over a specified period (typically 24 hours) with hourly time steps to capture daily patterns.

- **Demand Patterns**: Water usage varies throughout the day, so demand multipliers are applied to base demands:
  ```
  Actual Demand = Base Demand × Pattern Multiplier
  ```

### 5. Results Analysis

After simulation, the system processes the results:

- **Key Parameters**:

  - **Pressure**: At each junction (m or psi)
  - **Flow**: In each pipe (m³/s)
  - **Velocity**: Speed of water in pipes (m/s)
  - **Head**: Total energy (m)
  - **Headloss**: Energy loss in pipes (m/km)

- **Time Series Data**: Results for each parameter at each time step, enabling analysis of how the network behaves over time.

- **Statistics**: Calculated minimum, maximum, and average values for pressure, flow, and velocity.

### 6. Visualization

The final phase presents results to users:

- **Network Map**: Interactive map showing all components color-coded by:

  - Pressure at junctions
  - Flow rate in pipes
  - Velocity in pipes

- **Time Series Charts**: Graphs showing how parameters change over time

- **Statistics Charts**: Distributions of pipe diameters, lengths, and junction elevations

## Technical Implementation Details

The hydraulic modeling happens in two main files:

1. **network_model.py**: Builds the water distribution network:

   - Creates a graph representation using NetworkX
   - Computes network connectivity
   - Assigns properties to components
   - Generates the EPANET INP file

2. **simulation.py**: Runs the hydraulic analysis:
   - Parses the INP file
   - Runs EPANET if available
   - Applies hydraulic equations directly if EPANET isn't available
   - Processes and returns results

## In Practice: Example Flow

Let's walk through a practical example of what happens in the model:

1. A junction has a demand of 0.1 m³/s (i.e., 100 liters per second are being consumed)

2. Water flowing through a pipe to this junction experiences head loss according to the Hazen-Williams formula:

   - 200mm diameter pipe
   - 100m length
   - Roughness coefficient of 120 (typical for good condition pipes)
   - Flow rate matching the demand (0.1 m³/s)

   Resulting in a head loss of approximately:

   ```
   h = 10.67 × 100 × (0.1^1.85) / (120^1.85 × 0.2^4.87) ≈ 5.2m
   ```

3. This head loss means the pressure at the junction will be 5.2m less than at the source (plus/minus elevation differences)

4. The simulator balances all these equations simultaneously across the network, finding a solution where:

   - All junction demands are met
   - Mass is conserved at all junctions
   - Energy (head) loss around any loop sums to zero

5. Results show that during peak demand (e.g., 7-9 AM), pressure might drop to 40m in this area, while during low demand (e.g., 2 AM), it might rise to 55m.

This is how HydroFlow provides insights into water distribution systems without requiring the original WNTR library, while still maintaining the essential principles of hydraulic network modeling.
