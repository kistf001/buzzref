// BuzzRef - API Client Module
const API = {
    // Configure this to point to your backend server
    // Automatically detect: localhost for development, configure for production
    baseUrl: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : 'https://api.yoursite.com',  // Change this for production

    // Get stored auth token
    getToken() {
        return localStorage.getItem('auth_token');
    },

    // Make authenticated API request
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = this.getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Handle 401 Unauthorized
            if (response.status === 401) {
                Auth.logout();
                throw new Error('Unauthorized');
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // GET request
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    // POST request
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // DELETE request
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // Forum API endpoints
    forum: {
        async getCategories() {
            return API.get('/api/forum/categories');
        },

        async getPosts(categorySlug, page = 1) {
            return API.get(`/api/forum/categories/${categorySlug}?page=${page}`);
        },

        async getPost(postId) {
            return API.get(`/api/forum/posts/${postId}`);
        },

        async createPost(categorySlug, title, content) {
            return API.post(`/api/forum/categories/${categorySlug}`, { title, content });
        },

        async createReply(postId, content) {
            return API.post(`/api/forum/posts/${postId}/replies`, { content });
        },

        async deletePost(postId) {
            return API.delete(`/api/forum/posts/${postId}`);
        }
    }
};
