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
        console.log('Fetching models for make:', make);
        try {
            const encodedMake = encodeURIComponent(make);
            const modelsResponse = await fetch(`https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformake/${encodedMake}?format=json`);
            const modelsData = await modelsResponse.json();
            console.log('Received models data:', modelsData);
            
            this.modelsByMake[make] = modelsData.Results.map(model => model.Model_Name);
            console.log('Stored models:', this.modelsByMake[make]);
            
            return this.modelsByMake[make];
        } catch (error) {
            console.error('Error fetching models:', error);
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

        // If we have a confirmed make, fetch its models
        const confirmedMake = this.makes.find(make => 
            make.toLowerCase() === value.toLowerCase()
        );
        
        if (confirmedMake && !this.modelsByMake[confirmedMake]) {
            console.log('Fetching models for confirmed make:', confirmedMake);
            await this.fetchModelsForMake(confirmedMake);
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
                
                words.forEach((word, index) => {
                    if (index < suggestionWords.length) {
                        suggestionText += value.slice(currentPosition, currentPosition + word.length);
                        suggestionText += suggestionWords[index].slice(word.length).toLowerCase();
                        if (index < suggestionWords.length - 1) suggestionText += ' ';
                    }
                    currentPosition += word.length + 1;
                });
                
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

        console.log('Input value:', value);

        // If input includes a space, assume make is confirmed
        if (value.includes(' ')) {
            const [makeInput, ...modelParts] = value.split(' ');
            const modelInput = modelParts.join(' ').toLowerCase();
            
            console.log('Make input:', makeInput);
            console.log('Model input:', modelInput);
            
            // Find the confirmed make
            const confirmedMake = this.makes.find(make => 
                make.toLowerCase() === makeInput.toLowerCase()
            );
            
            console.log('Confirmed make:', confirmedMake);
            
            if (confirmedMake) {
                // Show all models for this make
                const models = this.modelsByMake[confirmedMake] || [];
                console.log('Models for', confirmedMake, ':', models);
                
                models.forEach(model => {
                    if (!modelInput || model.toLowerCase().includes(modelInput)) {
                        suggestions.add(`${confirmedMake} ${model}`);
                    }
                });
            }
        } else {
            // Just typing make - show matching makes
            this.makes.forEach(make => {
                if (make.toLowerCase().includes(lowercaseValue)) {
                    suggestions.add(make);
                }
            });
        }

        const finalSuggestions = Array.from(suggestions).slice(0, 10);
        console.log('Final suggestions:', finalSuggestions);
        return finalSuggestions;
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
