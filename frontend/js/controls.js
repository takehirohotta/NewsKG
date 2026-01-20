const Controls = {
    periodSelect: null,
    customDateRange: null,
    fromDate: null,
    toDate: null,
    refreshBtn: null,
    layoutSelect: null,
    filterCheckboxes: null,
    groupingToggle: null,
    tooltip: null,

    init() {
        this.periodSelect = document.getElementById('period-select');
        this.customDateRange = document.getElementById('custom-date-range');
        this.fromDate = document.getElementById('from-date');
        this.toDate = document.getElementById('to-date');
        this.refreshBtn = document.getElementById('refresh-btn');
        this.layoutSelect = document.getElementById('layout-select');
        this.filterCheckboxes = document.querySelectorAll('.filter-checkbox input:not(#grouping-toggle)');
        this.groupingToggle = document.getElementById('grouping-toggle');
        this.tooltip = document.getElementById('tooltip');

        this.setupEventListeners();
        this.setDefaultDates();
    },

    setupEventListeners() {
        this.periodSelect.addEventListener('change', (e) => {
            const isCustom = e.target.value === 'custom';
            this.customDateRange.style.display = isCustom ? 'flex' : 'none';
            if (!isCustom) {
                this.triggerRefresh();
            }
        });

        this.fromDate.addEventListener('change', () => this.triggerRefresh());
        this.toDate.addEventListener('change', () => this.triggerRefresh());

        this.refreshBtn.addEventListener('click', () => this.triggerRefresh());

        this.layoutSelect.addEventListener('change', (e) => {
            console.log('[Controls] layout-select changed to:', e.target.value);
            window.dispatchEvent(new CustomEvent('layout-change', {
                detail: { layout: e.target.value }
            }));
        });

        this.filterCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateTypeFilter());
        });

        // グループ化トグルがある場合のみイベント登録
        if (this.groupingToggle) {
            this.groupingToggle.addEventListener('change', (e) => {
                GraphManager.setGroupingEnabled(e.target.checked);
            });
        }

        window.addEventListener('node-hover', (e) => {
            this.showTooltip(e.detail.nodeData, e.detail.position);
        });

        window.addEventListener('node-hover-out', () => {
            this.hideTooltip();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                window.dispatchEvent(new CustomEvent('escape-pressed'));
            }
            if (e.key === 'f' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                window.dispatchEvent(new CustomEvent('fit-graph'));
            }
        });
    },

    setDefaultDates() {
        const today = new Date();
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);

        this.toDate.value = this.formatDateForInput(today);
        this.fromDate.value = this.formatDateForInput(weekAgo);
        this.toDate.max = this.formatDateForInput(today);
    },

    formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    },

    getQueryParams() {
        const params = {
            period: this.periodSelect.value,
        };

        if (params.period === 'custom') {
            params.from = this.fromDate.value;
            params.to = this.toDate.value;
        }

        return params;
    },

    triggerRefresh() {
        window.dispatchEvent(new CustomEvent('refresh-graph', {
            detail: this.getQueryParams()
        }));
    },

    updateTypeFilter() {
        const activeTypes = [];
        this.filterCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                activeTypes.push(checkbox.dataset.type);
            }
        });

        window.dispatchEvent(new CustomEvent('filter-change', {
            detail: { types: activeTypes }
        }));
    },

    showTooltip(nodeData, position) {
        this.tooltip.textContent = nodeData.label;
        this.tooltip.style.left = `${position.x + 15}px`;
        this.tooltip.style.top = `${position.y + 15}px`;
        this.tooltip.classList.add('visible');
    },

    hideTooltip() {
        this.tooltip.classList.remove('visible');
    },

    setLoading(isLoading) {
        this.refreshBtn.disabled = isLoading;
        this.refreshBtn.querySelector('.btn-icon').textContent = isLoading ? '⏳' : '↻';
    },
};

window.Controls = Controls;

// 物理パラメータ調整
const PhysicsControls = {
    init() {
        this.panel = document.getElementById('physics-panel');
        this.content = document.getElementById('physics-content');
        this.toggle = document.getElementById('physics-toggle');
        
        this.repulsionSlider = document.getElementById('repulsion-slider');
        this.attractionSlider = document.getElementById('attraction-slider');
        this.gravitySlider = document.getElementById('gravity-slider');
        this.dampingSlider = document.getElementById('damping-slider');
        this.resetBtn = document.getElementById('physics-reset');
        
        this.repulsionValue = document.getElementById('repulsion-value');
        this.attractionValue = document.getElementById('attraction-value');
        this.gravityValue = document.getElementById('gravity-value');
        this.dampingValue = document.getElementById('damping-value');
        
        this.defaults = {
            repulsion: 5000,
            attraction: 0.005,
            centerGravity: 0.01,
            damping: 0.85
        };
        
        this.setupEventListeners();
        this.preventGraphInteraction();
    },
    
    // パネル内のイベントがグラフに伝播しないようにする
    preventGraphInteraction() {
        const stopPropagation = (e) => {
            e.stopPropagation();
        };
        
        this.panel.addEventListener('mousedown', stopPropagation);
        this.panel.addEventListener('mousemove', stopPropagation);
        this.panel.addEventListener('mouseup', stopPropagation);
        this.panel.addEventListener('touchstart', stopPropagation);
        this.panel.addEventListener('touchmove', stopPropagation);
        this.panel.addEventListener('touchend', stopPropagation);
        this.panel.addEventListener('wheel', stopPropagation);
        this.panel.addEventListener('click', stopPropagation);
    },
    
    setupEventListeners() {
        // パネル折りたたみ
        this.toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.content.classList.toggle('collapsed');
            this.toggle.textContent = this.content.classList.contains('collapsed') ? '▶' : '▼';
        });
        
        document.querySelector('.physics-panel-header').addEventListener('click', () => {
            this.content.classList.toggle('collapsed');
            this.toggle.textContent = this.content.classList.contains('collapsed') ? '▶' : '▼';
        });
        
        // スライダー
        this.repulsionSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.repulsionValue.textContent = value;
            GraphManager.physics.repulsion = value;
        });
        
        this.attractionSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.attractionValue.textContent = value;
            GraphManager.physics.attraction = value;
        });
        
        this.gravitySlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.gravityValue.textContent = value;
            GraphManager.physics.centerGravity = value;
        });
        
        this.dampingSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.dampingValue.textContent = value;
            GraphManager.physics.damping = value;
        });
        
        // リセット
        this.resetBtn.addEventListener('click', () => {
            this.repulsionSlider.value = this.defaults.repulsion;
            this.attractionSlider.value = this.defaults.attraction;
            this.gravitySlider.value = this.defaults.centerGravity;
            this.dampingSlider.value = this.defaults.damping;
            
            this.repulsionValue.textContent = this.defaults.repulsion;
            this.attractionValue.textContent = this.defaults.attraction;
            this.gravityValue.textContent = this.defaults.centerGravity;
            this.dampingValue.textContent = this.defaults.damping;
            
            GraphManager.physics.repulsion = this.defaults.repulsion;
            GraphManager.physics.attraction = this.defaults.attraction;
            GraphManager.physics.centerGravity = this.defaults.centerGravity;
            GraphManager.physics.damping = this.defaults.damping;
        });
    }
};

// 初期化時に呼び出し
document.addEventListener('DOMContentLoaded', () => {
    PhysicsControls.init();
});
