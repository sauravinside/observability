let currentStep = 1;
const totalSteps = 4;
let selectedResources = [];
let selectedMetrics = [];
let availableMetrics = [];

document.addEventListener('DOMContentLoaded', async () => {
    try {
        await Promise.all([
            fetchServices(),
            fetchRegions()
        ]);
        setupEventListeners();
    } catch (error) {
        showError('Failed to initialize application: ' + error.message);
    }
});

const BACKEND_URL = window.location.origin.includes("localhost")
    ? "http://127.0.0.1:5000"
    : window.location.origin; // Automatically detect server IP

function setupEventListeners() {
    document.getElementById('service').addEventListener('change', handleServiceChange);
    document.getElementById('region').addEventListener('change', handleRegionChange);
    document.getElementById('enableAlerts').addEventListener('change', handleAlertsToggle);
    document.getElementById('prevBtn').addEventListener('click', prevStep);
    document.getElementById('nextBtn').addEventListener('click', nextStep);
    document.getElementById('submitBtn').addEventListener('click', submitConfiguration);
}

async function fetchServices() {
    const response = await fetch(`${BACKEND_URL}/api/services`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const services = await response.json();
    populateSelect('service', services);
}

async function fetchRegions() {
    const response = await fetch(`${BACKEND_URL}/api/regions`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const regions = await response.json();
    populateSelect('region', regions);
}

function populateSelect(elementId, items) {
    const select = document.getElementById(elementId);
    select.innerHTML = `<option value="">Select ${elementId.charAt(0).toUpperCase() + elementId.slice(1)}</option>`;
    items.forEach(item => {
        const option = document.createElement('option');
        option.value = item;
        option.textContent = item;
        select.appendChild(option);
    });
}

async function handleServiceChange() {
    const service = document.getElementById('service').value;
    if (!service) return;

    try {
        const response = await fetch(`/api/metrics/${service}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        availableMetrics = await response.json();
        updateMetricsGrid();
    } catch (error) {
        showError('Failed to fetch metrics: ' + error.message);
    }
}

async function handleRegionChange() {
    const service = document.getElementById('service').value;
    const region = document.getElementById('region').value;
    if (!service || !region) return;

    try {
        const response = await fetch(`/api/resources/${service}/${region}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const resources = await response.json();
        updateResourceList(resources);
    } catch (error) {
        showError('Failed to fetch resources: ' + error.message);
    }
}

function updateMetricsGrid() {
    const metricsGrid = document.getElementById('metricsGrid');
    metricsGrid.innerHTML = '';
    
    availableMetrics.forEach(metric => {
        const div = document.createElement('div');
        div.className = 'metric-item';
        div.innerHTML = `
            <input type="checkbox" id="${metric.name}" name="metrics" value="${metric.name}"
                   ${selectedMetrics.some(m => m.name === metric.name) ? 'checked' : ''}>
            <label for="${metric.name}">${metric.name}</label>
        `;
        div.querySelector('input').addEventListener('change', (e) => handleMetricSelection(e, metric));
        metricsGrid.appendChild(div);
    });
}

function handleMetricSelection(event, metric) {
    if (event.target.checked) {
        selectedMetrics.push({
            name: metric.name,
            namespace: metric.namespace
        });
    } else {
        selectedMetrics = selectedMetrics.filter(m => m.name !== metric.name);
    }
    updateNavigationButtons();
}

function updateResourceList(resources) {
    const resourceList = document.getElementById('resourceList');
    resourceList.innerHTML = '';
    
    resources.forEach(resource => {
        const div = document.createElement('div');
        div.className = 'resource-item';
        div.innerHTML = `
            <input type="checkbox" id="${resource.Id}" value="${resource.Id}"
                   ${selectedResources.includes(resource.Id) ? 'checked' : ''}>
            <label for="${resource.Id}">
                ${resource.Name}
                <span class="resource-info">${resource.Id} - ${resource.Type}</span>
            </label>
        `;
        div.querySelector('input').addEventListener('change', (e) => handleResourceSelection(e, resource.Id));
        resourceList.appendChild(div);
    });
}

function handleResourceSelection(event, resourceId) {
    if (event.target.checked) {
        selectedResources.push(resourceId);
    } else {
        selectedResources = selectedResources.filter(id => id !== resourceId);
    }
    updateNavigationButtons();
}

function handleAlertsToggle(event) {
    const thresholdsDiv = document.getElementById('thresholds');
    thresholdsDiv.style.display = event.target.checked ? 'block' : 'none';
    if (event.target.checked) updateThresholdsDisplay();
}

function updateThresholdsDisplay() {
    const thresholdsDiv = document.getElementById('thresholds');
    thresholdsDiv.innerHTML = '';

    selectedMetrics.forEach(metric => {
        const container = document.createElement('div');
        container.className = 'slider-container';
        container.innerHTML = `
            <label>${metric.name} Warning Threshold (%)</label>
            <input type="range" min="0" max="100" value="60" class="threshold-slider warning-slider" data-metric="${metric.name}" data-type="warning">
            <span class="threshold-value">60%</span>

            <label>${metric.name} Critical Threshold (%)</label>
            <input type="range" min="0" max="100" value="80" class="threshold-slider critical-slider" data-metric="${metric.name}" data-type="critical">
            <span class="threshold-value">80%</span>
        `;

        thresholdsDiv.appendChild(container);
    });
}



function nextStep() {
    if (validateCurrentStep()) {
        document.getElementById(`step${currentStep}`).style.display = 'none';
        currentStep++;
        document.getElementById(`step${currentStep}`).style.display = 'block';
        updateNavigationButtons();
    }
}

function prevStep() {
    document.getElementById(`step${currentStep}`).style.display = 'none';
    currentStep--;
    document.getElementById(`step${currentStep}`).style.display = 'block';
    updateNavigationButtons();
}

function updateNavigationButtons() {
    document.getElementById('prevBtn').style.display = currentStep > 1 ? 'block' : 'none';
    document.getElementById('nextBtn').style.display = currentStep < totalSteps ? 'block' : 'none';
    document.getElementById('submitBtn').style.display = currentStep === totalSteps ? 'block' : 'none';
}

function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            return document.getElementById('service').value && 
                   document.getElementById('region').value;
        case 2:
            return selectedResources.length > 0;
        case 3:
            return selectedMetrics.length > 0;
        default:
            return true;
    }
}

async function submitConfiguration() {
    const config = {
        service: document.getElementById('service').value,
        region: document.getElementById('region').value,
        resources: selectedResources.length > 0 ? selectedResources : ["placeholder-resource"],
        alerts: document.getElementById('enableAlerts').checked,
        metrics: [],  // ✅ Ensure metrics is always included
        thresholds: {}
    };

    selectedMetrics.forEach(metric => {
        config.metrics.push({ name: metric.name, namespace: metric.namespace });

        if (config.alerts) {
            const warningSlider = document.querySelector(`input[data-metric='${metric.name}'][data-type='warning']`);
            const criticalSlider = document.querySelector(`input[data-metric='${metric.name}'][data-type='critical']`);
            config.thresholds[metric.name] = {
                warning: warningSlider ? warningSlider.value : "0",
                critical: criticalSlider ? criticalSlider.value : "0"
            };
        } else {
            config.thresholds[metric.name] = { warning: "0", critical: "0" };
        }
    });

    console.log("Sending request:", JSON.stringify(config, null, 2)); // Debugging Log

    try {
        const response = await fetch('/api/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) {
            const errorMessage = await response.text();
            console.error("Error Response:", errorMessage);
            throw new Error(errorMessage);
        }

        showSuccess(await response.json());
    } catch (error) {
        console.error("Error:", error.message);
        showError('Failed to configure monitoring: ' + error.message);
    }
}

function showError(message) {
    alert(`Error: ${message}`);
}

function showSuccess(result) {
    alert(`Monitoring successfully configured: ${JSON.stringify(result)}`);
}


function closeModal() {
    document.getElementById('resultModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('resultModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};