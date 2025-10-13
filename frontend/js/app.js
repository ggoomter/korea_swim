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
        this.darkOverlay = null;
        this.selectedPoolNumber = null;
        this.radiusCircle = null;
        this.focusAnchor = { x: 0.3, y: 0.5 };
        this.popupMargin = 80;
        this.popupUtils = (typeof SwimPopupUtils !== 'undefined') ? SwimPopupUtils : null;
        this.cardScrollBias = 0;
        this.popupAutoAdjust = false;  // 팝업 자동 조정 비활성화 (기본값)
    }

    isPublicSource(source) {
        if (!source) return false;
        return /(공공|서울시|행정)/i.test(source);
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
            this.logFocusSettings();
            console.info('🎛️ 위치 조정: swimDebug.지도세로(0.8) swimDebug.지도가로(0.6) swimDebug.리스트위치(-0.15)');
        } catch (error) {
            console.error('❌ Failed to initialize app:', error);
            this.showError('앱을 초기화하는 중 오류가 발생했습니다.');
        }
    }

    async loadConfig() {
        const response = await fetch('data/config.json');
        this.config = await response.json();
        if (this.config.map?.focusAnchor) {
            this.focusAnchor = {
                x: this.config.map.focusAnchor.x ?? this.focusAnchor.x,
                y: this.config.map.focusAnchor.y ?? this.focusAnchor.y
            };
        }
        if (typeof this.config.map?.popupMargin === 'number') {
            this.popupMargin = this.config.map.popupMargin;
        }
        if (typeof this.config.map?.cardScrollBias === 'number') {
            this.cardScrollBias = this.config.map.cardScrollBias;
        }
        this.popupUtils = (typeof SwimPopupUtils !== 'undefined') ? SwimPopupUtils : this.popupUtils;
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

        // Create custom pane for overlay that sits between tiles and overlays
        this.map.createPane('darkOverlay');
        this.map.getPane('darkOverlay').style.zIndex = 250;
        this.map.getPane('darkOverlay').style.pointerEvents = 'none';
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

        // Current location search
        document.getElementById('search-current').addEventListener('click', () => this.searchCurrentLocation());

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
            if (!response.ok) {
                throw new Error(`Failed to fetch pools: ${response.status}`);
            }
            const pools = await response.json();

            this.displayPools(pools);
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Failed to load pools:', error);
            this.showError('수영장 정보를 불러오는데 실패했습니다.');
        }
    }

    displayPools(pools, options = {}) {
        const { autoSelectFirst = false, focusOptions = {} } = options;
        // Clear existing pool markers only (keep user marker and subway)
        this.poolMarkers.forEach(marker => this.map.removeLayer(marker));
        this.poolMarkers = [];

        // Clear pool list
        const poolList = document.getElementById('pool-list');
        poolList.innerHTML = '';

        if (pools.length === 0) {
            poolList.innerHTML = '<div style="padding:20px; text-align:center; color:#94A3B8;">검색 결과가 없습니다</div>';
            return;
        }

        const orderedPools = [...pools];
        if (orderedPools.every(pool => typeof pool.distance === 'number')) {
            orderedPools.sort((a, b) => a.distance - b.distance);
        }

        orderedPools.forEach((pool, index) => {
            const number = index + 1;

            // Add marker
            const marker = this.createPoolMarker(pool, number);
            this.poolMarkers.push(marker);

            // Add list item
            const listItem = this.createPoolListItem(pool, number);
            poolList.appendChild(listItem);
        });

        if (autoSelectFirst && this.poolMarkers[0]) {
            // Delay selection until markers render, then focus with popup
            setTimeout(() => {
                this.selectPool(1, {
                    focusMap: true,
                    openPopup: true,
                    ...focusOptions
                });
            }, 0);
        }
    }

    createPoolMarker(pool, number) {
        const icon = L.divIcon({
            html: `
                <div class="custom-marker" data-pool-number="${number}">
                    <div class="marker-number">${number}</div>
                </div>
            `,
            className: 'custom-div-icon',
            iconSize: [32, 32],
            iconAnchor: [16, 32]
        });

        const marker = L.marker([pool.lat, pool.lng], { icon: icon });
        marker.poolNumber = number;

        // Add click event to select pool
        marker.on('click', () => {
            this.selectPool(number, { focusMap: true, openPopup: true });
        });

        const popupContent = this.createPopupContent(pool);
        marker.bindPopup(popupContent, {
            maxWidth: 320,
            maxHeight: 460,
            offset: [0, -18],
            autoPan: false,
            closeButton: true,
            autoClose: true
        });

        marker.addTo(this.map);

        // Add hover events using DOM after marker is added
        setTimeout(() => {
            const markerElement = marker.getElement();
            if (markerElement) {
                const markerDiv = markerElement.querySelector('.custom-marker');
                if (markerDiv) {
                    markerDiv.addEventListener('mouseenter', () => {
                        if (this.selectedPoolNumber !== number) {
                            this.highlightPoolCard(number);
                            markerDiv.classList.add('highlighted');
                        }
                    });

                    markerDiv.addEventListener('mouseleave', () => {
                        if (this.selectedPoolNumber !== number) {
                            this.unhighlightPoolCard(number);
                            markerDiv.classList.remove('highlighted');
                        }
                    });
                }
            }
        }, 0);

        return marker;
    }

    createPopupContent(pool) {
        return `
            <div class="pool-popup">
                <h3>${pool.name}</h3>
                ${pool.image_url ? `<img src="${pool.image_url}" alt="${pool.name}" class="pool-popup-image">` : ''}
                <p><strong>📍</strong> ${pool.address}</p>
                <p><strong>☎️</strong> ${pool.phone || '정보 없음'}</p>
                <p><strong>💰 한달 수강권:</strong> ${pool.monthly_lesson_price?.toLocaleString() || '문의'}원</p>
                <p><strong>🏊 자유수영:</strong> ${pool.free_swim_price?.toLocaleString() || '문의'}원</p>
                ${pool.rating ? `<p><strong>⭐ 평점:</strong> ${pool.rating}/5.0</p>` : ''}
                ${pool.description ? `<p class="description">${pool.description}</p>` : ''}
            </div>
        `;
    }

    createPoolListItem(pool, number) {
        const li = document.createElement('div');
        li.className = 'pool-card';  // NOTE: 'pool-card'는 실제로는 사이드바의 리스트 아이템입니다 (히스토리컬한 클래스명)
        li.dataset.poolNumber = number;
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
                        <span class="price-label">한달 수강권</span>
                        <span class="price-value">${pool.monthly_lesson_price?.toLocaleString() || '문의'}원</span>
                    </div>
                    <div class="price-item">
                        <span class="price-label">자유수영</span>
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
            this.selectPool(number, { focusMap: true, openPopup: true, zoom: 16 });
        });

        // Add hover events to highlight corresponding marker
        li.addEventListener('mouseenter', () => {
            if (this.selectedPoolNumber !== number) {
                this.highlightMarker(number);
            }
        });

        li.addEventListener('mouseleave', () => {
            if (this.selectedPoolNumber !== number) {
                this.unhighlightMarker(number);
            }
        });

        return li;
    }

    highlightSidebarListItem(number) {
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) {
            listItem.classList.add('highlighted');

            // Custom fast scroll animation (100ms)
            const container = document.querySelector('.pool-list-container');
            const itemTop = listItem.offsetTop;
            const containerTop = container.scrollTop;
            const containerHeight = container.clientHeight;
            const itemHeight = listItem.clientHeight;

            // Calculate target scroll position
            // Center the item, but don't scroll above the first item
            let targetScroll = itemTop - (containerHeight / 2) + (itemHeight / 2);

            // Don't scroll past the top (first item should stay visible)
            targetScroll = Math.max(0, Math.min(targetScroll, container.scrollHeight - containerHeight));

            // If item is in the top portion, just scroll to make it visible at the top
            if (itemTop < containerHeight / 3) {
                targetScroll = Math.max(0, itemTop - 20); // 20px padding from top
            }

            // Animate scroll in 100ms
            const startScroll = container.scrollTop;
            const distance = targetScroll - startScroll;
            const duration = 100; // 100ms
            const startTime = performance.now();

            const animateScroll = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Ease-out function for smooth deceleration
                const easeOut = 1 - Math.pow(1 - progress, 3);

                container.scrollTop = startScroll + (distance * easeOut);

                if (progress < 1) {
                    requestAnimationFrame(animateScroll);
                }
            };

            requestAnimationFrame(animateScroll);
        }
    }

    unhighlightSidebarListItem(number) {
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) {
            listItem.classList.remove('highlighted');
        }
    }

    // 하위 호환성
    highlightPoolCard(number) { this.highlightSidebarListItem(number); }
    unhighlightPoolCard(number) { this.unhighlightSidebarListItem(number); }

    ensureSidebarListItemVisible(listItem) {
        if (!listItem) return;
        const container = document.querySelector('.pool-list-container');
        if (!container) return;

        const itemTop = listItem.offsetTop;
        const containerTop = container.scrollTop;
        const containerHeight = container.clientHeight;
        const itemHeight = listItem.clientHeight;

        // cardScrollBias: -값이면 카드를 위쪽에, +값이면 아래쪽에 배치
        const anchor = 0.5 + this.cardScrollBias;
        const clampedAnchor = Math.min(Math.max(anchor, 0.1), 0.9);
        let targetScroll = itemTop - (containerHeight * clampedAnchor) + (itemHeight / 2);

        // 카드 윗부분이 잘리지 않도록 최소 여백 확보 (20px)
        const minTopMargin = 20;
        if (targetScroll > itemTop - minTopMargin) {
            targetScroll = Math.max(0, itemTop - minTopMargin);
        }

        targetScroll = Math.max(0, Math.min(targetScroll, container.scrollHeight - containerHeight));

        if (Math.abs(targetScroll - containerTop) < 4) {
            return;
        }

        const startScroll = container.scrollTop;
        const distance = targetScroll - startScroll;
        const duration = 120;
        const startTime = performance.now();

        const animateScroll = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            container.scrollTop = startScroll + (distance * easeOut);
            if (progress < 1) {
                requestAnimationFrame(animateScroll);
            }
        };

        requestAnimationFrame(animateScroll);
    }

    // 하위 호환성
    ensurePoolCardVisible(listItem) {
        this.ensureSidebarListItemVisible(listItem);
    }

    highlightMarker(number) {
        const marker = this.poolMarkers[number - 1];
        if (marker) {
            const markerElement = marker.getElement();
            if (markerElement) {
                const markerDiv = markerElement.querySelector('.custom-marker');
                if (markerDiv) {
                    markerDiv.classList.add('highlighted');
                }
            }
        }
    }

    unhighlightMarker(number) {
        const marker = this.poolMarkers[number - 1];
        if (marker) {
            const markerElement = marker.getElement();
            if (markerElement) {
                const markerDiv = markerElement.querySelector('.custom-marker');
                if (markerDiv) {
                    markerDiv.classList.remove('highlighted');
                }
            }
        }
    }

    selectPool(number, options = {}) {
        const { focusMap = false, openPopup = false, zoom = null } = options;
        // Remove previous selection
        if (this.selectedPoolNumber !== null) {
            // Remove selected class from previous card
            const prevCard = document.querySelector(`.pool-card[data-pool-number="${this.selectedPoolNumber}"]`);
            if (prevCard) {
                prevCard.classList.remove('selected');
            }

            // Remove selected class from previous marker
            const prevMarker = this.poolMarkers[this.selectedPoolNumber - 1];
            if (prevMarker) {
                const prevMarkerElement = prevMarker.getElement();
                if (prevMarkerElement) {
                    const prevMarkerDiv = prevMarkerElement.querySelector('.custom-marker');
                    if (prevMarkerDiv) {
                        prevMarkerDiv.classList.remove('selected');
                    }
                }
            }
        }

        // Set new selection
        this.selectedPoolNumber = number;

        // Add selected class to new list item
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) {
            listItem.classList.add('selected');
            this.ensureSidebarListItemVisible(listItem);
        }

        // Add selected class to new marker
        const marker = this.poolMarkers[number - 1];
        if (marker) {
            const markerElement = marker.getElement();
            if (markerElement) {
                const markerDiv = markerElement.querySelector('.custom-marker');
                if (markerDiv) {
                    markerDiv.classList.add('selected');
                }
            }

            if (focusMap) {
                this.focusOnMarker(marker, { openPopup, zoom });
            } else if (openPopup) {
                marker.openPopup();
                this.schedulePopupAdjustments(marker);
            }
        }
    }

    focusOnMarker(marker, options = {}) {
        const { openPopup = false, zoom = null } = options;
        if (!marker || !this.map) {
            return;
        }

        const targetZoom = zoom !== null ? zoom : Math.max(this.map.getZoom(), 14);
        const latlng = marker.getLatLng();
        const mapSize = this.map.getSize();
        const anchor = this.focusAnchor;

        // 직관적 계산: anchor.x=0.2 → 왼쪽에서 20%, anchor.y=0.2 → 위에서 20%
        const offset = L.point(
            (anchor.x - 0.5) * mapSize.x,  // 왼쪽 기준으로 변경
            (anchor.y - 0.5) * mapSize.y   // 위 기준으로 변경
        );

        const markerPoint = this.map.project(latlng, targetZoom);
        const targetPoint = markerPoint.subtract(offset);
        const targetLatLng = this.map.unproject(targetPoint, targetZoom);

        this.map.setView(targetLatLng, targetZoom, { animate: true });

        if (openPopup) {
            setTimeout(() => {
                marker.openPopup();
                this.schedulePopupAdjustments(marker);
            }, 240);
        } else {
            this.schedulePopupAdjustments(marker);
        }
    }

    schedulePopupAdjustments(marker) {
        // 팝업 자동 조정 비활성화 (focusOnMarker가 이미 최적 위치 설정)
        // 필요시 this.popupAutoAdjust = true로 활성화 가능
        if (!this.popupAutoAdjust) {
            return;
        }

        if (!marker || !marker.getPopup) {
            return;
        }

        const adjust = () => this.ensurePopupVisible(marker);
        requestAnimationFrame(adjust);
        setTimeout(adjust, 260);
    }

    ensurePopupVisible(marker) {
        if (!marker || !marker.getPopup) {
            return;
        }

        const popup = marker.getPopup();
        if (!popup) {
            return;
        }

        const popupEl = popup.getElement();
        if (!popupEl) {
            return;
        }

        const mapEl = this.map.getContainer();
        if (!mapEl) {
            return;
        }

        const mapRect = mapEl.getBoundingClientRect();
        const popupRect = popupEl.getBoundingClientRect();

        const mapSize = this.map.getSize();
        const maxShift = {
            x: Math.min(mapSize.x * 0.4, 250),
            y: Math.min(mapSize.y * 0.4, 220)
        };

        const utils = this.popupUtils;
        if (!utils || typeof utils.computePopupShift !== 'function') {
            return;
        }

        const shift = utils.computePopupShift(mapRect, popupRect, {
            margin: this.popupMargin,
            maxShift
        });

        if (Math.abs(shift.x) < 1 && Math.abs(shift.y) < 1) {
            return;
        }

        this.map.panBy([-shift.x, -shift.y], { animate: true, duration: 0.25 });
    }

    logFocusSettings() {
        console.info(
            `[SwimSeoul] 지도뷰포트=(가로:${this.focusAnchor.x.toFixed(2)}, 세로:${this.focusAnchor.y.toFixed(2)}), ` +
            `사이드바리스트위치=${this.cardScrollBias.toFixed(2)}, 팝업여백=${this.popupMargin}`
        );
        console.info(
            `  → 가로: 0.2=왼쪽 20%, 0.5=중앙, 0.8=오른쪽 80%\n` +
            `  → 세로: 0.2=위 20%, 0.5=중앙, 0.8=아래 80%\n` +
            `  → 리스트: -0.15=위쪽, 0=중앙, +0.15=아래쪽`
        );
    }

    setMapViewportVertical(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) {
            console.warn('[SwimSeoul] 숫자를 입력하세요 (0.05~0.95)');
            return;
        }
        const clamped = Math.min(Math.max(value, 0.05), 0.95);
        this.focusAnchor.y = clamped;
        console.info(`✅ 지도 뷰포트 세로: ${clamped.toFixed(2)} (위에서 ${(clamped*100).toFixed(0)}% 위치)`);
        this.logFocusSettings();
        this.recenterSelectedMarker();
    }

    setMapViewportHorizontal(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) {
            console.warn('[SwimSeoul] 숫자를 입력하세요 (0.05~0.95)');
            return;
        }
        const clamped = Math.min(Math.max(value, 0.05), 0.95);
        this.focusAnchor.x = clamped;
        console.info(`✅ 지도 뷰포트 가로: ${clamped.toFixed(2)} (왼쪽에서 ${(clamped*100).toFixed(0)}% 위치)`);
        this.logFocusSettings();
        this.recenterSelectedMarker();
    }

    setSidebarListItemPosition(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) {
            console.warn('[SwimSeoul] 숫자를 입력하세요 (-0.45~0.45)');
            return;
        }
        const clamped = Math.min(Math.max(value, -0.45), 0.45);
        this.cardScrollBias = clamped;
        console.info(`✅ 사이드바 리스트 위치: ${clamped.toFixed(2)} (음수=위쪽, 0=중앙, 양수=아래쪽)`);
        this.logFocusSettings();
        const listItem = document.querySelector(`.pool-card[data-pool-number="${this.selectedPoolNumber}"]`);
        this.ensureSidebarListItemVisible(listItem);
    }

    // 하위 호환성 유지 (기존 함수명)
    setFocusAnchorY(value) { this.setMapViewportVertical(value); }
    setCardScrollBias(value) { this.setSidebarListItemPosition(value); }
    setMarkerVerticalPosition(value) { this.setMapViewportVertical(value); }
    setMarkerHorizontalPosition(value) { this.setMapViewportHorizontal(value); }
    setCardVerticalPosition(value) { this.setSidebarListItemPosition(value); }

    recenterSelectedMarker({ openPopup = true } = {}) {
        if (!this.selectedPoolNumber) {
            return;
        }
        const marker = this.poolMarkers[this.selectedPoolNumber - 1];
        if (marker) {
            this.focusOnMarker(marker, { openPopup });
        }
    }

    getZoomForRadius(radiusKm) {
        if (radiusKm <= 2) return 15;
        if (radiusKm <= 3) return 14;
        if (radiusKm <= 5) return 13;
        if (radiusKm <= 10) return 12;
        if (radiusKm <= 15) return 11;
        if (radiusKm <= 25) return 10;
        return 9;
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
                // 지도 이동 제거 - searchNearbyPools에서 자동으로 처리
                await this.searchNearbyPools(this.userLocation);
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
            html: `
                <div style="
                    width: 20px;
                    height: 20px;
                    background: #EF4444;
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 2px 12px rgba(239, 68, 68, 0.6), 0 0 0 6px rgba(239, 68, 68, 0.15);
                "></div>
            `,
            className: 'user-location-marker',
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });

        this.userMarker = L.marker([location.lat, location.lng], { icon: userIcon })
            .bindPopup('<strong>📍 현재 위치</strong>')
            .addTo(this.map);
    }

    async searchNearbyPools(location) {
        const radius = parseFloat(document.getElementById('search-radius').value);
        try {
            const params = new URLSearchParams({
                lat: location.lat,
                lng: location.lng,
                radius: radius
            });

            const response = await fetch(
                `${this.config.api.baseUrl}${this.config.api.endpoints.nearby}?${params.toString()}`
            );
            if (!response.ok) {
                throw new Error(`Failed to load nearby pools: ${response.status}`);
            }
            const pools = await response.json();
            const zoom = this.getZoomForRadius(radius);

            // Update radius overlay and map view
            if (this.radiusCircle) {
                this.map.removeLayer(this.radiusCircle);
                this.radiusCircle = null;
            }

        this.radiusCircle = L.circle([location.lat, location.lng], {
            radius: radius * 1000,
            color: '#38BDF8',
            fillColor: '#38BDF8',
            fillOpacity: 0.08,
            weight: 2,
            dashArray: '4 4',
            interactive: false
        }).addTo(this.map);

            this.radiusCircle.bindTooltip(`${radius}km`, {
                permanent: true,
                direction: 'center',
                className: 'radius-tooltip'
            });

            const bounds = this.radiusCircle.getBounds();
            this.map.fitBounds(bounds, { padding: [60, 60] });

            // 첫 번째 수영장 자동 선택 및 focusAnchor 적용 (x: 0.6, y: 0.8)
            this.displayPools(pools, {
                autoSelectFirst: pools.length > 0,
                focusOptions: { zoom }
            });
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Nearby search failed:', error);
            this.showError('주변 수영장 정보를 불러오지 못했습니다.');
        }
    }

    async searchSeoulCenter() {
        const seoulCenter = this.config.map.defaultCenter;
        this.userLocation = seoulCenter;
        this.updateUserMarker(seoulCenter);
        // 지도 이동 제거 - searchNearbyPools에서 자동으로 처리
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

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to filter pools: ${response.status}`);
            }
            let pools = await response.json();

            if (type === 'public') {
                pools = pools.filter(pool => this.isPublicSource(pool.source));
            } else if (type === 'private') {
                pools = pools.filter(pool => pool.source && !this.isPublicSource(pool.source));
            }
            this.displayPools(pools);
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Filter failed:', error);
            this.showError('수영장 필터링 중 오류가 발생했습니다.');
        }
    }

    toggleSubway() {
        this.showSubway = !this.showSubway;
        const btn = document.getElementById('toggle-subway');

        btn.classList.toggle('active', this.showSubway);
        btn.textContent = this.showSubway ? '🚇 지하철 숨기기' : '🚇 지하철 노선도';

        // Toggle dark overlay using Leaflet pane
        if (this.showSubway) {
            if (!this.darkOverlay) {
                this.darkOverlay = L.rectangle(
                    [[33, 124], [39, 132]], // Cover Korea area
                    {
                        pane: 'darkOverlay',
                        color: 'transparent',
                        fillColor: '#000000',
                        fillOpacity: 0.4,
                        interactive: false
                    }
                ).addTo(this.map);
            }
            this.displaySubwayLines();
        } else {
            if (this.darkOverlay) {
                this.map.removeLayer(this.darkOverlay);
                this.darkOverlay = null;
            }
            this.hideSubwayLines();
        }
    }

    async searchCurrentLocation() {
        if (!navigator.geolocation) {
            alert('브라우저가 위치 서비스를 지원하지 않습니다.');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                this.userLocation = location;
                this.updateUserMarker(location);
                // 지도 이동 제거 - searchNearbyPools에서 자동으로 처리

                // Search nearby pools
                await this.searchNearbyPools(location);

                // If no pools found nearby, show all pools
                if (this.poolMarkers.length === 0) {
                    console.log('No pools found nearby, loading all pools');
                    await this.loadPools();
                }
            },
            (error) => {
                console.error('Location error:', error);
                alert('현재 위치를 가져올 수 없습니다. 위치 권한을 확인해주세요.');
            }
        );
    }

    displaySubwayLines() {
        this.subwayData.lines.forEach(line => {
            // Draw line connections
            const coordinates = line.stations.map(s => [s.lat, s.lng]);
            const polyline = L.polyline(coordinates, {
                color: line.color,
                weight: 6,
                opacity: 0.9,
                pane: 'overlayPane'
            }).addTo(this.map);
            this.subwayLines.push(polyline);

            // Add station markers
            line.stations.forEach(station => {
                const marker = L.circleMarker([station.lat, station.lng], {
                    radius: 7,
                    fillColor: line.color,
                    color: '#fff',
                    weight: 2.5,
                    opacity: 1,
                    fillOpacity: 0.95,
                    pane: 'overlayPane'
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
    window.swimApp = app;
    window.swimDebug = {
        // 새 함수명 (명확함)
        지도세로: (y) => app.setMapViewportVertical(y),
        지도가로: (x) => app.setMapViewportHorizontal(x),
        리스트위치: (b) => app.setSidebarListItemPosition(b),
        재배치: () => app.recenterSelectedMarker(),
        현재값: () => app.logFocusSettings(),
        팝업자동조정: (enable) => {
            app.popupAutoAdjust = !!enable;
            console.info(`✅ 팝업 자동 조정: ${app.popupAutoAdjust ? 'ON' : 'OFF'}`);
        },

        // 영문 별칭
        mapY: (y) => app.setMapViewportVertical(y),
        mapX: (x) => app.setMapViewportHorizontal(x),
        listY: (b) => app.setSidebarListItemPosition(b),
        recenter: () => app.recenterSelectedMarker(),
        print: () => app.logFocusSettings(),
        popupAdjust: (enable) => {
            app.popupAutoAdjust = !!enable;
            console.info(`✅ Popup auto-adjust: ${app.popupAutoAdjust ? 'ON' : 'OFF'}`);
        },

        // 하위 호환 (기존 함수명)
        setFocusAnchorY: (y) => app.setFocusAnchorY(y),
        setCardScrollBias: (b) => app.setCardScrollBias(b),
        마커세로: (y) => app.setMapViewportVertical(y),
        마커가로: (x) => app.setMapViewportHorizontal(x),
        카드세로: (b) => app.setSidebarListItemPosition(b)
    };
    app.init();
});
