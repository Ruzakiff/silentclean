class PricingCalculator {
    constructor() {
        this.baseServicePrices = {
            'Essential Clean': 50,
            'Premium Detail': 100
        };
        this.frequencyDiscounts = {
            'once': 1.0,
            'monthly': 0.90,  // 10% off
            'biweekly': 0.85, // 15% off
            'weekly': 0.80    // 20% off
        };
        this.addOnPrices = {
            'pet_hair': 25,
            'odor_removal': 40,
            'wiper_change': 20,
            'windshield_fluid': 10,
            'wheel_sealant': 15
        };
        this.initializeListeners();
    }

    initializeListeners() {
        // Update price when service selection changes
        document.querySelectorAll('.service-card').forEach(card => {
            card.addEventListener('click', () => this.updateDisplay());
        });

        // Update price when add-ons change
        document.querySelectorAll('input[name="addons"]').forEach(addon => {
            addon.addEventListener('change', () => this.updateDisplay());
        });

        // Update price when frequency changes
        const frequencySelect = document.querySelector('select[name="frequency"]');
        if (frequencySelect) {
            frequencySelect.addEventListener('change', () => this.updateDisplay());
        }
    }

    calculateTotal() {
        let totalPrice = 0;
        
        // Get selected service price
        const selectedCard = document.querySelector('.service-card.selected');
        if (selectedCard) {
            const priceText = selectedCard.querySelector('.service-price').textContent;
            totalPrice += parseFloat(priceText.replace('$', ''));
        }

        // Add selected add-ons
        document.querySelectorAll('input[name="addons"]:checked').forEach(addon => {
            const priceText = addon.closest('.addon-item').querySelector('.text-primary').textContent;
            totalPrice += parseFloat(priceText.replace('+$', ''));
        });

        // Apply frequency discount
        const frequency = document.querySelector('select[name="frequency"]').value;
        totalPrice *= this.frequencyDiscounts[frequency] || 1;

        return totalPrice;
    }

    updateDisplay() {
        const totalPrice = this.calculateTotal();
        const totalPriceElement = document.querySelector('.total-price span:last-child');
        
        if (totalPriceElement) {
            // Add animation class
            totalPriceElement.classList.add('price-update');
            
            // Update the price
            totalPriceElement.textContent = `$${Math.round(totalPrice)}`;
            
            // Remove animation class after animation completes
            setTimeout(() => totalPriceElement.classList.remove('price-update'), 300);
        }
    }

    getServicePrice(serviceName) {
        return this.baseServicePrices[serviceName] || 0;
    }

    getAddOnPrice(addonId) {
        return this.addOnPrices[addonId] || 0;
    }

    getFrequencyDiscount(frequency) {
        return this.frequencyDiscounts[frequency] || 1;
    }
}