document.addEventListener('DOMContentLoaded', () => {
    // Initialize main components
    const bookingSystem = new BookingSystem();
    const pricingCalculator = new PricingCalculator();
    const bookingForm = new BookingForm(bookingSystem, pricingCalculator);

    // Set up cleanup
    window.addEventListener('beforeunload', () => {
        if (bookingSystem.activeHold) {
            bookingSystem.cleanup();
        }
    });

    // Add any necessary CSS
    const style = document.createElement('style');
    style.textContent = `
        .price-update {
            animation: price-flash 0.3s ease-in-out;
        }

        @keyframes price-flash {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }

        .highlight-required {
            animation: shake 0.5s ease-in-out;
            border-color: var(--error-red) !important;
            box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.25) !important;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-4px); }
            75% { transform: translateX(4px); }
        }
    `;
    document.head.appendChild(style);
});