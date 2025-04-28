// Firebase Collection Initialization
async function initializeFirebase() {
    const firestore = firebase.firestore();
    
    // Get the current user
    const user = firebase.auth().currentUser;
    if (!user) {
        showToast('Please sign in to initialize Firebase collections', 'error');
        return;
    }

    try {
        // First check if we can access the users collection
        const userRef = firestore.collection('users').doc(user.uid);
        try {
            await userRef.get();
        } catch (error) {
            if (error.code === 'permission-denied') {
                showToast('Please update your Firestore rules to allow user access', 'error');
                return;
            }
            throw error;
        }

        // Initialize user document if it doesn't exist
        if (!(await userRef.get()).exists) {
            try {
                await userRef.set({
                    displayName: user.displayName || '',
                    email: user.email || '',
                    photoURL: user.photoURL || '',
                    createdAt: firebase.firestore.FieldValue.serverTimestamp()
                });
            } catch (error) {
                if (error.code === 'permission-denied') {
                    showToast('Unable to create user profile. Please check Firebase rules.', 'error');
                    return;
                }
                throw error;
            }
        }

        showToast('Firebase collections initialized successfully!', 'success');
    } catch (error) {
        console.error('Error initializing Firebase:', error);
        if (error.code === 'permission-denied') {
            showToast('Permission denied. Please check your Firebase rules in the console.', 'error');
        } else {
            showToast(`Error initializing Firebase: ${error.message}`, 'error');
        }
    }
}

// Add initialization button to the settings panel
function addInitButton() {
    const settingsPanel = document.querySelector('.settings-container');
    if (settingsPanel) {
        const setupSection = document.createElement('div');
        setupSection.className = 'settings-section';
        setupSection.innerHTML = `
            <h3>Firebase Setup</h3>
            <div class="setting-item">
                <button id="init-firebase" class="settings-button primary">
                    Initialize Firebase Collections
                </button>
                <p class="setting-description">
                    Click to set up your Firebase collections and initial data.
                </p>
            </div>
        `;
        settingsPanel.appendChild(setupSection);

        // Add click event listener
        document.getElementById('init-firebase').addEventListener('click', initializeFirebase);
    }
}

// Initialize setup when document is ready
document.addEventListener('DOMContentLoaded', addInitButton); 