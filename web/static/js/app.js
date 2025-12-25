// Minimal JS setup
console.log('App.js loaded v0.5.6');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            sections.forEach(s => s.classList.add('hidden'));
            
            const targetId = tab.dataset.target;
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.remove('hidden');
            }
        });
    });

    // --- Modal Logic ---
    
    function openModal(modalId) {
        console.log('Opening modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            // Support legacy 'active' class used in settings_form.html
            modal.classList.add('active');
        } else {
            console.error('Modal element not found:', modalId);
        }
    }

    function closeModal(modalId) {
        console.log('Closing modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.classList.remove('active');
        }
    }

    // Help Modal
    const helpBtn = document.getElementById('help-btn');
    if (helpBtn) {
        helpBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('help-modal');
        });
    }

    const closeHelpBtn = document.querySelector('#help-modal .close-modal-btn');
    if (closeHelpBtn) {
        closeHelpBtn.addEventListener('click', () => closeModal('help-modal'));
    }

    // Upload Modal
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('upload-modal');
        });
    }

    // Close buttons for Upload Modal
    const closeUploadBtns = [
        document.getElementById('close-upload-modal-btn'),
        document.getElementById('x-close-upload-modal-btn')
    ];
    closeUploadBtns.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => closeModal('upload-modal'));
        }
    });

    // Close any modal when clicking overlay
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('show');
                overlay.classList.remove('active');
            }
        });
    });
});

// Legacy support for member modal in settings_form.html
function openMemberModal(name, minDaysDay, minDaysNight) {
    const modal = document.getElementById('member-modal');
    if (modal) {
        document.getElementById("modal-member-name").textContent = name;
        document.getElementById("modal-min-days-day").value = minDaysDay || "";
        document.getElementById("modal-min-days-night").value = minDaysNight || "";
        modal.classList.add('active');
        modal.classList.add('show');
        
        // Update currentMemberName which is used by saveMemberAttributes
        // This variable is local to settings_form.html's script, but we can't easily access it.
        // Let's ensure the script in settings_form.html still works by keeping its core logic.
    }
}

function closeMemberModal() {
    const modal = document.getElementById('member-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.remove('show');
    }
}
