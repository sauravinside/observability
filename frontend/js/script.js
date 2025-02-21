let currentStep = 1;
const totalSteps = 4;
let selectedResources = [];
let selectedMetrics = [];
let availableMetrics = [];
let selectedKeys = {};

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

function setupEventListeners() {
    document.getElementById('service').addEventListener('change', handleServiceChange);
    document.getElementById('region').addEventListener('change', handleRegionChange);
    document.getElementById('enableAlerts').addEventListener('change', handleAlertsToggle);
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('prevBtn').addEventListener('click', prevStep);
    document.getElementById('nextBtn').addEventListener('click', nextStep);
    document.getElementById('submitBtn').addEventListener('click', submitConfiguration);
}

async function fetchServices() {
    const response = await fetch('/api/services');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    const services = await response.json();
    populateSelect('service', services);
}

async function fetchRegions() {
    const response = await fetch('/api/regions');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
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
                   ${selectedResources.find(r => r.Id === resource.Id) ? 'checked' : ''}>
            <label for="${resource.Id}">
                ${resource.Name}
                <span class="resource-info">${resource.Id} - ${resource.Type}</span>
                <span class="resource-ips">
                    Public: ${resource.PublicIpAddress ? resource.PublicIpAddress : 'N/A'} | 
                    Private: ${resource.PrivateIpAddress ? resource.PrivateIpAddress : 'N/A'}
                </span>
            </label>
            <input type="file" id="key-${resource.Id}" class="key-upload" style="display:none;" accept=".pem">
        `;
        // Pass the entire resource object to the handler
        div.querySelector('input[type="checkbox"]').addEventListener('change', (e) => handleResourceSelection(e, resource));
        
        // Listen for key file uploads
        div.querySelector('.key-upload').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                selectedKeys[resource.Id] = file;
            } else {
                delete selectedKeys[resource.Id];
            }
        });
        resourceList.appendChild(div);
    });
}

function handleResourceSelection(event, resource) {
    const keyInput = document.getElementById(`key-${resource.Id}`);
    if (event.target.checked) {
        // Check if the resource is already in selectedResources based on its Id
        if (!selectedResources.find(r => r.Id === resource.Id)) {
            selectedResources.push(resource);
        }
        // Show the file upload for the key
        keyInput.style.display = 'inline-block';
    } else {
        selectedResources = selectedResources.filter(r => r.Id !== resource.Id);
        // Hide the file upload and clear its value
        keyInput.style.display = 'none';
        keyInput.value = "";
        delete selectedKeys[resource.Id];
    }
    updateNavigationButtons();
}

function handleAlertsToggle(event) {
    const thresholdsDiv = document.getElementById('thresholds');
    thresholdsDiv.style.display = event.target.checked ? 'block' : 'none';
    
    if (event.target.checked) {
        updateThresholdsDisplay();
    }
}

function updateThresholdsDisplay() {
    const thresholdsDiv = document.getElementById('thresholds');
    thresholdsDiv.innerHTML = '';
    
    selectedMetrics.forEach(metric => {
        const container = document.createElement('div');
        container.className = 'metric-threshold-container';
        container.innerHTML = `
            <h4 class="metric-name">${metric.name}</h4>
            <div class="slider-container warning">
                <label for="${metric.name}-warning">Warning Threshold (%)</label>
                <input type="range" id="${metric.name}-warning" 
                       min="0" max="100" value="70" 
                       class="threshold-slider warning-slider">
                <span class="threshold-value warning-value">70%</span>
            </div>
            <div class="slider-container critical">
                <label for="${metric.name}-critical">Critical Threshold (%)</label>
                <input type="range" id="${metric.name}-critical" 
                       min="0" max="100" value="90" 
                       class="threshold-slider critical-slider">
                <span class="threshold-value critical-value">90%</span>
            </div>
        `;
        
        // Add event listeners for both sliders
        const warningSlider = container.querySelector('.warning-slider');
        const criticalSlider = container.querySelector('.critical-slider');
        const warningValue = container.querySelector('.warning-value');
        const criticalValue = container.querySelector('.critical-value');
        
        warningSlider.addEventListener('input', () => {
            const warning = parseInt(warningSlider.value);
            const critical = parseInt(criticalSlider.value);
            if (warning >= critical) {
                warningSlider.value = critical - 1;
                warningValue.textContent = `${critical - 1}%`;
            } else {
                warningValue.textContent = `${warning}%`;
            }
        });
        
        criticalSlider.addEventListener('input', () => {
            const warning = parseInt(warningSlider.value);
            const critical = parseInt(criticalSlider.value);
            if (critical <= warning) {
                criticalSlider.value = warning + 1;
                criticalValue.textContent = `${warning + 1}%`;
            } else {
                criticalValue.textContent = `${critical}%`;
            }
        });
        
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
    // Build the configuration object (without keys for now)
    const config = {
        service: document.getElementById('service').value,
        region: document.getElementById('region').value,
        resources: selectedResources,
        metrics: selectedMetrics,
        alerts: document.getElementById('enableAlerts').checked,
        thresholds: {},
        keys: {}
    };

    if (config.alerts) {
        selectedMetrics.forEach(metric => {
            config.thresholds[metric.name] = {
                warning: document.getElementById(`${metric.name}-warning`).value,
                critical: document.getElementById(`${metric.name}-critical`).value
            };
        });
    }

    // Create a FormData object so we can include both JSON and file data.
    const formData = new FormData();
    // Append the configuration as a JSON string.
    formData.append('config', JSON.stringify(config));

    // Append each uploaded key file using a field name that includes the resource ID.
    selectedResources.forEach(resource => {
        if (selectedKeys[resource.Id]) {
            formData.append(`key_${resource.Id}`, selectedKeys[resource.Id]);
        }
    });

    try {
        const response = await fetch('/api/configure', {
            method: 'POST',
            // Do not set the Content-Type header manually when using FormData.
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to configure monitoring');
        }

        const result = await response.json();
        showSuccess(result);
    } catch (error) {
        showError('Failed to configure monitoring: ' + error.message);
    }
}

function showError(message) {
    const modal = document.getElementById('resultModal');
    const content = document.getElementById('modalContent');
    content.innerHTML = `<div class="error-message">${message}</div>`;
    modal.style.display = 'block';
}

function showSuccess(result) {
    const modal = document.getElementById('resultModal');
    const content = document.getElementById('modalContent');
    content.innerHTML = `
        <div class="success-message">
            <h3>Monitoring configuration completed successfully!</h3>
            <p><strong>Dashboard Name:</strong> ${result.dashboardName}</p>
            <p><strong>SNS Topic ARN:</strong> ${result.snsTopicArn}</p>
            <p><strong>Important:</strong> Please add subscribers to the SNS topic "${result.topicName}" to receive alerts.</p>
            <div class="dashboard-link">
                <a href="${result.dashboardUrl}" target="_blank" class="btn">View Dashboard</a>
            </div>
        </div>
    `;
    modal.style.display = 'block';
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