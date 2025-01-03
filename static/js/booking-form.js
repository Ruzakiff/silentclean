class BookingForm {
    constructor(bookingSystem, pricingCalculator) {
        this.bookingSystem = bookingSystem;
        this.pricingCalculator = pricingCalculator;
        this.form = document.querySelector('form');
        this.savedData = {};
        
        this.initializeDatePicker();
        this.initializeEventListeners();
        this.loadSavedBookingData();
    }

    initializeDatePicker() {
        const datePicker = document.querySelector('.date-picker');
        const now = new Date();
        const today = now.toISOString().split('T')[0];
        
        // Set date picker constraints
        datePicker.min = today;
        const twoWeeksFromNow = new Date(now);
        twoWeeksFromNow.setDate(now.getDate() + 14);
        datePicker.max = twoWeeksFromNow.toISOString().split('T')[0];
        datePicker.value = today;
    }

    initializeEventListeners() {
        // Service selection
        document.querySelectorAll('.service-card').forEach(card => {
            card.addEventListener('click', () => this.handleServiceSelection(card));
        });

        // Form submission
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Required field validation
        document.querySelectorAll('input[required]').forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
        });

        // Add address change listener
        document.querySelector('input[name="address"]').addEventListener('blur', () => {
            if (document.querySelector('.service-card.selected')) {
                this.updateAvailableSlots();
            }
        });

        // Update date picker listener
        document.querySelector('.date-picker').addEventListener('change', () => {
            if (document.querySelector('.service-card.selected')) {
                this.updateAvailableSlots();
            }
        });
    }

    handleServiceSelection(card) {
        document.querySelectorAll('.service-card').forEach(c => 
            c.classList.remove('selected')
        );
        card.classList.add('selected');
        
        this.pricingCalculator.updateDisplay();
        this.updateAvailableSlots();
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateAllFields()) {
            return;
        }

        const formData = new FormData(this.form);
        const bookingData = {
            service: document.querySelector('.service-card.selected h3').textContent.split('$')[0].trim(),
            date: document.querySelector('.date-picker').value,
            time: document.querySelector('.time-slot.selected')?.dataset.time,
            // Add other form fields
            contact: {
                name: formData.get('fullName'),
                email: formData.get('email'),
                phone: formData.get('phone')
            },
            location: {
                address: formData.get('address'),
                unit: formData.get('unit'),
                instructions: formData.get('parking')
            },
            vehicle: {
                model: formData.get('vehicleModel'),
                color: formData.get('vehicleColor'),
                plate: formData.get('licensePlate')
            },
            addons: Array.from(formData.getAll('addons')),
            frequency: formData.get('frequency'),
            totalPrice: this.pricingCalculator.calculateTotal()
        };

        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookingData)
            });

            const result = await response.json();
            if (result.status === 'success') {
                window.location.href = '/booking/confirmation';
            } else {
                this.showError(result.message || 'Booking failed. Please try again.');
            }
        } catch (error) {
            this.showError('An error occurred. Please try again.');
        }
    }

    validateField(input) {
        const isValid = input.checkValidity();
        input.classList.toggle('is-invalid', !isValid);
        return isValid;
    }

    validateAllFields() {
        const requiredFields = document.querySelectorAll('input[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
                field.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        return isValid;
    }

    loadSavedBookingData() {
        this.savedData = JSON.parse(sessionStorage.getItem('bookingData') || '{}');
        
        if (Object.keys(this.savedData).length > 0) {
            this.restoreSavedData();
            this.showConfirmationMessage();
        }
    }

    restoreSavedData() {
        // Restore service selection
        if (this.savedData.serviceType) {
            const serviceCards = document.querySelectorAll('.service-card');
            serviceCards.forEach(card => {
                const cardTitle = card.querySelector('h3').textContent
                    .split('$')[0].trim().toLowerCase();
                const savedService = this.savedData.serviceType.toLowerCase();
                
                if ((savedService === 'basic' && cardTitle === 'essential clean') ||
                    (savedService === 'premium' && cardTitle === 'premium detail')) {
                    card.click();
                }
            });
        }

        // Restore add-ons
        if (this.savedData.addons?.length > 0) {
            this.savedData.addons.forEach(addon => {
                const checkbox = document.querySelector(`input[name="addons"][value="${addon}"]`);
                if (checkbox) checkbox.checked = true;
            });
        }

        // Restore frequency
        if (this.savedData.frequency) {
            const frequencySelect = document.querySelector('select[name="frequency"]');
            if (frequencySelect) frequencySelect.value = this.savedData.frequency;
        }

        // Update price
        this.pricingCalculator.updateDisplay();
    }

    showConfirmationMessage() {
        const bookingHeader = document.querySelector('.booking-header');
        const message = document.createElement('div');
        message.className = 'alert alert-success mb-4 fade show';
        message.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-check-circle me-2"></i>
                <div>
                    <strong>Your selections have been transferred!</strong>
                    <p class="mb-0 small">We've pre-filled your choices from the calculator.</p>
                </div>
            </div>
        `;
        
        bookingHeader.insertAdjacentElement('afterend', message);
        setTimeout(() => {
            message.classList.remove('show');
            setTimeout(() => message.remove(), 150);
        }, 5000);
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        this.form.insertBefore(errorDiv, this.form.firstChild);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    // Add new method to get location data
    getLocationData() {
        const address = document.querySelector('input[name="address"]').value;
        const unit = document.querySelector('input[name="unit"]').value;
        
        if (!address) return null;
        
        return {
            address: address,
            unit: unit || ''
        };
    }

    // Add method to update slots with location
    updateAvailableSlots() {
        const location = this.getLocationData();
        if (location) {
            this.bookingSystem.updateTimeSlots(location);
        } else {
            // If no address, show message to enter address first
            this.bookingSystem.showTimeslotError('Please enter your service address first');
        }
    }
}