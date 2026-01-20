const API_BASE_URL = 'http://localhost:8000/api';

const NewsKGAPI = {
    async getGraph(params = {}) {
        const queryParams = new URLSearchParams();
        
        if (params.period) queryParams.set('period', params.period);
        if (params.from) queryParams.set('from', params.from);
        if (params.to) queryParams.set('to', params.to);
        if (params.types) queryParams.set('types', params.types);
        if (params.limit) queryParams.set('limit', params.limit);
        
        const url = `${API_BASE_URL}/graph?${queryParams.toString()}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    },

    async getStats() {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    },

    async getEntityDetail(entityId) {
        const response = await fetch(`${API_BASE_URL}/entities/${encodeURIComponent(entityId)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    },

    async checkHealth() {
        try {
            const response = await fetch('http://localhost:8000/health');
            return response.ok;
        } catch {
            return false;
        }
    }
};

window.NewsKGAPI = NewsKGAPI;
