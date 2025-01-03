class BookingSystem {
    constructor() {
        this.googleCalendarId = 'your_calendar_id';
        this.servicesDuration = {
            'Essential Clean': 60,
            'Premium Detail': 120
        };
        this.businessHours = { start: 9, end: 17 };
        this.bufferTime = 30;
        this.now = new Date();
        this.activeHold = null;
        this.holdTimeout = null;
        this.DEBUG = true;

        this.initializeDatePicker();
    }

    initializeDatePicker() {
        const datePicker = document.querySelector('.date-picker');
        if (datePicker) {
            datePicker.addEventListener('change', () => {
                this.debug('Date changed, updating time slots');
                this.updateTimeSlots();
            });
        }
    }

    async updateTimeSlots() {
        const dateInput = document.querySelector('.date-picker').value;
        const selectedServiceElement = document.querySelector('.service-card.selected h3');
        
        if (!dateInput || !selectedServiceElement) {
            this.debug('Date or service not selected');
            return;
        }

        const serviceName = selectedServiceElement.childNodes[0].textContent.trim();
        const timeSlotsContainer = document.getElementById('timeSlots');
        timeSlotsContainer.innerHTML = '<div class="time-slots-loading"><i class="fas fa-circle-notch fa-spin"></i> Loading available times...</div>';

        try {
            const response = await fetch(`/api/available-slots?date=${dateInput}&service=${encodeURIComponent(serviceName)}`);
            const data = await response.json();
            
            if (!data.slots || data.slots.length === 0) {
                timeSlotsContainer.innerHTML = `
                    <div class="no-slots-message">
                        <i class="fas fa-calendar-times"></i>
                        <p>No available times on this date. Please try another day.</p>
                    </div>
                `;
                return;
            }

            timeSlotsContainer.innerHTML = data.slots.map(slot => `
                <div class="time-slot" data-time="${slot.start}">
                    ${slot.start} - ${slot.end}
                </div>
            `).join('');

            // Add click handlers for time slots
            this.initializeTimeSlotHandlers();

        } catch (error) {
            this.debug('Error updating time slots:', error);
            timeSlotsContainer.innerHTML = `
                <div class="no-slots-message error">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error loading time slots. Please try again.</p>
                </div>
            `;
        }
    }

    initializeTimeSlotHandlers() {
        document.querySelectorAll('.time-slot').forEach(slot => {
            slot.addEventListener('click', async () => {
                if (!this.validateRequiredFields()) return;

                const date = document.querySelector('.date-picker').value;
                const time = slot.dataset.time;
                const selectedService = document.querySelector('.service-card.selected h3')
                    .textContent.split('$')[0].trim();

                const success = await this.holdTimeSlot(date, time, selectedService);
                
                if (success) {
                    document.querySelectorAll('.time-slot').forEach(s => 
                        s.classList.remove('selected')
                    );
                    slot.classList.add('selected');
                    
                    const bookButton = document.querySelector('.book-button');
                    if (bookButton) {
                        bookButton.disabled = false;
                    }
                } else {
                    this.updateTimeSlots(); // Refresh available slots
                }
            });
        });
    }

    validateRequiredFields() {
        const requiredFields = document.querySelectorAll('.booking-summary input[required]');
        const emptyFields = Array.from(requiredFields).filter(field => !field.value.trim());
        
        if (emptyFields.length > 0) {
            emptyFields[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            emptyFields[0].classList.add('highlight-required');
            setTimeout(() => emptyFields[0].classList.remove('highlight-required'), 2000);
            
            this.showTimeslotError('Please fill in all required information first');
            return false;
        }
        return true;
    }

    async holdTimeSlot(date, time, serviceType) {
        this.debug('Attempting to hold slot:', { date, time, serviceType });
        
        // If there's already an active hold, release it first
        if (this.activeHold) {
            this.debug('Releasing previous hold:', this.activeHold);
            await this.releaseHold(this.activeHold.date, this.activeHold.time);
        }

        try {
            const response = await fetch('/api/hold-slot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, time, service_type: serviceType })
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.activeHold = { date, time, serviceType };
                this.debug('Successfully created hold:', this.activeHold);
                this.startHoldCountdown();
                return true;
            } else {
                this.showTimeslotError(data.message || 'Unable to hold time slot');
                return false;
            }
        } catch (error) {
            this.debug('Error holding slot:', error);
            return false;
        }
    }

    async releaseHold(date, time) {
        if (!date || !time) {
            this.debug('Invalid release request - missing data');
            return false;
        }

        try {
            const response = await fetch('/api/release-hold', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, time })
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                this.debug('Successfully released hold');
                this.activeHold = null;
                return true;
            } else {
                this.debug('Failed to release hold:', data.message);
                return false;
            }
        } catch (error) {
            this.debug('Error releasing hold:', error);
            return false;
        }
    }

    startHoldCountdown() {
        if (this.holdTimeout) {
            clearInterval(this.holdTimeout);
        }

        const expirationTime = new Date(Date.now() + 5 * 60 * 1000);
        let countdownEl = document.getElementById('holdCountdown');
        
        if (!countdownEl) {
            countdownEl = document.createElement('div');
            countdownEl.id = 'holdCountdown';
            countdownEl.className = 'hold-countdown';
            const timeSlotsSection = document.querySelector('.summary-section:has(#timeSlots)');
            if (timeSlotsSection) {
                timeSlotsSection.insertBefore(countdownEl, document.getElementById('timeSlots'));
            }
        }

        this.holdTimeout = setInterval(() => {
            const now = new Date();
            const timeLeft = Math.max(0, expirationTime - now);
            
            if (timeLeft === 0) {
                clearInterval(this.holdTimeout);
                this.handleHoldExpired();
                return;
            }

            const minutes = Math.floor(timeLeft / 60000);
            const seconds = Math.floor((timeLeft % 60000) / 1000);
            
            countdownEl.innerHTML = `
                <div class="hold-message">
                    <i class="fas fa-clock"></i>
                    Time slot held for ${minutes}:${seconds.toString().padStart(2, '0')}
                </div>
            `;
        }, 1000);
    }

    handleHoldExpired() {
        document.querySelectorAll('.time-slot').forEach(slot => 
            slot.classList.remove('selected')
        );

        const countdownEl = document.getElementById('holdCountdown');
        if (countdownEl) {
            countdownEl.innerHTML = `
                <div class="hold-expired">
                    <i class="fas fa-exclamation-circle"></i>
                    Session expired. Please select a new time slot.
                </div>
            `;
            setTimeout(() => countdownEl.remove(), 5000);
        }

        const bookButton = document.querySelector('.book-button');
        if (bookButton) {
            bookButton.disabled = true;
        }
    }

    showTimeslotError(message) {
        const timeSlotsContainer = document.getElementById('timeSlots');
        const errorMsg = document.createElement('div');
        errorMsg.className = 'time-slot-error';
        errorMsg.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            ${message}
        `;
        timeSlotsContainer.insertBefore(errorMsg, timeSlotsContainer.firstChild);
        setTimeout(() => errorMsg.remove(), 3000);
    }

    debug(...args) {
        if (this.DEBUG) {
            console.log('[BookingSystem]', new Date().toISOString(), ...args);
        }
    }

    cleanup() {
        if (this.activeHold) {
            this.releaseHold(this.activeHold.date, this.activeHold.time);
        }
        if (this.holdTimeout) {
            clearInterval(this.holdTimeout);
        }
    }
}