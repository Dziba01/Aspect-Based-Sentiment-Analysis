// Main JavaScript for the Sentiment Analysis System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Rating stars interactive
    const ratingInputs = document.querySelectorAll('.rating-stars input');
    ratingInputs.forEach(input => {
        input.addEventListener('change', function() {
            const value = this.value;
            const container = this.closest('.rating-stars');
            const stars = container.querySelectorAll('.star');
            stars.forEach((star, index) => {
                if (index < value) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
        });
    });
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });
    
    // Confirmation for destructive actions
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-submit forms with select changes
    document.querySelectorAll('[data-auto-submit]').forEach(element => {
        element.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
});

// Helper: Format date
function formatDate(date) {
    const d = new Date(date);
    return d.toLocaleDateString('en-ZA', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Helper: Truncate text
function truncateText(text, length = 100) {
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
}

// Helper: Get sentiment color
function getSentimentColor(sentiment) {
    const colors = {
        'positive': '#198754',
        'neutral': '#ffc107',
        'negative': '#dc3545'
    };
    return colors[sentiment] || '#6c757d';
}

// Helper: Get sentiment icon
function getSentimentIcon(sentiment) {
    const icons = {
        'positive': 'fa-smile',
        'neutral': 'fa-meh',
        'negative': 'fa-frown'
    };
    return icons[sentiment] || 'fa-question';
}

// Export for use in other scripts
window.sentiment = {
    formatDate,
    truncateText,
    getSentimentColor,
    getSentimentIcon
};