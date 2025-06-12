/**
 * LLM DriftGuard - Semantic Analysis Visualization
 * Interactive visualizations for semantic comparison and analysis
 */

// Semantic Similarity Network Visualization
class SemanticNetworkViz {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = 800;
        this.height = 600;
        this.nodes = [];
        this.links = [];
        this.simulation = null;
        
        this.initializeNetwork();
    }
    
    initializeNetwork() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height)
            .style('border', '1px solid #ccc');
        
        // Create force simulation
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2));
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.svg.selectAll('g').attr('transform', event.transform);
            });
        
        this.svg.call(zoom);
        
        // Create container group
        this.g = this.svg.append('g');
        
        // Initialize tooltip
        this.tooltip = d3.select('body')
            .append('div')
            .attr('class', 'semantic-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none');
    }
    
    updateData(semanticData) {
        // Transform data into nodes and links
        this.nodes = semanticData.map((d, i) => ({
            id: d.id || i,
            text: d.text || d.response || '',
            model: d.model_id || 'unknown',
            similarity: d.similarity_score || 0,
            timestamp: new Date(d.timestamp || Date.now()),
            drift_score: d.drift_score || 0,
            confidence: d.confidence_score || 0
        }));
        
        // Create links based on similarity
        this.links = [];
        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                const similarity = this.calculateSimilarity(this.nodes[i], this.nodes[j]);
                if (similarity > 0.5) {
                    this.links.push({
                        source: this.nodes[i].id,
                        target: this.nodes[j].id,
                        similarity: similarity,
                        weight: similarity
                    });
                }
            }
        }
        
        this.render();
    }
    
    calculateSimilarity(node1, node2) {
        // Simple similarity calculation based on text overlap
        const words1 = new Set(node1.text.toLowerCase().split(' '));
        const words2 = new Set(node2.text.toLowerCase().split(' '));
        const intersection = new Set([...words1].filter(x => words2.has(x)));
        const union = new Set([...words1, ...words2]);
        return intersection.size / union.size;
    }
    
    render() {
        // Clear existing elements
        this.g.selectAll('*').remove();
        
        // Create color scales
        const modelColorScale = d3.scaleOrdinal(d3.schemeCategory10);
        const similarityColorScale = d3.scaleSequential(d3.interpolateBlues)
            .domain([0, 1]);
        
        // Add links
        const link = this.g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(this.links)
            .enter().append('line')
            .attr('stroke', d => similarityColorScale(d.similarity))
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight) * 5);
        
        // Add nodes
        const node = this.g.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(this.nodes)
            .enter().append('circle')
            .attr('r', d => 5 + d.confidence * 10)
            .attr('fill', d => modelColorScale(d.model))
            .attr('stroke', d => d.drift_score > 0.5 ? '#ff4444' : '#333')
            .attr('stroke-width', d => d.drift_score > 0.5 ? 3 : 1)
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip())
            .call(this.drag());
        
        // Add labels
        const label = this.g.append('g')
            .attr('class', 'labels')
            .selectAll('text')
            .data(this.nodes)
            .enter().append('text')
            .text(d => d.model)
            .style('font-size', '10px')
            .style('text-anchor', 'middle')
            .style('pointer-events', 'none');
        
        // Update simulation
        this.simulation
            .nodes(this.nodes)
            .on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                label
                    .attr('x', d => d.x)
                    .attr('y', d => d.y + 4);
            });
        
        this.simulation.force('link')
            .links(this.links);
        
        this.simulation.alpha(1).restart();
    }
    
    drag() {
        function dragstarted(event, d) {
            if (!event.active) this.simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) this.simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        return d3.drag()
            .on('start', dragstarted.bind(this))
            .on('drag', dragged)
            .on('end', dragended.bind(this));
    }
    
    showTooltip(event, d) {
        this.tooltip.transition()
            .duration(200)
            .style('opacity', 0.9);
        
        const tooltipContent = `
            <div><strong>Model:</strong> ${d.model}</div>
            <div><strong>Time:</strong> ${d.timestamp.toLocaleTimeString()}</div>
            <div><strong>Drift Score:</strong> ${d.drift_score.toFixed(3)}</div>
            <div><strong>Confidence:</strong> ${d.confidence.toFixed(3)}</div>
            <div><strong>Text Preview:</strong> ${d.text.substring(0, 50)}...</div>
        `;
        
        this.tooltip.html(tooltipContent)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
    }
    
    hideTooltip() {
        this.tooltip.transition()
            .duration(500)
            .style('opacity', 0);
    }
}

// Semantic Similarity Matrix Visualization
class SimilarityMatrixViz {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.margin = {top: 80, right: 80, bottom: 80, left: 80};
        this.width = 500 - this.margin.left - this.margin.right;
        this.height = 500 - this.margin.top - this.margin.bottom;
        
        this.initializeMatrix();
    }
    
    initializeMatrix() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Create color scale
        this.colorScale = d3.scaleSequential(d3.interpolateRdYlBu)
            .domain([0, 1]);
    }
    
    updateData(matrixData) {
        this.data = matrixData;
        this.render();
    }
    
    render() {
        if (!this.data || this.data.length === 0) return;
        
        const models = [...new Set(this.data.map(d => d.model1))];
        const n = models.length;
        const cellSize = Math.min(this.width, this.height) / n;
        
        // Create scales
        const xScale = d3.scaleBand()
            .domain(models)
            .range([0, this.width])
            .padding(0.05);
        
        const yScale = d3.scaleBand()
            .domain(models)
            .range([0, this.height])
            .padding(0.05);
        
        // Create matrix cells
        const cells = this.svg.selectAll('.matrix-cell')
            .data(this.data);
        
        cells.enter()
            .append('rect')
            .attr('class', 'matrix-cell')
            .attr('x', d => xScale(d.model1))
            .attr('y', d => yScale(d.model2))
            .attr('width', xScale.bandwidth())
            .attr('height', yScale.bandwidth())
            .attr('fill', d => this.colorScale(d.similarity))
            .attr('stroke', '#fff')
            .attr('stroke-width', 1)
            .on('mouseover', (event, d) => this.showMatrixTooltip(event, d))
            .on('mouseout', () => this.hideMatrixTooltip());
        
        cells.transition()
            .duration(750)
            .attr('fill', d => this.colorScale(d.similarity));
        
        cells.exit().remove();
        
        // Add axes
        this.svg.selectAll('.x-axis-matrix').remove();
        this.svg.append('g')
            .attr('class', 'x-axis-matrix')
            .attr('transform', `translate(0,${this.height})`)
            .call(d3.axisBottom(xScale))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-65)');
        
        this.svg.selectAll('.y-axis-matrix').remove();
        this.svg.append('g')
            .attr('class', 'y-axis-matrix')
            .call(d3.axisLeft(yScale));
        
        // Add similarity values as text
        const text = this.svg.selectAll('.matrix-text')
            .data(this.data);
        
        text.enter()
            .append('text')
            .attr('class', 'matrix-text')
            .attr('x', d => xScale(d.model1) + xScale.bandwidth() / 2)
            .attr('y', d => yScale(d.model2) + yScale.bandwidth() / 2)
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .style('font-size', '10px')
            .style('fill', d => d.similarity > 0.5 ? 'white' : 'black')
            .text(d => d.similarity.toFixed(2));
        
        text.transition()
            .duration(750)
            .text(d => d.similarity.toFixed(2));
        
        text.exit().remove();
    }
    
    showMatrixTooltip(event, d) {
        // Similar tooltip implementation
    }
    
    hideMatrixTooltip() {
        // Hide tooltip
    }
}

// Word Cloud for Semantic Analysis
class SemanticWordCloud {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = 600;
        this.height = 400;
        
        this.initializeWordCloud();
    }
    
    initializeWordCloud() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        this.g = this.svg.append('g')
            .attr('transform', `translate(${this.width/2},${this.height/2})`);
    }
    
    updateData(textData) {
        // Extract words and frequencies
        const words = this.extractWords(textData);
        this.renderWordCloud(words);
    }
    
    extractWords(textData) {
        const stopWords = new Set(['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'a', 'an']);
        const wordFreq = {};
        
        textData.forEach(d => {
            const text = (d.response || d.text || '').toLowerCase();
            const words = text.match(/\b\w+\b/g) || [];
            
            words.forEach(word => {
                if (word.length > 3 && !stopWords.has(word)) {
                    wordFreq[word] = (wordFreq[word] || 0) + 1;
                }
            });
        });
        
        // Convert to array and sort
        return Object.entries(wordFreq)
            .map(([word, freq]) => ({text: word, size: freq}))
            .sort((a, b) => b.size - a.size)
            .slice(0, 50);
    }
    
    renderWordCloud(words) {
        if (words.length === 0) return;
        
        const maxSize = d3.max(words, d => d.size);
        const sizeScale = d3.scaleLinear()
            .domain([1, maxSize])
            .range([10, 40]);
        
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
        
        // Clear previous words
        this.g.selectAll('text').remove();
        
        // Simple word cloud layout (not using d3-cloud for simplicity)
        const radius = 150;
        words.forEach((d, i) => {
            const angle = (i / words.length) * 2 * Math.PI;
            const r = Math.random() * radius;
            d.x = Math.cos(angle) * r;
            d.y = Math.sin(angle) * r;
        });
        
        this.g.selectAll('text')
            .data(words)
            .enter().append('text')
            .attr('text-anchor', 'middle')
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .text(d => d.text)
            .style('font-size', d => sizeScale(d.size) + 'px')
            .style('font-family', 'sans-serif')
            .style('fill', (d, i) => colorScale(i))
            .style('opacity', 0)
            .transition()
            .duration(1000)
            .style('opacity', 1);
    }
}

// Initialize semantic visualizations
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('semantic-network')) {
        window.semanticNetwork = new SemanticNetworkViz('semantic-network');
    }
    
    if (document.getElementById('similarity-matrix')) {
        window.similarityMatrix = new SimilarityMatrixViz('similarity-matrix');
    }
    
    if (document.getElementById('semantic-wordcloud')) {
        window.semanticWordCloud = new SemanticWordCloud('semantic-wordcloud');
    }
});

// Export classes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SemanticNetworkViz, SimilarityMatrixViz, SemanticWordCloud };
}
