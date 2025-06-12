/**
 * LLM DriftGuard - Drift Visualization JavaScript
 * Interactive visualizations for semantic drift analysis
 */

// Drift Visualization Class
class DriftVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.margin = {top: 20, right: 30, bottom: 40, left: 50};
        this.width = 800 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;
        
        // Initialize D3 scales and axes
        this.xScale = d3.scaleTime().range([0, this.width]);
        this.yScale = d3.scaleLinear().range([this.height, 0]);
        this.colorScale = d3.scaleOrdinal(d3.schemeCategory10);
        
        this.svg = null;
        this.data = [];
        this.tooltip = null;
        
        this.initializeVisualization();
    }
    
    initializeVisualization() {
        // Clear any existing content
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        // Create SVG
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Create tooltip
        this.tooltip = d3.select('body')
            .append('div')
            .attr('class', 'drift-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none');
        
        // Add axes
        this.svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.height})`);
        
        this.svg.append('g')
            .attr('class', 'y-axis');
        
        // Add axis labels
        this.svg.append('text')
            .attr('class', 'x-label')
            .attr('text-anchor', 'middle')
            .attr('x', this.width / 2)
            .attr('y', this.height + 35)
            .text('Time');
        
        this.svg.append('text')
            .attr('class', 'y-label')
            .attr('text-anchor', 'middle')
            .attr('y', -35)
            .attr('x', -this.height / 2)
            .attr('transform', 'rotate(-90)')
            .text('Drift Score');
        
        // Add threshold line
        this.addThresholdLine(0.5);
    }
    
    addThresholdLine(threshold) {
        this.svg.append('line')
            .attr('class', 'threshold-line')
            .attr('x1', 0)
            .attr('x2', this.width)
            .attr('y1', this.yScale(threshold))
            .attr('y2', this.yScale(threshold))
            .style('stroke', '#ff6b6b')
            .style('stroke-width', 2)
            .style('stroke-dasharray', '5,5')
            .style('opacity', 0.7);
        
        this.svg.append('text')
            .attr('class', 'threshold-label')
            .attr('x', this.width - 80)
            .attr('y', this.yScale(threshold) - 5)
            .text(`Threshold: ${threshold}`)
            .style('font-size', '12px')
            .style('fill', '#ff6b6b');
    }
    
    updateData(newData) {
        this.data = newData.map(d => ({
            timestamp: new Date(d.timestamp),
            driftScore: +d.drift_score,
            modelId: d.model_id,
            confidence: +d.confidence_score || 0,
            responseTime: +d.response_time || 0
        }));
        
        this.render();
    }
    
    render() {
        if (!this.data || this.data.length === 0) return;
        
        // Update scales
        this.xScale.domain(d3.extent(this.data, d => d.timestamp));
        this.yScale.domain([0, d3.max(this.data, d => d.driftScore) * 1.1]);
        
        // Update axes
        this.svg.select('.x-axis')
            .transition()
            .duration(750)
            .call(d3.axisBottom(this.xScale).tickFormat(d3.timeFormat('%H:%M')));
        
        this.svg.select('.y-axis')
            .transition()
            .duration(750)
            .call(d3.axisLeft(this.yScale));
        
        // Group data by model
        const groupedData = d3.group(this.data, d => d.modelId);
        
        // Create line generator
        const line = d3.line()
            .x(d => this.xScale(d.timestamp))
            .y(d => this.yScale(d.driftScore))
            .curve(d3.curveMonotoneX);
        
        // Bind data to lines
        const lines = this.svg.selectAll('.drift-line')
            .data(Array.from(groupedData), d => d[0]);
        
        // Enter new lines
        lines.enter()
            .append('path')
            .attr('class', 'drift-line')
            .attr('fill', 'none')
            .attr('stroke', d => this.colorScale(d[0]))
            .attr('stroke-width', 2)
            .attr('d', d => line(d[1]))
            .style('opacity', 0)
            .transition()
            .duration(750)
            .style('opacity', 1);
        
        // Update existing lines
        lines.transition()
            .duration(750)
            .attr('d', d => line(d[1]));
        
        // Remove old lines
        lines.exit()
            .transition()
            .duration(750)
            .style('opacity', 0)
            .remove();
        
        // Add data points
        const circles = this.svg.selectAll('.data-point')
            .data(this.data);
        
        circles.enter()
            .append('circle')
            .attr('class', 'data-point')
            .attr('cx', d => this.xScale(d.timestamp))
            .attr('cy', d => this.yScale(d.driftScore))
            .attr('r', 3)
            .attr('fill', d => this.colorScale(d.modelId))
            .style('opacity', 0.7)
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip())
            .on('click', (event, d) => this.onPointClick(d));
        
        circles.transition()
            .duration(750)
            .attr('cx', d => this.xScale(d.timestamp))
            .attr('cy', d => this.yScale(d.driftScore));
        
        circles.exit()
            .transition()
            .duration(750)
            .style('opacity', 0)
            .remove();
        
        // Update threshold line position
        this.svg.select('.threshold-line')
            .transition()
            .duration(750)
            .attr('y1', this.yScale(0.5))
            .attr('y2', this.yScale(0.5));
        
        this.svg.select('.threshold-label')
            .transition()
            .duration(750)
            .attr('y', this.yScale(0.5) - 5);
    }
    
    showTooltip(event, d) {
        this.tooltip.transition()
            .duration(200)
            .style('opacity', 0.9);
        
        const tooltipContent = `
            <div><strong>Model:</strong> ${d.modelId}</div>
            <div><strong>Time:</strong> ${d.timestamp.toLocaleTimeString()}</div>
            <div><strong>Drift Score:</strong> ${d.driftScore.toFixed(3)}</div>
            <div><strong>Confidence:</strong> ${d.confidence.toFixed(3)}</div>
            <div><strong>Response Time:</strong> ${d.responseTime.toFixed(2)}s</div>
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
    
    onPointClick(d) {
        // Emit custom event for point selection
        const event = new CustomEvent('driftPointSelected', {
            detail: d
        });
        document.dispatchEvent(event);
    }
    
    setThreshold(newThreshold) {
        this.svg.select('.threshold-line')
            .transition()
            .duration(500)
            .attr('y1', this.yScale(newThreshold))
            .attr('y2', this.yScale(newThreshold));
        
        this.svg.select('.threshold-label')
            .transition()
            .duration(500)
            .attr('y', this.yScale(newThreshold) - 5)
            .text(`Threshold: ${newThreshold}`);
    }
    
    highlightModel(modelId) {
        this.svg.selectAll('.drift-line')
            .style('opacity', d => d[0] === modelId ? 1 : 0.3);
        
        this.svg.selectAll('.data-point')
            .style('opacity', d => d.modelId === modelId ? 1 : 0.3);
    }
    
    resetHighlight() {
        this.svg.selectAll('.drift-line')
            .style('opacity', 1);
        
        this.svg.selectAll('.data-point')
            .style('opacity', 0.7);
    }
}

// Heatmap Visualization Class
class DriftHeatmap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.margin = {top: 50, right: 50, bottom: 50, left: 100};
        this.width = 600 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;
        this.gridSize = Math.floor(this.width / 24);
        
        this.svg = null;
        this.data = [];
        
        this.initializeHeatmap();
    }
    
    initializeHeatmap() {
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
        this.colorScale = d3.scaleSequential(d3.interpolateReds)
            .domain([0, 1]);
    }
    
    updateData(newData) {
        this.data = newData;
        this.render();
    }
    
    render() {
        if (!this.data || this.data.length === 0) return;
        
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const hours = d3.range(24);
        
        // Create scales
        const xScale = d3.scaleBand()
            .domain(hours)
            .range([0, this.width])
            .padding(0.05);
        
        const yScale = d3.scaleBand()
            .domain(days)
            .range([0, this.height])
            .padding(0.05);
        
        // Bind data to rectangles
        const rectangles = this.svg.selectAll('.heatmap-cell')
            .data(this.data);
        
        rectangles.enter()
            .append('rect')
            .attr('class', 'heatmap-cell')
            .attr('x', d => xScale(d.hour))
            .attr('y', d => yScale(d.day))
            .attr('width', xScale.bandwidth())
            .attr('height', yScale.bandwidth())
            .attr('fill', d => this.colorScale(d.driftScore))
            .on('mouseover', (event, d) => this.showHeatmapTooltip(event, d))
            .on('mouseout', () => this.hideHeatmapTooltip());
        
        rectangles.transition()
            .duration(750)
            .attr('fill', d => this.colorScale(d.driftScore));
        
        rectangles.exit().remove();
        
        // Add axes
        this.svg.selectAll('.x-axis-heatmap').remove();
        this.svg.append('g')
            .attr('class', 'x-axis-heatmap')
            .attr('transform', `translate(0,${this.height})`)
            .call(d3.axisBottom(xScale));
        
        this.svg.selectAll('.y-axis-heatmap').remove();
        this.svg.append('g')
            .attr('class', 'y-axis-heatmap')
            .call(d3.axisLeft(yScale));
    }
    
    showHeatmapTooltip(event, d) {
        // Similar tooltip implementation as line chart
    }
    
    hideHeatmapTooltip() {
        // Hide tooltip
    }
}

// Initialize visualizations when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize drift visualizer if container exists
    if (document.getElementById('drift-visualizer')) {
        window.driftVisualizer = new DriftVisualizer('drift-visualizer');
    }
    
    // Initialize heatmap if container exists
    if (document.getElementById('drift-heatmap')) {
        window.driftHeatmap = new DriftHeatmap('drift-heatmap');
    }
    
    // Listen for Splunk search results and update visualizations
    if (typeof splunkjs !== 'undefined') {
        // Integration with Splunk Web Framework would go here
        console.log('Splunk JS SDK detected - ready for integration');
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DriftVisualizer, DriftHeatmap };
}
