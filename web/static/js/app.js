// Minimal JS setup
document.addEventListener('DOMContentLoaded', () => {
    // Tab Switching Logic
    const tabs = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            tab.classList.add('active');

            // Hide all sections
            sections.forEach(s => s.classList.add('hidden'));
            
            // Show target section
            const targetId = tab.dataset.target;
            document.getElementById(targetId).classList.remove('hidden');
        });
    });
});

