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

        // 요일 매핑
        this.DAY_NAMES_KR = ['일', '월', '화', '수', '목', '금', '토'];
        this.WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일'];

        // New UI Elements
        this.loader = document.getElementById('loader');
        this.isMobileMapView = false;
    }

    // ─── 요일/시간 헬퍼 ───────────────────────────────

    getTodayDayKr() {
        return this.DAY_NAMES_KR[new Date().getDay()];
    }

    isWeekend() {
        const day = new Date().getDay();
        return day === 0 || day === 6;
    }

    getTodayFreeSwim(pool) {
        if (!pool.free_swim_schedule) return [];
        const schedule = typeof pool.free_swim_schedule === 'string'
            ? JSON.parse(pool.free_swim_schedule)
            : pool.free_swim_schedule;
        const today = this.getTodayDayKr();
        return schedule[today] || [];
    }

    getTodayPrice(pool) {
        if (!pool.pricing) return null;
        const pricing = typeof pool.pricing === 'string'
            ? JSON.parse(pool.pricing)
            : pool.pricing;

        // 자유수영 > 성인 우선, 없으면 일일권 > 성인
        const categories = ['자유수영', '일일권'];
        const dayType = this.isWeekend() ? '주말' : '평일';

        for (const cat of categories) {
            const catData = pricing[cat];
            if (!catData) continue;
            const adult = catData['성인'];
            if (!adult) continue;
            if (typeof adult === 'number') return adult;
            if (typeof adult === 'object') {
                return adult[dayType] || adult['평일'] || Object.values(adult)[0] || null;
            }
        }
        return null;
    }

    // ─── 포맷터 ───────────────────────────────────────

    isPublicSource(source) {
        if (!source) return false;
        return /(공공|서울시|행정)/i.test(source);
    }

    formatPrice(price) {
        if (!price && price !== 0) return '문의';
        const num = parseInt(price);
        if (isNaN(num)) return price;
        return num.toLocaleString() + '원';
    }

    formatOperatingHours(hours) {
        if (!hours) return '';
        const parsed = typeof hours === 'string' ? JSON.parse(hours) : hours;

        // 새 구조: {"월": "06:00-22:00", ...} (한글 요일 키)
        const weekdays = ['월', '화', '수', '목', '금'];
        const weekdayHours = weekdays.map(d => parsed[d]).filter(Boolean);
        const satHours = parsed['토'];
        const sunHours = parsed['일'];

        const parts = [];

        // 평일이 모두 같으면 하나로 표시
        if (weekdayHours.length > 0) {
            const allSame = weekdayHours.every(h => h === weekdayHours[0]);
            if (allSame) {
                parts.push(`평일 ${weekdayHours[0]}`);
            } else {
                weekdays.forEach(d => {
                    if (parsed[d]) parts.push(`${d} ${parsed[d]}`);
                });
            }
        }

        // 영문 키 호환 (기존 데이터)
        if (weekdayHours.length === 0) {
            const engLabels = {
                weekday: '평일', weekend: '주말', saturday: '토', sunday: '일',
                'mon-fri': '평일', sat: '토', sun: '일',
                mon: '월', tue: '화', wed: '수', thu: '목', fri: '금'
            };
            for (const [key, value] of Object.entries(parsed)) {
                if (value && value !== '휴관' && engLabels[key]) {
                    parts.push(`${engLabels[key]} ${value}`);
                }
            }
        } else {
            if (satHours) parts.push(`토 ${satHours}`);
            if (sunHours) parts.push(`일 ${sunHours}`);
        }

        return parts.join(' / ') || '';
    }

    isNowOpen(operatingHours) {
        if (!operatingHours) return { status: 'unknown', text: '운영시간 정보 없음' };

        try {
            const parsed = typeof operatingHours === 'string'
                ? JSON.parse(operatingHours)
                : operatingHours;
            const now = new Date();
            const todayKr = this.getTodayDayKr();
            const currentTime = now.getHours() * 60 + now.getMinutes();

            // 한글 요일 키로 먼저 조회
            let todayHours = parsed[todayKr];

            // 영문 키 폴백
            if (!todayHours) {
                const engDays = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
                const engDay = engDays[now.getDay()];
                todayHours = parsed[engDay];

                if (!todayHours) {
                    if (['mon', 'tue', 'wed', 'thu', 'fri'].includes(engDay)) {
                        todayHours = parsed['mon-fri'] || parsed['weekday'];
                    }
                    if (['sat', 'sun'].includes(engDay)) {
                        todayHours = parsed['weekend'] || parsed[engDay];
                    }
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

    // ─── 네비게이션 ───────────────────────────────────

    openNavigation(pool, platform) {
        const { name, lat, lng } = pool;
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

    // ─── 렌더링 헬퍼 ─────────────────────────────────

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

    renderPricingTable(pricing) {
        if (!pricing) return '';
        const parsed = typeof pricing === 'string' ? JSON.parse(pricing) : pricing;

        // 자유수영 가격표 렌더링
        const freeSwim = parsed['자유수영'];
        if (!freeSwim) return '';

        const targets = Object.keys(freeSwim);
        if (targets.length === 0) return '';

        let html = `
            <div class="popup-section-title">💰 자유수영 가격</div>
            <table class="pricing-table">
                <thead><tr><th>대상</th><th>평일</th><th>주말</th></tr></thead>
                <tbody>
        `;

        for (const target of targets) {
            const data = freeSwim[target];
            let weekday = '-', weekend = '-';

            if (typeof data === 'number') {
                weekday = this.formatPrice(data);
                weekend = weekday;
            } else if (typeof data === 'object') {
                weekday = data['평일'] ? this.formatPrice(data['평일']) : '-';
                weekend = data['주말'] ? this.formatPrice(data['주말']) : '-';
            }

            html += `<tr>
                <td>${target}</td>
                <td class="price-highlight">${weekday}</td>
                <td class="price-highlight">${weekend}</td>
            </tr>`;
        }

        html += '</tbody></table>';

        // 강습 가격 (있을 때만)
        const lesson = parsed['강습_월'];
        if (lesson) {
            html += '<div class="popup-section-title">📚 강습 (월)</div><div style="font-size:12px; margin-bottom:8px;">';
            for (const [target, price] of Object.entries(lesson)) {
                html += `<span style="margin-right:12px;">${target}: <strong>${this.formatPrice(price)}</strong></span>`;
            }
            html += '</div>';
        }

        return html;
    }

    renderWeeklySchedule(schedule) {
        if (!schedule) return '';
        const parsed = typeof schedule === 'string' ? JSON.parse(schedule) : schedule;
        const todayKr = this.getTodayDayKr();

        let html = `
            <div class="weekly-schedule">
                <div class="weekly-schedule-header">🏊 자유수영 시간표</div>
                <div class="weekly-schedule-grid">
        `;

        for (const day of this.WEEKDAYS_KR) {
            const times = parsed[day] || [];
            const isToday = day === todayKr;

            html += `<div class="schedule-day ${isToday ? 'today' : ''}">
                <div class="schedule-day-label">${day}</div>
                <div class="schedule-day-times">`;

            if (Array.isArray(times) && times.length > 0) {
                for (const t of times) {
                    const startTime = t.split('-')[0];
                    html += `<div class="schedule-time-slot">${startTime}</div>`;
                }
            } else {
                html += '<div class="schedule-no-time">-</div>';
            }

            html += '</div></div>';
        }

        html += '</div>';

        // 휴관 정보
        if (parsed['휴관']) {
            html += `<div style="font-size:10px; color:var(--text-muted); margin-top:6px;">휴관: ${parsed['휴관']}</div>`;
        }

        html += '</div>';
        return html;
    }

    // 기존 renderFreeSwimTimetable도 새 구조로 대응 (팝업용)
    renderFreeSwimTimetable(schedule) {
        return this.renderWeeklySchedule(schedule);
    }

    // ─── 로더 ─────────────────────────────────────────

    showLoader() {
        if (this.loader) this.loader.classList.remove('hidden');
    }

    hideLoader() {
        if (this.loader) this.loader.classList.add('hidden');
    }

    // ─── 초기화 ───────────────────────────────────────

    async init() {
        try {
            this.showLoader();
            await this.loadConfig();
            await this.loadSubwayData();
            this.initMap();
            this.setupEventListeners();
            await this.loadPools();
            console.log('SwimSeoul initialized successfully');
            this.logFocusSettings();
            this.hideLoader();
        } catch (error) {
            console.error('Failed to initialize app:', error);
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

    // ─── 필터 파라미터 수집 ───────────────────────────

    getFilterParams() {
        const params = {};
        const day = document.getElementById('filter-day')?.value;
        const time = document.getElementById('filter-time')?.value;
        const maxPrice = document.getElementById('filter-max-price')?.value;
        const sort = document.getElementById('filter-sort')?.value;

        if (day) params.day = day;
        if (time) params.time = time;
        if (maxPrice) params.max_price = maxPrice;
        if (sort && sort !== 'distance') params.sort = sort;

        return params;
    }

    // ─── 이벤트 리스너 ───────────────────────────────

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
        document.getElementById('search-radius').addEventListener('change', () => {
            if (this.userLocation) this.searchNearbyPools(this.userLocation);
        });

        // 새 필터 변경 시 재검색
        const filterIds = ['filter-day', 'filter-time', 'filter-max-price', 'filter-sort'];
        for (const id of filterIds) {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    if (this.userLocation) {
                        this.searchNearbyPools(this.userLocation);
                    }
                });
            }
        }

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

    // ─── 데이터 로드 ──────────────────────────────────

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

    // ─── 마커 생성 ────────────────────────────────────

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
        });

        const popupContent = this.createPopupContent(pool);
        marker.bindPopup(popupContent, {
            maxWidth: 340,
            maxHeight: 500,
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

    // ─── 팝업 (상세 정보) ─────────────────────────────

    createPopupContent(pool) {
        const openInfo = this.isNowOpen(pool.operating_hours);
        const statusClass = `status-${openInfo.status}`;
        const todayPrice = this.getTodayPrice(pool);

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
                ${todayPrice ? `
                <div class="popup-info-row">
                    <span class="popup-icon">💰</span>
                    <span class="popup-text">자유수영 ${this.formatPrice(todayPrice)} (${this.isWeekend() ? '주말' : '평일'})</span>
                </div>` : ''}
                ${pool.operating_hours ? `
                <div class="popup-info-row">
                    <span class="popup-icon">🕐</span>
                    <span class="popup-text">${this.formatOperatingHours(pool.operating_hours)}</span>
                </div>` : ''}
                ${pool.lanes || pool.pool_size ? `
                <div class="popup-info-row">
                    <span class="popup-icon">🏊</span>
                    <span class="popup-text">${pool.pool_size || ''}${pool.lanes ? ` · ${pool.lanes}레인` : ''}</span>
                </div>` : ''}
                ${pool.parking !== null && pool.parking !== undefined ? `
                <div class="popup-info-row">
                    <span class="popup-icon">🅿️</span>
                    <span class="popup-text">주차 ${pool.parking ? '가능' : '불가'}</span>
                </div>` : ''}
                <div class="popup-actions">
                    <button class="nav-btn naver" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'naver')">네이버 지도</button>
                    <button class="nav-btn kakao" onclick="event.stopPropagation(); window.swimApp.openNavigation(${JSON.stringify(pool).replace(/"/g, '&quot;')}, 'kakao')">카카오 맵</button>
                </div>
                <div class="premium-divider"></div>
                ${this.renderPricingTable(pool.pricing)}
                ${this.renderWeeklySchedule(pool.free_swim_schedule)}
                ${this.renderFacilityIcons(pool.facilities)}
                ${pool.notes ? `<div class="popup-notes">📝 ${pool.notes}</div>` : ''}
                ${pool.description ? `<p class="description">${pool.description}</p>` : ''}
            </div>
        `;
    }

    // ─── 카드 (목록) ──────────────────────────────────

    createPoolListItem(pool, number) {
        const openInfo = this.isNowOpen(pool.operating_hours);
        const statusClass = `status-${openInfo.status}`;
        const todayPrice = this.getTodayPrice(pool);
        const todayTimes = this.getTodayFreeSwim(pool);
        const todayKr = this.getTodayDayKr();

        // 오늘 자유수영 정보 렌더링
        let todayInfoHtml = '';
        if (todayPrice || todayTimes.length > 0) {
            todayInfoHtml = '<div class="card-today-info">';
            if (todayPrice) {
                todayInfoHtml += `<div class="card-today-price">${this.formatPrice(todayPrice)} <span class="price-unit">${this.isWeekend() ? '주말' : '평일'}</span></div>`;
            }
            if (todayTimes.length > 0) {
                todayInfoHtml += '<div class="card-today-times">';
                todayInfoHtml += `<span class="card-time-label">${todayKr}</span>`;
                for (const t of todayTimes) {
                    todayInfoHtml += `<span class="card-time-chip">${t.split('-')[0]}</span>`;
                }
                todayInfoHtml += '</div>';
            }
            todayInfoHtml += '</div>';
        }

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
                ${todayInfoHtml}
                ${pool.phone ? `<p class="pool-phone">📞 ${pool.phone}</p>` : ''}
                ${pool.operating_hours ? `<p class="pool-hours">🕐 ${this.formatOperatingHours(pool.operating_hours)}</p>` : ''}
                ${pool.lanes || pool.pool_size ? `<p class="pool-lanes">🏊 ${pool.pool_size || ''}${pool.lanes ? ` · ${pool.lanes}레인` : ''}</p>` : ''}
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

    // ─── 하이라이트/선택 ──────────────────────────────

    highlightSidebarListItem(number) {
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) listItem.classList.add('highlighted');
    }

    unhighlightSidebarListItem(number) {
        const listItem = document.querySelector(`.pool-card[data-pool-number="${number}"]`);
        if (listItem) listItem.classList.remove('highlighted');
    }

    highlightPoolCard(number) { this.highlightSidebarListItem(number); }
    unhighlightPoolCard(number) { this.unhighlightSidebarListItem(number); }

    ensureSidebarListItemVisible(listItem) {
        if (!listItem) return;
        const container = document.querySelector('.pool-list-container');
        if (!container) return;

        const itemTop = listItem.offsetTop;
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

        if (Math.abs(targetScroll - container.scrollTop) < 4) return;

        const startScroll = container.scrollTop;
        const distance = targetScroll - startScroll;
        const duration = 120;
        const startTime = performance.now();

        const animateScroll = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            container.scrollTop = startScroll + (distance * easeOut);
            if (progress < 1) requestAnimationFrame(animateScroll);
        };

        requestAnimationFrame(animateScroll);
    }

    ensurePoolCardVisible(listItem) {
        this.ensureSidebarListItemVisible(listItem);
    }

    highlightMarker(number) {
        const marker = this.poolMarkers[number - 1];
        if (marker) {
            const el = marker.getElement();
            if (el) {
                const div = el.querySelector('.custom-marker');
                if (div) div.classList.add('highlighted');
            }
        }
    }

    unhighlightMarker(number) {
        const marker = this.poolMarkers[number - 1];
        if (marker) {
            const el = marker.getElement();
            if (el) {
                const div = el.querySelector('.custom-marker');
                if (div) div.classList.remove('highlighted');
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
                const el = prevMarker.getElement();
                if (el) {
                    const div = el.querySelector('.custom-marker');
                    if (div) div.classList.remove('selected');
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
            const el = marker.getElement();
            if (el) {
                const div = el.querySelector('.custom-marker');
                if (div) div.classList.add('selected');
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

    // ─── 디버그 ───────────────────────────────────────

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

    // ─── 검색 ─────────────────────────────────────────

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
            const filterParams = this.getFilterParams();
            const params = new URLSearchParams({
                lat: location.lat,
                lng: location.lng,
                radius: radius,
                ...filterParams
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

    // ─── 지하철 ───────────────────────────────────────

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
            console.info(`팝업 자동 조정: ${app.popupAutoAdjust ? 'ON' : 'OFF'}`);
        }
    };
    app.init();
});
