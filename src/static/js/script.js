let downloadUrl = '';
    let uploadedImagesCount = 0;
    const uploadForm = document.getElementById('uploadForm');
    const processButton = document.getElementById('processButton');
    const downloadButton = document.getElementById('downloadButton');
    const startOverButton = document.getElementById('startOver');
    const progressContainer = document.getElementById('progressContainer');
    const fileInput = document.getElementById('fileInput');
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    let wakeLock = null;

    // Initialize Flatpickr date range picker
    flatpickr("#dateRange", {
        mode: "range",
        dateFormat: "m/d/Y",
        defaultDate: ["",""]
    });

    async function requestWakeLock() {
        try {
            wakeLock = await navigator.wakeLock.request('screen');
        } catch (err) {
            console.error(`${err.name}, ${err.message}`);
        }
    }
    
    async function releaseWakeLock() {
        if (wakeLock !== null) {
            try {
                await wakeLock.release();
                wakeLock = null;
            } catch (err) {
                console.error(`${err.name}, ${err.message}`);
            }
        }
    }

    function startLoadingAnimation() {
        let dots = 0;
        loadingInterval = setInterval(() => {
            dots = (dots + 1) % 4;
            processButton.textContent = 'Processing' + '.'.repeat(dots);
        }, 500);
    }
    
    function stopLoadingAnimation() {
        clearInterval(loadingInterval);
        processButton.textContent = 'Process and upload';
    }

    uploadForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = new FormData(this);

        // Get the selected date range
        const dateRange = document.getElementById('dateRange').value;
        formData.append('date_range', dateRange);

        processButton.disabled = true;
        processButton.classList.add('disabled');
        progressContainer.style.display = 'block';

        uploadedImagesCount = fileInput.files.length;
        fileInput.disabled = true;
        checkboxes.forEach(checkbox => checkbox.disabled = true);

        startLoadingAnimation();
        await requestWakeLock();


        fetch('/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                if (response.status === 403) {
                    throw new Error('Human verification failed. Please reload and try again.');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    console.error('Data error:', data.error);
                } else {
                    downloadUrl = data.download_url;
                    processButton.style.display = 'none';
                    downloadButton.style.display = 'block';
                    clearInterval(intervalId);
                }
            })
            .catch(error => {
                alert('Error: ' + error.message);
                console.error('Error:', error);

                
                console.error('Error:', error);
                processButton.disabled = false;
                processButton.textContent = 'Process and upload';
                processButton.classList.remove('disabled');
                progressContainer.style.display = 'none';
                clearInterval(intervalId);
                fileInput.disabled = false;
                checkboxes.forEach(checkbox => checkbox.disabled = false);
                
            })
            .finally(() => {
                stopLoadingAnimation();
                releaseWakeLock();
            });

        // Poll progress
        let intervalId = setInterval(function () {
            fetch('/api/progress')
                .then(response => response.json())
                .then(progressData => {
                    const { num_images, current_image_num } = progressData;
                    if (num_images > 0) {
                        const progressPercentage = Math.round((current_image_num / num_images) * 100);
                        document.getElementById('progressBarFill').style.width = progressPercentage + '%';
                        document.getElementById('progressText').innerText = `Processed ${current_image_num} of ${num_images} images...`;

                        if (current_image_num >= num_images) {
                            clearInterval(intervalId);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching progress:', error);
                    clearInterval(intervalId);
                });
        }, 750);
    });

    // Handle the dependency between "Crop images" and "Draw contours" checkboxes
    document.getElementById('cropImages').addEventListener('change', function() {
        var drawContoursLabel = document.getElementById('drawContoursLabel');
        var drawContours = document.getElementById('drawContours');
        if (this.checked) {
            drawContoursLabel.classList.remove('disabled');
            drawContours.disabled = false;
        } else {
            drawContoursLabel.classList.add('disabled');
            drawContours.disabled = true;
            drawContours.checked = false;
        }
    });

    // Initial state setup
    document.getElementById('cropImages').dispatchEvent(new Event('change'));


    downloadButton.addEventListener('click', function() {
        window.location.href = downloadUrl;
        startOverButton.style.display = 'block';
    });

    startOverButton.addEventListener('click', function () {
        location.reload();
    });


    document.addEventListener('DOMContentLoaded', function() {
        const dateOptionsBtn = document.getElementById('dateOptionsBtn');
        const dateOptionsBox = document.getElementById('dateOptionsBox');
    
        dateOptionsBtn.addEventListener('click', function(e) {
            e.preventDefault();

            const isBoxVisible = dateOptionsBox.style.display === 'block';
            dateOptionsBtn.style.transform = isBoxVisible ? 'rotate(0deg)' : 'rotate(90deg)';

            dateOptionsBox.style.display = dateOptionsBox.style.display === 'none' ? 'block' : 'none';
        });
    });

    window.addEventListener('load', function() {
        const popup1 = document.getElementById('usagePopup1');
        const popup2 = document.getElementById('usagePopup2');
        const nextButton = document.getElementById('nextButton');
        const okButton = document.getElementById('okButton');
        const dontShowAgainButton = document.getElementById('dontShowAgainButton');
    
        // Check if popups exist before attempting to manipulate them
        if (popup1 && popup2 && nextButton && okButton && dontShowAgainButton) {
            // Check if the user has previously selected "Don't Show Again"
            if (!localStorage.getItem('hideUsagePopup')) {
                popup1.style.display = 'flex'; // Show the first popup
            }
    
            // Show the second popup when "Next" is clicked
            nextButton.addEventListener('click', function() {
                popup1.style.display = 'none';  // Hide the first popup
                popup2.style.display = 'flex'; // Show the second popup
            });
    
            // Hide all popups when "OK" is clicked
            okButton.addEventListener('click', function() {
                popup2.style.display = 'none';  // Hide the second popup
            });
    
            // Don't show popups again when "Don't Show Again" is clicked
            dontShowAgainButton.addEventListener('click', function() {
                localStorage.setItem('hideUsagePopup', 'true');  // Save preference
                popup2.style.display = 'none';  // Hide the second popup
            });
        } else {
            console.error('One or more popup elements were not found.');
        }
    });
    