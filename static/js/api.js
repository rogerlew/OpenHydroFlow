/**
 * API client for HydroFlow - Water Distribution Modeling
 */

const api = {
  /**
   * Check for existing data files
   */
  checkExistingData: async function () {
    // Simulate API call to check existing data
    // In a real application, this would check for files on the server
    try {
      const response = await fetch("/api/check-data", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      // For demo purposes, check for files directly
      const hasRawData = await this._checkFileExists(
        "/data/raw/madison_water_mains.geojson"
      );
      const hasProcessedData = await this._checkFileExists(
        "/data/processed/processed_water_mains.geojson"
      );
      const hasNetworkModel = await this._checkFileExists(
        "/data/output/madison_network.inp"
      );
      const hasSimulationResults = await this._checkFileExists(
        "/data/output/simulation_results.json"
      );

      return {
        hasRawData,
        hasProcessedData,
        hasNetworkModel,
        hasSimulationResults,
      };
    }
  },

  /**
   * Helper method to check if a file exists
   */
  _checkFileExists: async function (url) {
    try {
      const response = await fetch(url, {
        method: "HEAD",
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  },

  /**
   * Collect water distribution data
   */
  collectData: async function () {
    try {
      const response = await fetch("/collect-data", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error collecting data:", error);
      throw error;
    }
  },

  /**
   * Process collected data
   */
  processData: async function (options = {}) {
    try {
      const response = await fetch("/process-data", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(options),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error processing data:", error);
      throw error;
    }
  },

  /**
   * Build EPANET network model
   */
  buildNetwork: async function (options = {}) {
    try {
      const response = await fetch("/build-network", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(options),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error building network:", error);
      throw error;
    }
  },

  /**
   * Run EPANET hydraulic simulation
   */
  runSimulation: async function (options = {}) {
    try {
      const response = await fetch("/run-simulation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(options),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error running simulation:", error);
      throw error;
    }
  },

  /**
   * Get network visualization data
   */
  getNetworkData: async function () {
    try {
      const response = await fetch("/visualize-network", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error getting network data:", error);
      throw error;
    }
  },

  /**
   * Get simulation results
   */
  getSimulationResults: async function () {
    try {
      const response = await fetch("/visualization-results", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error getting simulation results:", error);
      throw error;
    }
  },

  /**
   * List available scenarios
   */
  listScenarios: async function () {
    try {
      const response = await fetch("/scenarios", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error listing scenarios:", error);
      throw error;
    }
  },

  /**
   * Get a specific scenario
   */
  getScenario: async function (scenarioId) {
    try {
      const response = await fetch(`/scenarios/${scenarioId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error getting scenario:", error);
      throw error;
    }
  },

  /**
   * Create a new scenario
   */
  createScenario: async function (scenarioData) {
    try {
      const response = await fetch("/scenarios", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(scenarioData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error creating scenario:", error);
      throw error;
    }
  },

  /**
   * Download a file
   */
  downloadFile: function (filename) {
    window.location.href = `/download/${filename}`;
  },
};
