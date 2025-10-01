/* Home Page JavaScript - Mobile First Interactive Features */

class HomePageManager {
    constructor() {
        this.init();
    }

    init() {
        this.initTabs();
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

        // Parallax effect for hero section (only on non-mobile)
        if (window.innerWidth > 768 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            this.initParallax();
        }
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
    new HomePageManager();
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

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HomePageManager;
}
