document.addEventListener('DOMContentLoaded', () => {
    // Auth related elements
    const loginButton = document.getElementById('login-button');
    const registerButton = document.getElementById('register-button');
    const logoutButton = document.getElementById('logout-button');
    const usageInfo = document.getElementById('usage-info');
    const redesignsCount = document.getElementById('redesigns-count');
    const authButtons = document.getElementById('auth-buttons');
    const userInfo = document.getElementById('user-info');
    const userEmail = document.getElementById('user-email');
    
    // Login modal elements
    const loginModal = document.getElementById('login-modal');
    const loginEmailInput = document.getElementById('login-email');
    const loginPasswordInput = document.getElementById('login-password');
    const loginSubmitButton = document.getElementById('login-submit');
    const loginError = document.getElementById('login-error');
    const toRegisterLink = document.getElementById('to-register');
    
    // Register modal elements
    const registerModal = document.getElementById('register-modal');
    const registerEmailInput = document.getElementById('register-email');
    const registerPasswordInput = document.getElementById('register-password');
    const registerPasswordConfirmInput = document.getElementById('register-password-confirm');
    const registerSubmitButton = document.getElementById('register-submit');
    const registerError = document.getElementById('register-error');
    const toLoginLink = document.getElementById('to-login');
    
    // Auth required modal elements
    const authRequiredModal = document.getElementById('auth-required-modal');
    const authRequiredLoginButton = document.getElementById('auth-required-login');
    const authRequiredRegisterButton = document.getElementById('auth-required-register');
    
    // All modal close buttons
    const closeButtons = document.querySelectorAll('.auth-close-button');
    
    // Authentication state
    let authState = {
        isAuthenticated: false,
        user: null,
        token: null,
        anonymousId: null,
        usageCount: 0,
        remainingUsage: 3
    };
    
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
    const downloadBtn = document.getElementById('download-btn');
    
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
    
    // Constants
    const MAX_ANONYMOUS_USAGE = 3;
    const AUTH_TOKEN_KEY = 'redesign_auth_token';
    
    // Auth utility functions
    function saveAuthToken(token) {
        localStorage.setItem(AUTH_TOKEN_KEY, token);
        authState.token = token;
    }
    
    function getAuthToken() {
        return localStorage.getItem(AUTH_TOKEN_KEY);
    }
    
    function clearAuthToken() {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        authState.token = null;
    }
    
    function updateAuthUI() {
        if (authState.isAuthenticated) {
            authButtons.classList.add('hidden');
            userInfo.classList.remove('hidden');
            userEmail.textContent = authState.user.email;
            usageInfo.classList.add('hidden');
        } else {
            authButtons.classList.remove('hidden');
            userInfo.classList.add('hidden');
            if (authState.remainingUsage !== 'unlimited') {
                usageInfo.classList.remove('hidden');
                redesignsCount.textContent = authState.remainingUsage;
            } else {
                usageInfo.classList.add('hidden');
            }
        }
    }
    
    // Check authentication status on load
    async function checkAuthStatus() {
        const token = getAuthToken();
        
        if (token) {
            try {
                // Verify token with backend
                const response = await fetch('/api/auth/user', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const userData = await response.json();
                    authState.isAuthenticated = true;
                    authState.user = userData.user;
                    authState.token = token;
                    authState.remainingUsage = 'unlimited';
                } else {
                    // Token invalid or expired
                    clearAuthToken();
                }
            } catch (error) {
                console.error('Error checking authentication status:', error);
                clearAuthToken();
            }
        }
        
        // If not authenticated, check anonymous usage
        if (!authState.isAuthenticated) {
            try {
                const response = await fetch('/api/usage/count');
                const data = await response.json();
                
                authState.anonymousId = data.anonymousId;
                authState.usageCount = data.usage_count;
                authState.remainingUsage = data.remaining;
                
                if (data.authenticated) {
                    authState.isAuthenticated = true;
                    // Need to get user details separately
                    checkAuthStatus();
                }
            } catch (error) {
                console.error('Error checking usage count:', error);
            }
        }
        
        // Update UI based on auth state
        updateAuthUI();
    }
    
    // Initialize auth status
    checkAuthStatus();
    
    // Modal Management
    function showModal(modal) {
        // Hide any other open modals
        document.querySelectorAll('.auth-modal').forEach(m => {
            m.classList.add('hidden');
            m.classList.remove('visible');
        });
        
        // Show this modal
        modal.classList.remove('hidden');
        // Trigger animation
        setTimeout(() => {
            modal.classList.add('visible');
        }, 10);
        
        // Add body class to prevent scrolling
        document.body.classList.add('modal-open');
    }
    
    function hideModal(modal) {
        // Hide animation
        modal.classList.remove('visible');
        
        // Actually hide after transition
        setTimeout(() => {
            modal.classList.add('hidden');
            // Remove body class to allow scrolling
            document.body.classList.remove('modal-open');
        }, 300);
    }
    
    // Show login modal
    loginButton.addEventListener('click', () => {
        showModal(loginModal);
        loginEmailInput.focus();
    });
    
    // Show register modal
    registerButton.addEventListener('click', () => {
        showModal(registerModal);
        registerEmailInput.focus();
    });
    
    // Switch between login and register
    toRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        hideModal(loginModal);
        setTimeout(() => {
            showModal(registerModal);
            registerEmailInput.focus();
        }, 300);
    });
    
    // Switch between register and login
    toLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        hideModal(registerModal);
        setTimeout(() => {
            showModal(loginModal);
            loginEmailInput.focus();
        }, 300);
    });
    
    // Auth required modal buttons
    authRequiredLoginButton.addEventListener('click', () => {
        hideModal(authRequiredModal);
        setTimeout(() => {
            showModal(loginModal);
        }, 300);
    });
    
    authRequiredRegisterButton.addEventListener('click', () => {
        hideModal(authRequiredModal);
        setTimeout(() => {
            showModal(registerModal);
        }, 300);
    });
    
    // Close modals with close button
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.auth-modal');
            hideModal(modal);
        });
    });
    
    // Close modals when clicking outside
    document.querySelectorAll('.auth-modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal(modal);
            }
        });
    });
    
    // Login form submission
    loginSubmitButton.addEventListener('click', async () => {
        const email = loginEmailInput.value.trim();
        const password = loginPasswordInput.value.trim();
        
        // Reset error
        loginError.textContent = '';
        
        // Basic validation
        if (!email || !password) {
            loginError.textContent = 'Please enter both email and password';
            return;
        }
        
        try {
            // Disable button and show loading
            loginSubmitButton.disabled = true;
            loginSubmitButton.textContent = 'Logging in...';
            
            // Send login request
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Save token and update auth state
                saveAuthToken(data.access_token);
                authState.isAuthenticated = true;
                authState.user = data.user;
                
                // Update UI
                updateAuthUI();
                
                // Close modal
                hideModal(loginModal);
                
                // Clear form
                loginEmailInput.value = '';
                loginPasswordInput.value = '';
                
                // Show success message
                showAlert('Logged in successfully', false);
            } else {
                // Show error
                loginError.textContent = data.error || 'Login failed';
            }
        } catch (error) {
            console.error('Login error:', error);
            loginError.textContent = 'An error occurred. Please try again.';
        } finally {
            // Re-enable button
            loginSubmitButton.disabled = false;
            loginSubmitButton.textContent = 'Login';
        }
    });
    
    // Register form submission
    registerSubmitButton.addEventListener('click', async () => {
        const email = registerEmailInput.value.trim();
        const password = registerPasswordInput.value.trim();
        const passwordConfirm = registerPasswordConfirmInput.value.trim();
        
        // Reset error
        registerError.textContent = '';
        
        // Basic validation
        if (!email || !password || !passwordConfirm) {
            registerError.textContent = 'Please fill out all fields';
            return;
        }
        
        // Password match validation
        if (password !== passwordConfirm) {
            registerError.textContent = 'Passwords do not match';
            return;
        }
        
        // Password strength validation
        const hasUppercase = /[A-Z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const isLongEnough = password.length >= 8;
        
        if (!hasUppercase || !hasNumber || !isLongEnough) {
            registerError.textContent = 'Password must be at least 8 characters with one uppercase letter and one number';
            return;
        }
        
        try {
            // Disable button and show loading
            registerSubmitButton.disabled = true;
            registerSubmitButton.textContent = 'Creating account...';
            
            // Send register request
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Save token and update auth state
                saveAuthToken(data.access_token);
                authState.isAuthenticated = true;
                authState.user = data.user;
                
                // Update UI
                updateAuthUI();
                
                // Close modal
                hideModal(registerModal);
                
                // Clear form
                registerEmailInput.value = '';
                registerPasswordInput.value = '';
                registerPasswordConfirmInput.value = '';
                
                // Show success message
                showAlert('Account created successfully', false);
            } else {
                // Show error
                registerError.textContent = data.error || 'Registration failed';
            }
        } catch (error) {
            console.error('Registration error:', error);
            registerError.textContent = 'An error occurred. Please try again.';
        } finally {
            // Re-enable button
            registerSubmitButton.disabled = false;
            registerSubmitButton.textContent = 'Register';
        }
    });
    
    // Logout handler
    logoutButton.addEventListener('click', async () => {
        try {
            // Call logout endpoint
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authState.token}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        // Clear local auth state regardless of API response
        clearAuthToken();
        authState.isAuthenticated = false;
        authState.user = null;
        
        // Check anonymous usage again
        checkAuthStatus();
        
        // Show success message
        showAlert('Logged out successfully', false);
    });
    
    // Handle authentication error responses
    function handleAuthError(error) {
        if (error && error.code === 'AUTH_REQUIRED') {
            showModal(authRequiredModal);
            return true;
        }
        return false;
    }
    
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
        updateDownloadButtonState();
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
            
            // Force the border radius on the original image
            beforeElements.image.style.borderRadius = '8px';
            
            // Show the comparison indicator
            if (comparisonIndicator) {
                comparisonIndicator.classList.remove('hidden');
                
                // Set a timeout to fade it out
                setTimeout(() => {
                    comparisonIndicator.classList.add('fade-out');
                }, 1500);
            }
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
        // Stop loading animations
        stopLoadingTextCycle();
        
        // Hide loading elements
        redesignLoading.classList.add('hidden');
        loadingContainer.classList.add('hidden');
        
        // Show upload elements
        uploadSectionContainer.classList.remove('hidden');
        redesignButtonContainer.classList.remove('hidden');
        instructionsContainer.classList.remove('hidden');
        
        // Reset processing state
        isProcessing = false;
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
                suggestionStatuses[i].classList.remove('loading');
                suggestionStatuses[i].classList.add('completed');
            }
            
            // Show this step as loading - replaces active with loading
            suggestionStatuses[suggestionIndex].classList.remove('active');
            suggestionStatuses[suggestionIndex].classList.add('loading');
            
            // Show result as loading
            resultPlaceholder.classList.add('hidden');
            resultImage.classList.add('hidden');
            resultLoadingSpinner.classList.remove('hidden');
            
            // Use URL directly if sourceImage is a string URL
            let formData = new FormData();
            let imageFile;
            
            // Handle different sourceImage types
            if (typeof sourceImage === 'string') {
                // It's a URL - need to fetch it and convert to file
                console.log('Source is a URL, fetching...');
                try {
                    const response = await fetch(sourceImage);
                    const blob = await response.blob();
                    imageFile = new File([blob], "processed_image.jpg", { type: 'image/jpeg' });
                } catch (e) {
                    console.error('Error fetching source image:', e);
                    throw new Error('Could not load source image');
                }
            } else if (sourceImage instanceof File) {
                // It's already a file
                imageFile = sourceImage;
            } else {
                throw new Error('Invalid source image format');
            }
            
            // Add image and suggestion text to form data
            formData.append('image', imageFile);
            formData.append('message', suggestionText);
            
            // Prepare headers for authentication
            const headers = {};
            if (authState.token) {
                headers['Authorization'] = `Bearer ${authState.token}`;
            }
            
            // Show loading spinner in corner while processing
            cornerLoadingSpinner.classList.remove('hidden');
            
            // Make the API request with proper authentication
            console.log('Sending suggestion to API');
            const response = await fetch('/api/chat-with-image', {
                method: 'POST',
                headers: headers,
                body: formData
            });
            
            const data = await response.json();
            
            // Handle errors
            if (!response.ok) {
                throw new Error(data.error || 'Failed to process suggestion');
            }
            
            // Hide corner spinner
            cornerLoadingSpinner.classList.add('hidden');
            
            // Log response
            console.log('Received response:', data);
            
            // Update UI with the image result
            if (data.images && data.images.length > 0) {
                const imageUrl = data.images[0];
                resultImage.src = imageUrl;
                resultImage.classList.remove('hidden');
                resultLoadingSpinner.classList.add('hidden');
                
                // Update the "before after" comparison if available
                setupBeforeAfterComparison();
                
                // Save the generated image to history
                generatedImagesHistory.push({
                    index: suggestionIndex,
                    imageUrl: imageUrl,
                    description: suggestionText
                });
                
                // Update download button state
                updateDownloadButtonState();
                
                // Mark this suggestion as completed
                suggestionStatuses[suggestionIndex].classList.remove('loading');
                suggestionStatuses[suggestionIndex].classList.add('completed');
                
                // Activate next suggestion if available
                if (suggestionIndex < suggestionStatuses.length - 1) {
                    suggestionStatuses[suggestionIndex + 1].classList.add('active');
                }
                
                // Return success
                return {
                    success: true,
                    resultImageUrl: imageUrl
                };
            } else {
                throw new Error('No image was generated');
            }
        } catch (error) {
            console.error(`Error processing suggestion ${suggestionIndex + 1}:`, error);
            
            // Update UI to show error state
            suggestionStatuses[suggestionIndex].classList.remove('loading');
            suggestionStatuses[suggestionIndex].classList.add('error');
            
            // Hide corner spinner
            cornerLoadingSpinner.classList.add('hidden');
            
            // Show placeholder for error
            resultLoadingSpinner.classList.add('hidden');
            resultPlaceholder.classList.remove('hidden');
            
            // Return failure
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    // Generate suggestions from Claude and process them with Gemini
    async function runRedesignProcess() {
        if (isProcessing || !originalSelectedImage || !inspirationSelectedImage) {
            return;
        }
        
        // Check if we need to authenticate
        if (!authState.isAuthenticated && (authState.remainingUsage <= 0)) {
            console.log('No remaining usage, showing auth required modal');
            showModal(authRequiredModal);
            return;
        }
        
        try {
            isProcessing = true;
            console.log('Starting redesign process');
            
            // Hide content, show loading
            uploadSectionContainer.classList.add('hidden');
            redesignButtonContainer.classList.add('hidden');
            redesignLoading.classList.remove('hidden');
            instructionsContainer.classList.add('hidden');
            loadingContainer.classList.remove('hidden');
            
            // Start loading animation
            startLoadingTextCycle();
            
            // Reset state
            generatedImagesHistory = [];
            suggestions = [];
            currentSuggestionIndex = 0;
            
            // Reset UI
            document.querySelectorAll('.suggestion-status').forEach(el => {
                el.classList.remove('active', 'completed', 'loading');
            });
            document.querySelectorAll('.suggestion-text').forEach(el => {
                el.textContent = '';
            });
            
            // Create form data with both images
            const formData = new FormData();
            formData.append('original', originalSelectedImage);
            formData.append('inspiration', inspirationSelectedImage);
            
            // Prepare headers for authentication
            const headers = {};
            if (authState.token) {
                headers['Authorization'] = `Bearer ${authState.token}`;
            }
            
            // Get suggestions from the server
            console.log('Fetching redesign suggestions');
            
            // Use a timeout promise to handle long requests
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Request timed out after 120 seconds')), 120000);
            });
            
            const fetchPromise = fetch('/api/claude-suggestions', {
                method: 'POST',
                headers: headers,
                body: formData
            });
            
            // Race the fetch against the timeout
            const response = await Promise.race([fetchPromise, timeoutPromise]);
            
            // Handle possible 401 unauthorized
            if (response.status === 401) {
                const data = await response.json();
                console.log('Authentication required:', data);
                isProcessing = false;
                redesignLoading.classList.add('hidden');
                uploadSectionContainer.classList.remove('hidden');
                redesignButtonContainer.classList.remove('hidden');
                instructionsContainer.classList.remove('hidden');
                loadingContainer.classList.add('hidden');
                stopLoadingTextCycle();
                
                if (data.error === 'ANONYMOUS_USAGE_LIMIT') {
                    showModal(authRequiredModal);
                } else {
                    // Token might be expired, clear it and update UI
                    clearAuthToken();
                    authState.isAuthenticated = false;
                    authState.user = null;
                    updateAuthUI();
                    showModal(authRequiredModal);
                }
                return;
            }
            
            // Handle server errors
            if (!response.ok) {
                let errorMessage = 'Server error occurred';
                
                try {
                    // Try to get the error message from the response
                    const errorData = await response.json();
                    errorMessage = errorData.error || `Server error: ${response.status}`;
                    console.error('API error:', errorData);
                } catch (e) {
                    // If cannot parse JSON, use status text
                    errorMessage = `Server error: ${response.status} ${response.statusText}`;
                    console.error('API error:', response.status, response.statusText);
                }
                
                // Show error alert and reset UI
                showAlert(`Error: ${errorMessage}`, true);
                resetProcessing();
                return;
            }
            
            // Parse JSON response
            let data;
            try {
                data = await response.json();
            } catch (e) {
                console.error('Error parsing response:', e);
                showAlert('Error: Unable to parse server response. Please try again.', true);
                resetProcessing();
                return;
            }
            
            // Use the suggestions
            suggestions = data.suggestions;
            console.log('Received suggestions:', suggestions);
            
            // Update the UI with suggestions
            suggestionsPlaceholder.classList.add('hidden');
            
            for (let i = 0; i < suggestions.length; i++) {
                const suggestion = suggestions[i];
                suggestionTexts[i].textContent = suggestion.title;
            }
            
            // Activate the first suggestion
            suggestionStatuses[0].classList.add('active');
            suggestionsClickHint.classList.remove('hidden');
            
            // Show results container
            resultsContainer.classList.remove('hidden');
            
            // Update usage count
            checkAuthStatus();
            
            // Process first suggestion automatically
            await processSuggestion(originalImageUrl, suggestions[0].description, 0);
            
        } catch (error) {
            console.error('Error in redesign process:', error);
            
            // Hide loading indicators
            redesignLoading.classList.add('hidden');
            loadingContainer.classList.add('hidden');
            stopLoadingTextCycle();
            
            // Show upload sections again
            uploadSectionContainer.classList.remove('hidden');
            redesignButtonContainer.classList.remove('hidden');
            instructionsContainer.classList.remove('hidden');
            
            // Show error message
            let errorMessage = error.message || 'An unexpected error occurred';
            if (errorMessage.includes('timed out')) {
                errorMessage = 'The server took too long to respond. Please try again later.';
            }
            
            showAlert(`Error: ${errorMessage}`, true);
            
            isProcessing = false;
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

    // Define updateDownloadButtonState function
    function updateDownloadButtonState() {
        if (downloadBtn) {
            downloadBtn.disabled = !(
                generatedImagesHistory.length > 0 && 
                resultImage.src && 
                suggestions.length > 0
            );
            
            if (downloadBtn.disabled) {
                downloadBtn.style.display = 'none';
            } else {
                downloadBtn.style.display = 'flex';
            }
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

    // Add event listener for download button
    if (downloadBtn) {
        downloadBtn.addEventListener('click', saveResults);
    }

    // Function to save results
    function saveResults() {
        if (!generatedImagesHistory || generatedImagesHistory.length === 0) {
            console.error('No results to save');
            return;
        }
        
        // Find the currently selected suggestion
        let selectedIndex = 0;
        suggestionStatuses.forEach((status, index) => {
            if (status.classList.contains('selected')) {
                selectedIndex = index;
            }
        });
        
        // Get the selected image URL
        const selectedImage = generatedImagesHistory[selectedIndex];
        if (!selectedImage || !selectedImage.imageUrl) {
            console.error('No image URL found for the selected suggestion');
            return;
        }
        
        // Disable download button during processing
        downloadBtn.disabled = true;
        
        // Request headers with auth
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add auth token if available
        if (authState.token) {
            headers['Authorization'] = `Bearer ${authState.token}`;
        }
        
        // Send the save request to the server
        fetch('/api/save-results', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                result_image: selectedImage.imageUrl,
                suggestions: suggestions
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Create a link to download the file
                const link = document.createElement('a');
                link.href = data.download_url;
                link.download = 'redesign_result.jpg';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Copy text to clipboard if supported
                if (data.clipboard_content && navigator.clipboard) {
                    navigator.clipboard.writeText(data.clipboard_content)
                        .then(() => {
                            console.log('Suggestions copied to clipboard');
                        })
                        .catch(err => {
                            console.error('Could not copy text: ', err);
                        });
                }
                
                showAlert('Image saved successfully', false);
            } else {
                showAlert('Error: ' + (data.error || 'Could not save the image'), true);
            }
        })
        .catch(error => {
            console.error('Error saving results:', error);
            showAlert('Error: Could not save the image', true);
        })
        .finally(() => {
            // Re-enable download button
            downloadBtn.disabled = false;
        });
    }
}); 