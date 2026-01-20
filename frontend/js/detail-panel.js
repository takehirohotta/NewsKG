const DetailPanel = {
    panel: null,
    content: null,
    closeBtn: null,
    currentNodeId: null,

    init() {
        this.panel = document.getElementById('detail-panel');
        this.content = document.getElementById('detail-content');
        this.closeBtn = document.getElementById('detail-close');
        
        this.closeBtn.addEventListener('click', () => this.close());
        
        window.addEventListener('node-selected', (e) => {
            this.showNodeDetail(e.detail.nodeData);
        });
        
        window.addEventListener('canvas-clicked', () => {
            this.close();
        });
    },

    open() {
        this.panel.classList.add('open');
    },

    close() {
        this.panel.classList.remove('open');
        this.currentNodeId = null;
    },

    async showNodeDetail(nodeData) {
        this.currentNodeId = nodeData.id;
        this.open();
        
        this.content.innerHTML = this.renderBasicInfo(nodeData);
        
        try {
            const detail = await NewsKGAPI.getEntityDetail(nodeData.id);
            if (this.currentNodeId === nodeData.id) {
                this.content.innerHTML = this.renderFullDetail(detail, nodeData);
            }
        } catch (error) {
            console.warn('Failed to fetch entity detail:', error);
        }
    },

    renderBasicInfo(nodeData) {
        const typeClass = this.getTypeClass(nodeData.type);
        
        return `
            <div class="detail-section">
                <div class="detail-label">${this.escapeHtml(nodeData.label)}</div>
                <span class="detail-type ${typeClass}">${nodeData.type}</span>
            </div>
            ${this.renderProperties(nodeData.properties)}
        `;
    },

    renderFullDetail(detail, originalNodeData) {
        const typeClass = this.getTypeClass(detail.type);
        
        let html = `
            <div class="detail-section">
                <div class="detail-label">${this.escapeHtml(detail.label)}</div>
                <span class="detail-type ${typeClass}">${detail.type}</span>
            </div>
        `;
        
        if (Object.keys(detail.properties || {}).length > 0) {
            html += this.renderProperties(detail.properties);
        } else if (Object.keys(originalNodeData.properties || {}).length > 0) {
            html += this.renderProperties(originalNodeData.properties);
        }
        
        if (detail.relatedArticles && detail.relatedArticles.length > 0) {
            html += `
                <div class="detail-section">
                    <div class="detail-section-title">関連記事 (${detail.relatedArticles.length}件)</div>
                    <ul class="detail-articles">
                        ${detail.relatedArticles.map(article => this.renderArticleItem(article)).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (detail.connectionCount) {
            html += `
                <div class="detail-section">
                    <div class="detail-property">
                        <span class="detail-property-key">接続数</span>
                        <span class="detail-property-value">${detail.connectionCount}</span>
                    </div>
                </div>
            `;
        }
        
        return html;
    },

    renderProperties(properties) {
        if (!properties || Object.keys(properties).length === 0) {
            return '';
        }

        const propHtml = Object.entries(properties)
            .filter(([key]) => key !== 'url')
            .map(([key, value]) => {
                const displayKey = this.formatPropertyKey(key);
                const displayValue = this.formatPropertyValue(key, value);
                return `
                    <div class="detail-property">
                        <span class="detail-property-key">${displayKey}</span>
                        <span class="detail-property-value">${displayValue}</span>
                    </div>
                `;
            }).join('');

        if (properties.url) {
            return `
                <div class="detail-section">
                    ${propHtml}
                    <div class="detail-property">
                        <span class="detail-property-key">URL</span>
                        <span class="detail-property-value">
                            <a href="${this.escapeHtml(properties.url)}" target="_blank" class="detail-article-link">
                                記事を開く 🔗
                            </a>
                        </span>
                    </div>
                </div>
            `;
        }

        return `<div class="detail-section">${propHtml}</div>`;
    },

    renderArticleItem(article) {
        const pubDate = article.pubDate ? this.formatDate(article.pubDate) : '';
        
        return `
            <li class="detail-article-item">
                <div class="detail-article-title">${this.escapeHtml(article.title)}</div>
                <div class="detail-article-meta">
                    <span>${pubDate}</span>
                    <a href="${this.escapeHtml(article.url)}" target="_blank" class="detail-article-link">
                        開く 🔗
                    </a>
                </div>
            </li>
        `;
    },

    getTypeClass(type) {
        const baseTypes = {
            Person: 'person',
            Organization: 'organization',
            Place: 'place',
            NewsArticle: 'article',
        };
        return baseTypes[type] || 'statement';
    },

    formatPropertyKey(key) {
        const keyMap = {
            role: '役職',
            pubDate: '公開日',
            seismicIntensity: '震度',
            magnitude: 'マグニチュード',
            articleUrl: '記事URL',
            articleTitle: '記事タイトル',
        };
        return keyMap[key] || key;
    },

    formatPropertyValue(key, value) {
        if (key === 'pubDate' || key.toLowerCase().includes('date')) {
            return this.formatDate(value);
        }
        return this.escapeHtml(String(value));
    },

    formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleString('ja-JP', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    },

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};

window.DetailPanel = DetailPanel;
