class BeforeAfterSlider {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            images: options.images || [
                {
                    before: '/static/images/tesla-dirty.jpg',
                    after: '/static/images/tesla-clean.jpg'
                }
            ],
            ...options
        };
        
        this.init();
    }

    createHTML() {
        return `
            <style>
                .before-after-slider {
                    width: 100%;
                    position: relative;
                    overflow: hidden;
                    border-radius: 12px;
                    aspect-ratio: 16/9;
                    box-shadow: 0 4px 12px rgba(28, 30, 38, 0.1);
                }

                .before-image {
                    position: absolute;
                    height: 100%;
                    width: 50%;
                    top: 0;
                    left: 0;
                    overflow: hidden;
                    z-index: 2;
                }

                .before-image img,
                .after-image img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    display: block;
                }

                .resizer {
                    position: absolute;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 5;
                    top: 0;
                    left: 50%;
                    height: 100%;
                    width: 2px;
                    background: #F4F4F4;
                    touch-action: pan-y;
                    cursor: ew-resize;
                }

                .resizer::after {
                    content: '';
                    position: absolute;
                    width: 44px;
                    height: 44px;
                    border-radius: 50%;
                    background: #F4F4F4;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 8px rgba(28, 30, 38, 0.15);
                }

                .resizer i {
                    color: #5ABFBF;
                    font-size: 18px;
                    z-index: 6;
                }
            </style>

            <div class="before-after-slider" id="before-after-slider">
                <div class="after-image">
                    <img src="${this.options.images[0].after}" alt="After"/>
                </div>
                <div class="before-image" id="before-image">
                    <img src="${this.options.images[0].before}" alt="Before"/>
                </div>
                <div class="resizer" id="resizer">
                    <i class="fas fa-arrows-left-right"></i>
                </div>
            </div>
        `;
    }

    init() {
        // Insert HTML
        this.container.innerHTML = this.createHTML();
        
        // Get elements
        this.slider = document.getElementById('before-after-slider');
        this.before = document.getElementById('before-image');
        this.beforeImage = this.before.getElementsByTagName('img')[0];
        this.resizer = document.getElementById('resizer');
        
        // Initialize state
        this.active = false;

        // Set initial width
        this.setImageWidth();
        
        // Bind events
        this.bindEvents();
    }

    setImageWidth() {
        const width = this.slider.offsetWidth;
        this.beforeImage.style.width = width + 'px';
    }

    bindEvents() {
        // Resize handling
        window.addEventListener('resize', () => this.setImageWidth());

        // Mouse events
        this.resizer.addEventListener('mousedown', () => this.active = true);
        document.body.addEventListener('mouseup', () => this.active = false);
        document.body.addEventListener('mouseleave', () => this.active = false);
        document.body.addEventListener('mousemove', (e) => this.handleMove(e));

        // Touch events
        this.resizer.addEventListener('touchstart', () => this.active = true);
        document.body.addEventListener('touchend', () => this.active = false);
        document.body.addEventListener('touchcancel', () => this.active = false);
        document.body.addEventListener('touchmove', (e) => this.handleMove(e));
    }

    handleMove(e) {
        if (!this.active) return;

        let x;
        if (e.type === 'touchmove') {
            x = e.touches[0].pageX;
        } else {
            x = e.pageX;
        }

        x -= this.slider.getBoundingClientRect().left;
        this.slideIt(x);
        this.pauseEvent(e);
    }

    slideIt(x) {
        const transform = Math.max(0, Math.min(x, this.slider.offsetWidth));
        this.before.style.width = transform + "px";
        this.resizer.style.left = transform + "px";
    }

    pauseEvent(e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
        e.cancelBubble = true;
        e.returnValue = false;
        return false;
    }
}
