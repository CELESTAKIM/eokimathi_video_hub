// core/static/core/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Dynamically toggle video_file and video_url visibility on admin upload/edit forms
    const videoTypeRadios = document.querySelectorAll('input[name="video_type"]');
    const videoFileFieldGroup = document.querySelector('.video-file-field') ? document.querySelector('.video-file-field').closest('.mb-3') : null;
    const videoUrlFieldGroup = document.querySelector('.video-url-field') ? document.querySelector('.video-url-field').closest('.mb-3') : null;

    function toggleVideoFields() {
        const selectedValue = document.querySelector('input[name="video_type"]:checked');
        if (!selectedValue) return; // No radio button selected yet (e.g., on page load for new form)

        if (videoFileFieldGroup && videoUrlFieldGroup) {
            if (selectedValue.value === 'file') {
                videoFileFieldGroup.style.display = 'block';
                videoUrlFieldGroup.style.display = 'none';
                // Adjust required attribute for form validation if needed
                // document.querySelector('.video-file-field').setAttribute('required', 'required');
                // document.querySelector('.video-url-field').removeAttribute('required');
            } else if (selectedValue.value === 'link') {
                videoFileFieldGroup.style.display = 'none';
                videoUrlFieldGroup.style.display = 'block';
                // document.querySelector('.video-file-field').removeAttribute('required');
                // document.querySelector('.video-url-field').setAttribute('required', 'required');
            }
        }
    }

    if (videoTypeRadios.length > 0) {
        videoTypeRadios.forEach(radio => {
            radio.addEventListener('change', toggleVideoFields);
        });
        // Initial call to set visibility based on default/saved value on page load
        toggleVideoFields();
    }

    // WebSocket for Real-time Notifications (Basic Implementation)
    // This assumes you have a Notification consumer set up in Django Channels
    if (document.body.dataset.userPk) { // Check if user is logged in (add data-user-pk to body in base.html)
        const userPk = document.body.dataset.userPk;
        const notificationSocket = new WebSocket(
            'ws://' + window.location.host + '/ws/notifications/'
        );

        notificationSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'notification') {
                alert(`New Notification: ${data.message}`);
                // In a real app, you'd update a notification bell icon, show a toast, etc.
                // For now, a simple alert.
            }
        };

        notificationSocket.onclose = function(e) {
            console.log('Notification socket closed unexpectedly');
        };

        notificationSocket.onerror = function(e) {
            console.error('Notification socket error:', e);
        };
    }
});