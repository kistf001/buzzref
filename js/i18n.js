// BuzzRef - Internationalization (i18n) Module
const I18n = {
    supportedLangs: ['en', 'ko', 'zh_CN', 'zh_TW', 'ja', 'es', 'fr'],
    langNames: {
        'en': 'English',
        'ko': '한국어',
        'zh_CN': '简体中文',
        'zh_TW': '繁體中文',
        'ja': '日本語',
        'es': 'Español',
        'fr': 'Français'
    },
    translations: {},
    currentLang: 'en',

    // Get language from cookie or browser
    detectLanguage() {
        // Check cookie first
        const cookie = document.cookie.split('; ').find(row => row.startsWith('lang='));
        if (cookie) {
            const lang = cookie.split('=')[1];
            if (this.supportedLangs.includes(lang)) {
                return lang;
            }
        }

        // Check browser language
        const browserLang = navigator.language.replace('-', '_');
        if (this.supportedLangs.includes(browserLang)) {
            return browserLang;
        }

        // Check language prefix (e.g., 'ko' from 'ko-KR')
        const langPrefix = browserLang.split('_')[0];
        if (this.supportedLangs.includes(langPrefix)) {
            return langPrefix;
        }

        // Special case for Chinese
        if (langPrefix === 'zh') {
            return browserLang.includes('TW') || browserLang.includes('HK') ? 'zh_TW' : 'zh_CN';
        }

        return 'en';
    },

    // Set language cookie
    async setLanguage(lang) {
        if (!this.supportedLangs.includes(lang)) return;

        document.cookie = `lang=${lang};path=/;max-age=31536000`;
        this.currentLang = lang;

        // Load translation file if not already loaded
        await this.loadTranslation(lang);
        this.applyTranslations();
    },

    // Load translation file
    async loadTranslation(lang) {
        if (this.translations[lang]) {
            return this.translations[lang];
        }

        try {
            const response = await fetch(`./translations/${lang}.json`);
            if (!response.ok) throw new Error('Translation not found');
            this.translations[lang] = await response.json();
            return this.translations[lang];
        } catch (e) {
            console.error(`Failed to load translation for ${lang}:`, e);
            // Fallback to English
            if (lang !== 'en') {
                return this.loadTranslation('en');
            }
            return {};
        }
    },

    // Get nested translation value
    get(key) {
        const t = this.translations[this.currentLang] || this.translations['en'] || {};
        const keys = key.split('.');
        let value = t;

        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                return key; // Return key if translation not found
            }
        }

        return value;
    },

    // Apply translations to DOM elements with data-i18n attribute
    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            let text = this.get(key);

            // Handle special replacements (e.g., [GitHub] link)
            if (text.includes('[GitHub]')) {
                text = text.replace('[GitHub]', '<a href="https://github.com/kistf001/buzzref" target="_blank">GitHub</a>');
            }

            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = text;
            } else {
                el.innerHTML = text;
            }
        });

        // Update page title
        const titleKey = document.querySelector('title')?.getAttribute('data-i18n');
        if (titleKey) {
            document.title = this.get(titleKey);
        }

        // Update language selector
        const langSelect = document.getElementById('lang-select');
        if (langSelect) {
            langSelect.value = this.currentLang;
        }

        // Update html lang attribute
        document.documentElement.lang = this.currentLang.replace('_', '-');
    },

    // Build language selector HTML
    buildLangSelector() {
        let html = '<select id="lang-select" onchange="I18n.setLanguage(this.value)">';
        for (const [code, name] of Object.entries(this.langNames)) {
            const selected = code === this.currentLang ? 'selected' : '';
            html += `<option value="${code}" ${selected}>${name}</option>`;
        }
        html += '</select>';
        return html;
    },

    // Initialize i18n
    async init() {
        this.currentLang = this.detectLanguage();
        await this.loadTranslation(this.currentLang);

        // Also load English as fallback
        if (this.currentLang !== 'en') {
            await this.loadTranslation('en');
        }

        // Insert language selector
        const langContainer = document.getElementById('lang-selector-container');
        if (langContainer) {
            langContainer.innerHTML = this.buildLangSelector();
        }

        this.applyTranslations();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => I18n.init());
