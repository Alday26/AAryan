function acceptApplication(applicationId) {
    fetch(`/approve/${applicationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(data.message);
        } else {
            console.error("Error approving application:", data.message);
        }
    })
    .catch(error => console.error("Error:", error));
}

function rejectApplication(applicationId) {
    fetch(`/reject/${applicationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(data.message);
        } else {
            console.error("Error rejecting application:", data.message);
        }
    })
    .catch(error => console.error("Error:", error));
}