let downloadUrl = '';
    let uploadedImagesCount = 0;
    const uploadForm = document.getElementById('uploadForm');
    const processButton = document.getElementById('processButton');
    const downloadButton = document.getElementById('downloadButton');
    const startOverButton = document.getElementById('startOver');
    const progressContainer = document.getElementById('progressContainer');
    const fileInput = document.getElementById('fileInput');

    uploadForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        processButton.disabled = true;
        processButton.textContent = 'Processing...';
        processButton.classList.add('disabled');
        progressContainer.style.display = 'block';
        uploadedImagesCount = fileInput.files.length;

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                if (response.status === 403) {
                    throw new Error('Turntile verification failed. Please try again.');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
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
                processButton.disabled = false;
                processButton.textContent = 'Process';
                processButton.classList.remove('disabled');
                progressContainer.style.display = 'none';
                clearInterval(intervalId);

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