// SwimSeoul - Main Application Logic
class SwimSeoulApp {
    constructor() {
        this.config = null;
        this.subwayData = null;
        this.map = null;
        this.poolMarkers = [];
        this.subwayMarkers = [];
        this.subwayLines = [];
        this.showSubway = false;
        this.userMarker = null;
        this.userLocation = null;
    }

    async init() {
        try {
            // Load configuration and data
            await this.loadConfig();
            await this.loadSubwayData();

            // Initialize map
            this.initMap();

            // Setup event listeners
            this.setupEventListeners();

            // Load pools
            await this.loadPools();

            console.log('✅ SwimSeoul initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize app:', error);
            this.showError('앱을 초기화하는 중 오류가 발생했습니다.');
        }
    }

    async loadConfig() {
        const response = await fetch('data/config.json');
        this.config = await response.json();
    }

    async loadSubwayData() {
        const response = await fetch('data/subway_lines.json');
        this.subwayData = await response.json();
    }

    initMap() {
        const { defaultCenter, defaultZoom, tileLayer, attribution } = this.config.map;

        this.map = L.map('map').setView([defaultCenter.lat, defaultCenter.lng], defaultZoom);

        L.tileLayer(tileLayer, {
            attribution: attribution,
            maxZoom: 19
        }).addTo(this.map);
    }

    setupEventListeners() {
        // Address search
        const addressInput = document.getElementById('address-search');
        let searchTimeout;

        addressInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (e.target.value.trim().length > 1) {
                    this.searchAddress(e.target.value);
                }
            }, this.config.search.debounceDelay);
        });

        // Filter buttons
        document.getElementById('filter-all').addEventListener('click', () => this.filterPools('all'));
        document.getElementById('filter-public').addEventListener('click', () => this.filterPools('public'));
        document.getElementById('filter-private').addEventListener('click', () => this.filterPools('private'));

        // Subway toggle
        document.getElementById('toggle-subway').addEventListener('click', () => this.toggleSubway());

        // Seoul center search
        document.getElementById('search-seoul').addEventListener('click', () => this.searchSeoulCenter());

        // Radius change
        document.getElementById('search-radius').addEventListener('change', (e) => {
            this.searchByRadius(parseFloat(e.target.value));
        });
    }

    async loadPools() {
        try {
            const response = await fetch(`${this.config.api.baseUrl}${this.config.api.endpoints.pools}`);
            const pools = await response.json();

            this.displayPools(pools);
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Failed to load pools:', error);
            this.showError('수영장 정보를 불러오는데 실패했습니다.');
        }
    }

    displayPools(pools) {
        // Clear existing markers
        this.poolMarkers.forEach(marker => this.map.removeLayer(marker));
        this.poolMarkers = [];

        // Clear pool list
        const poolList = document.getElementById('pool-list');
        poolList.innerHTML = '';

        pools.forEach((pool, index) => {
            // Add marker
            const marker = this.createPoolMarker(pool, index + 1);
            this.poolMarkers.push(marker);

            // Add list item
            const listItem = this.createPoolListItem(pool, index + 1);
            poolList.appendChild(listItem);
        });
    }

    createPoolMarker(pool, number) {
        const markerDiv = document.createElement('div');
        markerDiv.className = 'custom-marker';
        markerDiv.innerHTML = `
            <div class="marker-number">${number}</div>
            <div class="marker-name">${pool.name}</div>
        `;

        const icon = L.divIcon({
            html: markerDiv.outerHTML,
            className: 'custom-div-icon',
            iconSize: [160, 50],
            iconAnchor: [80, 50]
        });

        const marker = L.marker([pool.lat, pool.lng], { icon: icon });

        const popupContent = this.createPopupContent(pool);
        marker.bindPopup(popupContent, { maxWidth: 300 });
        marker.addTo(this.map);

        return marker;
    }

    createPopupContent(pool) {
        return `
            <div class="pool-popup">
                <h3>${pool.name}</h3>
                ${pool.image_url ? `<img src="${pool.image_url}" alt="${pool.name}" style="width:100%; border-radius:8px; margin:8px 0;">` : ''}
                <p><strong>📍</strong> ${pool.address}</p>
                <p><strong>☎️</strong> ${pool.phone || '정보 없음'}</p>
                <p><strong>💰 일일권:</strong> ${pool.daily_price?.toLocaleString() || '문의'}원</p>
                <p><strong>🏊 자율수영:</strong> ${pool.free_swim_price?.toLocaleString() || '문의'}원</p>
                ${pool.rating ? `<p><strong>⭐ 평점:</strong> ${pool.rating}/5.0</p>` : ''}
                ${pool.description ? `<p class="description">${pool.description}</p>` : ''}
            </div>
        `;
    }

    createPoolListItem(pool, number) {
        const li = document.createElement('div');
        li.className = 'pool-card';
        li.innerHTML = `
            <div class="pool-number">${number}</div>
            <div class="pool-info">
                <h3 class="pool-name">${pool.name}</h3>
                <p class="pool-address">${pool.address}</p>
                <div class="pool-meta">
                    <span class="meta-badge">${pool.source || '공공시설'}</span>
                    ${pool.rating ? `<span class="meta-rating">⭐ ${pool.rating}</span>` : ''}
                </div>
                <div class="pool-prices">
                    <div class="price-item">
                        <span class="price-label">일일권</span>
                        <span class="price-value">${pool.daily_price?.toLocaleString() || '문의'}원</span>
                    </div>
                    <div class="price-item">
                        <span class="price-label">자율수영</span>
                        <span class="price-value">${pool.free_swim_price?.toLocaleString() || '문의'}원</span>
                    </div>
                </div>
                ${pool.facilities && pool.facilities.length > 0 ? `
                    <div class="pool-facilities">
                        ${pool.facilities.slice(0, 4).map(f => `<span class="facility-tag">${f}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;

        li.addEventListener('click', () => {
            this.map.setView([pool.lat, pool.lng], 16);
            this.poolMarkers[number - 1].openPopup();
        });

        return li;
    }

    async searchAddress(query) {
        try {
            const url = `${this.config.search.nominatimUrl}?q=${encodeURIComponent(query + ' 서울')}&format=json&limit=1`;
            const response = await fetch(url);
            const results = await response.json();

            if (results && results.length > 0) {
                const { lat, lon } = results[0];
                this.userLocation = { lat: parseFloat(lat), lng: parseFloat(lon) };
                this.updateUserMarker(this.userLocation);
                this.map.setView([this.userLocation.lat, this.userLocation.lng], 14);
                this.searchNearbyPools(this.userLocation);
            }
        } catch (error) {
            console.error('Address search failed:', error);
        }
    }

    updateUserMarker(location) {
        if (this.userMarker) {
            this.map.removeLayer(this.userMarker);
        }

        const userIcon = L.divIcon({
            html: '<div style="background:#EC4899; width:20px; height:20px; border-radius:50%; border:3px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.3);"></div>',
            className: '',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        this.userMarker = L.marker([location.lat, location.lng], { icon: userIcon })
            .bindPopup('📍 현재 위치')
            .addTo(this.map);
    }

    async searchNearbyPools(location) {
        const radius = parseFloat(document.getElementById('search-radius').value);
        try {
            const response = await fetch(
                `${this.config.api.baseUrl}${this.config.api.endpoints.nearby}?lat=${location.lat}&lng=${location.lng}&radius=${radius}`
            );
            const pools = await response.json();
            this.displayPools(pools);
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Nearby search failed:', error);
        }
    }

    async searchSeoulCenter() {
        const seoulCenter = this.config.map.defaultCenter;
        this.userLocation = seoulCenter;
        this.updateUserMarker(seoulCenter);
        this.map.setView([seoulCenter.lat, seoulCenter.lng], 12);
        await this.searchNearbyPools(seoulCenter);
    }

    async searchByRadius(radius) {
        if (this.userLocation) {
            await this.searchNearbyPools(this.userLocation);
        }
    }

    async filterPools(type) {
        // Update active button
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`filter-${type}`).classList.add('active');

        try {
            let url = `${this.config.api.baseUrl}${this.config.api.endpoints.pools}`;
            if (type !== 'all') {
                const source = type === 'public' ? '공공시설' : '민간시설';
                url += `?source=${encodeURIComponent(source)}`;
            }

            const response = await fetch(url);
            const pools = await response.json();
            this.displayPools(pools);
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Filter failed:', error);
        }
    }

    toggleSubway() {
        this.showSubway = !this.showSubway;
        const btn = document.getElementById('toggle-subway');
        btn.classList.toggle('active', this.showSubway);
        btn.textContent = this.showSubway ? '🚇 지하철 숨기기' : '🚇 지하철 노선도';

        if (this.showSubway) {
            this.displaySubwayLines();
        } else {
            this.hideSubwayLines();
        }
    }

    displaySubwayLines() {
        this.subwayData.lines.forEach(line => {
            // Draw line connections
            const coordinates = line.stations.map(s => [s.lat, s.lng]);
            const polyline = L.polyline(coordinates, {
                color: line.color,
                weight: 3,
                opacity: 0.7
            }).addTo(this.map);
            this.subwayLines.push(polyline);

            // Add station markers
            line.stations.forEach(station => {
                const marker = L.circleMarker([station.lat, station.lng], {
                    radius: 5,
                    fillColor: line.color,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).bindPopup(`<strong>${station.name}</strong><br>${line.name}`).addTo(this.map);

                this.subwayMarkers.push(marker);
            });
        });
    }

    hideSubwayLines() {
        this.subwayLines.forEach(line => this.map.removeLayer(line));
        this.subwayMarkers.forEach(marker => this.map.removeLayer(marker));
        this.subwayLines = [];
        this.subwayMarkers = [];
    }

    updateStats(count) {
        document.querySelector('.stat-number').textContent = count;
    }

    showError(message) {
        alert(message);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new SwimSeoulApp();
    app.init();
});
