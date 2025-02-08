let currentStep = 1;
const totalSteps = 4;
let selectedInstances = [];
let selectedMetrics = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    fetchRegions();
    setupEventListeners();
});

function setupEventListeners() {
    // Region change listener
    document.getElementById('region').addEventListener('change', handleRegionChange);
    
    // Metrics change listener
    document.querySelectorAll('input[name="metrics"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleMetricsChange);
    });
    
    // Alerts toggle listener
    document.getElementById('enableAlerts').addEventListener('change', handleAlertsToggle);
    
    // Modal close button
    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('resultModal').style.display = 'none';
    });
}

// Fetch available AWS regions
async function fetchRegions() {
    try {
        const response = await fetch('/api/regions');
        
        // Check if response is successful
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch regions');
        }

        const regions = await response.json();
        
        // Add validation for array type
        if (!Array.isArray(regions)) {
            throw new Error('Invalid regions data received');
        }

        const regionSelect = document.getElementById('region');
        regionSelect.innerHTML = '<option value="">Select AWS Region</option>';
        
        regions.forEach(region => {
            const option = document.createElement('option');
            option.value = region;
            option.textContent = region;
            regionSelect.appendChild(option);
        });
    } catch (error) {
        showError('Failed to fetch regions: ' + error.message);
    }
}

// Handle region selection change
async function handleRegionChange(event) {
    const region = event.target.value;
    if (!region) return;

    try {
        const response = await fetch(`/api/instances/${region}`);
        const instances = await response.json();
        
        const instanceList = document.getElementById('instanceList');
        instanceList.innerHTML = '';
        
        instances.forEach(instance => {
            const div = document.createElement('div');
            div.className = 'instance-item';
            div.innerHTML = `
                <input type="checkbox" id="${instance.InstanceId}" value="${instance.InstanceId}">
                <label for="${instance.InstanceId}">
                    ${instance.Name || 'Unnamed'} (${instance.InstanceId})
                    <span class="instance-type">${instance.Type}</span>
                </label>
            `;
            instanceList.appendChild(div);
        });

        // Add instance selection listeners
        instanceList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    selectedInstances.push(checkbox.value);
                } else {
                    selectedInstances = selectedInstances.filter(id => id !== checkbox.value);
                }
                updateNavigationButtons();
            });
        });
    } catch (error) {
        showError('Failed to fetch instances: ' + error.message);
    }
}

// Handle metrics selection change
function handleMetricsChange(event) {
    if (event.target.checked) {
        selectedMetrics.push(event.target.value);
    } else {
        selectedMetrics = selectedMetrics.filter(metric => metric !== event.target.value);
    }
    updateNavigationButtons();
}

// Handle alerts toggle
function handleAlertsToggle(event) {
    const thresholdsDiv = document.getElementById('thresholds');
    thresholdsDiv.style.display = event.target.checked ? 'block' : 'none';
    
    if (event.target.checked) {
        thresholdsDiv.innerHTML = '';
        selectedMetrics.forEach(metric => {
            const container = document.createElement('div');
            container.className = 'slider-container';
            container.innerHTML = `
                <label for="${metric}-threshold">${metric} Threshold (%)</label>
                <input type="range" id="${metric}-threshold" 
                       min="0" max="100" value="80" 
                       class="threshold-slider">
                <span class="threshold-value">80%</span>
            `;
            thresholdsDiv.appendChild(container);

            // Add slider value update listener
            const slider = container.querySelector('input[type="range"]');
            const valueDisplay = container.querySelector('.threshold-value');
            slider.addEventListener('input', () => {
                valueDisplay.textContent = `${slider.value}%`;
            });
        });
    }
}

// Navigation functions
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
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    prevBtn.style.display = currentStep > 1 ? 'block' : 'none';
    nextBtn.style.display = currentStep < totalSteps ? 'block' : 'none';
    submitBtn.style.display = currentStep === totalSteps ? 'block' : 'none';
}

// Validate current step
function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            return document.getElementById('region').value !== '';
        case 2:
            return selectedInstances.length > 0;
        case 3:
            return selectedMetrics.length > 0;
        default:
            return true;
    }
}

// Submit configuration
async function submitConfiguration() {
    const region = document.getElementById('region').value;
    const enableAlerts = document.getElementById('enableAlerts').checked;
    
    const thresholds = {};
    if (enableAlerts) {
        selectedMetrics.forEach(metric => {
            const threshold = document.getElementById(`${metric}-threshold`).value;
            thresholds[metric] = threshold;
        });
    }

    const config = {
        region: region,
        instanceIds: selectedInstances,
        metrics: selectedMetrics,
        alerts: enableAlerts,
        thresholds: thresholds
    };

    try {
        const response = await fetch('/api/configure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        
        if (result.error) {
            showError(result.error);
        } else {
            showSuccess(result);
        }
    } catch (error) {
        showError('Failed to submit configuration: ' + error.message);
    }
}

// Show error message
function showError(message) {
    const modal = document.getElementById('resultModal');
    const content = document.getElementById('modalContent');
    content.innerHTML = `<div class="error-message">${message}</div>`;
    modal.style.display = 'block';
}

// Show success message
function showSuccess(result) {
    const modal = document.getElementById('resultModal');
    const content = document.getElementById('modalContent');
    content.innerHTML = `
        <div class="success-message">
            <p>Monitoring configuration completed successfully!</p>
            <p>Dashboard Name: ${result.dashboardName}</p>
            <p>SNS Topic ARN: ${result.snsTopicArn}</p>
            <p><strong>Important:</strong> Please add subscribers to the SNS topic "${result.topicName}" to receive alerts.</p>
            <p><a href="${result.dashboardUrl}" target="_blank">View Dashboard</a></p>
        </div>
    `;
    modal.style.display = 'block';
}

// Window click handler for modal
window.onclick = function(event) {
    const modal = document.getElementById('resultModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}