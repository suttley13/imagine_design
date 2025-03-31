document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const originalImageUpload = document.getElementById('original-image-upload');
    const originalPreviewContainer = document.getElementById('original-preview-container');
    const originalPreview = document.getElementById('original-preview');
    const originalRemoveImageBtn = document.getElementById('original-remove-image');
    const originalUploadArea = document.getElementById('original-upload-area');
    
    const inspirationImageUpload = document.getElementById('inspiration-image-upload');
    const inspirationPreviewContainer = document.getElementById('inspiration-preview-container');
    const inspirationPreview = document.getElementById('inspiration-preview');
    const inspirationRemoveImageBtn = document.getElementById('inspiration-remove-image');
    const inspirationUploadArea = document.getElementById('inspiration-upload-area');
    
    const redesignButton = document.getElementById('redesign-button');
    const saveButton = document.querySelector('.save-button');
    
    const suggestionsContainer = document.querySelector('.suggestions-container');
    const suggestionsList = document.getElementById('suggestions-list');
    const suggestionsLoading = document.getElementById('suggestions-loading');
    const suggestionStatuses = document.querySelectorAll('.suggestion-status');
    const suggestionTexts = document.querySelectorAll('.suggestion-text');
    const suggestionsPlaceholder = document.getElementById('suggestions-placeholder');
    const suggestionsClickHint = document.getElementById('suggestions-click-hint');
    
    const resultContainer = document.getElementById('result-container');
    const resultImage = document.getElementById('result-image');
    const resultLoadingSpinner = document.getElementById('result-loading-spinner');
    const resultPlaceholder = document.getElementById('result-placeholder');
    const currentSuggestionNumber = document.getElementById('current-suggestion-number');
    const clickHint = document.querySelector('.click-hint');
    
    const resultsContainer = document.getElementById('results-container');
    const redesignLoading = document.getElementById('redesign-loading');
    const uploadSectionContainer = document.querySelector('.upload-section-container');
    const redesignButtonContainer = document.querySelector('.redesign-button-container');
    const backButton = document.getElementById('back-button');
    
    const cornerLoadingSpinner = document.getElementById('corner-loading-spinner');
    
    const instructionsContainer = document.querySelector('.instructions-container');
    const loadingContainer = document.querySelector('.loading-container');
    const loadingTextElement = document.getElementById('loading-text-cycle');
    
    let originalSelectedImage = null;
    let inspirationSelectedImage = null;
    let currentSuggestionIndex = 0;
    let isProcessing = false;
    let suggestions = [];
    let generatedImagesHistory = []; // Store history of generated images
    let originalImageUrl = null; // Store URL of original image for comparison
    
    // Loading message cycling
    let loadingTextInterval;
    const loadingMessages = [
        "Analyzing your room...",
        "Reviewing the inspiration...",
        "Developing a color palette...",
        "Refining suggestions..."
    ];

    function startLoadingTextCycle() {
        let index = 0;
        loadingTextElement.textContent = loadingMessages[index];
        
        loadingTextInterval = setInterval(() => {
            index = (index + 1) % loadingMessages.length;
            loadingTextElement.textContent = loadingMessages[index];
            
            // If we've reached "Refining suggestions" (the last message), stop cycling
            if (index === loadingMessages.length - 1) {
                clearInterval(loadingTextInterval);
                loadingTextInterval = null;
            }
        }, 2300);
    }

    function stopLoadingTextCycle() {
        if (loadingTextInterval) {
            clearInterval(loadingTextInterval);
            loadingTextInterval = null;
        }
    }
    
    // Add this function near the top of the file, after variable declarations
    function showAlert(message, isError = true) {
        // Create alert element
        const alertElement = document.createElement('div');
        alertElement.className = isError ? 'alert alert-error' : 'alert alert-success';
        alertElement.textContent = message;
        
        // Add to DOM
        document.body.appendChild(alertElement);
        
        // Auto-remove after a few seconds
        setTimeout(() => {
            alertElement.classList.add('fade-out');
            setTimeout(() => alertElement.remove(), 1000);
        }, 5000);
    }
    
    // Show a special loading state for image processing
    function showProcessingStatus() {
        const statusElement = document.createElement('div');
        statusElement.className = 'conversion-status';
        statusElement.id = 'image-processing-status';
        statusElement.innerHTML = `
            <div class="spinner"></div>
            <p>Processing image...</p>
        `;
        document.body.appendChild(statusElement);
        return statusElement;
    }
    
    // Check if file is likely HEIC format
    function isHeicImage(file) {
        const fileName = file.name.toLowerCase();
        const fileType = file.type.toLowerCase();
        return fileName.endsWith('.heic') || fileName.endsWith('.heif') || 
               fileType.includes('heic') || fileType.includes('heif');
    }
    
    // Handle original image upload
    originalImageUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            console.log('Original image selected:', file.name);
            
            // Check if this is a HEIC image and show processing message
            let processingStatus = null;
            if (isHeicImage(file)) {
                console.log('HEIC image detected, conversion will be performed on server');
                processingStatus = showProcessingStatus();
            }
            
            originalSelectedImage = file;
            
            // For non-HEIC images, display preview immediately
            if (!isHeicImage(file)) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    originalPreview.src = event.target.result;
                    originalImageUrl = event.target.result; // Store the original image URL
                    originalPreviewContainer.classList.remove('hidden');
                    originalUploadArea.classList.add('hidden');
                    updateRedesignButtonState();
                };
                reader.readAsDataURL(file);
            } else {
                // For HEIC images, we'll display a placeholder until properly processed
                originalPreviewContainer.classList.remove('hidden');
                originalUploadArea.classList.add('hidden');
                originalPreview.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIGZpbGw9IiM1NTUiPkNvbnZlcnRpbmcgSEVJQy4uLjwvdGV4dD48L3N2Zz4=';
                updateRedesignButtonState();
                
                // Create a small form data to test-process this HEIC file to get a JPEG version
                const testFormData = new FormData();
                testFormData.append('image', file);
                testFormData.append('message', 'Processing HEIC preview');
                
                // Send to process on the server
                fetch('/api/chat-with-image', {
                    method: 'POST',
                    body: testFormData
                })
                .then(response => response.json())
                .then(data => {
                    // If we got images back, update our preview with the processed version
                    if (data.images && data.images.length > 0) {
                        console.log('Received processed HEIC image:', data.images[0]);
                        
                        // Update the preview with processed image
                        fetch(data.images[0])
                            .then(response => response.blob())
                            .then(blob => {
                                const url = URL.createObjectURL(blob);
                                originalPreview.src = url;
                                originalImageUrl = url; // Update the original image URL to the processed version
                                console.log('Original image preview updated with processed version');
                            });
                    }
                    
                    // Remove processing status 
                    if (processingStatus) {
                        processingStatus.remove();
                    }
                })
                .catch(error => {
                    console.error('Error processing HEIC preview:', error);
                    // Just remove the processing status if there's an error
                    if (processingStatus) {
                        processingStatus.remove();
                    }
                });
            }
        }
    });
    
    // Handle original image removal
    originalRemoveImageBtn.addEventListener('click', () => {
        console.log('Original image removed');
        originalSelectedImage = null;
        originalPreview.src = '';
        originalImageUrl = null;
        originalImageUpload.value = '';
        originalPreviewContainer.classList.add('hidden');
        originalUploadArea.classList.remove('hidden');
        updateRedesignButtonState();
    });
    
    // Handle inspiration image upload
    inspirationImageUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            console.log('Inspiration image selected:', file.name);
            
            // Check if this is a HEIC image and show processing message
            let processingStatus = null;
            if (isHeicImage(file)) {
                console.log('HEIC image detected, conversion will be performed on server');
                processingStatus = showProcessingStatus();
            }
            
            inspirationSelectedImage = file;
            
            // For non-HEIC images, display preview immediately
            if (!isHeicImage(file)) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    inspirationPreview.src = event.target.result;
                    inspirationPreviewContainer.classList.remove('hidden');
                    inspirationUploadArea.classList.add('hidden');
                    updateRedesignButtonState();
                };
                reader.readAsDataURL(file);
            } else {
                // For HEIC images, we'll display a placeholder until properly processed
                inspirationPreviewContainer.classList.remove('hidden');
                inspirationUploadArea.classList.add('hidden');
                inspirationPreview.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIGZpbGw9IiM1NTUiPkNvbnZlcnRpbmcgSEVJQy4uLjwvdGV4dD48L3N2Zz4=';
                updateRedesignButtonState();
                
                // Create a small form data to test-process this HEIC file to get a JPEG version
                const testFormData = new FormData();
                testFormData.append('image', file);
                testFormData.append('message', 'Processing HEIC preview');
                
                // Send to process on the server
                fetch('/api/chat-with-image', {
                    method: 'POST',
                    body: testFormData
                })
                .then(response => response.json())
                .then(data => {
                    // If we got images back, update our preview with the processed version
                    if (data.images && data.images.length > 0) {
                        console.log('Received processed HEIC image:', data.images[0]);
                        
                        // Update the preview with processed image
                        fetch(data.images[0])
                            .then(response => response.blob())
                            .then(blob => {
                                const url = URL.createObjectURL(blob);
                                inspirationPreview.src = url;
                                console.log('Inspiration image preview updated with processed version');
                            });
                    }
                    
                    // Remove processing status 
                    if (processingStatus) {
                        processingStatus.remove();
                    }
                })
                .catch(error => {
                    console.error('Error processing HEIC preview:', error);
                    // Just remove the processing status if there's an error
                    if (processingStatus) {
                        processingStatus.remove();
                    }
                });
            }
        }
    });
    
    // Handle inspiration image removal
    inspirationRemoveImageBtn.addEventListener('click', () => {
        console.log('Inspiration image removed');
        inspirationSelectedImage = null;
        inspirationPreview.src = '';
        inspirationImageUpload.value = '';
        inspirationPreviewContainer.classList.add('hidden');
        inspirationUploadArea.classList.remove('hidden');
        updateRedesignButtonState();
    });
    
    // Enable/disable redesign button based on inputs
    function updateRedesignButtonState() {
        const hasOriginalImage = originalSelectedImage !== null;
        const hasInspirationImage = inspirationSelectedImage !== null;
        redesignButton.disabled = !(hasOriginalImage && hasInspirationImage);
        updateSaveButtonState();
    }
    
    // Add click-and-hold functionality to show original image
    function setupBeforeAfterComparison() {
        if (!resultImage || !originalImageUrl) return;
        
        console.log('Setting up before/after comparison');
        
        // Remove any existing event listeners to prevent conflicts
        const oldShowOriginal = resultImage._showOriginal;
        const oldShowResult = resultImage._showResult;
        
        if (oldShowOriginal) {
            resultImage.removeEventListener('mousedown', oldShowOriginal);
            resultImage.removeEventListener('touchstart', oldShowOriginal);
        }
        
        if (oldShowResult) {
            document.removeEventListener('mouseup', oldShowResult);
            document.removeEventListener('touchend', oldShowResult);
        }
        
        // Create variables to store current state
        let currentImageUrl;
        
        // Create hidden image to preload the original at full size
        const preloadOriginal = new Image();
        preloadOriginal.src = originalImageUrl;
        
        // Create a wrapper div for the before image to maintain exact dimensions
        const createBeforeImageElement = () => {
            // Get current result image dimensions and position
            const resultRect = resultImage.getBoundingClientRect();
            
            // Create a div to hold the before image with exact same dimensions
            const beforeContainer = document.createElement('div');
            beforeContainer.className = 'before-image-container';
            beforeContainer.style.position = 'absolute';
            beforeContainer.style.top = '0';
            beforeContainer.style.left = '0';
            beforeContainer.style.width = '100%';
            beforeContainer.style.height = '100%';
            beforeContainer.style.zIndex = '100';
            
            // Create the before image that will match result dimensions exactly
            const beforeImage = document.createElement('img');
            beforeImage.src = originalImageUrl;
            beforeImage.className = 'before-image';
            beforeImage.style.width = '100%';
            beforeImage.style.height = '100%';
            beforeImage.style.objectFit = resultImage.style.objectFit || 'contain';
            
            beforeContainer.appendChild(beforeImage);
            
            return {container: beforeContainer, image: beforeImage};
        };
        
        // Show original image on mouse down or touch start
        const showOriginal = (e) => {
            console.log('Showing original image');
            // Store the current image URL at the moment of click
            currentImageUrl = resultImage.src;
            
            // Save current resultImage styles
            const resultStyles = {
                width: resultImage.offsetWidth,
                height: resultImage.offsetHeight,
                objectFit: window.getComputedStyle(resultImage).objectFit
            };
            
            // Set the result container to relative if not already
            const resultContainerStyle = window.getComputedStyle(resultContainer);
            if (resultContainerStyle.position !== 'relative' && resultContainerStyle.position !== 'absolute') {
                resultContainer.style.position = 'relative';
            }
            
            // Create and add the before image as an overlay
            const beforeElements = createBeforeImageElement();
            resultContainer.appendChild(beforeElements.container);
            
            // Add comparing class to show we're in comparison mode
            resultImage.classList.add('comparing');
            beforeElements.container.classList.add('comparing');
        };
        
        // Show result image on mouse up or touch end
        const showResult = () => {
            console.log('Showing result image');
            
            // Remove any before-image-container elements
            const beforeContainers = document.querySelectorAll('.before-image-container');
            beforeContainers.forEach(container => container.remove());
            
            // Remove comparing class
            resultImage.classList.remove('comparing');
        };
        
        // Store the handlers on the element itself for future cleanup
        resultImage._showOriginal = showOriginal;
        resultImage._showResult = showResult;
        
        // Add event listeners
        resultImage.addEventListener('mousedown', showOriginal);
        resultImage.addEventListener('touchstart', showOriginal);
        
        // Add global event listeners to handle release even if cursor moves out of image
        document.addEventListener('mouseup', showResult);
        document.addEventListener('touchend', showResult);
        
        // Add tooltip to inform users
        resultImage.title = "Click and hold to see original image";
        
        // Add a visual indicator (only if it doesn't already exist)
        if (!document.querySelector('.comparison-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'comparison-indicator';
            indicator.textContent = 'Click and hold to compare with original';
            resultContainer.appendChild(indicator);
            
            // Hide indicator after a few seconds
            setTimeout(() => {
                indicator.classList.add('fade-out');
                setTimeout(() => {
                    if (indicator.parentNode) {
                        indicator.remove();
                    }
                }, 1000);
            }, 5000);
        }
    }
    
    // Reset processing state
    function resetProcessing() {
        isProcessing = false;
        redesignButton.disabled = false;
        redesignButton.classList.remove('hidden');
        redesignLoading.classList.add('hidden');
        
        // Hide loading states
        suggestionsLoading.classList.add('hidden');
        resultLoadingSpinner.classList.add('hidden');
        cornerLoadingSpinner.classList.add('hidden');
        
        // Reset suggestion statuses
        suggestionStatuses.forEach(status => {
            status.classList.remove('completed');
            status.classList.remove('active');
            status.classList.remove('selected');
        });
        
        // Clear image history
        generatedImagesHistory = [];
        
        // Hide click hint
        clickHint.classList.add('hidden');
        suggestionsClickHint.classList.add('hidden');
        
        // Reset current suggestion index
        currentSuggestionIndex = 0;
        
        // Update UI
        resultLoadingSpinner.classList.add('hidden');
        resultContainer.classList.add('hidden');
        resultPlaceholder.classList.remove('hidden');
        
        suggestionsLoading.classList.add('hidden');
        suggestionsList.classList.add('hidden');
        suggestionsPlaceholder.classList.remove('hidden');
        
        redesignButton.disabled = false;
        
        // Show upload sections and hide results
        uploadSectionContainer.classList.remove('hidden');
        redesignButtonContainer.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        
        // Enable save button if we have results
        updateSaveButtonState();
    }
    
    // Process a single suggestion with Gemini
    async function processSuggestion(sourceImage, suggestionText, suggestionIndex) {
        try {
            console.log(`Processing suggestion ${suggestionIndex + 1}: "${suggestionText}"`);
            
            // Update UI
            currentSuggestionNumber.textContent = suggestionIndex + 1;
            
            // Mark all previous steps as completed
            for (let i = 0; i < suggestionIndex; i++) {
                suggestionStatuses[i].classList.remove('active');
                suggestionStatuses[i].classList.add('completed');
            }
            
            // Show this step as active
            suggestionStatuses[suggestionIndex].classList.add('active');
            
            // Create FormData for image upload
            const formData = new FormData();
            formData.append('message', suggestionText);
            
            // Use either a File object or a URL depending on the source
            if (sourceImage instanceof File) {
                // Direct file upload from the first step
                formData.append('image', sourceImage);
            } else if (typeof sourceImage === 'string' && sourceImage.startsWith('data:')) {
                // Convert dataURL to File object
                const response = await fetch(sourceImage);
                const blob = await response.blob();
                const file = new File([blob], "image.jpg", { type: "image/jpeg" });
                formData.append('image', file);
            } else if (typeof sourceImage === 'string' && (sourceImage.startsWith('/') || sourceImage.startsWith('http'))) {
                // Handle relative or absolute URLs from previous steps
                const fullUrl = sourceImage.startsWith('/') ? window.location.origin + sourceImage : sourceImage;
                console.log('Fetching image from URL:', fullUrl);
                
                try {
                    const response = await fetch(fullUrl);
                    if (!response.ok) throw new Error(`Failed to fetch image: ${response.status}`);
                    
                    const blob = await response.blob();
                    const file = new File([blob], "image.jpg", { type: blob.type || "image/jpeg" });
                    formData.append('image', file);
                } catch (fetchError) {
                    console.error('Error fetching image:', fetchError);
                    throw new Error('Could not load the image from the previous step');
                }
            } else {
                throw new Error('Invalid image source: ' + (typeof sourceImage));
            }
            
            // Send to server
            console.log('Sending request to Gemini API');
            const response = await fetch('/api/chat-with-image', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            console.log('Response data for suggestion', suggestionIndex + 1, data);
            
            // Check if we got images back
            if (data.images && data.images.length > 0) {
                // Get the first image URL
                const imageUrl = data.images[0];
                
                // Store this image in our history at the correct index
                generatedImagesHistory[suggestionIndex] = {
                    suggestion: suggestionText,
                    imageUrl: imageUrl
                };
                
                // Set the result image
                resultImage.src = imageUrl;
                resultPlaceholder.classList.add('hidden');
                resultContainer.classList.remove('hidden');
                resultLoadingSpinner.classList.add('hidden');
                cornerLoadingSpinner.classList.add('hidden');
                
                // Show this image to the user
                // Add a visual indicator for the current step
                suggestionStatuses.forEach((status, idx) => {
                    status.classList.remove('selected');
                    if (idx === suggestionIndex) {
                        status.classList.add('selected');
                    }
                });
                
                // Mark this suggestion as completed
                suggestionStatuses[suggestionIndex].classList.remove('active');
                suggestionStatuses[suggestionIndex].classList.add('completed');
                
                // Wait a moment for the user to see this generation if it's not the last one
                if (suggestionIndex < 2) {
                    // If it's not the last image, wait a bit before moving to the next step
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    // Show the corner loading spinner instead of the full-screen one
                    cornerLoadingSpinner.classList.remove('hidden');
                }
                
                // Add click event listener to the suggestion status
                suggestionStatuses[suggestionIndex].addEventListener('click', () => {
                    // Remove selected class from all statuses
                    suggestionStatuses.forEach(s => s.classList.remove('selected'));
                    
                    // Add selected class to this status
                    suggestionStatuses[suggestionIndex].classList.add('selected');
                    
                    // Display this image
                    resultImage.src = imageUrl;
                    resultContainer.classList.remove('hidden');
                    resultLoadingSpinner.classList.add('hidden');
                    cornerLoadingSpinner.classList.add('hidden');
                    
                    // Setup before/after comparison for this result
                    setupBeforeAfterComparison();
                });
                
                // If there's more than one image in history, show the click hint
                if (generatedImagesHistory.filter(img => img).length > 1) {
                    clickHint.classList.remove('hidden');
                }
                
                // Setup before/after comparison for this result
                if (suggestionIndex === 0) {
                    setupBeforeAfterComparison();
                }
                
                // Enable the save button now that we have a result
                updateSaveButtonState();
                
                return {
                    success: true,
                    resultImageUrl: imageUrl
                };
            } else {
                throw new Error('No image was returned');
            }
            
        } catch (error) {
            console.error('Error in suggestion', suggestionIndex + 1, error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    // Generate suggestions from Claude and process them with Gemini
    async function runRedesignProcess() {
        if (isProcessing) return;
        isProcessing = true;
        
        console.log('Starting redesign process');
        
        try {
            // First, get suggestions from Claude
            console.log('Requesting suggestions from Claude');
            
            // Create FormData with both images
            const formData = new FormData();
            formData.append('original', originalSelectedImage);
            formData.append('inspiration', inspirationSelectedImage);
            
            // Get suggestions from Claude
            const claudeResponse = await fetch('/api/claude-suggestions', {
                method: 'POST',
                body: formData
            });
            
            // Check if we have an error response
            if (!claudeResponse.ok) {
                const errorData = await claudeResponse.json();
                const errorMessage = errorData.error || claudeResponse.statusText;
                console.error('Claude API error:', errorMessage);
                
                // Stop loading messages cycle
                stopLoadingTextCycle();
                
                // Show a more user-friendly message for known errors
                if (errorMessage.includes('HEIC') || errorMessage.includes('heic')) {
                    showAlert('We attempted to convert your HEIC image but encountered an issue. Please convert it to JPEG format using Photos app or similar before uploading.', true);
                } else if (errorMessage.includes('overloaded')) {
                    showAlert('The AI service is currently experiencing high demand. Please wait a moment and try again.', true);
                } else {
                    showAlert(`Error: ${errorMessage}`);
                }
                
                throw new Error(`Claude API error: ${errorMessage}`);
            }
            
            const claudeData = await claudeResponse.json();
            suggestions = claudeData.suggestions;
            
            // Stop loading messages cycle
            stopLoadingTextCycle();
            
            console.log('Received suggestions from Claude:', suggestions);
            
            if (!suggestions || suggestions.length !== 3) {
                throw new Error(`Expected 3 suggestions, got ${suggestions ? suggestions.length : 0}`);
            }
            
            // Hide upload sections and show results container
            uploadSectionContainer.classList.add('hidden');
            redesignButtonContainer.classList.add('hidden');
            resultsContainer.classList.remove('hidden');
            
            // Hide loading container once we show results
            if (loadingContainer) loadingContainer.style.display = 'none';
            
            // Display suggestion titles in the UI
            const suggestionElements = document.querySelectorAll('.suggestion-item');
            suggestionElements.forEach((element, index) => {
                if (index < suggestions.length) {
                    const titleElement = element.querySelector('.suggestion-text');
                    // Remove the number prefix (like "1. " or "2. ") from the title
                    const cleanTitle = suggestions[index].title.replace(/^\d+\.\s*/, '');
                    titleElement.textContent = cleanTitle;
                    titleElement.setAttribute('data-description', suggestions[index].description);
                    
                    // Add click event to show description in modal
                    titleElement.addEventListener('click', () => {
                        // Also use the clean title for the modal
                        showDescriptionModal(cleanTitle, suggestions[index].description);
                    });
                    
                    // Add tooltip
                    titleElement.title = "Click to view full description";
                    
                    // Add clickable styling
                    titleElement.classList.add('clickable-title');
                }
            });
            
            // Show suggestions and hide loading
            suggestionsPlaceholder.classList.add('hidden');
            suggestionsLoading.classList.add('hidden');
            suggestionsContainer.classList.remove('hidden');
            const suggestionsList = document.getElementById('suggestions-list');
            suggestionsList.classList.remove('hidden');
            
            // Reset suggestion statuses
            suggestionStatuses.forEach(status => {
                status.classList.remove('completed');
                status.classList.remove('active');
                status.classList.remove('selected');
            });
            
            // Now process each suggestion with Gemini
            console.log('Starting to process suggestions with Gemini');
            resultPlaceholder.classList.add('hidden');
            resultLoadingSpinner.classList.remove('hidden');
            
            // Start with the original image
            let currentSourceImage = originalSelectedImage;
            
            // Process each suggestion in sequence
            for (let i = 0; i < suggestions.length; i++) {
                console.log(`Processing suggestion ${i + 1}`);
                
                // Process this suggestion - send description only, not title
                const result = await processSuggestion(
                    currentSourceImage, 
                    suggestions[i].description, // Use only the description for Gemini
                    i
                );
                
                if (result.success) {
                    console.log(`Suggestion ${i + 1} completed successfully`);
                    // Use the result image as the source for the next step
                    currentSourceImage = result.resultImageUrl;
                } else {
                    // If there's an error, stop the process
                    console.error(`Error on suggestion ${i + 1}:`, result.error);
                    alert(`Error on suggestion ${i + 1}: ${result.error}`);
                    resetProcessing();
                    return;
                }
            }
            
            // All done
            console.log('Redesign process completed successfully');
            resultLoadingSpinner.classList.add('hidden');
            redesignButton.classList.remove('hidden');
            redesignLoading.classList.add('hidden');
            redesignButton.disabled = false;
            isProcessing = false;
            
            // Show the suggestions click hint now that all images are processed
            suggestionsClickHint.classList.remove('hidden');
            
        } catch (error) {
            console.error('Error in redesign process:', error);
            
            // Stop loading messages cycle
            stopLoadingTextCycle();
            
            // Check for specific error types
            if (error.message.includes('HEIC') || error.message.includes('heic')) {
                showAlert('We attempted to convert your HEIC image but encountered an issue. Please convert it to JPEG format using Photos app or similar before uploading.', true);
            } else {
                showAlert(`Error: ${error.message}`);
            }
            
            // Hide loading container on error
            if (loadingContainer) loadingContainer.style.display = 'none';
            
            resetProcessing();
        }
    }
    
    // Handle redesign button click
    redesignButton.addEventListener('click', () => {
        // Track custom event in Google Analytics
        if (typeof gtag === 'function') {
            gtag('event', 'Clicked_Redesign_Button', {
                'event_name': 'lksdfjfdjk'
            });
            console.log('Tracked: Clicked_Redesign_Button event');
        }
        
        // Hide instructions and show loading spinner
        if (instructionsContainer) instructionsContainer.style.display = 'none';
        if (loadingContainer) loadingContainer.style.display = 'flex';
        
        // Start cycling loading messages
        startLoadingTextCycle();
        
        // Don't show the redesign loading spinner, just disable the button
        redesignButton.disabled = true;
        
        runRedesignProcess();
    });

    // Add function to show description modal
    function showDescriptionModal(title, description) {
        console.log('Showing description modal');
        
        // Remove any existing modals
        const existingModal = document.getElementById('description-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Create modal elements
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay';
        modalOverlay.id = 'description-modal';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';
        
        const modalTitle = document.createElement('h3');
        modalTitle.textContent = title;
        
        const closeButton = document.createElement('button');
        closeButton.className = 'modal-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', () => {
            modalOverlay.classList.add('fade-out');
            setTimeout(() => modalOverlay.remove(), 300);
        });
        
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        modalBody.textContent = description;
        
        // Assemble the modal
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalOverlay.appendChild(modalContent);
        
        // Add to the document
        document.body.appendChild(modalOverlay);
        
        // Close on overlay click
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.classList.add('fade-out');
                setTimeout(() => modalOverlay.remove(), 300);
            }
        });
        
        // Close on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && document.getElementById('description-modal')) {
                modalOverlay.classList.add('fade-out');
                setTimeout(() => modalOverlay.remove(), 300);
            }
        });
        
        // Prevent body scrolling when modal is open
        document.body.style.overflow = 'hidden';
        
        // Restore scrolling when modal is closed
        const restoreScrolling = () => {
            document.body.style.overflow = '';
        };
        
        modalOverlay.addEventListener('transitionend', function() {
            if (this.classList.contains('fade-out')) {
                restoreScrolling();
            }
        });
    }

    // Handle save button click
    saveButton.addEventListener('click', async () => {
        if (!suggestions.length || !resultImage.src) {
            showAlert('No results to save yet', true);
            return;
        }
        
        try {
            // Always use the third (final) generated image as the result
            let finalResultImageUrl = null;
            if (generatedImagesHistory.length >= 3 && generatedImagesHistory[2] && generatedImagesHistory[2].imageUrl) {
                finalResultImageUrl = generatedImagesHistory[2].imageUrl;
            } else {
                // Fallback to current displayed image if third isn't available
                finalResultImageUrl = resultImage.src;
            }
            
            // Extract the relative paths for the server
            const resultPath = new URL(finalResultImageUrl, window.location.href).pathname;
            
            // Send the request to prepare the download
            const response = await fetch('/api/save-results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    result_image: resultPath,
                    suggestions: suggestions
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to prepare download');
            }
            
            const data = await response.json();
            
            // Copy the content to clipboard
            await navigator.clipboard.writeText(data.clipboard_content);
            
            // Trigger the download by creating a link and clicking it
            if (data.download_url) {
                // Create a hidden anchor element for the download
                const downloadLink = document.createElement('a');
                downloadLink.href = data.download_url;
                downloadLink.download = 'redesign_result.jpg'; // Add a default filename
                downloadLink.setAttribute('download', ''); // Ensure it's a download
                downloadLink.style.display = 'none';
                document.body.appendChild(downloadLink);
                
                // Trigger the download
                downloadLink.click();
                
                // Clean up
                setTimeout(() => {
                    document.body.removeChild(downloadLink);
                }, 100);
                
                // Show success message
                showAlert('Final redesign image downloading and descriptions copied to clipboard', false);
            } else {
                throw new Error('No download URL provided');
            }
            
        } catch (error) {
            console.error('Error saving results:', error);
            showAlert(`Error: ${error.message}`, true);
        }
    });

    // Define updateSaveButtonState function
    function updateSaveButtonState() {
        if (saveButton) {
            saveButton.disabled = !(
                generatedImagesHistory.length > 0 && 
                resultImage.src && 
                suggestions.length > 0
            );
        }
    }

    // Handle back button click
    backButton.addEventListener('click', () => {
        // Show upload sections and hide results
        uploadSectionContainer.classList.remove('hidden');
        redesignButtonContainer.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        
        // Show instructions div again
        if (instructionsContainer) instructionsContainer.style.display = 'flex';
        if (loadingContainer) loadingContainer.style.display = 'none';
        
        // Enable the redesign button 
        redesignButton.disabled = false;
        redesignButton.classList.remove('hidden');
        redesignLoading.classList.add('hidden');
    });

    function handleRedesign() {
        const instructionsContainer = document.querySelector('.instructions-container');
        const loadingContainer = document.querySelector('.loading-container');
        const resultsContent = document.querySelector('.results-content');
        
        // Hide instructions and show loading spinner
        if (instructionsContainer) instructionsContainer.style.display = 'none';
        loadingContainer.style.display = 'flex';
        
        // Your existing redesign logic here
        // When results are ready:
        // loadingContainer.style.display = 'none';
        // resultsContent.style.display = 'flex';
    }
}); 