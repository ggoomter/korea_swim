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
        this.popupAutoAdjust = false;

        // New UI Elements
        this.loader = document.getElementById('loader');
        this.isMobileMapView = false;
    }

    isPublicSource(source) {
        if (!source) return false;
        return /(공공|서울시|행정)/i.test(source);
    }

    formatPrice(price) {
        if (!price) return '문의';
        if (/^\d+$/.test(String(price))) {
            return parseInt(price).toLocaleString() + '원';
        }
        return price;
    }

    isNowOpen(operatingHours) {
        if (!operatingHours) return { status: 'unknown', text: '운영시간 정보 없음' };

        try {
            const now = new Date();
            const days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
            const day = days[now.getDay()];
            const currentTime = now.getHours() * 60 + now.getMinutes();

            let todayHours = operatingHours[day];

            if (!todayHours) {
                if (['mon', 'tue', 'wed', 'thu', 'fri'].includes(day) && operatingHours['mon-fri']) {
                    todayHours = operatingHours['mon-fri'];
                } else if (['sat', 'sun'].includes(day) && operatingHours['weekend']) {
                    todayHours = operatingHours['weekend'];
                } else if (day === 'sat' && operatingHours['sat']) {
                    todayHours = operatingHours['sat'];
                } else if (day === 'sun' && operatingHours['sun']) {
                    todayHours = operatingHours['sun'];
                }
            }

            if (!todayHours || todayHours === '휴관' || todayHours === 'Closed') {
                return { status: 'closed', text: '오늘 휴관' };
            }

            const [start, end] = todayHours.split('-').map(time => {
                const [h, m] = time.trim().split(':').map(Number);
                return h * 60 + m;
            });

            if (currentTime >= start && currentTime < end) {
                const remainMin = end - currentTime;
                if (remainMin < 30) return { status: 'closing-soon', text: `마감 ${remainMin}분 전` };
                return { status: 'open', text: '영업 중' };
            } else if (currentTime < start) {
                return { status: 'closed', text: `${todayHours.split('-')[0]} 오픈` };
            } else {
                return { status: 'closed', text: '영업 종료' };
            }
        } catch (e) {
            return { status: 'unknown', text: '영업시간 확인 불가' };
        }
    }

    openNavigation(pool, platform) {
        const { name, lat, lng, address } = pool;
        let url = '';
        if (platform === 'naver') {
            url = `https://map.naver.com/v5/search/${encodeURIComponent(name)}/place?c=${lng},${lat},15,0,0,0,dh`;
        } else if (platform === 'kakao') {
            url = `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lng}`;
        } else if (platform === 'google') {
            url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        }
        if (url) window.open(url, '_blank');
    }

    renderFacilityIcons(facilities) {
        if (!facilities || !Array.isArray(facilities)) return '';

        const iconMap = {
            '주차장': { icon: '🅿️', label: '주차' },
            '사우나': { icon: '♨️', label: '사우나' },
            '샤워실': { icon: '🚿', label: '샤워' },
            '카페': { icon: '☕', label: '카페' },
            '매점': { icon: '🍱', label: '매점' },
            '운동장': { icon: '🏃', label: '운동장' },
            '헬스장': { icon: '🏋️', label: '헬스' },
            '유아풀': { icon: '👶', label: '유아풀' }
        };

        return `
            <div class="facility-icons">
                ${facilities.map(f => {
            const item = iconMap[f.trim()] || { icon: '✅', label: f.trim() };
            return `
                        <div class="facility-icon-item" title="${f.trim()}">
                            <div class="facility-icon-circle">${item.icon}</div>
                            <span class="facility-icon-label">${item.label}</span>
                        </div>
                    `;
        }).join('')}
            </div>
        `;
    }

    renderFreeSwimTimetable(times) {
        if (!times || typeof times !== 'object') return '';

        const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
        const dayLabels = { mon: '월', tue: '화', wed: '수', thu: '목', fri: '금', sat: '토', sun: '일' };
        const todayIdx = (new Date().getDay() + 6) % 7;

        return `
            <div class="timetable-container">
                <div class="timetable-header">
                    <span>🏊 자유수영 시간표</span>
                    <span style="font-size: 9px; opacity: 0.7;">타임별 상이</span>
                </div>
                <div class="timetable-grid">
                    ${days.map((day, idx) => {
            const dayTimes = times[day] || [];
            const isToday = idx === todayIdx;
            return `
                            <div class="day-slot ${isToday ? 'today' : ''}">
                                <span class="day-label">${dayLabels[day]}</span>
                                <div class="time-pill-container">
                                    ${dayTimes.length > 0 ?
                    dayTimes.map(t => `<span class="time-pill">${t.split('-')[0]}</span>`).join('')
                    : '<span class="time-pill" style="opacity:0.3">-</span>'}
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    }

    showLoader() {
        if (this.loader) this.loader.classList.remove('hidden');
    }

    hideLoader() {
        if (this.loader) this.loader.classList.add('hidden');
    }
    }

    async init() {
        try {
            this.showLoader();

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

            // Initial loader hide
            this.hideLoader();
        } catch (error) {
            console.error('❌ Failed to initialize app:', error);
            this.showError('앱을 초기화하는 중 오류가 발생했습니다.');
            this.hideLoader();
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

        // Mobile View Toggle
        const mobileToggleBtn = document.getElementById('mobile-toggle');
        if (mobileToggleBtn) {
            mobileToggleBtn.addEventListener('click', () => this.toggleMobileView());
        }
    }

    toggleMobileView() {
        this.isMobileMapView = !this.isMobileMapView;
        const sidebar = document.querySelector('.sidebar');
        const btn = document.getElementById('mobile-toggle');

        if (this.isMobileMapView) {
            sidebar.classList.add('mobile-hidden');
            btn.innerHTML = '<span class="icon">📋</span><span class="text">목록 보기</span>';
        } else {
            sidebar.classList.remove('mobile-hidden');
            btn.innerHTML = '<span class="icon">🗺️</span><span class="text">지도 보기</span>';
        }
    }

    async loadPools() {
        try {
            this.showLoader();
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
        } finally {
            this.hideLoader();
        }
    }

    displayPools(pools, options = {}) {
        const { autoSelectFirst = false, focusOptions = {} } = options;

        this.poolMarkers.forEach(marker => this.map.removeLayer(marker));
        this.poolMarkers = [];

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
            const marker = this.createPoolMarker(pool, number);
            this.poolMarkers.push(marker);
            const listItem = this.createPoolListItem(pool, number);
            poolList.appendChild(listItem);
        });

        if (autoSelectFirst && this.poolMarkers[0]) {
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

        marker.on('click', () => {
            this.selectPool(number, { focusMap: true, openPopup: true });

            // Mobile specific: Switch to map view on marker click if not already
            if (window.innerWidth <= 768 && !this.isMobileMapView) {
                // this.toggleMobileView(); // Optional: Decide if we want to auto-switch
            }
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
        const openInfo = this.isNowOpen(pool.operating_hours);
        const statusClass = `status-${openInfo.status}`;

        return `
            <div class="pool-popup">
                <div class="popup-header">
                    <span class="status-badge ${statusClass}">${openInfo.text}</span>
                    <h3>${pool.name}</h3>
                </div>
                ${pool.image_url ? `<img src="${pool.image_url}" alt="${pool.name}" class="pool-popup-image">` : ''}
                <div class="popup-info-row">
                    <span class="popup-icon">📍</span>
                    <span class="popup-text">${pool.address}</span>
                </div>
                <div class="popup-info-row">
                    <span class="popup-icon">☎️</span>
                    <span class="popup-text">${pool.phone || '정보 없음'}</span>
                </div>
                <div class="popup-price-grid">
                    <div class="popup-price-item">
                        <span class="price-label">한달 수강</span>
                        <span class="price-value">${this.formatPrice(pool.monthly_lesson_price)}</span>
                    </div>
                    <div class="popup-price-item">
                        <span class="price-label">자유 수영</span>
                        <span class="price-value">${this.formatPrice(pool.free_swim_price)}</span>
                    </div>
                </div>
                <div class="popup-actions">
                    <button class="nav-btn naver" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'naver')">네이버 지도</button>
                    <button class="nav-btn kakao" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'kakao')">카카오 맵</button>
                </div>
                <div class="premium-divider"></div>
                ${this.renderFreeSwimTimetable(pool.free_swim_times)}
                ${this.renderFacilityIcons(pool.facilities)}
                ${pool.description ? `<p class="description">${pool.description}</p>` : ''}
            </div>
        `;
    }

    createPoolListItem(pool, number) {
        const openInfo = this.isNowOpen(pool.operating_hours);
        const statusClass = `status-${openInfo.status}`;

        const li = document.createElement('div');
        li.className = 'pool-card';
        li.dataset.poolNumber = number;
        li.innerHTML = `
            <div class="pool-card-left">
                <div class="pool-number">${number}</div>
                <span class="status-dot ${statusClass}"></span>
            </div>
            <div class="pool-info">
                <div class="pool-header-flex">
                    <h3 class="pool-name">${pool.name}</h3>
                    <span class="status-text ${statusClass}">${openInfo.text}</span>
                </div>
                <p class="pool-address">${pool.address}</p>
                <div class="pool-meta">
                    <span class="meta-badge source">${pool.source || '공공시설'}</span>
                    ${pool.rating ? `<span class="meta-badge rating">⭐ ${pool.rating}</span>` : ''}
                    ${pool.distance ? `<span class="meta-badge distance">📍 ${(pool.distance).toFixed(1)}km</span>` : ''}
                </div>
                <div class="pool-prices">
                    <div class="price-item">
                        <span class="price-label">강습</span>
                        <span class="price-value">${this.formatPrice(pool.monthly_lesson_price)}</span>
                    </div>
                    <div class="price-item">
                        <span class="price-label">자유수영</span>
                        <span class="price-value">${this.formatPrice(pool.free_swim_price)}</span>
                    </div>
                </div>
                ${this.renderFacilityIcons(pool.facilities)}
                <div class="card-actions">
                    <button class="action-btn-mini naver" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'naver')">N</button>
                    <button class="action-btn-mini kakao" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'kakao')">K</button>
                    <button class="action-btn-mini google" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'google')">G</button>
                </div>
            </div>
        `;

        li.addEventListener('click', () => {
            this.selectPool(number, { focusMap: true, openPopup: true, zoom: 16 });

            // Mobile specific: Switch to map view on list click
            if (window.innerWidth <= 768 && !this.isMobileMapView) {
                this.toggleMobileView();
            }
        });

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

            // Only scroll if we are in list view
            if (window.innerWidth > 768 || !this.isMobileMapView) {
                // Scroll logic...
            }
        }
    }

    unhighlightSidebarListItem(number) {
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) {
            listItem.classList.remove('highlighted');
        }
    }

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

        const anchor = 0.5 + this.cardScrollBias;
        const clampedAnchor = Math.min(Math.max(anchor, 0.1), 0.9);
        let targetScroll = itemTop - (containerHeight * clampedAnchor) + (itemHeight / 2);

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

        if (this.selectedPoolNumber !== null) {
            const prevCard = document.querySelector(`.pool-card[data-pool-number="${this.selectedPoolNumber}"]`);
            if (prevCard) prevCard.classList.remove('selected');

            const prevMarker = this.poolMarkers[this.selectedPoolNumber - 1];
            if (prevMarker) {
                const prevMarkerElement = prevMarker.getElement();
                if (prevMarkerElement) {
                    const prevMarkerDiv = prevMarkerElement.querySelector('.custom-marker');
                    if (prevMarkerDiv) prevMarkerDiv.classList.remove('selected');
                }
            }
        }

        this.selectedPoolNumber = number;

        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) {
            listItem.classList.add('selected');
            this.ensureSidebarListItemVisible(listItem);
        }

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
        if (!marker || !this.map) return;

        const targetZoom = zoom !== null ? zoom : Math.max(this.map.getZoom(), 14);
        const latlng = marker.getLatLng();
        const mapSize = this.map.getSize();
        const anchor = this.focusAnchor;

        const offset = L.point(
            (anchor.x - 0.5) * mapSize.x,
            (anchor.y - 0.5) * mapSize.y
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
        if (!this.popupAutoAdjust) return;
        if (!marker || !marker.getPopup) return;

        const adjust = () => this.ensurePopupVisible(marker);
        requestAnimationFrame(adjust);
        setTimeout(adjust, 260);
    }

    ensurePopupVisible(marker) {
        if (!marker || !marker.getPopup) return;

        const popup = marker.getPopup();
        if (!popup) return;

        const popupEl = popup.getElement();
        if (!popupEl) return;

        const mapEl = this.map.getContainer();
        if (!mapEl) return;

        const mapRect = mapEl.getBoundingClientRect();
        const popupRect = popupEl.getBoundingClientRect();

        const mapSize = this.map.getSize();
        const maxShift = {
            x: Math.min(mapSize.x * 0.4, 250),
            y: Math.min(mapSize.y * 0.4, 220)
        };

        const utils = this.popupUtils;
        if (!utils || typeof utils.computePopupShift !== 'function') return;

        const shift = utils.computePopupShift(mapRect, popupRect, {
            margin: this.popupMargin,
            maxShift
        });

        if (Math.abs(shift.x) < 1 && Math.abs(shift.y) < 1) return;

        this.map.panBy([-shift.x, -shift.y], { animate: true, duration: 0.25 });
    }

    logFocusSettings() {
        console.info(
            `[SwimSeoul] Viewport=(${this.focusAnchor.x.toFixed(2)}, ${this.focusAnchor.y.toFixed(2)}), ` +
            `ListPos=${this.cardScrollBias.toFixed(2)}`
        );
    }

    setMapViewportVertical(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) return;
        this.focusAnchor.y = Math.min(Math.max(value, 0.05), 0.95);
        this.recenterSelectedMarker();
    }

    setMapViewportHorizontal(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) return;
        this.focusAnchor.x = Math.min(Math.max(value, 0.05), 0.95);
        this.recenterSelectedMarker();
    }

    setSidebarListItemPosition(value) {
        if (typeof value !== 'number' || Number.isNaN(value)) return;
        this.cardScrollBias = Math.min(Math.max(value, -0.45), 0.45);
        if (this.selectedPoolNumber) {
            const listItem = document.querySelector(`.pool-card[data-pool-number="${this.selectedPoolNumber}"]`);
            this.ensureSidebarListItemVisible(listItem);
        }
    }

    setFocusAnchorY(value) { this.setMapViewportVertical(value); }
    setCardScrollBias(value) { this.setSidebarListItemPosition(value); }
    setMarkerVerticalPosition(value) { this.setMapViewportVertical(value); }
    setMarkerHorizontalPosition(value) { this.setMapViewportHorizontal(value); }
    setCardVerticalPosition(value) { this.setSidebarListItemPosition(value); }

    recenterSelectedMarker({ openPopup = true } = {}) {
        if (!this.selectedPoolNumber) return;
        const marker = this.poolMarkers[this.selectedPoolNumber - 1];
        if (marker) this.focusOnMarker(marker, { openPopup });
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
            this.showLoader();
            const url = `${this.config.search.nominatimUrl}?q=${encodeURIComponent(query + ' 서울')}&format=json&limit=1`;
            const response = await fetch(url);
            const results = await response.json();

            if (results && results.length > 0) {
                const { lat, lon } = results[0];
                this.userLocation = { lat: parseFloat(lat), lng: parseFloat(lon) };
                this.updateUserMarker(this.userLocation);
                await this.searchNearbyPools(this.userLocation);
            }
        } catch (error) {
            console.error('Address search failed:', error);
        } finally {
            this.hideLoader();
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
        this.showLoader();
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

            this.displayPools(pools, {
                autoSelectFirst: pools.length > 0,
                focusOptions: { zoom }
            });
            this.updateStats(pools.length);
        } catch (error) {
            console.error('Nearby search failed:', error);
            this.showError('주변 수영장 정보를 불러오지 못했습니다.');
        } finally {
            this.hideLoader();
        }
    }

    async searchSeoulCenter() {
        const seoulCenter = this.config.map.defaultCenter;
        this.userLocation = seoulCenter;
        this.updateUserMarker(seoulCenter);
        await this.searchNearbyPools(seoulCenter);
    }

    async searchByRadius(radius) {
        if (this.userLocation) {
            await this.searchNearbyPools(this.userLocation);
        }
    }

    async filterPools(type) {
        this.showLoader();
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
        } finally {
            this.hideLoader();
        }
    }

    toggleSubway() {
        this.showSubway = !this.showSubway;
        const btn = document.getElementById('toggle-subway');

        btn.classList.toggle('active', this.showSubway);
        btn.textContent = this.showSubway ? '🚇 지하철 숨기기' : '🚇 지하철 노선도';

        if (this.showSubway) {
            if (!this.darkOverlay) {
                this.darkOverlay = L.rectangle(
                    [[33, 124], [39, 132]],
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

        this.showLoader();
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                this.userLocation = location;
                this.updateUserMarker(location);
                await this.searchNearbyPools(location);

                if (this.poolMarkers.length === 0) {
                    console.log('No pools found nearby, loading all pools');
                    await this.loadPools();
                }
            },
            (error) => {
                console.error('Location error:', error);
                this.hideLoader();
                alert('현재 위치를 가져올 수 없습니다. 위치 권한을 확인해주세요.');
            }
        );
    }

    displaySubwayLines() {
        this.subwayData.lines.forEach(line => {
            const coordinates = line.stations.map(s => [s.lat, s.lng]);
            const polyline = L.polyline(coordinates, {
                color: line.color,
                weight: 6,
                opacity: 0.9,
                pane: 'overlayPane'
            }).addTo(this.map);
            this.subwayLines.push(polyline);

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

document.addEventListener('DOMContentLoaded', () => {
    const app = new SwimSeoulApp();
    window.swimApp = app;
    window.swimDebug = {
        지도세로: (y) => app.setMapViewportVertical(y),
        지도가로: (x) => app.setMapViewportHorizontal(x),
        리스트위치: (b) => app.setSidebarListItemPosition(b),
        재배치: () => app.recenterSelectedMarker(),
        현재값: () => app.logFocusSettings(),
        팝업자동조정: (enable) => {
            app.popupAutoAdjust = !!enable;
            console.info(`✅ 팝업 자동 조정: ${app.popupAutoAdjust ? 'ON' : 'OFF'}`);
        }
    };
    app.init();
});
