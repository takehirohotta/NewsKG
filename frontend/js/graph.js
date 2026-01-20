if (typeof cytoscapeFcose !== 'undefined') {
    cytoscape.use(cytoscapeFcose);
}

const GraphManager = {
    cy: null,
    currentData: null,
    visibleTypes: new Set(['Person', 'Organization', 'Place', 'Event', 'Entity']),
    groupingEnabled: false,
    expandedGroups: new Set(),
    groupedData: null,
    animationId: null,
    frameCount: 0,
    isSimulating: false,

    STATEMENT_TYPES: [],

    nodeStyles: {
        Person: { color: '#4a90d9', shape: 'ellipse' },
        Organization: { color: '#7cb342', shape: 'rectangle' },
        Place: { color: '#ff9800', shape: 'triangle' },
        Event: { color: '#9c27b0', shape: 'diamond' },
        Entity: { color: '#607d8b', shape: 'ellipse' },
        NewsArticle: { color: '#78909c', shape: 'hexagon' },
        GroupNode: { color: '#e91e63', shape: 'round-rectangle' },
        default: { color: '#999999', shape: 'ellipse' }
    },

    edgeStyles: {
        default: { lineStyle: 'solid', color: '#666666', width: 2 }
    },

    physics: {
        repulsion: 5000,
        attraction: 0.005,
        damping: 0.85,
        centerGravity: 0.01,
    },

    init(containerId) {
        console.log('GraphManager.init called');
        this.cy = cytoscape({
            container: document.getElementById(containerId),
            style: this.buildStylesheet(),
            layout: { name: 'preset' },
            minZoom: 0.1,
            maxZoom: 3,
        });

        this.setupEventHandlers();
        return this.cy;
    },

    buildStylesheet() {
        return [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'font-size': '11px',
                    'text-margin-y': 5,
                    'text-max-width': '150px',
                    'text-wrap': 'wrap',
                    'text-overflow-wrap': 'anywhere',
                    'width': 'data(size)',
                    'height': 'data(size)',
                    'background-color': 'data(color)',
                    'border-width': 2,
                    'border-color': 'data(borderColor)',
                    'shape': 'data(shape)',
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': 4,
                    'border-color': '#1976d2',
                    'background-opacity': 1,
                }
            },
            {
                selector: 'node.highlighted',
                style: {
                    'border-width': 3,
                    'border-color': '#ff5722',
                }
            },
            {
                selector: 'node.hidden',
                style: {
                    'display': 'none',
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 'data(width)',
                    'line-color': 'data(color)',
                    'line-style': 'data(lineStyle)',
                    'target-arrow-color': 'data(color)',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 0.8,
                    'opacity': 0.7,
                }
            },
            {
                selector: 'edge:selected',
                style: {
                    'width': 3,
                    'opacity': 1,
                }
            },
            {
                selector: 'edge.hidden',
                style: {
                    'display': 'none',
                }
            },
            {
                selector: 'edge[label]',
                style: {
                    'label': 'data(label)',
                    'font-size': '10px',
                    'text-rotation': 'autorotate',
                    'text-margin-y': -10,
                    'color': '#333333',
                    'text-background-color': '#ffffff',
                    'text-background-opacity': 0.8,
                    'text-background-padding': '2px',
                }
            },
            {
                selector: 'node[?isGroup]',
                style: {
                    'font-weight': 'bold',
                    'font-size': '12px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'border-width': 3,
                    'border-style': 'double',
                }
            },
        ];
    },

    setupEventHandlers() {
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            const nodeData = node.data();
            
            if (nodeData.isGroup) {
                this.toggleGroup(nodeData.groupType);
                return;
            }
            
            window.dispatchEvent(new CustomEvent('node-selected', { 
                detail: { nodeData: nodeData }
            }));
        });

        this.cy.on('dbltap', 'node', (evt) => {
            const node = evt.target;
            const nodeData = node.data();
            
            if (nodeData.isGroup) {
                return;
            }
            
            const url = nodeData.properties?.url;
            if (url) {
                window.open(url, '_blank');
            }
        });

        this.cy.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            window.dispatchEvent(new CustomEvent('node-hover', {
                detail: { 
                    nodeData: node.data(),
                    position: evt.renderedPosition 
                }
            }));
        });

        this.cy.on('mouseout', 'node', () => {
            window.dispatchEvent(new CustomEvent('node-hover-out'));
        });

        this.cy.on('grab', 'node', (evt) => {
            evt.target.data('dragging', true);
            console.log('Grab:', evt.target.id());
        });

        this.cy.on('free', 'node', (evt) => {
            evt.target.data('dragging', false);
            evt.target.data('vx', 0);
            evt.target.data('vy', 0);
            console.log('Free:', evt.target.id());
        });

        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                window.dispatchEvent(new CustomEvent('canvas-clicked'));
            }
        });
    },

    loadData(graphData) {
        console.log('loadData called');
        this.currentData = graphData;
        
        console.log('[loadData] calling stopSimulation');
        this.stopSimulation();
        
        const elements = this.transformData(graphData);
        
        this.cy.elements().remove();
        this.cy.add(elements);
        
        this.randomizePositions();
        
        this.cy.nodes().forEach(node => {
            node.data('vx', 0);
            node.data('vy', 0);
            node.data('dragging', false);
        });
        
        this.applyTypeFilter();
        
        const visibleCount = this.cy.nodes().not('.hidden').length;
        console.log('Before startSimulation, visible nodes:', visibleCount);
        
        this.startSimulation();
        
        console.log('After startSimulation, isSimulating:', this.isSimulating, 'animationId:', this.animationId);
    },

    transformData(graphData) {
        const nodes = graphData.nodes.map(node => {
            const type = node.data.type;
            const style = this.nodeStyles[type] || this.nodeStyles.default;
            
            return {
                group: 'nodes',
                data: {
                    ...node.data,
                    color: style.color,
                    borderColor: this.darkenColor(style.color, 20),
                    shape: style.shape,
                    baseType: type,
                }
            };
        });

        const edges = graphData.edges.map(edge => {
            const style = this.edgeStyles.default;
            
            return {
                group: 'edges',
                data: {
                    ...edge.data,
                    color: style.color,
                    lineStyle: style.lineStyle,
                    width: style.width || 1.5,
                }
            };
        });

        return [...nodes, ...edges];
    },

    randomizePositions() {
        const width = this.cy.width() || 800;
        const height = this.cy.height() || 600;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) * 0.3;

        this.cy.nodes().forEach(node => {
            const angle = Math.random() * 2 * Math.PI;
            const r = Math.random() * radius;
            node.position({
                x: centerX + r * Math.cos(angle),
                y: centerY + r * Math.sin(angle)
            });
        });
        console.log('Randomized positions, center:', centerX, centerY);
    },

    darkenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max((num >> 16) - amt, 0);
        const G = Math.max((num >> 8 & 0x00FF) - amt, 0);
        const B = Math.max((num & 0x0000FF) - amt, 0);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    },

    startSimulation() {
        console.log('[startSimulation] called, current animationId:', this.animationId);
        console.log('[startSimulation] calling stopSimulation');
        this.stopSimulation();
        this.frameCount = 0;
        this.isSimulating = true;
        
        const self = this;
        
        function loop() {
            if (!self.isSimulating) {
                console.log('Loop stopped because isSimulating is false');
                return;
            }
            self.frameCount++;
            
            if (self.frameCount <= 5) {
                console.log('Loop frame:', self.frameCount);
            }
            
            self.simulationStep();
            self.animationId = requestAnimationFrame(loop);
        }
        
        console.log('Calling requestAnimationFrame...');
        this.animationId = requestAnimationFrame(loop);
        console.log('animationId set to:', this.animationId);
    },

    stopSimulation(caller) {
        console.log('[stopSimulation] called from:', caller || 'unknown', ', animationId:', this.animationId);
        this.isSimulating = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    },

    simulationStep() {
        const nodes = this.cy.nodes().not('.hidden');
        
        if (nodes.length === 0) {
            return;
        }

        const width = this.cy.width() || 800;
        const height = this.cy.height() || 600;
        const centerX = width / 2;
        const centerY = height / 2;

        nodes.forEach((node, idx) => {
            if (node.data('dragging')) return;

            let fx = 0, fy = 0;
            const pos = node.position();

            nodes.forEach(other => {
                if (node.id() === other.id()) return;
                if (other.data('dragging')) return;
                
                const otherPos = other.position();
                const dx = pos.x - otherPos.x;
                const dy = pos.y - otherPos.y;
                const distSq = dx * dx + dy * dy;
                const dist = Math.sqrt(distSq) || 1;
                const force = this.physics.repulsion / distSq;
                fx += (dx / dist) * force;
                fy += (dy / dist) * force;
            });

            node.connectedEdges().not('.hidden').forEach(edge => {
                const other = edge.source().id() === node.id() ? edge.target() : edge.source();
                if (other.hasClass('hidden')) return;
                
                const otherPos = other.position();
                const dx = otherPos.x - pos.x;
                const dy = otherPos.y - pos.y;
                fx += dx * this.physics.attraction;
                fy += dy * this.physics.attraction;
            });

            fx += (centerX - pos.x) * this.physics.centerGravity;
            fy += (centerY - pos.y) * this.physics.centerGravity;

            let vx = (node.data('vx') || 0) + fx;
            let vy = (node.data('vy') || 0) + fy;
            
            vx *= this.physics.damping;
            vy *= this.physics.damping;

            node.data('vx', vx);
            node.data('vy', vy);

            if (this.frameCount <= 5 && idx === 0) {
                console.log(`  Node[0]: pos=(${pos.x.toFixed(1)},${pos.y.toFixed(1)}) v=(${vx.toFixed(2)},${vy.toFixed(2)})`);
            }
        });

        nodes.forEach(node => {
            if (node.data('dragging')) return;

            const vx = node.data('vx') || 0;
            const vy = node.data('vy') || 0;
            
            const pos = node.position();
            node.position({
                x: pos.x + vx,
                y: pos.y + vy
            });
        });
    },

    runLayout(layoutName = 'fcose') {
        console.log('[runLayout] calling stopSimulation');
        this.stopSimulation('runLayout');
        const layoutOptions = this.getLayoutOptions(layoutName);
        const layout = this.cy.layout(layoutOptions);
        layout.run();
    },

    runLayoutOnVisible(layoutName = 'fcose') {
        console.log('[runLayoutOnVisible] calling stopSimulation');
        this.stopSimulation('runLayoutOnVisible');
        
        const visibleElements = this.cy.elements().not('.hidden');
        if (visibleElements.length === 0) return;
        
        const layoutOptions = {
            ...this.getLayoutOptions(layoutName),
            animate: true,
            animationDuration: 300,
        };
        
        visibleElements.layout(layoutOptions).run();
    },

    getLayoutOptions(name) {
        const layouts = {
            fcose: {
                name: 'fcose',
                quality: 'default',
                randomize: true,
                animate: true,
                animationDuration: 500,
                fit: true,
                padding: 50,
                nodeSeparation: 150,
                idealEdgeLength: 150,
                nodeRepulsion: 6000,
                edgeElasticity: 0.45,
            },
            cose: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                fit: true,
                padding: 50,
                nodeRepulsion: 400000,
                idealEdgeLength: 100,
                edgeElasticity: 100,
            },
            concentric: {
                name: 'concentric',
                animate: true,
                fit: true,
                padding: 50,
                concentric: (node) => node.data('size') || 10,
                levelWidth: () => 2,
            },
            breadthfirst: {
                name: 'breadthfirst',
                animate: true,
                fit: true,
                padding: 50,
                directed: true,
                spacingFactor: 1.5,
            },
            circle: {
                name: 'circle',
                animate: true,
                fit: true,
                padding: 50,
            },
        };
        
        return layouts[name] || layouts.fcose;
    },

    setTypeFilter(types) {
        console.log('[setTypeFilter] called with types:', types);
        this.visibleTypes = new Set(types);
        this.applyTypeFilter();
    },

    applyTypeFilter() {
        this.cy.nodes().forEach(node => {
            const baseType = node.data('baseType') || node.data('type');
            if (this.visibleTypes.has(baseType)) {
                node.removeClass('hidden');
            } else {
                node.addClass('hidden');
            }
        });

        this.cy.edges().forEach(edge => {
            const source = edge.source();
            const target = edge.target();
            if (source.hasClass('hidden') || target.hasClass('hidden')) {
                edge.addClass('hidden');
            } else {
                edge.removeClass('hidden');
            }
        });
    },

    toggleGroup(groupType) {
    },

    setGroupingEnabled(enabled) {
    },

    highlightNode(nodeId) {
        this.cy.nodes().removeClass('highlighted');
        const node = this.cy.getElementById(nodeId);
        if (node) {
            node.addClass('highlighted');
            this.cy.animate({
                center: { eles: node },
                zoom: 1.5,
            }, { duration: 300 });
        }
    },

    fit() {
        this.cy.fit(50);
    },

    getStats() {
        return {
            nodes: this.cy.nodes().length,
            edges: this.cy.edges().length,
        };
    },
};

window.GraphManager = GraphManager;
