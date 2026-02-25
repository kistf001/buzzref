// BuzzRef - Authentication Module
const Auth = {
    // Check if user is logged in
    isLoggedIn() {
        return !!localStorage.getItem('auth_token');
    },

    // Get current user info
    getUser() {
        const userJson = localStorage.getItem('user');
        return userJson ? JSON.parse(userJson) : null;
    },

    // Login
    async login(username, password) {
        try {
            const response = await fetch(`${API.baseUrl}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            // Store token and user info
            localStorage.setItem('auth_token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));

            return data.user;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    },

    // Register
    async register(username, email, password, captchaId, captchaAnswer) {
        try {
            const response = await fetch(`${API.baseUrl}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    captcha_id: captchaId,
                    captcha_answer: captchaAnswer
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }

            return data;
        } catch (error) {
            console.error('Register error:', error);
            throw error;
        }
    },

    // Logout
    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        window.location.href = './';
    },

    // Get CAPTCHA image
    async getCaptcha() {
        try {
            const response = await fetch(`${API.baseUrl}/api/auth/captcha`);
            const data = await response.json();
            return data; // { captcha_id, image_url }
        } catch (error) {
            console.error('Captcha error:', error);
            throw error;
        }
    },

    // Update UI based on auth state
    updateUI() {
        const user = this.getUser();
        const authContainer = document.getElementById('auth-buttons');

        if (!authContainer) return;

        if (user) {
            authContainer.innerHTML = `
                <span class="username">${user.username}</span>
                <button onclick="Auth.logout()" class="btn btn-secondary" data-i18n="nav.logout">Logout</button>
            `;
        } else {
            authContainer.innerHTML = `
                <a href="./auth/login.html" class="btn btn-secondary" data-i18n="nav.login">Login</a>
                <a href="./auth/register.html" class="btn btn-primary" data-i18n="nav.signup">Sign Up</a>
            `;
        }

        // Re-apply translations
        if (typeof I18n !== 'undefined') {
            I18n.applyTranslations();
        }
    }
};

// Update UI when page loads
document.addEventListener('DOMContentLoaded', () => Auth.updateUI());
