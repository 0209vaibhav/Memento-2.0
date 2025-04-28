// ========== NAVIGATION HANDLING ==========

document.addEventListener('DOMContentLoaded', function() {
    // Get all explorer tab buttons
    const explorerTabButtons = document.querySelectorAll('.explorer-tab-btn');
    
    // Get all containers
    const containers = {
        'profile': document.querySelector('.profile-container'),
        'archive': document.querySelector('#archive-container'),
        'my-mementos': document.querySelector('.my-mementos-container'),
        'capture': document.querySelector('#journey-capture-form'),
        'drafts': document.querySelector('#journey-drafts-container'),
        'live-feed': document.querySelector('.live-feed-container'),
        'filter': document.querySelector('.filter-settings-container'),
        'curated': document.querySelector('.curated-container')
    };

    // Function to hide all containers
    function hideAllContainers() {
        Object.values(containers).forEach(container => {
            if (container) {
                container.classList.add('hidden');
            }
        });
    }

    // Function to show selected container
    function showContainer(tabName) {
        hideAllContainers();
        const container = containers[tabName];
        if (container) {
            container.classList.remove('hidden');
        }
    }

    // Add click event listeners to all explorer tab buttons
    explorerTabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            explorerTabButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the tab name from data-tab attribute
            const tabName = this.getAttribute('data-tab');
            
            // Show the corresponding container
            showContainer(tabName);
        });
    });

    // Handle main activity tab switching
    const activityTabs = document.querySelectorAll('.activity-tab');
    const explorerSubtabs = document.querySelectorAll('.explorer-subtabs');

    activityTabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all activity tabs
            activityTabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Hide all subtabs
            explorerSubtabs.forEach(subtabs => subtabs.classList.add('hidden'));
            
            // Show subtabs for clicked activity
            const subtabs = this.nextElementSibling;
            if (subtabs && subtabs.classList.contains('explorer-subtabs')) {
                subtabs.classList.remove('hidden');
            }
        });
    });
});
