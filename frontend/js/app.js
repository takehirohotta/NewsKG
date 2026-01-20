const App = {
    loadingOverlay: null,
    statusNodes: null,
    statusEdges: null,
    statusPeriod: null,

    async init() {
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.statusNodes = document.getElementById('status-nodes');
        this.statusEdges = document.getElementById('status-edges');
        this.statusPeriod = document.getElementById('status-period');

        Controls.init();
        DetailPanel.init();
        GraphManager.init('cy');

        this.setupEventListeners();

        await this.loadInitialData();
    },

    setupEventListeners() {
        window.addEventListener('refresh-graph', async (e) => {
            await this.loadGraphData(e.detail);
        });

        window.addEventListener('filter-change', (e) => {
            GraphManager.setTypeFilter(e.detail.types);
        });

        window.addEventListener('layout-change', (e) => {
            const layout = e.detail.layout;
            console.log('[App] layout-change event received:', layout);
            if (layout === 'physics') {
                // 物理シミュレーションモード
                GraphManager.startSimulation();
            } else {
                // 静的レイアウト
                GraphManager.runLayout(layout);
            }
        });

        window.addEventListener('escape-pressed', () => {
            DetailPanel.close();
        });

        window.addEventListener('fit-graph', () => {
            GraphManager.fit();
        });

        window.addEventListener('grouping-changed', (e) => {
            this.updateStatus(e.detail.originalMeta, e.detail.currentStats);
        });
    },

    async loadInitialData() {
        const isHealthy = await NewsKGAPI.checkHealth();
        if (!isHealthy) {
            this.showError('APIサーバーに接続できません。サーバーが起動しているか確認してください。');
            return;
        }

        await this.loadGraphData({ period: 'week' });
    },

    async loadGraphData(params) {
        this.showLoading(true);
        Controls.setLoading(true);

        try {
            const graphData = await NewsKGAPI.getGraph(params);
            
            // loadDataが物理シミュレーションを開始する
            GraphManager.loadData(graphData);
            
            this.updateStatus(graphData.meta, GraphManager.getStats());
            
        } catch (error) {
            console.error('Failed to load graph data:', error);
            this.showError(`データの読み込みに失敗しました: ${error.message}`);
        } finally {
            this.showLoading(false);
            Controls.setLoading(false);
        }
    },

    updateStatus(meta, currentStats) {
        const displayNodes = currentStats ? currentStats.nodes : meta.totalNodes;
        const displayEdges = currentStats ? currentStats.edges : meta.totalEdges;
        
        if (currentStats && (currentStats.nodes !== meta.totalNodes)) {
            this.statusNodes.textContent = `ノード: ${displayNodes} (元: ${meta.totalNodes})`;
            this.statusEdges.textContent = `エッジ: ${displayEdges} (元: ${meta.totalEdges})`;
        } else {
            this.statusNodes.textContent = `ノード: ${displayNodes}`;
            this.statusEdges.textContent = `エッジ: ${displayEdges}`;
        }
        
        const period = meta.period;
        if (period && period.from && period.to) {
            this.statusPeriod.textContent = `期間: ${period.from} 〜 ${period.to}`;
        }
    },

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('active');
        } else {
            this.loadingOverlay.classList.remove('active');
        }
    },

    showError(message) {
        const existingError = document.querySelector('.error-banner');
        if (existingError) {
            existingError.remove();
        }

        const banner = document.createElement('div');
        banner.className = 'error-banner';
        banner.style.cssText = `
            position: fixed;
            top: 70px;
            left: 50%;
            transform: translateX(-50%);
            background: #f44336;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 1000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 12px;
        `;
        
        banner.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="
                background: none;
                border: none;
                color: white;
                font-size: 1.25rem;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            ">×</button>
        `;
        
        document.body.appendChild(banner);
        
        setTimeout(() => {
            if (banner.parentElement) {
                banner.remove();
            }
        }, 10000);
    },
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
