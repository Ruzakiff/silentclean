class VehicleAutofill {
    constructor() {
        // Store makes/models after fetching
        this.makes = [];
        this.modelsByMake = {};
        
        // Store recent inputs
        this.recentInputs = new Set(
            JSON.parse(localStorage.getItem('recentVehicles') || '[]')
        );
        
        // Check for cached data first
        const cachedData = localStorage.getItem('vehicleData');
        if (cachedData) {
            const data = JSON.parse(cachedData);
            const cacheAge = Date.now() - data.timestamp;
            
            // Use cache if less than 24 hours old
            if (cacheAge < 24 * 60 * 60 * 1000) {
                this.makes = data.makes;
                this.modelsByMake = data.modelsByMake;
                this.init();
                return;
            }
        }
        
        // Fetch fresh data if no cache or cache is old
        this.fetchVehicleData().then(() => this.init());
    }

    async fetchVehicleData() {
        try {
            // Get all makes first
            const makesResponse = await fetch('https://vpic.nhtsa.dot.gov/api/vehicles/getallmakes?format=json');
            const makesData = await makesResponse.json();
            this.makes = makesData.Results.map(make => make.Make_Name);

            // Cache in localStorage
            localStorage.setItem('vehicleData', JSON.stringify({
                makes: this.makes,
                modelsByMake: this.modelsByMake,
                timestamp: Date.now()
            }));

        } catch (error) {
            console.error('Error fetching vehicle data:', error);
            // Fallback to cached data if available
            const cachedData = localStorage.getItem('vehicleData');
            if (cachedData) {
                const data = JSON.parse(cachedData);
                this.makes = data.makes;
                this.modelsByMake = data.modelsByMake;
            }
        }
    }

    async fetchModelsForMake(make) {
        try {
            const encodedMake = encodeURIComponent(make);
            const modelsResponse = await fetch(`https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformake/${encodedMake}?format=json`);
            const modelsData = await modelsResponse.json();
            this.modelsByMake[make] = modelsData.Results.map(model => model.Model_Name);
            
            // Update cache
            const cachedData = JSON.parse(localStorage.getItem('vehicleData') || '{}');
            cachedData.modelsByMake = this.modelsByMake;
            localStorage.setItem('vehicleData', JSON.stringify(cachedData));
            
            return this.modelsByMake[make];
        } catch (error) {
            console.error('Error fetching models for make:', error);
            return [];
        }
    }

    async handleInput(event) {
        const input = event.target;
        const value = input.value.trim();
        const suggestionSpan = input.parentNode.querySelector('.vehicle-suggestion');
        
        if (!value) {
            suggestionSpan.textContent = '';
            return;
        }

        // Get suggestions and update datalist
        const suggestions = this.getSuggestions(value);
        this.updateDatalist(suggestions);

        // Update inline suggestion
        if (suggestions.length > 0) {
            const suggestion = suggestions[0];
            if (suggestion.toLowerCase().startsWith(value.toLowerCase())) {
                // Preserve user's case for each word
                const words = value.split(' ');
                const suggestionWords = suggestion.split(' ');
                
                let suggestionText = '';
                let currentPosition = 0;
                
                // For each word the user has typed
                words.forEach((word, index) => {
                    if (index < suggestionWords.length) {
                        // Use the user's case for what they've typed
                        suggestionText += value.slice(currentPosition, currentPosition + word.length);
                        // Add the rest of the suggested word in lowercase
                        suggestionText += suggestionWords[index].slice(word.length).toLowerCase();
                        // Add space if not the last word
                        if (index < suggestionWords.length - 1) suggestionText += ' ';
                    }
                    currentPosition += word.length + 1; // +1 for the space
                });
                
                // Add any remaining suggestion words in lowercase
                if (words.length < suggestionWords.length) {
                    suggestionText += suggestionWords.slice(words.length).join(' ').toLowerCase();
                }
                
                suggestionSpan.textContent = suggestionText;
            } else {
                suggestionSpan.textContent = '';
            }
        } else {
            suggestionSpan.textContent = '';
        }
    }

    getSuggestions(value) {
        const suggestions = new Set();
        const lowercaseValue = value.toLowerCase();

        // If input is empty or very short, show recent inputs and popular makes
        if (value.length < 2) {
            this.recentInputs.forEach(recent => suggestions.add(recent));
            this.makes.slice(0, 10).forEach(make => suggestions.add(make));
            return Array.from(suggestions).slice(0, 10);
        }

        // If input includes a space, try to match specific models
        if (value.includes(' ')) {
            const [makeInput, ...modelParts] = value.split(' ');
            const modelInput = modelParts.join(' ').toLowerCase();
            
            this.makes.forEach(make => {
                if (make.toLowerCase().startsWith(makeInput.toLowerCase())) {
                    const models = this.modelsByMake[make] || [];
                    models.forEach(model => {
                        if (model.toLowerCase().includes(modelInput)) {
                            suggestions.add(`${make} ${model}`);
                        }
                    });
                }
            });
        } else {
            // Add matching makes
            this.makes.forEach(make => {
                if (make.toLowerCase().includes(lowercaseValue)) {
                    suggestions.add(make);
                }
            });
        }

        // Add recent inputs that match
        this.recentInputs.forEach(recent => {
            if (recent.toLowerCase().includes(lowercaseValue)) {
                suggestions.add(recent);
            }
        });

        return Array.from(suggestions).slice(0, 10);
    }

    init() {
        const input = document.getElementById('vehicleModel');
        if (!input) return;

        // Create datalist for suggestions
        const datalist = document.createElement('datalist');
        datalist.id = 'vehicle-suggestions';
        document.body.appendChild(datalist);
        input.setAttribute('list', datalist.id);

        // Add suggestion span
        const suggestionSpan = document.createElement('span');
        suggestionSpan.className = 'vehicle-suggestion';
        input.parentNode.appendChild(suggestionSpan);

        // Add event listeners
        input.addEventListener('input', (e) => this.handleInput(e));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Tab' && suggestionSpan.textContent) {
                e.preventDefault();
                input.value = suggestionSpan.textContent;
                suggestionSpan.textContent = ''; // Clear the suggestion
                input.style.color = '#000'; // Force black text
                input.dispatchEvent(new Event('input'));
            }
        });
    }

    updateDatalist(suggestions) {
        const datalist = document.getElementById('vehicle-suggestions');
        if (!datalist) return;

        // Clear existing options
        datalist.innerHTML = '';

        // Add filtered suggestions
        suggestions.forEach(suggestion => {
            const option = document.createElement('option');
            option.value = suggestion;
            datalist.appendChild(option);
        });
    }

    saveValidInput(value) {
        if (!value || value.length < 3) return;

        // Add to recent inputs
        this.recentInputs.add(value);

        // Keep only the most recent 20 entries
        const recentArray = Array.from(this.recentInputs).slice(-20);

        // Save to localStorage
        localStorage.setItem('recentVehicles', JSON.stringify(recentArray));
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VehicleAutofill();
});
