document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const loginContainer = document.getElementById('loginContainer');
    const mainApp = document.getElementById('mainApp');
    const loginForm = document.getElementById('loginForm');
    const moodContainer = document.getElementById('moodContainer');
    const logoutBtn = document.getElementById('logoutBtn');

    // 4 mood options arranged in a row: high energy happy, low energy happy, low energy sad, high energy sad/angry
    const moods = [
        { emoji: '🤩', description: 'Excited', position: 1, question: 'What are you most excited about right now?' },
        { emoji: '😌', description: 'Content', position: 2, question: 'What made you feel satisfied today?' },
        { emoji: '😔', description: 'Down', position: 3, question: 'What\'s weighing on your mind today?' },
        { emoji: '😡', description: 'Angry', position: 4, question: 'What triggered this anger? How can we help you process it?' }
    ];

    // Activities options
    const activities = [
        { emoji: '💼', label: 'Work' },
        { emoji: '🏃‍♂️', label: 'Exercise' },
        { emoji: '🍳', label: 'Cooking' },
        { emoji: '📚', label: 'Reading' },
        { emoji: '👥', label: 'Socializing' },
        { emoji: '🎵', label: 'Music' },
        { emoji: '🎮', label: 'Gaming' },
        { emoji: '🧘‍♀️', label: 'Meditation' },
        { emoji: '🛒', label: 'Shopping' },
        { emoji: '🎨', label: 'Creative' },
        { emoji: '📱', label: 'Social Media' },
        { emoji: '🚗', label: 'Commuting' }
    ];

    // Sleep quality options
    const sleepOptions = [
        { emoji: '😴', label: 'Great Sleep', value: 'great' },
        { emoji: '😊', label: 'Good Sleep', value: 'good' },
        { emoji: '😐', label: 'Okay Sleep', value: 'okay' },
        { emoji: '😵', label: 'Poor Sleep', value: 'poor' }
    ];

    // Rating options for previous recommendations
    const ratingOptions = [
        { emoji: '⭐', label: 'Excellent', value: 'excellent' },
        { emoji: '👍', label: 'Good', value: 'good' },
        { emoji: '👌', label: 'Okay', value: 'okay' },
        { emoji: '👎', label: 'Not Helpful', value: 'poor' }
    ];

    // Emotion elaboration options for each mood
    const emotionElaborations = {
        'Excited': [
            { emoji: '⚡', description: 'Energetic', question: 'What\'s giving you this burst of energy today?' },
            { emoji: '🌟', description: 'Euphoric', question: 'What amazing thing happened that made you feel this way?' },
            { emoji: '🚀', description: 'Motivated', question: 'What goals or projects are driving your motivation right now?' },
            { emoji: '💡', description: 'Inspired', question: 'What or who has inspired you today?' }
        ],
        'Content': [
            { emoji: '🕊️', description: 'Peaceful', question: 'What\'s bringing you this sense of peace and calm?' },
            { emoji: '🙏', description: 'Grateful', question: 'What are you feeling most grateful for right now?' },
            { emoji: '😌', description: 'Relaxed', question: 'What helped you feel so relaxed and at ease today?' },
            { emoji: '🌅', description: 'Hopeful', question: 'What are you looking forward to or feeling hopeful about?' }
        ],
        'Down': [
            { emoji: '🌧️', description: 'Melancholy', question: 'What\'s been weighing on your mind lately?' },
            { emoji: '💔', description: 'Lonely', question: 'What would help you feel more connected right now?' },
            { emoji: '🌊', description: 'Overwhelmed', question: 'What\'s making you feel like there\'s too much to handle?' },
            { emoji: '😴', description: 'Tired', question: 'What\'s been draining your energy recently?' }
        ],
        'Angry': [
            { emoji: '😠', description: 'Frustrated', question: 'What situation or challenge is causing this frustration?' },
            { emoji: '🔥', description: 'Resentful', question: 'What\'s making you feel resentful, and how long have you felt this way?' },
            { emoji: '😤', description: 'Annoyed', question: 'What specific things have been getting under your skin today?' },
            { emoji: '⚔️', description: 'Betrayed', question: 'What happened that made you feel betrayed or let down?' }
        ]
    };

    let selectedMood = null;
    let selectedActivities = [];
    let selectedSleep = null;
    let selectedEmotionElaboration = null;
    let selectedRating = null;

    // Check if user is already logged in
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const currentUser = localStorage.getItem('currentUser');
    
    if (isLoggedIn === 'true' && currentUser) {
        showMainApp();
    } else {
        showLogin();
    }

    // Login form submission
    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const userId = document.getElementById('userId').value;
        const password = document.getElementById('password').value;
        
        if (userId && password) {
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentUser', userId);
            showMainApp();
        } else {
            alert('Please enter both User ID and Password');
        }
    });

    // Logout functionality
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('currentUser');
        resetAppState();
        showLogin();
        
    });

    function showLogin() {
        loginContainer.style.display = 'flex';
        mainApp.style.display = 'none';
        document.getElementById('userId').value = '';
        document.getElementById('password').value = '';
    }

    function showMainApp() {
        loginContainer.style.display = 'none';
        mainApp.style.display = 'block';
        resetAppState();
        
        const currentUser = localStorage.getItem('currentUser');
        if (currentUser) {
            document.querySelector('#mainApp h1').textContent = `How are you feeling today, ${currentUser}?`;
        }
        
        createMoodButtons();
    }

    function resetAppState() {
        selectedMood = null;
        selectedActivities = [];
        selectedSleep = null;
        selectedEmotionElaboration = null;
        document.getElementById('selectedMoodDisplay').style.display = 'none';
        document.getElementById('activitiesPage').style.display = 'none';
        moodContainer.style.display = 'grid';
        
        const userResponseInput = document.getElementById('userResponse');
        if (userResponseInput) {
            userResponseInput.value = '';
        }
    }

    function createMoodButtons() {
        moodContainer.innerHTML = '';
        
        moods.forEach((mood) => {
            const button = document.createElement('button');
            button.className = 'mood-option';
            button.textContent = mood.emoji;
            button.setAttribute('aria-label', mood.description);
            button.setAttribute('data-description', mood.description);
            
            // Position in single row (1 to 4)
            button.style.gridArea = `1 / ${mood.position}`;
            
            // Add hover tooltip
            button.addEventListener('mouseenter', () => {
                moodContainer.setAttribute('data-tooltip', mood.description);
                moodContainer.classList.add('show-tooltip');
            });
            
            button.addEventListener('mouseleave', () => {
                moodContainer.classList.remove('show-tooltip');
            });
            
            // Click handler
            button.addEventListener('click', () => {
                document.querySelectorAll('.mood-option').forEach(btn => {
                    btn.classList.remove('selected');
                });
                
                button.classList.add('selected');
                selectedMood = mood;
                showActivitiesPage(mood);
            });
            
            moodContainer.appendChild(button);
        });
    }

    function showActivitiesPage(mood) {
        // Update activities page header
        document.getElementById('activitiesEmoji').textContent = mood.emoji;
        document.getElementById('activitiesMoodName').textContent = mood.description;
        
        // Hide mood container and show activities page
        moodContainer.style.display = 'none';
        document.getElementById('activitiesPage').style.display = 'block';
        
        // Create emotion elaboration, activity, sleep, and rating buttons
        createEmotionElaborationButtons(mood);
        createActivityButtons();
        createSleepButtons();
        createRatingButtons();
    }

    function showSelectedMood(mood) {
        // Use emotion elaboration if available, otherwise fall back to original mood
        const displayMood = selectedEmotionElaboration || mood;
        
        document.getElementById('selectedEmoji').textContent = displayMood.emoji;
        document.getElementById('selectedMoodName').textContent = displayMood.description;
        document.getElementById('followUpQuestion').textContent = displayMood.question || mood.question;
        
        document.getElementById('activitiesPage').style.display = 'none';
        document.getElementById('selectedMoodDisplay').style.display = 'block';
        
        setTimeout(() => {
            document.getElementById('userResponse').focus();
        }, 300);
    }

    function createActivityButtons() {
        const activitiesGrid = document.getElementById('activitiesGrid');
        activitiesGrid.innerHTML = '';
        
        activities.forEach((activity) => {
            const button = document.createElement('button');
            button.className = 'activity-option';
            button.innerHTML = `
                <span class="activity-emoji">${activity.emoji}</span>
                <span class="activity-label">${activity.label}</span>
            `;
            
            button.addEventListener('click', () => {
                button.classList.toggle('selected');
                
                if (button.classList.contains('selected')) {
                    if (!selectedActivities.includes(activity.label)) {
                        selectedActivities.push(activity.label);
                    }
                } else {
                    selectedActivities = selectedActivities.filter(a => a !== activity.label);
                }
            });
            
            activitiesGrid.appendChild(button);
        });
    }

    function createSleepButtons() {
        const sleepOptionsContainer = document.getElementById('sleepOptions');
        sleepOptionsContainer.innerHTML = '';
        
        sleepOptions.forEach((sleep) => {
            const button = document.createElement('button');
            button.className = 'sleep-option';
            button.innerHTML = `
                <span class="sleep-emoji">${sleep.emoji}</span>
                <span class="sleep-label">${sleep.label}</span>
            `;
            
            button.addEventListener('click', () => {
                // Remove selected from all sleep options
                document.querySelectorAll('.sleep-option').forEach(btn => {
                    btn.classList.remove('selected');
                });
                
                // Add selected to clicked option
                button.classList.add('selected');
                selectedSleep = sleep.value;
            });
            
            sleepOptionsContainer.appendChild(button);
        });
    }

    function createEmotionElaborationButtons(mood) {
        const emotionOptionsContainer = document.getElementById('emotionOptions');
        emotionOptionsContainer.innerHTML = '';
        
        const elaborations = emotionElaborations[mood.description] || [mood.description];
        
        elaborations.forEach((emotion) => {
            const button = document.createElement('button');
            button.className = 'emotion-option';
            button.innerHTML = `${emotion.emoji} ${emotion.description}`;
            
            button.addEventListener('click', () => {
                // Remove selected from all emotion options
                document.querySelectorAll('.emotion-option').forEach(btn => {
                    btn.classList.remove('selected');
                });
                
                // Add selected to clicked option
                button.classList.add('selected');
                selectedEmotionElaboration = emotion;
            });
            
            emotionOptionsContainer.appendChild(button);
        });
    }

    function createRatingButtons() {
        const ratingOptionsContainer = document.getElementById('ratingOptions');
        ratingOptionsContainer.innerHTML = '';
        
        ratingOptions.forEach((rating) => {
            const button = document.createElement('button');
            button.className = 'rating-option';
            button.innerHTML = `
                <span class="rating-emoji">${rating.emoji}</span>
                <span class="rating-label">${rating.label}</span>
            `;
            
            button.addEventListener('click', () => {
                // Remove selected from all rating options
                document.querySelectorAll('.rating-option').forEach(btn => {
                    btn.classList.remove('selected');
                });
                
                // Add selected to clicked option
                button.classList.add('selected');
                selectedRating = rating.value;
            });
            
            ratingOptionsContainer.appendChild(button);
        });
    }

    // Activities page navigation buttons
    document.getElementById('activitiesBackButton').addEventListener('click', () => {
        document.getElementById('activitiesPage').style.display = 'none';
        moodContainer.style.display = 'grid';
        selectedMood = null;
        selectedActivities = [];
        selectedSleep = null;
        
        document.querySelectorAll('.mood-option').forEach(btn => {
            btn.classList.remove('selected');
        });
    });

    document.getElementById('activitiesSkipButton').addEventListener('click', () => {
        if (selectedMood) {
            showSelectedMood(selectedMood);
        }
    });

    // Next button functionality
    document.getElementById('activitiesNextButton').addEventListener('click', () => {
        if (selectedMood) {
            showSelectedMood(selectedMood);
        }
    });

    // Chat page navigation buttons
    document.getElementById('backButton').addEventListener('click', () => {
        document.getElementById('selectedMoodDisplay').style.display = 'none';
        document.getElementById('activitiesPage').style.display = 'block';
        document.getElementById('userResponse').value = '';
    });

    document.getElementById('doneButton').addEventListener('click', () => {
        if (selectedMood) {
            saveMoodWithActivities(selectedMood, selectedActivities, selectedSleep);
            alert('Your mood has been logged. Thank you!');
        }
    });

    document.getElementById('submitResponse').addEventListener('click', () => {
        const userResponse = document.getElementById('userResponse').value.trim();
        if (userResponse) {
            saveResponseWithActivities(selectedMood, selectedActivities, selectedSleep, userResponse);
            alert('Thank you for sharing! Your response has been saved.');
        } else {
            alert('Please share your thoughts before submitting.');
        }
    });

    function saveMoodWithActivities(mood, activities, sleep) {
        const timestamp = new Date().toISOString();
        const moodEntry = {
            mood: mood.description,
            emotionElaboration: selectedEmotionElaboration,
            emoji: mood.emoji,
            activities: activities,
            sleep: sleep,
            timestamp: timestamp
        };
        
        const entries = JSON.parse(localStorage.getItem('moodEntries') || '[]');
        entries.push(moodEntry);
        localStorage.setItem('moodEntries', JSON.stringify(entries.slice(-100)));
    }

    function saveResponseWithActivities(mood, activities, sleep, response) {
        const timestamp = new Date().toISOString();
        const responseEntry = {
            mood: mood.description,
            emotionElaboration: selectedEmotionElaboration,
            emoji: mood.emoji,
            question: mood.question,
            activities: activities,
            sleep: sleep,
            response: response,
            timestamp: timestamp
        };
        
        const responses = JSON.parse(localStorage.getItem('moodResponses') || '[]');
        responses.push(responseEntry);
        localStorage.setItem('moodResponses', JSON.stringify(responses.slice(-50)));
    }
});
