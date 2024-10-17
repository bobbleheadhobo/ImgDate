
// Global variables
let downloadUrl = '';
let uploadedImagesCount = 0;
let wakeLock = null;
let progressIntervalId = null;
let batchId = null;
let pollTimeoutId = null;
let pollInterval = 1000;
const maxPollInterval = 30000; // Maximum interval of 30 seconds
let isPolling = false;
let retryCount = 0;
const maxRetries = 5;

// DOM elements
const uploadForm = document.getElementById('uploadForm');
const processButton = document.getElementById('processButton');
const downloadButton = document.getElementById('downloadButton');
const startOverButton = document.getElementById('startOver');
const progressContainer = document.getElementById('progressContainer');
const fileInput = document.getElementById('fileInput');
const checkboxes = document.querySelectorAll('input[type="checkbox"]');
const dateRange = document.getElementById('dateRange');
const infoButton = document.getElementById('infoButton');

// Initialize Flatpickr date range picker
flatpickr(dateRange, {
    mode: "range",
    dateFormat: "m/d/Y",
    defaultDate: ["", ""]
});

// Event listeners
document.addEventListener('DOMContentLoaded', initializeApp);
uploadForm.addEventListener('submit', handleFormSubmit);
downloadButton.addEventListener('click', handleDownload);
startOverButton.addEventListener('click', () => location.reload());
document.getElementById('cropImages').addEventListener('change', handleCropImagesChange);
document.getElementById('dateOptionsBtn').addEventListener('click', toggleDateOptionsBox);

// Wake Lock API
async function requestWakeLock() {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
    } catch (err) {
        console.error(`Wake Lock error: ${err.name}, ${err.message}`);
    }
}

async function releaseWakeLock() {
    if (wakeLock) {
        try {
            await wakeLock.release();
            wakeLock = null;
        } catch (err) {
            console.error(`Wake Lock release error: ${err.name}, ${err.message}`);
        }
    }
}

// Loading animation
let loadingInterval;
function startLoadingAnimation(text) {
    let dots = 0;
    loadingInterval = setInterval(() => {
        dots = (dots + 1) % 4;
        processButton.textContent = text + '.'.repeat(dots);
    }, 500);
}

function stopLoadingAnimation(text) {
    clearInterval(loadingInterval);
    processButton.textContent = text;
}

// Form submission
async function handleFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(this);
    formData.append('date_range', dateRange.value);

    disableForm();
    startLoadingAnimation("Verifying");
    await requestWakeLock();

    try {
        // First, verify the Turnstile
        await verifyTurnstile(formData);
        stopLoadingAnimation("Uploading");
        startLoadingAnimation("Uploading");;

        // If verification succeeds, start the upload
        await startUpload(formData);
        stopLoadingAnimation("Processing");
        startLoadingAnimation("Processing");


        // Start polling for progress
        startStatusPolling();

    } catch (error) {
        handleError(error);
    }
}

async function verifyTurnstile(formData) {
    const response = await fetch('/verify-turnstile', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        if (response.status === 403) {
            throw new Error('Human verification failed. Please reload and try again.');
        }
        throw new Error(`Turnstile verification failed: ${response.status}`);
    }
}

async function startUpload(formData) {
    const response = await fetch('/start-upload', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error(`Upload start failed: ${response.status}`);
    }

    const data = await response.json();
    if (data.error) {
        throw new Error(data.error);
    }

    // Store the batch ID for later use
    batchId = data.batchId;


}

function startStatusPolling() {
    isPolling = true;
    pollStatus();
}

function stopStatusPolling() {
    isPolling = false;
    if (pollTimeoutId) {
        clearTimeout(pollTimeoutId);
        pollTimeoutId = null;
    }
}

function pollStatus() {
    if (!isPolling) return;

    pollTimeoutId = setTimeout(async function () {
        try {
            const response = await fetch(`/api/status/${batchId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const statusData = await response.json();
            updateProgressBar(statusData);

            if (statusData.status === 'completed') {
                stopStatusPolling();
                handleSuccessfulUpload(statusData);
            } else if (statusData.status === 'failed') {
                stopStatusPolling();
                handleError(new Error('Failed to process images'));
            } else {
                // Reset retry count on successful poll
                retryCount = 0;
                // Continue polling with exponential backoff
                pollInterval = Math.min(pollInterval * 1.5, maxPollInterval);
                pollStatus();
            }
        } catch (error) {
            console.error('Error fetching status:', error);
            retryCount++;
            if (retryCount <= maxRetries) {
                // Retry with exponential backoff
                console.log(`Retrying in ${pollInterval}ms...`);
                pollInterval = Math.min(pollInterval * 2, maxPollInterval);
                pollStatus();
            } else {
                console.error('Max retries reached. Stopping polling.');
                stopStatusPolling();
                handleError(new Error('Failed to fetch status after multiple retries'));
            }
        }
    }, pollInterval);
}

function handleSuccessfulUpload(statusData) {
    downloadUrl = `/download/${batchId}`;
    processButton.style.display = 'none';
    downloadButton.style.display = 'block';
    stopLoadingAnimation("Download Images");
    releaseWakeLock();
}

function handleError(error) {
    alert('Error: ' + error.message);
    console.error('Error:', error);
    stopStatusPolling();
    resetForm();
}

function handleVisibilityChange() {
    if (document.hidden) {
        // Page is hidden, pause polling
        stopStatusPolling();
    } else {
        // Page is visible again, resume polling
        if (batchId) {
            startStatusPolling();
        }
    }
}

// Add event listener for visibility change
document.addEventListener('visibilitychange', handleVisibilityChange);


function disableForm() {
    document.getElementById('dateOptionsBtn').disabled = true;
    processButton.disabled = true;
    processButton.classList.add('disabled');
    progressContainer.style.display = 'block';
    uploadedImagesCount = fileInput.files.length;
    fileInput.disabled = true;
    checkboxes.forEach(checkbox => checkbox.disabled = true);
}

function resetForm() {
    processButton.disabled = false;
    processButton.classList.remove('disabled');
    progressContainer.style.display = 'none';
    fileInput.disabled = false;
    checkboxes.forEach(checkbox => checkbox.disabled = false);
    stopLoadingAnimation("Upload and Process");
    releaseWakeLock();
}

function updateProgressBar(statusData) {
    const { current_image_num, num_images } = statusData;
    if (num_images > 0) {
        const progressPercentage = Math.round((current_image_num / num_images) * 100);
        document.getElementById('progressBarFill').style.width = progressPercentage + '%';
        document.getElementById('progressText').innerText = `Processed ${current_image_num} of ${num_images} images...`;
    }
    else if (num_images === 0) {
        document.getElementById('progressText').innerText = ``;
    }
    else {
        log.error('Invalid number of images:', num_images);
    }
}

// UI Handlers
function handleCropImagesChange() {
    const drawContoursLabel = document.getElementById('drawContoursLabel');
    const drawContours = document.getElementById('drawContours');
    if (this.checked) {
        drawContoursLabel.classList.remove('disabled');
        drawContours.disabled = false;
    } else {
        drawContoursLabel.classList.add('disabled');
        drawContours.disabled = true;
        drawContours.checked = false;
    }
}

function toggleDateOptionsBox(e) {
    e.preventDefault();
    const dateOptionsBox = document.getElementById('dateOptionsBox');
    const isBoxVisible = dateOptionsBox.style.display === 'block';
    this.style.transform = isBoxVisible ? 'rotate(0deg)' : 'rotate(90deg)';
    dateOptionsBox.style.display = isBoxVisible ? 'none' : 'block';
}

function handleDownload() {
    window.location.href = downloadUrl;
    startOverButton.style.display = 'block';
}

// Initialize app
function initializeApp() {
    // Set up any initial state or event listeners
    document.getElementById('cropImages').dispatchEvent(new Event('change'));

    // Add event listener for the info button
    if (infoButton) {
        infoButton.addEventListener('click', showUsagePopup);
    }
    
    // Check for usage popup preferences
    const hidePopup = localStorage.getItem('hideUsagePopup');
    console.log('Initial hideUsagePopup value:', hidePopup);
    
    if (hidePopup !== 'true') {
        console.log('Showing popup');
        showUsagePopup();
    } else {
        closePopups();
        console.log('Popup hidden due to user preference');
    }
}

// Usage popup handling
function showUsagePopup() {
    const popup1 = document.getElementById('usagePopup1');
    const popup2 = document.getElementById('usagePopup2');
    const nextButton = document.getElementById('nextButton');
    const okButton = document.getElementById('okButton');
    const dontShowAgainButton = document.getElementById('dontShowAgainButton');

    if (popup1 && popup2 && nextButton && okButton && dontShowAgainButton) {
        popup1.style.display = 'flex';
        popup2.style.display = 'none';

        nextButton.addEventListener('click', () => {
            popup1.style.display = 'none';
            popup2.style.display = 'flex';
        });

        okButton.addEventListener('click', () => {
            closePopups();
        });

        dontShowAgainButton.addEventListener('click', () => {
            console.log('Don\'t show again clicked');
            localStorage.setItem('hideUsagePopup', 'true');
            console.log('hideUsagePopup set to:', localStorage.getItem('hideUsagePopup'));
            closePopups();
        });
    } else {
        console.error('One or more popup elements were not found.');
    }
}

function closePopups() {
    const popup1 = document.getElementById('usagePopup1');
    const popup2 = document.getElementById('usagePopup2');
    
    if (popup1 && popup2) {
        popup1.style.display = 'none';
        popup2.style.display = 'none';
    }
}
