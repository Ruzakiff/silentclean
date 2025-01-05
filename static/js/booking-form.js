class BookingForm {
    constructor(bookingSystem, pricingCalculator) {
        this.bookingSystem = bookingSystem;
        this.pricingCalculator = pricingCalculator;
        this.form = document.querySelector('form');
        this.savedData = {};
        
        this.initializeDatePicker();
        this.initializeEventListeners();
        this.loadSavedBookingData();
        this.initializeAddressAutocomplete();
        this.submitButton = this.form.querySelector('button[type="submit"]');
        this.updateSubmitButtonState();
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

        // Add input listeners for required fields
        document.querySelectorAll('input[required]').forEach(input => {
            input.addEventListener('input', () => this.updateSubmitButtonState());
            input.addEventListener('blur', () => {
                this.validateField(input);
                this.updateSubmitButtonState();
            });
        });

        // Add time slot selection listener
        document.addEventListener('click', (e) => {
            const timeSlot = e.target.closest('.time-slot');
            if (timeSlot) {
                this.handleTimeSlotSelection(timeSlot);
                this.updateSubmitButtonState();
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
        this.updateSubmitButtonState();
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateAllFields()) {
            return;
        }

        const selectedTimeSlot = document.querySelector('.time-slot.selected');
        if (!selectedTimeSlot) {
            this.showError('Please select a time slot');
            return;
        }

        // Show loading state
        const submitButton = this.form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

        const formData = new FormData(this.form);
        const bookingData = {
            service_type: document.querySelector('.service-card.selected h3').textContent.split('$')[0].trim(),
            date: document.querySelector('.date-picker').value,
            time: selectedTimeSlot.dataset.time,
            name: formData.get('fullName'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            address: formData.get('address'),
            unit: formData.get('unit') || '',
            vehicle: `${formData.get('vehicleYear') || ''} ${formData.get('vehicleModel')} - ${formData.get('vehicleColor')} (${formData.get('licensePlate')})`,
            notes: `
                Parking Instructions: ${formData.get('parking') || 'None'}
                Additional Notes: ${formData.get('notes') || 'None'}
            `.trim(),
            addons: Array.from(formData.getAll('addons')),
            frequency: formData.get('frequency'),
            total_price: this.pricingCalculator.calculateTotal()
        };

        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookingData)
            });

            const result = await response.json();
            
            if (result.status === 'success') {
                // Redirect to confirmation page
                window.location.href = `/booking/confirmation/${result.event_id}`;
            } else {
                this.showError(result.message || 'Booking failed. Please try again.');
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        } catch (error) {
            console.error('Booking error:', error);
            this.showError('An error occurred. Please try again.');
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    validateField(input) {
        const isValid = input.checkValidity();
        input.classList.toggle('is-invalid', !isValid);
        return isValid;
    }

    validateAllFields(shouldScroll = true) {
        const requiredFields = document.querySelectorAll('input[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
                if (shouldScroll) {
                    field.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
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
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-exclamation-circle me-2"></i>
                <div>${message}</div>
                <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
            </div>
        `;
        this.form.insertBefore(errorDiv, this.form.firstChild);
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
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

    initializeAddressAutocomplete() {
        const addressInput = document.querySelector('input[name="address"]');
        if (!addressInput) return;

        // Create suggestions container
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'address-suggestions';
        addressInput.parentNode.insertBefore(suggestionsContainer, addressInput.nextSibling);

        let timeoutId = null;

        addressInput.addEventListener('input', async (e) => {
            const query = e.target.value.trim();
            
            if (timeoutId) clearTimeout(timeoutId);
            
            if (!query) {
                suggestionsContainer.innerHTML = '';
                return;
            }

            timeoutId = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/place-suggestions?input=${encodeURIComponent(query)}`);
                    const data = await response.json();
                    
                    if (!data.suggestions) {
                        suggestionsContainer.innerHTML = '';
                        return;
                    }

                    suggestionsContainer.innerHTML = data.suggestions
                        .map(suggestion => `
                            <div class="suggestion-item" data-place-id="${suggestion.place_id}">
                                <strong>${suggestion.main_text}</strong>
                                <small>${suggestion.secondary_text}</small>
                            </div>
                        `).join('');

                    // Add click handlers to suggestions
                    document.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            addressInput.value = item.querySelector('strong').textContent + ', ' + 
                                               item.querySelector('small').textContent;
                            suggestionsContainer.innerHTML = '';
                            // Use existing method to update slots
                            this.updateAvailableSlots();
                            // Validate the field
                            this.validateField(addressInput);
                        });
                    });

                } catch (error) {
                    console.error('Error fetching address suggestions:', error);
                }
            }, 300);
        });

        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!addressInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.innerHTML = '';
            }
        });

        // Handle keyboard navigation
        addressInput.addEventListener('keydown', (e) => {
            const suggestions = document.querySelectorAll('.suggestion-item');
            const current = document.querySelector('.suggestion-item.highlighted');
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (!current) {
                        suggestions[0]?.classList.add('highlighted');
                    } else {
                        const next = current.nextElementSibling;
                        if (next) {
                            current.classList.remove('highlighted');
                            next.classList.add('highlighted');
                        }
                    }
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    if (current) {
                        const prev = current.previousElementSibling;
                        current.classList.remove('highlighted');
                        if (prev) {
                            prev.classList.add('highlighted');
                        }
                    }
                    break;
                    
                case 'Enter':
                    if (current) {
                        e.preventDefault();
                        current.click();
                    }
                    break;
            }
        });
    }

    // Add new method to handle time slot selection
    handleTimeSlotSelection(timeSlot) {
        // Remove selection from other slots
        document.querySelectorAll('.time-slot').forEach(slot => {
            slot.classList.remove('selected');
        });
        
        // Add selection to clicked slot
        timeSlot.classList.add('selected');
    }

    updateSubmitButtonState() {
        const allFieldsValid = this.validateAllFields(false);
        const timeSlotSelected = document.querySelector('.time-slot.selected');
        const serviceSelected = document.querySelector('.service-card.selected');

        this.submitButton.disabled = !(allFieldsValid && timeSlotSelected && serviceSelected);
    }
}
