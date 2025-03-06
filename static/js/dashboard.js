// Update charts every 30 seconds
const UPDATE_INTERVAL = 30000;

// Initialize charts
let realtimeChart = null;
let predictionChart = null;

// Format timestamp to readable date
function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleString();
}

// Create real-time temperature chart
function createRealtimeChart(data) {
    const traces = [];
    const buildings = {};
    
    // Group data by building
    data.forEach(item => {
        if (!buildings[item.building_id]) {
            buildings[item.building_id] = {
                x: [],
                y: [],
                name: `Building ${item.building_id} (${item.room_count} rooms)`,
                type: 'scatter'
            };
        }
        buildings[item.building_id].x.push(formatDate(item.timestamp));
        buildings[item.building_id].y.push(item.temperature);
    });
    
    // Create traces for each building
    for (const building in buildings) {
        traces.push(buildings[building]);
    }
    
    const layout = {
        title: 'Real-time Temperature Data',
        xaxis: { title: 'Time' },
        yaxis: { title: 'Temperature (°C)' }
    };
    
    Plotly.newPlot('realtime-chart', traces, layout);
}

// Create prediction chart
function createPredictionChart(data) {
    const traces = data.map(building => ({
        x: building.predictions.map(p => formatDate(p.timestamp)),
        y: building.predictions.map(p => p.temperature),
        name: building.building_type,
        type: 'scatter'
    }));
    
    const layout = {
        title: '24-Hour Temperature Predictions',
        xaxis: { title: 'Time' },
        yaxis: { title: 'Predicted Temperature (°C)' }
    };
    
    Plotly.newPlot('prediction-chart', traces, layout);
}

// Fetch and update real-time data
async function updateRealtimeData() {
    try {
        const response = await fetch('/api/sensor-data');
        const data = await response.json();
        createRealtimeChart(data);
    } catch (error) {
        console.error('Error fetching real-time data:', error);
    }
}

// Fetch and update prediction data
async function updatePredictions() {
    try {
        const response = await fetch('/api/ml-predictions');
        const data = await response.json();
        createPredictionChart(data);
    } catch (error) {
        console.error('Error fetching predictions:', error);
    }
}

// Initialize dashboard
function initDashboard() {
    updateRealtimeData();
    updatePredictions();
    
    // Set up periodic updates
    setInterval(() => {
        updateRealtimeData();
        updatePredictions();
    }, UPDATE_INTERVAL);
}

// Start dashboard when page loads
document.addEventListener('DOMContentLoaded', initDashboard);
