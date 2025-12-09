/* Home Page JavaScript - Mobile First Interactive Features */

class HomePageManager {
    constructor() {
        this.init();
    }

    init() {
        this.initTabs();
        this.initDemoMediaTabs();
        this.initQuickPrompt();
        this.initFAQ();
        this.initAnimations();
        this.initAccessibility();
    }

    // Tab functionality for demo section
    initTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panel');

        if (!tabButtons.length || !tabPanels.length) return;

        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const tabId = button.getAttribute('data-tab');

                // Remove active class from all buttons and panels
                tabButtons.forEach(btn => {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-selected', 'false');
                });

                tabPanels.forEach(panel => {
                    panel.classList.add('hidden');
                    panel.classList.remove('active');
                    panel.setAttribute('aria-hidden', 'true');
                });

                // Add active class to clicked button and corresponding panel
                button.classList.add('active');
                button.setAttribute('aria-selected', 'true');

                const activePanel = document.getElementById(tabId);
                if (activePanel) {
                    activePanel.classList.remove('hidden');
                    activePanel.classList.add('active');
                    activePanel.setAttribute('aria-hidden', 'false');
                }
            });

            // Keyboard navigation
            button.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    button.click();
                }
            });
        });
    }

    // Sync left side panel with media tabs (Фото/Видео)
    initDemoMediaTabs() {
        const imagesTab = document.querySelector('.demo-tab[data-demo-tab="images"]');
        const videosTab = document.querySelector('.demo-tab[data-demo-tab="videos"]');
        const resultBtn = document.querySelector('.tab-btn[data-tab="result"]');
        const resultPanel = document.getElementById('result');
        const promptBtn = document.querySelector('.tab-btn[data-tab="prompt"]');
        const promptPanel = document.getElementById('prompt');

        // Track last selected items to ensure different prompts for Photo vs Video
        let lastImageItem = null;
        let lastVideoItem = null;

        const applyFromItem = (item) => {
            if (!item) return;
            const promptEl = document.getElementById('promptText');
            const sSteps = document.getElementById('settingsSteps');
            const sCfg = document.getElementById('settingsCfg');
            const sRatio = document.getElementById('settingsRatio');
            const sSeed = document.getElementById('settingsSeed');
            const resultImg = document.getElementById('resultImage');

            if (promptEl) promptEl.textContent = item.prompt || '';
            if (sSteps) sSteps.textContent = item.settings?.steps ?? '';
            if (sCfg) sCfg.textContent = item.settings?.cfg ?? '';
            if (sRatio) sRatio.textContent = item.settings?.ratio ?? '3:2';
            if (sSeed) sSeed.textContent = item.settings?.seed ?? 'auto';

            // Для фото item.image, для видео — item.thumbnail (если есть)
            if (resultImg) {
                if (item.image) {
                    resultImg.src = item.image;
                    resultImg.alt = `Результат: ${item.title || ''}`;
                } else if (item.thumbnail) {
                    resultImg.src = item.thumbnail;
                    resultImg.alt = `Результат: ${item.title || ''}`;
                }
            }
        };

        const updateFromImage = () => {
            try {
                const pre = window.sliderExamples || [];
                let idx = 0;
                const active = document.querySelector('#sliderContainer .slide.active');
                if (active && active.dataset && active.dataset.slide) {
                    const n = parseInt(active.dataset.slide, 10);
                    if (!isNaN(n)) idx = n;
                } else {
                    const gs = window.homeManager?.generationSlider;
                    if (gs && Number.isFinite(gs.currentSlide)) idx = gs.currentSlide;
                }
                const item = pre[idx] || pre[0];
                if (item) {
                    applyFromItem(item);
                    lastImageItem = item;
                }
            } catch (e) { /* noop */ }
        };

        const updateFromVideo = () => {
            try {
                const data = window.videoSliderExamples || [];
                const idx = (typeof window.videoActiveIndex !== 'undefined') ? window.videoActiveIndex : 0;
                const item = data[idx] || data[0];
                if (item) lastVideoItem = item;
                applyFromItem(item);
            } catch (e) { /* noop */ }
        };

        // Показ/скрытие вкладки "Результат" в зависимости от режима
        const setResultVisibility = (mode) => {
            const isImages = mode === 'images';
            if (!resultBtn || !resultPanel) return;

            // Какой таб в левом блоке сейчас активен (prompt/settings/result)
            const activeLeftTab = document.querySelector('.tab-btn.active')?.getAttribute('data-tab');

            if (isImages) {
                // Для фото показываем кнопку "Результат"
                resultBtn.classList.remove('hidden');
                // Панель "Результат" показываем ТОЛЬКО если активен соответствующий таб
                if (activeLeftTab === 'result') {
                    resultPanel.classList.remove('hidden');
                    resultPanel.setAttribute('aria-hidden', 'false');
                } else {
                    resultPanel.classList.add('hidden');
                    resultPanel.setAttribute('aria-hidden', 'true');
                }
            } else {
                // Для видео прячем кнопку "Результат"
                resultBtn.classList.add('hidden');
                // Если был активен "Результат" — переключаем на "Промпт"
                if (activeLeftTab === 'result' && promptBtn && promptPanel) {
                    resultBtn.classList.remove('active');
                    resultBtn.setAttribute('aria-selected', 'false');
                    promptBtn.classList.add('active');
                    promptBtn.setAttribute('aria-selected', 'true');
                    // Прячем панель "Результат", показываем панель "Промпт"
                    resultPanel.classList.add('hidden');
                    resultPanel.setAttribute('aria-hidden', 'true');
                    promptPanel.classList.remove('hidden');
                    promptPanel.classList.add('active');
                    promptPanel.setAttribute('aria-hidden', 'false');
                } else {
                    // При видео всегда скрываем панель "Результат"
                    resultPanel.classList.add('hidden');
                    resultPanel.setAttribute('aria-hidden', 'true');
                }
            }
        };

        // Инициализация по текущему активному табу (вёрстка по умолчанию — "Видео")
        const initialMode = (videosTab && videosTab.classList.contains('active')) ? 'videos' : 'images';
        setResultVisibility(initialMode);
        if (initialMode === 'videos') {
            setTimeout(updateFromVideo, 0);
        } else {
            setTimeout(updateFromImage, 0);
        }

        // На переключение вкладки "Фото" / "Видео" — синхронизируем левую панель
        if (imagesTab) {
            imagesTab.addEventListener('click', () => {
                setResultVisibility('images');
                document.dispatchEvent(new CustomEvent('demoMediaTabChanged', { detail: { tab: 'images' } }));
                updateFromImage();
            });
        }
        if (videosTab) {
            videosTab.addEventListener('click', () => {
                setResultVisibility('videos');
                document.dispatchEvent(new CustomEvent('demoMediaTabChanged', { detail: { tab: 'videos' } }));
                updateFromVideo();
            });
        }

        // Когда сменили слайд видео (стрелки/индикатор) — если активна вкладка "Видео", обновляем левую панель
        document.addEventListener('videoSlideChanged', (e) => {
            window.videoActiveIndex = e?.detail?.index || 0;
            const isVideosActive = videosTab && videosTab.classList.contains('active');
            if (isVideosActive && e?.detail?.item) {
                applyFromItem(e.detail.item);
            }
        });

        // Если данные видео подгрузились позже — при событии загрузки тоже синхронизируем
        document.addEventListener('videoSliderDataLoaded', () => {
            const isVideosActive = videosTab && videosTab.classList.contains('active');
            if (isVideosActive) updateFromVideo();
        });

        // Фото-слайдер: при загрузке данных мгновенно обновляем левую панель, если активна вкладка «Фото»
        document.addEventListener('sliderDataLoaded', (e) => {
            const isImagesActive = imagesTab && imagesTab.classList.contains('active');
            if (Array.isArray(e?.detail?.data) && e.detail.data.length) {
                lastImageItem = e.detail.data[0];
            }
            if (isImagesActive) updateFromImage();
        });
    }

    // Quick prompt functionality
    initQuickPrompt() {
        const promptInput = document.getElementById('quick-prompt');
        const tryButton = document.getElementById('try-prompt');

        if (!promptInput || !tryButton) return;

        const handleSubmit = () => {
            const prompt = promptInput.value?.trim();

            if (prompt) {
                // Validate prompt length
                if (prompt.length < 3) {
                    this.showToast('Промпт слишком короткий. Добавьте больше деталей.', 'warning');
                    return;
                }

                if (prompt.length > 500) {
                    this.showToast('Промпт слишком длинный. Сократите до 500 символов.', 'warning');
                    return;
                }

                // Store prompt for analytics
                this.trackPromptSubmission(prompt);

                // Create URL with prompt parameter
                try {
                    const genUrl = document.querySelector('[data-generate-url]')?.dataset.generateUrl;
                    if (genUrl) {
                        const url = new URL(genUrl, window.location.origin);
                        url.searchParams.set('prompt', prompt);
                        window.location.href = url.toString();
                    } else {
                        // Fallback to direct navigation
                        window.location.href = '/generate/new/?prompt=' + encodeURIComponent(prompt);
                    }
                } catch (error) {
                    console.error('Error navigating to generation page:', error);
                    this.showToast('Произошла ошибка. Попробуйте еще раз.', 'error');
                }
            } else {
                // Navigate to generation page without prompt
                try {
                    const genUrl = document.querySelector('[data-generate-url]')?.dataset.generateUrl || '/generate/new/';
                    window.location.href = genUrl;
                } catch (error) {
                    console.error('Error navigating to generation page:', error);
                    window.location.href = '/generate/new/';
                }
            }
        };

        // Button click handler
        tryButton.addEventListener('click', handleSubmit);

        // Enter key handler
        promptInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSubmit();
            }
        });

        // Auto-resize textarea if it's a textarea
        if (promptInput.tagName === 'TEXTAREA') {
            promptInput.addEventListener('input', () => {
                promptInput.style.height = 'auto';
                promptInput.style.height = promptInput.scrollHeight + 'px';
            });
        }

        // Character counter for prompt input
        const createCharCounter = () => {
            const counter = document.createElement('div');
            counter.className = 'text-xs text-muted mt-1';
            counter.id = 'prompt-counter';

            const updateCounter = () => {
                const length = promptInput.value.length;
                counter.textContent = `${length}/500 символов`;

                if (length > 450) {
                    counter.classList.add('text-warning');
                } else if (length > 500) {
                    counter.classList.remove('text-warning');
                    counter.classList.add('text-error');
                } else {
                    counter.classList.remove('text-warning', 'text-error');
                }
            };

            promptInput.addEventListener('input', updateCounter);
            promptInput.parentNode.appendChild(counter);
            updateCounter();
        };

        // Add character counter if not exists
        if (!document.getElementById('prompt-counter')) {
            createCharCounter();
        }
    }

    // FAQ accordion functionality
    initFAQ() {
        const faqItems = document.querySelectorAll('.faq-item');

        faqItems.forEach(item => {
            const summary = item.querySelector('.faq-summary');
            const icon = item.querySelector('.faq-icon');

            if (!summary || !icon) return;

            summary.addEventListener('click', (e) => {
                // Prevent default detail toggle for custom behavior
                e.preventDefault();

                const isOpen = item.hasAttribute('open');

                // Close all other FAQ items (accordion behavior)
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.hasAttribute('open')) {
                        otherItem.removeAttribute('open');
                        const otherIcon = otherItem.querySelector('.faq-icon');
                        if (otherIcon) {
                            otherIcon.style.transform = 'rotate(0deg)';
                        }
                    }
                });

                // Toggle current item
                if (isOpen) {
                    item.removeAttribute('open');
                    icon.style.transform = 'rotate(0deg)';
                } else {
                    item.setAttribute('open', '');
                    icon.style.transform = 'rotate(180deg)';
                }

                // Track FAQ interaction
                this.trackFAQInteraction(summary.textContent, !isOpen);
            });

            // Keyboard support
            summary.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    summary.click();
                }
            });
        });
    }

    // Initialize animations and intersection observers
    initAnimations() {
        // Intersection Observer for animation triggers
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');

                    // Stagger animation for grid items
                    if (entry.target.matches('.features-grid, .use-cases-grid, .how-it-works-grid')) {
                        this.staggerGridAnimation(entry.target);
                    }
                }
            });
        }, observerOptions);

        // Observe animatable elements
        const animatableElements = document.querySelectorAll(`
            .hero-section,
            .trust-section,
            .features-section,
            .demo-section,
            .how-it-works-section,
            .use-cases-section,
            .comparison-section,
            .faq-section,
            .cta-section
        `);

        animatableElements.forEach(el => {
            observer.observe(el);
        });

        // Parallax effect disabled for performance on all devices
        // if (window.innerWidth > 768 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        //     this.initParallax();
        // }
    }

    // Stagger animations for grid items
    staggerGridAnimation(container) {
        const items = container.querySelectorAll('.card, .feature-card, .use-case-card, .step-card');

        items.forEach((item, index) => {
            setTimeout(() => {
                item.classList.add('animate-in');
            }, index * 100);
        });
    }

    // Parallax effect for hero floating elements
    initParallax() {
        const floatingElements = document.querySelectorAll('.floating-element-left, .floating-element-right');

        if (!floatingElements.length) return;

        let ticking = false;

        const updateParallax = () => {
            const scrollY = window.pageYOffset;

            floatingElements.forEach((element, index) => {
                const speed = 0.5 + (index * 0.2);
                const yPos = scrollY * speed;
                element.style.transform = `translateY(${yPos}px)`;
            });

            ticking = false;
        };

        const requestParallax = () => {
            if (!ticking) {
                requestAnimationFrame(updateParallax);
                ticking = true;
            }
        };

        window.addEventListener('scroll', requestParallax, { passive: true });
    }

    // Accessibility improvements
    initAccessibility() {
        // Enhanced focus management
        this.initFocusManagement();

        // Keyboard navigation improvements
        this.initKeyboardNavigation();

        // Screen reader announcements
        this.initScreenReaderSupport();
    }

    initFocusManagement() {
        // Trap focus in modals/overlays if any
        const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

        // Enhanced focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    initKeyboardNavigation() {
        // Skip to content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Перейти к основному содержимому';
        skipLink.setAttribute('aria-label', 'Перейти к основному содержимому');

        document.body.insertBefore(skipLink, document.body.firstChild);

        // Arrow key navigation for tabs
        const tabContainer = document.querySelector('[role="tablist"]');
        if (tabContainer) {
            tabContainer.addEventListener('keydown', (e) => {
                const tabs = Array.from(tabContainer.querySelectorAll('[role="tab"]'));
                const currentIndex = tabs.indexOf(e.target);

                let nextIndex;

                switch (e.key) {
                    case 'ArrowLeft':
                        e.preventDefault();
                        nextIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
                        tabs[nextIndex].focus();
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        nextIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
                        tabs[nextIndex].focus();
                        break;
                    case 'Home':
                        e.preventDefault();
                        tabs[0].focus();
                        break;
                    case 'End':
                        e.preventDefault();
                        tabs[tabs.length - 1].focus();
                        break;
                }
            });
        }
    }

    initScreenReaderSupport() {
        // Announce dynamic content changes
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'announcer';
        document.body.appendChild(announcer);

        this.announcer = announcer;
    }

    // Utility methods
    showToast(message, type = 'info') {
        // Create or get toast container
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');

        // Add to container
        toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);

        // Announce to screen readers
        if (this.announcer) {
            this.announcer.textContent = message;
        }
    }

    announce(message) {
        if (this.announcer) {
            this.announcer.textContent = message;
        }
    }

    // Analytics tracking methods
    trackPromptSubmission(prompt) {
        // Track prompt submission for analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'prompt_submit', {
                event_category: 'engagement',
                event_label: 'home_quick_prompt',
                value: prompt.length
            });
        }

        // Custom analytics
        if (typeof analytics !== 'undefined') {
            analytics.track('Prompt Submitted', {
                source: 'home_page',
                prompt_length: prompt.length,
                prompt_words: prompt.split(' ').length
            });
        }
    }

    trackFAQInteraction(question, opened) {
        if (typeof gtag !== 'undefined') {
            gtag('event', opened ? 'faq_open' : 'faq_close', {
                event_category: 'engagement',
                event_label: question.substring(0, 50)
            });
        }
    }

    // Performance optimization
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Initialize home page functionality when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.homeManager = new HomePageManager();
    window.generationSlider = new GenerationSlider();
});

// CSS for toast notifications (if not already in CSS)
const toastStyles = `
.toast-container {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 1000;
    pointer-events: none;
}

.toast {
    background: var(--bg-card);
    border: 1px solid var(--bord);
    border-radius: 0.5rem;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    pointer-events: auto;
    animation: slideIn 0.3s ease-out;
}

.toast-info {
    border-left: 4px solid var(--primary);
}

.toast-warning {
    border-left: 4px solid #f59e0b;
}

.toast-error {
    border-left: 4px solid #ef4444;
}

.toast-success {
    border-left: 4px solid #10b981;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

.skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: var(--primary);
    color: white;
    padding: 8px;
    border-radius: 4px;
    text-decoration: none;
    z-index: 1000;
    transition: top 0.3s;
}

.skip-link:focus {
    top: 6px;
}

/* Focus management styles */
.keyboard-navigation *:focus {
    outline: 2px solid var(--primary);
    outline-offset: 2px;
}

/* Animation classes */
.animate-in {
    animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Responsive toast positioning */
@media (max-width: 640px) {
    .toast-container {
        top: 1rem;
        left: 1rem;
        right: 1rem;
    }

    .toast {
        margin-bottom: 0.25rem;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
    }
}
`;

// Inject toast styles if not already present
if (!document.getElementById('home-toast-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'home-toast-styles';
    styleElement.textContent = toastStyles;
    document.head.appendChild(styleElement);
}

// Generation Slider Class
class GenerationSlider {
    constructor() {
        this.currentSlide = 0;
        this.slides = [];
        this.sliderData = [];
        this.generationTimes = [26, 18, 32]; // Different generation times for each slide

        this.init();
    }

    init() {
        // Не используем больше демо/фоллбеки: только то, что создано админом
        this.setupElements();
        this.bindEvents();

        // Мгновенно берём предзагруженные данные (из generation_slider.html)
        if (Array.isArray(window.sliderExamples) && window.sliderExamples.length) {
            this.sliderData = window.sliderExamples;
            this.updateSlide(0);
        }

        // Обновляемся, когда слайды фотографий построены из preloaded/кэша
        document.addEventListener('sliderDataLoaded', (event) => {
            if (event.detail && Array.isArray(event.detail.data)) {
                this.sliderData = event.detail.data;
                this.updateSlide(0);
            }
        });

        if (this.sliderData && this.sliderData.length > 1) {
            this.startAutoplay();
        }
    }

    loadSliderData() {
        // Источник данных только из preloaded (созданные админом)
        this.sliderData = Array.isArray(window.sliderExamples) ? window.sliderExamples : [];
    }

    async loadSliderDataFromJSON() {
        try {
            console.log('Loading slider data from JSON...');
            const response = await fetch('/static/data/slider_examples.json');
            if (!response.ok) throw new Error('Failed to load slider data');

            this.sliderData = await response.json();
            console.log('Slider data loaded:', this.sliderData);

            // Обновляем слайдер после загрузки данных
            if (this.sliderData.length > 0) {
                this.updateSlide(0);
            }
        } catch (error) {
            console.warn('Failed to load slider data from JSON, using fallback:', error);
            this.sliderData = this.getFallbackData();
        }
    }

    getFallbackData() {
        // Больше не используем демо-данные — только админские примеры
        return [];
    }

    setupElements() {
        this.slider = document.getElementById('generationSlider');
        // Scope only to the IMAGE slider to avoid interfering with video slides
        this.slides = this.slider ? this.slider.querySelectorAll('.slide') : [];
        this.indicators = this.slider ? this.slider.querySelectorAll('.indicator') : [];
        this.prevBtn = document.getElementById('prevSlide');
        this.nextBtn = document.getElementById('nextSlide');

        // Text elements
        this.promptText = document.getElementById('promptText');
        this.resultImage = document.getElementById('resultImage');
        this.generationTimeElement = document.getElementById('generationTime');

        // Логируем найденные элементы
        console.log('Setup elements:');
        console.log('- resultImage:', this.resultImage);
        console.log('- promptText:', this.promptText);
        console.log('- slider:', this.slider);

        // Settings elements
        this.settingsSteps = document.getElementById('settingsSteps');
        this.settingsCfg = document.getElementById('settingsCfg');
        this.settingsRatio = document.getElementById('settingsRatio');
        this.settingsSeed = document.getElementById('settingsSeed');

        // Copy button
        this.copyBtn = document.getElementById('copyPromptBtn');

        if (!this.slider || !this.slides.length) return;
    }

    bindEvents() {
        if (!this.prevBtn || !this.nextBtn) return;

        this.prevBtn.addEventListener('click', () => this.previousSlide());
        this.nextBtn.addEventListener('click', () => this.nextSlide());

        // Copy prompt functionality
        if (this.copyBtn) {
            this.copyBtn.addEventListener('click', () => this.copyPrompt());
        }

        // Indicator clicks
        this.indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => this.goToSlide(index));
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.slider && this.isInViewport(this.slider)) {
                if (e.key === 'ArrowLeft') this.previousSlide();
                if (e.key === 'ArrowRight') this.nextSlide();
            }
        });

        // Touch/swipe support
        this.addTouchSupport();

        // Pause autoplay on hover
        this.slider.addEventListener('mouseenter', () => this.pauseAutoplay());
        this.slider.addEventListener('mouseleave', () => this.startAutoplay());
    }

    addTouchSupport() {
        let startX = 0;
        let startY = 0;
        let endX = 0;
        let isDragging = false;

        this.slider.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isDragging = false;
        }, { passive: true });

        this.slider.addEventListener('touchmove', (e) => {
            if (!isDragging) {
                const currentX = e.touches[0].clientX;
                const currentY = e.touches[0].clientY;
                const diffX = Math.abs(currentX - startX);
                const diffY = Math.abs(currentY - startY);

                // Определяем направление свайпа
                if (diffX > diffY && diffX > 10) {
                    // Горизонтальный свайп - предотвращаем скролл
                    isDragging = true;
                    e.preventDefault();
                }
                // Если вертикальный свайп - разрешаем нативный скролл
            } else if (isDragging) {
                // Продолжаем предотвращать скролл только если уже начат горизонтальный свайп
                e.preventDefault();
            }
        }, { passive: false });

        this.slider.addEventListener('touchend', (e) => {
            if (isDragging) {
                endX = e.changedTouches[0].clientX;
                const diffX = startX - endX;

                if (Math.abs(diffX) > 50) { // Minimum swipe distance
                    if (diffX > 0) {
                        this.nextSlide();
                    } else {
                        this.previousSlide();
                    }
                }
            }
            isDragging = false;
        }, { passive: true });
    }

    async copyPrompt() {
        if (!this.promptText || !this.copyBtn) return;

        const promptText = this.promptText.textContent.trim();

        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(promptText);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = promptText;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                textArea.remove();
            }

            // Show copy success feedback
            this.showCopySuccess();

        } catch (err) {
            console.error('Failed to copy prompt:', err);
            this.showCopyError();
        }
    }

    showCopySuccess() {
        // Button visual feedback
        this.copyBtn.classList.add('copied');

        // Show toast notification
        this.showToast('Промпт скопирован!', 'success');

        // Reset button state
        setTimeout(() => {
            this.copyBtn.classList.remove('copied');
        }, 1000);
    }

    showCopyError() {
        this.showToast('Ошибка копирования', 'error');
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `copy-toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 100);

        // Remove toast
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2000);
    }

    nextSlide() {
        this.currentSlide = (this.currentSlide + 1) % this.slides.length;
        this.updateSlide(this.currentSlide);
    }

    previousSlide() {
        this.currentSlide = this.currentSlide === 0 ? this.slides.length - 1 : this.currentSlide - 1;
        this.updateSlide(this.currentSlide);
    }

    goToSlide(index) {
        this.currentSlide = index;
        this.updateSlide(this.currentSlide);
    }

    updateSlide(index) {
        // Проверяем, что данные загружены
        if (!this.sliderData || this.sliderData.length === 0) {
            console.log('Slider data not loaded yet');
            return;
        }

        const slideData = this.sliderData[index];
        if (!slideData) {
            console.warn('Slide data not found for index:', index);
            return;
        }

        // Update slides
        this.slides.forEach((slide, i) => {
            slide.classList.toggle('active', i === index);
        });

        // Update indicators
        this.indicators.forEach((indicator, i) => {
            indicator.classList.toggle('active', i === index);
        });

        // Обновлять левую панель только если активна вкладка "Фото"
        const imagesTab = document.querySelector('.demo-tab[data-demo-tab="images"]');
        const isImagesActive = imagesTab && imagesTab.classList.contains('active');

        if (isImagesActive) {
            // Update prompt text
            if (this.promptText) {
                this.promptText.textContent = slideData.prompt;
            }

            // Update result image
            if (this.resultImage && slideData.image) {
                this.resultImage.src = slideData.image;
                this.resultImage.alt = `Результат: ${slideData.title}`;
                console.log('Updated result image to:', slideData.image);
            }

            // Update generation time
            if (this.generationTimeElement) {
                this.generationTimeElement.textContent = this.generationTimes[index] || '26';
            }

            // Update settings
            if (slideData.settings) {
                if (this.settingsSteps) this.settingsSteps.textContent = slideData.settings.steps;
                if (this.settingsCfg) this.settingsCfg.textContent = slideData.settings.cfg;
                if (this.settingsRatio) this.settingsRatio.textContent = slideData.settings.ratio;
                if (this.settingsSeed) this.settingsSeed.textContent = slideData.settings.seed;
            }

            // Announce to screen readers
            this.announceSlideChange(index);
        }

        // Restart autoplay timer
        this.startAutoplay();
    }

    announceSlideChange(index) {
        const slideData = this.sliderData[index];
        const announcement = `Слайд ${index + 1} из ${this.slides.length}: ${slideData?.title || ''}`;

        const ariaLive = document.createElement('div');
        ariaLive.setAttribute('aria-live', 'polite');
        ariaLive.setAttribute('aria-atomic', 'true');
        ariaLive.className = 'sr-only';
        ariaLive.textContent = announcement;

        document.body.appendChild(ariaLive);
        setTimeout(() => document.body.removeChild(ariaLive), 1000);
    }

    startAutoplay() {
        this.stopAutoplay();
        this.autoplayInterval = setInterval(() => {
            this.nextSlide();
        }, 6000); // 6 seconds for better UX
    }

    pauseAutoplay() {
        this.stopAutoplay();
    }

    stopAutoplay() {
        if (this.autoplayInterval) {
            clearInterval(this.autoplayInterval);
            this.autoplayInterval = null;
        }
    }

    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    // Диагностическая функция для отладки
    debugSlider() {
        console.log('=== SLIDER DEBUG INFO ===');
        console.log('Slider data:', this.sliderData);
        console.log('Current slide:', this.currentSlide);
        console.log('Result image element:', this.resultImage);
        console.log('Window.sliderExamples:', window.sliderExamples);

        if (this.sliderData && this.sliderData.length > 0) {
            console.log('Current slide data:', this.sliderData[this.currentSlide]);
        }

        console.log('=========================');
    }
}

// Функция для глобального доступа к диагностике
window.debugSlider = function() {
    if (window.homeManager && window.homeManager.generationSlider) {
        window.homeManager.generationSlider.debugSlider();
    } else {
        console.log('Slider not initialized yet');
    }
};

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HomePageManager, GenerationSlider };
}
