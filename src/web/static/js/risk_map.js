const config = JSON.parse(document.getElementById("risk-map-config").textContent);
const riskData = config.riskData || [];
const colorByGrade = config.colorByGrade || {};
const kakaoKeyExists = config.kakaoKeyExists;
const kakaoKeyMode = config.kakaoKeyMode;
const kakaoSdkUrl = config.kakaoSdkUrl;
const defaultCenter = config.defaultCenter || { lat: 36.35, lon: 127.95 };
const defaultLevel = config.defaultLevel || 13;
const allowedOrigins = config.allowedOrigins || [];
const mapMode = config.mapMode || "static";
const pageTitleText = config.pageTitle || "교통사고 위험도 지도";
const pageDescriptionText = config.pageDescription || "지역을 선택한 뒤, 해당 구간의 위험도를 지도에서 확인할 수 있습니다.";
const pageSubDescriptionText = config.pageSubDescription || "원하는 지역과 위험등급을 선택한 후 지도를 불러와 주세요.";
const gradePriority = ["매우높음", "높음", "보통", "낮음"];

const app = document.getElementById("app");
const sidebar = document.getElementById("sidebar");
const panelToggle = document.getElementById("panelToggle");
const mapToolbar = document.getElementById("mapToolbar");
const mapMessage = document.getElementById("mapMessage");
const mapElement = document.getElementById("map");
const mapShell = document.querySelector(".map-shell");
const pageTitle = document.getElementById("pageTitle");
const pageDescription = document.getElementById("pageDescription");
const pageSubDescription = document.getElementById("pageSubDescription");
const scoreLabel = document.getElementById("scoreLabel");
const locateBtn = document.getElementById("locateBtn");
const nearestPanel = document.getElementById("nearestPanel");
const destinationSearchInput = document.getElementById("destinationSearchInput");
const destinationSearchBtn = document.getElementById("destinationSearchBtn");
const destinationResultBox = document.getElementById("destinationResultBox");
const routeAnalyzeBtn = document.getElementById("routeAnalyzeBtn");
const voiceToggle = document.getElementById("voiceToggle");
const routePanel = document.getElementById("routePanel");
const routeLoadingBar = document.getElementById("routeLoadingBar");

const sidoSelect = document.getElementById("sidoSelect");
const sigunguSelect = document.getElementById("sigunguSelect");
const gradeSelect = document.getElementById("gradeSelect");

const countValue = document.getElementById("countValue");
const scoreValue = document.getElementById("scoreValue");
const topGradeValue = document.getElementById("topGradeValue");
const filterValue = document.getElementById("filterValue");
const toolbarValue = document.getElementById("toolbarValue");
const toolbarTitle = document.getElementById("toolbarTitle");
const toolbarKicker = mapToolbar ? mapToolbar.querySelector(".toolbar-kicker") : null;
const errorBox = document.getElementById("errorBox");

let map = null;
let baseCenter = null;
let circles = [];
let markers = [];
let infoWindows = [];
let isMapReady = false;
let sdkPromise = null;
let markerStates = [];
let overlapPanel = null;
let activeState = null;
let userOverlay = null;
let userAccuracyCircle = null;
let lastRenderedItems = [];
let userWatchId = null;
let lastRiskAlertZoneId = null;
let currentUserPosition = null;
let selectedDestination = null;
let activeRouteRiskItems = [];
let activeRoutePathPoints = [];
let lastRouteOriginPosition = null;
let lastAutoRerouteAt = 0;
let routeAnalyzeInProgress = false;
let routeAlertStateByZone = new Map();
let routePolyline = null;
let routeRiskMarkers = [];
let destinationOverlay = null;
let lastVoiceAlertKey = null;
let nearestPanelCollapsed = false;
let nearestPanelSuppressedByDetail = false;
let latestNearestItems = [];
let routePanelCollapsed = false;
let latestRoutePayload = null;
let nearestTrackingPaused = false;
let renderedUserPosition = null;
let userLocationAnimationId = null;
let lastNearestRenderAt = 0;
let lastNearestRenderKey = "";
let lastMapFollowPosition = null;
let rawUserPosition = null;
let lastAcceptedGeoPosition = null;
let lastLocationUpdateAt = 0;
let lastRejectedLocationReason = "";
let navigationFollowMode = "follow";
let lastHeadingDeg = null;
let lastSpeedMps = null;
let routeProgressState = null;
let simulationFrameId = null;
let simulationRunning = false;
let simulationButton = null;
let followModeButton = null;
let navigationControlDock = null;
let wakeLock = null;
let speechPrimed = false;

const OVERLAP_PIXEL_THRESHOLD = 36;
const MARKER_HIDE_DELAY = 450;
const MARKER_ZINDEX_HIDDEN = 2;
const MARKER_ZINDEX_HOVER = 12;
const MARKER_ZINDEX_DEFAULT = 8;
const INFOWINDOW_ZINDEX = 200;
const NEAREST_DISPLAY_COUNT = 20;
const NEAREST_LIST_COUNT = 20;
const AUTO_ALERT_DISTANCE_M = 300;
const AUTO_ALERT_GRADES = new Set(["매우높음", "높음", "보통", "낮음"]);
const ROUTE_ALERT_GRADES = new Set(["매우높음", "높음", "보통", "낮음"]);
const NAVIGATION_API_ROUTE = "/api/route";
const ROUTE_PRIORITY = "DISTANCE";
const DESTINATION_SEARCH_RADIUS_M = 50000;
const DESTINATION_SEARCH_CANDIDATE_PREFIXES = [
    "",
    "천안시 ",
    "천안시 서북구 ",
    "천안시 동남구 ",
    "충남 천안시 ",
    "충남 천안시 서북구 ",
    "충남 천안시 동남구 ",
    "충청남도 천안시 ",
    "충청남도 천안시 서북구 ",
    "충청남도 천안시 동남구 "
];
const NEAREST_REFRESH_INTERVAL_MS = 7000;
const USER_LOCATION_ANIMATION_MS = 650;
const USER_FOLLOW_PAN_MIN_MOVE_M = 5;
const GEOLOCATION_TIMEOUT_MS = 8000;
const GEOLOCATION_MAXIMUM_AGE_MS = 0;
const GEOLOCATION_DEBUG_ENABLED = true;
const GEOLOCATION_STALE_MS = 3000;
const GEOLOCATION_JUMP_SPEED_MPS = 45;
const GEOLOCATION_JUMP_DISTANCE_M = 120;
const GEOLOCATION_ACCURACY_WARN_M = 80;
const ROUTE_SNAP_MAX_DISTANCE_M = 45;
const ROUTE_SNAP_RELEASE_DISTANCE_M = 70;
const ROUTE_SIMULATION_SPEED_MPS = 11.5;
const ROUTE_SIMULATION_MIN_FRAME_MS = 80;
const ROUTE_DEPARTURE_MOVE_REROUTE_M = 220;
const ROUTE_DEVIATION_REROUTE_M = 160;
const ROUTE_REROUTE_COOLDOWN_MS = 45000;
const ROUTE_APPROACH_EXTRA_M = 250;
const ROUTE_CLEAR_EXTRA_M = 180;

function initializePageText() {
    document.title = `RoadSafe - ${pageTitleText}`;
    if (pageTitle) pageTitle.textContent = "RoadSafe";
    if (pageDescription) pageDescription.textContent = pageDescriptionText;
    if (pageSubDescription) pageSubDescription.textContent = pageSubDescriptionText;

    [toolbarKicker, toolbarTitle].forEach(element => {
        if (!element) return;
        element.textContent = "";
        element.setAttribute("aria-hidden", "true");
        element.style.display = "none";
        if (element.parentElement) element.parentElement.removeChild(element);
    });

    if (toolbarValue) toolbarValue.textContent = "목적지를 검색하고 현재 위치 기준 경로 위험도를 확인하세요.";
    if (scoreLabel && mapMode === "live") scoreLabel.textContent = "평균 실시간점수";
}

function setError(message) {
    if (!errorBox) return;
    errorBox.style.display = message ? "block" : "none";
    errorBox.textContent = message || "";
}

function setMapMessage(message) {
    if (!mapMessage) return;
    mapMessage.classList.toggle("show", !!message);
    mapMessage.innerHTML = message || "";
    requestUiLayoutSync();
}

function requestUiLayoutSync() {
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
        syncNavigationControlDockPosition();
        syncMapMessageLayout();
    });
}

function getVisibleElementRect(element) {
    if (!element || !element.classList || element.classList.contains("detail-hidden")) return null;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return null;
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    return rect;
}

function syncNavigationControlDockPosition() {
    if (!navigationControlDock || !mapShell) return;

    const shellRect = mapShell.getBoundingClientRect();
    const nearestRect = getVisibleElementRect(nearestPanel);
    let bottom = 18;
    let width = Math.min(410, Math.max(300, shellRect.width - 36));

    if (nearestRect) {
        bottom = Math.max(18, shellRect.bottom - nearestRect.top + 12);
        width = Math.max(300, Math.min(nearestRect.width, shellRect.width - 36));
    }

    mapShell.style.setProperty("--navigation-control-bottom", `${Math.round(bottom)}px`);
    mapShell.style.setProperty("--navigation-control-width", `${Math.round(width)}px`);
}

function syncMapMessageLayout() {
    if (!mapShell || !mapMessage) return;

    const shellRect = mapShell.getBoundingClientRect();
    const nearestRect = getVisibleElementRect(nearestPanel);
    let safeRight = 0;

    if (nearestRect) {
        safeRight = Math.max(0, shellRect.right - nearestRect.left + 18);
    }

    const maxSafeRight = Math.max(0, shellRect.width - 360);
    mapShell.style.setProperty("--message-safe-right", `${Math.round(Math.min(safeRight, maxSafeRight))}px`);
}

function escapeHtml(value) {
    if (value === null || value === undefined || value === "") return "-";
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function buildDebugBlock(extraMessage = "") {
    const origin = window.location.origin || "unknown";
    const href = window.location.href || "unknown";
    const host = window.location.host || "unknown";

    return `
        <div class="map-debug">
            현재 주소: ${escapeHtml(href)}<br>
            Origin: ${escapeHtml(origin)}<br>
            Host: ${escapeHtml(host)}<br>
            키 적용 방식: ${escapeHtml(kakaoKeyMode)}<br>
            허용 Origin: ${escapeHtml(allowedOrigins.join(", "))}<br>
            ${extraMessage}
        </div>
    `;
}

function toNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
}

function hasKakaoObject() {
    return !!(window.kakao && window.kakao.maps && typeof window.kakao.maps.load === "function");
}

function createLatLng(lat, lon) {
    return new kakao.maps.LatLng(toNumber(lat), toNumber(lon));
}

function getCurrentOrigin() {
    return window.location.origin || "";
}

function validateCurrentOrigin() {
    return allowedOrigins.includes(getCurrentOrigin());
}

function optionalInfoRow(label, value) {
    if (value === null || value === undefined || value === "" || value === "nan" || value === "NaN") return "";
    return `<div class="info-row"><div class="info-key">${escapeHtml(label)}</div><div class="info-value">${escapeHtml(value)}</div></div>`;
}


function formatGradeValue(value) {
    if (!value || value === "-") return "-";
    const color = colorByGrade[value] || "#e5e7eb";
    return `<span class="grade-value-pill" style="--grade-color:${color};">${escapeHtml(value)}</span>`;
}

function buildInfoContent(item) {
    const isLive = item.mode === "live" || mapMode === "live";
    const titleLabel = isLive ? "실시간위험등급" : "위험등급";
    const scoreLabelText = isLive ? "실시간위험점수" : "위험점수";
    const weatherLabel = isLive ? "현재기상" : "주의기상상태";
    const timeLabel = isLive ? "현재시간대" : "주의시간대";

    const liveRows = isLive ? `
            ${optionalInfoRow("정적위험점수", item.static_score)}
            <div class="info-row"><div class="info-key">기존위험등급</div><div class="info-value">${formatGradeValue(item.static_grade)}</div></div>
            ${optionalInfoRow("위험변화점수", item.change_score)}
            ${optionalInfoRow("위험변화상태", item.change_status)}
            ${optionalInfoRow("변화사유", item.change_reason)}
            ${optionalInfoRow("기상가중치", item.weather_weight)}
            ${optionalInfoRow("기상가중치사유", item.weather_weight_reason)}
            ${optionalInfoRow("시간가중치", item.time_weight)}
            ${optionalInfoRow("시간가중치사유", item.time_weight_reason)}
            ${optionalInfoRow("돌발상황가중치", item.incident_weight)}
            ${optionalInfoRow("돌발상황사유", item.incident_reason)}
            ${optionalInfoRow("가까운돌발상황거리", item.nearest_incident_distance_m ? `${item.nearest_incident_distance_m}m` : "")}
            ${optionalInfoRow("가까운돌발상황유형", item.nearest_incident_type)}
            ${optionalInfoRow("가까운돌발상황도로명", item.nearest_incident_road)}
            ${optionalInfoRow("가까운돌발상황내용", item.nearest_incident_message)}
            ${optionalInfoRow("기온", item.current_temp_c ? `${item.current_temp_c}℃` : "")}
            ${optionalInfoRow("습도", item.humidity_pct ? `${item.humidity_pct}%` : "")}
            ${optionalInfoRow("1시간 강수량", item.rain_1h_mm ? `${item.rain_1h_mm}mm` : "")}
            ${optionalInfoRow("풍속", item.wind_speed_ms ? `${item.wind_speed_ms}m/s` : "")}
            ${optionalInfoRow("경로와의거리", item.distance_to_route_m !== undefined ? `${formatDistance(item.distance_to_route_m)}` : "")}
            ${optionalInfoRow("관측시각", item.obs_time)}
            ${optionalInfoRow("수집시각", item.collected_at_kst)}
            ${optionalInfoRow("기상API상태", item.weather_api_status)}
            ${optionalInfoRow("대체기상지역", item.weather_fallback_region)}
            ${optionalInfoRow("대체기상거리", item.weather_fallback_distance_m ? `${item.weather_fallback_distance_m}m` : "")}
            ${optionalInfoRow("대체기상사유", item.weather_fallback_note)}
            ${optionalInfoRow("갱신시각", item.updated_at)}
        ` : "";

    return `
        <div class="info-window">
            <div class="info-title">${escapeHtml(item.location_name)}</div>
            <div class="info-row"><div class="info-key">구간ID</div><div class="info-value">${escapeHtml(item.zone_id)}</div></div>
            <div class="info-row"><div class="info-key">지역</div><div class="info-value">${escapeHtml(item.region)}</div></div>
            <div class="info-row"><div class="info-key">좌표</div><div class="info-value">${escapeHtml(item.lat)}, ${escapeHtml(item.lon)}</div></div>
            <div class="info-row"><div class="info-key">${titleLabel}</div><div class="info-value">${formatGradeValue(item.grade)}</div></div>
            <div class="info-row"><div class="info-key">${scoreLabelText}</div><div class="info-value">${escapeHtml(item.score)}</div></div>
            <div class="info-row"><div class="info-key">알림반경</div><div class="info-value">${escapeHtml(item.radius_m)}m</div></div>
            ${optionalInfoRow("사고건수합", item.accident_count)}
            ${optionalInfoRow("사상자수합", item.casualty_count)}
            ${optionalInfoRow("사망자수합", item.death_count)}
            ${optionalInfoRow("중상자수합", item.serious_injury_count)}
            ${optionalInfoRow("경상자수합", item.minor_injury_count)}
            ${optionalInfoRow("부상신고자수합", item.reported_injury_count)}
            ${optionalInfoRow("평균 사고위험원점수", item.raw_avg_score)}
            ${optionalInfoRow("최대 사고위험원점수", item.raw_max_score)}
            <div class="info-row"><div class="info-key">${weatherLabel}</div><div class="info-value">${escapeHtml(item.weather)}</div></div>
            <div class="info-row"><div class="info-key">${timeLabel}</div><div class="info-value">${escapeHtml(item.time_band)}</div></div>
            ${liveRows}
            <div class="info-row"><div class="info-key">경고문구</div><div class="info-value info-warning">${escapeHtml(item.warning)}</div></div>
        </div>
    `;
}

function buildDetailSidePanel(item) {
    const container = document.createElement("div");
    container.className = "detail-modal-panel";
    container.addEventListener("click", event => event.stopPropagation());

    const gradeColor = colorByGrade[item.grade] || "#94a3b8";

    container.innerHTML = `
        <div class="detail-modal-header">
            <div>
                <div class="detail-eyebrow">위험구간 상세</div>
                <div class="detail-title">${escapeHtml(item.location_name || item.region || "위험구간")}</div>
                <div class="detail-subtitle">
                    <span class="detail-grade-dot" style="background:${gradeColor};"></span>
                    ${escapeHtml(item.grade)} · 점수 ${escapeHtml(item.score)} · 반경 ${escapeHtml(item.radius_m)}m
                </div>
            </div>
            <button type="button" class="overlay-close-btn" aria-label="상세 정보 닫기">×</button>
        </div>
        <div class="detail-scroll">${buildInfoContent(item)}</div>
    `;

    const closeBtn = container.querySelector(".overlay-close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closeOverlapOverlay);

    return container;
}

function getValidItems(items) {
    return items.filter(item => {
        const lat = Number(item.lat);
        const lon = Number(item.lon);
        return Number.isFinite(lat) && Number.isFinite(lon);
    });
}

function closeAllInfoWindows() {
    infoWindows.forEach(info => info.close());
}

function closeOverlapOverlay() {
    if (overlapPanel && overlapPanel.parentNode) {
        overlapPanel.parentNode.removeChild(overlapPanel);
    }
    overlapPanel = null;
    restoreNearestPanelAfterDetail();
}


function isDetailOverlayOpen() {
    return !!(
        overlapPanel &&
        (
            overlapPanel.classList.contains("detail-modal-panel") ||
            overlapPanel.classList.contains("detail-modal-backdrop")
        )
    );
}

function suppressNearestPanelForDetail() {
    nearestPanelSuppressedByDetail = true;
    if (nearestPanel) nearestPanel.classList.add("detail-hidden");
    requestUiLayoutSync();
}

function restoreNearestPanelAfterDetail() {
    nearestPanelSuppressedByDetail = false;
    if (nearestPanel) nearestPanel.classList.remove("detail-hidden");
    refreshNearestPanelState();
    requestUiLayoutSync();
}

function closeNearestPanel() {
    nearestPanelCollapsed = true;
    showNearestPanel(currentUserPosition ? currentUserPosition.lat : null, currentUserPosition ? currentUserPosition.lon : null, latestNearestItems);
}

function openNearestPanel() {
    nearestPanelCollapsed = false;
    showNearestPanel(currentUserPosition ? currentUserPosition.lat : null, currentUserPosition ? currentUserPosition.lon : null, latestNearestItems);
}

function refreshNearestPanelState() {
    showNearestPanel(currentUserPosition ? currentUserPosition.lat : null, currentUserPosition ? currentUserPosition.lon : null, latestNearestItems);
}

function pauseNearestTracking() {
    nearestTrackingPaused = true;
    if (userWatchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(userWatchId);
        userWatchId = null;
    }
    releaseNavigationWakeLock();
    if (locateBtn) locateBtn.textContent = "내 위치 추적 일시정지";
    refreshNearestPanelState();
}

async function resumeNearestTracking() {
    nearestTrackingPaused = false;
    if (locateBtn) locateBtn.textContent = "위치 재확인 중...";
    try {
        const position = await getCurrentPositionOnce();
        handleGeolocationPosition(position, { center: false, follow: true, keepMessage: true });
        startUserRiskWatch();
        if (selectedDestination) await analyzeRouteRisk({ skipSearch: true, keepMessage: true });
        if (locateBtn) locateBtn.textContent = "내 위치 위험 추적 중";
    } catch (error) {
        setError("위치 추적을 다시 시작하지 못했습니다. 위치 권한과 서버 실행 상태를 확인해 주세요.");
        if (locateBtn) locateBtn.textContent = "내 위치 주변 위험 확인";
        refreshNearestPanelState();
    }
}

function toggleNearestTrackingPause(event) {
    if (event) event.stopPropagation();
    if (nearestTrackingPaused) {
        resumeNearestTracking();
    } else {
        pauseNearestTracking();
    }
}

function clearHideTimer(state) {
    if (state && state.hideTimer) {
        window.clearTimeout(state.hideTimer);
        state.hideTimer = null;
    }
}

function hideMarkerState(state) {
    if (!state || !state.marker) return;
    clearHideTimer(state);

    if (state.locked) return;
    if (state.hoveringCircle || state.hoveringMarker) return;

    state.marker.setMap(null);
    state.marker.setZIndex(MARKER_ZINDEX_HIDDEN);
    state.marker.setImage(state.defaultImage);
}

function showMarkerState(state, mode = "hover") {
    if (!state || !state.marker || !map) return;
    clearHideTimer(state);

    state.marker.setMap(map);

    if (mode === "hidden-anchor") {
        state.marker.setImage(state.invisibleImage);
        state.marker.setZIndex(MARKER_ZINDEX_DEFAULT);
        return;
    }

    state.marker.setImage(mode === "hover" ? state.hoverImage : state.defaultImage);
    state.marker.setZIndex(mode === "hover" ? MARKER_ZINDEX_HOVER : MARKER_ZINDEX_DEFAULT);
}

function scheduleHideMarker(state) {
    if (!state) return;

    clearHideTimer(state);

    if (state.locked) return;

    state.hideTimer = window.setTimeout(() => {
        if (state.locked) return;
        if (state.hoveringCircle) return;
        if (state.hoveringMarker) return;

        hideMarkerState(state);
    }, MARKER_HIDE_DELAY);
}

function unlockAndHideAllMarkers() {
    markerStates.forEach(state => {
        state.locked = false;
        state.hoveringCircle = false;
        state.hoveringMarker = false;
        if (state.marker) state.marker.setImage(state.defaultImage);
        hideMarkerState(state);
    });
    activeState = null;
}

function closeAllInfoWindowsAndResetMarkers() {
    closeAllInfoWindows();
    closeOverlapOverlay();
    unlockAndHideAllMarkers();
}

function hasActiveInfoWindow() {
    return !!activeState;
}

function clearMapObjects(options = {}) {
    const keepUserLocation = !!options.keepUserLocation;
    const keepNearestPanel = !!options.keepNearestPanel;
    const keepDetailPanel = !!options.keepDetailPanel;

    circles.forEach(circle => circle.setMap(null));
    markers.forEach(marker => marker.setMap(null));
    closeAllInfoWindows();

    if (!keepDetailPanel) {
        closeOverlapOverlay();
    }

    circles = [];
    markers = [];
    infoWindows = [];
    markerStates = [];
    activeState = null;
    lastRenderedItems = [];

    if (!keepUserLocation) {
        clearUserLocation();
        if (!keepNearestPanel) closeNearestPanel();
    }
}

function clearUserLocation() {
    if (userLocationAnimationId) {
        window.cancelAnimationFrame(userLocationAnimationId);
        userLocationAnimationId = null;
    }
    renderedUserPosition = null;
    lastMapFollowPosition = null;
    if (userOverlay) {
        userOverlay.setMap(null);
        userOverlay = null;
    }
    if (userAccuracyCircle) {
        userAccuracyCircle.setMap(null);
        userAccuracyCircle = null;
    }
}

function populateSidoOptions() {
    const sidoList = [...new Set(
        riskData.map(item => (item.sido || "").trim()).filter(Boolean)
    )].sort();

    sidoSelect.innerHTML = '<option value="">시/도 선택</option>';

    sidoList.forEach(sido => {
        const option = document.createElement("option");
        option.value = sido;
        option.textContent = sido;
        sidoSelect.appendChild(option);
    });
}

function populateSigunguOptions(selectedSido) {
    sigunguSelect.innerHTML = '<option value="">시/군/구 선택</option>';

    if (!selectedSido) {
        sigunguSelect.disabled = true;
        return;
    }

    const sigunguList = [...new Set(
        riskData
            .filter(item => item.sido === selectedSido)
            .map(item => (item.sigungu || "").trim())
            .filter(Boolean)
    )].sort();

    sigunguList.forEach(sigungu => {
        const option = document.createElement("option");
        option.value = sigungu;
        option.textContent = sigungu;
        sigunguSelect.appendChild(option);
    });

    sigunguSelect.disabled = false;
}

function filterData() {
    const sido = sidoSelect.value;
    const sigungu = sigunguSelect.value;
    const grade = gradeSelect.value;

    let filtered = [...riskData];

    if (sido) filtered = filtered.filter(item => item.sido === sido);
    if (sigungu) filtered = filtered.filter(item => item.sigungu === sigungu);
    if (grade) filtered = filtered.filter(item => item.grade === grade);

    return getValidItems(filtered);
}

function getTopGrade(items) {
    for (const grade of gradePriority) {
        if (items.some(item => item.grade === grade)) return grade;
    }
    return "-";
}

function updateSummary(items, customFilterText = null) {
    countValue.textContent = String(items.length);

    const avgScore = items.length
        ? (items.reduce((sum, item) => sum + toNumber(item.score, 0), 0) / items.length).toFixed(2)
        : "0";

    scoreValue.textContent = avgScore;

    const topGrade = getTopGrade(items);
    topGradeValue.innerHTML = topGrade === "-"
        ? "-"
        : `<span class="pill" style="background:${colorByGrade[topGrade] || "#e5e7eb"};">${topGrade}</span>`;

    const filterText = customFilterText || [sidoSelect.value, sigunguSelect.value, gradeSelect.value]
        .filter(Boolean)
        .join(" / ") || "전체";

    filterValue.textContent = filterText;
    if (!mapToolbar || !mapToolbar.classList.contains("nav-toolbar")) {
        toolbarValue.textContent = items.length
            ? `${filterText} · 표시 ${items.length}개 · 최고등급 ${topGrade}`
            : `${filterText} · 표시 가능한 구간이 없습니다.`;
    }
}

function resetMapView() {
    if (!isMapReady || !map) return;
    map.setCenter(baseCenter);
    map.setLevel(defaultLevel);
}

function syncToolbarWithSidebar() {
    const collapsed = sidebar.classList.contains("collapsed");
    app.classList.toggle("sidebar-collapsed", collapsed);
    mapToolbar.classList.add("show");

    if (isMapReady && map) {
        const center = map.getCenter();
        window.setTimeout(() => {
            map.relayout();
            map.setCenter(center);
        }, 280);
    }
    requestUiLayoutSync();
}

function toggleSidebar() {
    sidebar.classList.toggle("collapsed");
    syncToolbarWithSidebar();
}

function initMapUIOnlyMode(message) {
    setMapMessage(message);
    isMapReady = false;
    map = null;
}

function getExistingSdkScript() {
    return document.querySelector("script[data-kakao-map-sdk='true']");
}

function loadKakaoSdk() {
    if (sdkPromise) return sdkPromise;

    sdkPromise = new Promise((resolve, reject) => {
        if (!kakaoKeyExists) {
            reject(new Error("카카오 JavaScript 키가 비어 있습니다."));
            return;
        }

        if (!validateCurrentOrigin()) {
            reject(new Error(
                "현재 Origin이 카카오 Developers에 등록한 JavaScript SDK 도메인과 일치하지 않습니다. " +
                `현재 Origin: ${getCurrentOrigin()}`
            ));
            return;
        }

        if (hasKakaoObject()) {
            resolve();
            return;
        }

        const existingScript = getExistingSdkScript();
        if (existingScript) {
            existingScript.addEventListener("load", () => hasKakaoObject() ? resolve() : reject(new Error("기존 SDK 스크립트 로드 후에도 kakao.maps.load 객체가 없습니다.")));
            existingScript.addEventListener("error", () => reject(new Error("기존 SDK 스크립트 요청이 실패했습니다.")));
            return;
        }

        const script = document.createElement("script");
        script.src = kakaoSdkUrl;
        script.async = true;
        script.defer = true;
        script.dataset.kakaoMapSdk = "true";

        script.onload = () => {
            if (hasKakaoObject()) {
                resolve();
            } else {
                reject(new Error(
                    "카카오 SDK 응답은 도착했지만 window.kakao.maps.load 객체가 없습니다. " +
                    "잘못된 키, 권한 미활성화, 캐시 문제를 다시 확인해 주세요."
                ));
            }
        };

        script.onerror = () => {
            reject(new Error(
                "카카오 SDK 스크립트 요청이 실패했습니다. " +
                "브라우저 Network 탭에서 sdk.js 요청 상태코드(401/403/blocked)를 꼭 확인해 주세요."
            ));
        };

        document.head.appendChild(script);
    });

    return sdkPromise;
}

function createMarkerImages() {
    const defaultImage = new kakao.maps.MarkerImage(
        "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png",
        new kakao.maps.Size(24, 35),
        { offset: new kakao.maps.Point(12, 35) }
    );

    const hoverImage = new kakao.maps.MarkerImage(
        "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png",
        new kakao.maps.Size(30, 42),
        { offset: new kakao.maps.Point(15, 42) }
    );

    const invisibleImage = new kakao.maps.MarkerImage(
        "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==",
        new kakao.maps.Size(1, 1),
        { offset: new kakao.maps.Point(0, 0) }
    );

    return { defaultImage, hoverImage, invisibleImage };
}

function bindMapCloseEvents() {
    if (!map) return;

    kakao.maps.event.addListener(map, "click", function (mouseEvent) {
        closeAllInfoWindows();
        unlockAndHideAllMarkers();
        handleMapDestinationClick(mouseEvent.latLng);
    });

    kakao.maps.event.addListener(map, "dragstart", function () {
        setNavigationFollowMode("free");
        closeAllInfoWindows();
        unlockAndHideAllMarkers();
    });
}

function getProjectionPoint(latlng) {
    const projection = map.getProjection();
    return projection.pointFromCoords(latlng);
}

function getDistanceInPixels(latlng1, latlng2) {
    const p1 = getProjectionPoint(latlng1);
    const p2 = getProjectionPoint(latlng2);
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
}

function getOverlappingStates(targetState) {
    return markerStates
        .filter(state => getDistanceInPixels(state.latlng, targetState.latlng) <= OVERLAP_PIXEL_THRESHOLD)
        .sort((a, b) => {
            const gradeDiff = gradePriority.indexOf(a.item.grade) - gradePriority.indexOf(b.item.grade);
            if (gradeDiff !== 0) return gradeDiff;
            return toNumber(b.item.score, 0) - toNumber(a.item.score, 0);
        });
}

function openStateInfo(state) {
    closeAllInfoWindowsAndResetMarkers();
    suppressNearestPanelForDetail();

    state.hoveringCircle = false;
    state.hoveringMarker = false;
    state.locked = true;
    activeState = state;

    showMarkerState(state, "default");

    const panel = buildDetailSidePanel(state.item);
    overlapPanel = panel;
    mapShell.appendChild(panel);

    map.panTo(state.latlng);
}

function buildOverlapOverlayContent(states) {
    const container = document.createElement("div");
    container.className = "floating-list-panel overlap-list-panel show";
    container.addEventListener("click", event => event.stopPropagation());

    const rows = states.map((state, index) => {
        const gradeColor = colorByGrade[state.item.grade] || "#94a3b8";
        return `
            <button type="button" class="nearest-item overlap-result-item" data-index="${index}" style="--item-color:${gradeColor};">
                <span class="nearest-index" style="background:${gradeColor};">${index + 1}</span>
                <span class="nearest-main">
                    <strong>${escapeHtml(state.item.location_name || state.item.region || "위험구간")}</strong>
                    <small>
                        <span class="mini-grade-dot" style="background:${gradeColor};"></span>
                        ${escapeHtml(state.item.grade)} · 점수 ${escapeHtml(state.item.score)} · 반경 ${escapeHtml(state.item.radius_m)}m
                    </small>
                </span>
            </button>
        `;
    }).join("");

    container.innerHTML = `
        <div class="nearest-header">
            <div>
                <div class="nearest-title">겹친 위험구간 ${states.length}개</div>
                
            </div>
            <button type="button" class="overlay-close-btn" aria-label="겹친 구간 목록 닫기">×</button>
        </div>
        <div class="nearest-list">${rows}</div>
    `;

    const closeBtn = container.querySelector(".overlay-close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closeOverlapOverlay);

    container.querySelectorAll(".overlap-result-item").forEach(button => {
        button.addEventListener("click", function (event) {
            event.stopPropagation();
            const index = Number(this.dataset.index);
            const state = states[index];
            if (state) openStateInfo(state);
        });
    });

    return container;
}

function openOverlapOverlay(targetState, states) {
    closeAllInfoWindowsAndResetMarkers();
    suppressNearestPanelForDetail();

    targetState.locked = true;
    activeState = targetState;

    const content = buildOverlapOverlayContent(states);
    overlapPanel = content;
    mapShell.appendChild(overlapPanel);

    showMarkerState(targetState, "default");
    map.panTo(targetState.latlng);
}

async function initMap() {
    if (!kakaoKeyExists) {
        initMapUIOnlyMode(
            "카카오 지도 JavaScript Key가 없어 실제 지도를 표시할 수 없습니다." +
            buildDebugBlock(".env 파일에 KAKAO_JS_KEY를 등록하면 지도가 표시됩니다.")
        );
        return;
    }

    try {
        await loadKakaoSdk();

        kakao.maps.load(function () {
            try {
                baseCenter = createLatLng(defaultCenter.lat, defaultCenter.lon);

                map = new kakao.maps.Map(mapElement, {
                    center: baseCenter,
                    level: defaultLevel
                });

                const zoomControl = new kakao.maps.ZoomControl();
                map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

                bindMapCloseEvents();

                isMapReady = true;
                setMapMessage("");
                syncToolbarWithSidebar();
            } catch (error) {
                console.error("지도 초기화 오류:", error);
                initMapUIOnlyMode(
                    "카카오 지도 객체 생성 중 오류가 발생했습니다." +
                    buildDebugBlock(`오류 메시지: ${escapeHtml(error.message || String(error))}`)
                );
            }
        });
    } catch (error) {
        console.error("카카오 SDK 로드 오류:", error);
        initMapUIOnlyMode(
            `카카오 지도 SDK 로딩에 실패했습니다.<br>${escapeHtml(error.message || String(error))}` +
            buildDebugBlock("브라우저 개발자도구 F12 → Network → sdk.js 요청 상태를 확인해 주세요.")
        );
    }
}

function drawRiskItems(items, options = {}) {
    if (!isMapReady || !map) return;

    const fitBounds = options.fitBounds !== false;
    const keepUserLocation = !!options.keepUserLocation;
    const keepNearestPanel = !!options.keepNearestPanel;
    const keepDetailPanel = !!options.keepDetailPanel;

    clearMapObjects({ keepUserLocation, keepNearestPanel, keepDetailPanel });
    if (!keepNearestPanel) closeNearestPanel();

    if (!items.length) return;

    const bounds = new kakao.maps.LatLngBounds();
    const markerImages = createMarkerImages();

    items.forEach(item => {
        const color = colorByGrade[item.grade] || "#64748b";
        const latlng = createLatLng(item.lat, item.lon);
        bounds.extend(latlng);

        const radius = Math.max(30, toNumber(item.radius_m, 0));

        const circle = new kakao.maps.Circle({
            center: latlng,
            radius: radius,
            strokeWeight: 2,
            strokeColor: color,
            strokeOpacity: 0.75,
            strokeStyle: "solid",
            fillColor: color,
            fillOpacity: 0.10
        });
        circle.setMap(map);
        circles.push(circle);

        const marker = new kakao.maps.Marker({
            position: latlng,
            title: item.location_name || item.region || "위험구간",
            image: markerImages.defaultImage
        });

        marker.setZIndex(MARKER_ZINDEX_HIDDEN);
        markers.push(marker);

        const infoWindow = new kakao.maps.InfoWindow({
            content: buildInfoContent(item),
            removable: true,
            zIndex: INFOWINDOW_ZINDEX
        });
        infoWindows.push(infoWindow);

        const state = {
            item,
            latlng,
            circle,
            marker,
            infoWindow,
            defaultImage: markerImages.defaultImage,
            hoverImage: markerImages.hoverImage,
            invisibleImage: markerImages.invisibleImage,
            locked: false,
            hideTimer: null,
            hoveringCircle: false,
            hoveringMarker: false
        };
        markerStates.push(state);

        kakao.maps.event.addListener(circle, "mouseover", function () {
            if (state.locked) return;
            if (hasActiveInfoWindow() && activeState !== state) return;

            state.hoveringCircle = true;
            showMarkerState(state, "hover");
        });

        kakao.maps.event.addListener(circle, "mouseout", function () {
            if (state.locked) return;
            if (hasActiveInfoWindow() && activeState !== state) return;

            state.hoveringCircle = false;
            scheduleHideMarker(state);
        });

        kakao.maps.event.addListener(marker, "mouseover", function () {
            if (state.locked) return;
            if (hasActiveInfoWindow() && activeState !== state) return;

            state.hoveringMarker = true;
            showMarkerState(state, "hover");
        });

        kakao.maps.event.addListener(marker, "mouseout", function () {
            if (state.locked) return;
            if (hasActiveInfoWindow() && activeState !== state) return;

            state.hoveringMarker = false;
            scheduleHideMarker(state);
        });

        const handleClick = function () {
            const overlappedStates = getOverlappingStates(state);

            if (overlappedStates.length > 1) {
                state.hoveringCircle = true;
                showMarkerState(state, "default");
                openOverlapOverlay(state, overlappedStates);
                return;
            }

            openStateInfo(state);
        };

        kakao.maps.event.addListener(marker, "click", handleClick);
        kakao.maps.event.addListener(circle, "click", handleClick);
    });

    lastRenderedItems = [...items];

    if (fitBounds) {
        map.setBounds(bounds);
    }
}

function renderMap() {
    setError("");

    const items = filterData();
    updateSummary(items);

    if (!sidoSelect.value) {
        clearMapObjects();
        if (isMapReady) resetMapView();
        setError("시/도를 먼저 선택해 주세요.");
        return;
    }

    if (!isMapReady || !map) {
        setError("지도가 아직 준비되지 않았습니다. 상단 중앙 안내 문구와 브라우저 콘솔 로그를 먼저 확인해 주세요.");
        return;
    }

    if (!items.length) {
        clearMapObjects();
        resetMapView();
        setError("선택한 조건에 맞는 데이터가 없습니다. 다른 지역 또는 위험등급을 선택해 주세요.");
        return;
    }

    try {
        drawRiskItems(items, { fitBounds: true });
    } catch (error) {
        console.error(error);
        setError("지도를 불러오는 중 오류가 발생했습니다. 좌표 또는 데이터 형식을 다시 확인해 주세요.");
    }
}

function resetFilters() {
    sidoSelect.value = "";
    gradeSelect.value = "";
    populateSigunguOptions("");
    sigunguSelect.value = "";
    updateSummary([]);
    clearMapObjects();
    clearRouteSession();
    closeNearestPanel();
    setError("");
    toolbarValue.textContent = "목적지를 검색하고 현재 위치 기준 경로 위험도를 확인하세요.";

    if (isMapReady) resetMapView();
}

function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
    const earthRadius = 6371000;
    const toRad = deg => deg * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return earthRadius * c;
}

function formatDistance(meters) {
    if (!Number.isFinite(meters)) return "-";
    if (meters >= 1000) return `${(meters / 1000).toFixed(2)}km`;
    return `${Math.round(meters)}m`;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function getPositionTimestamp(position) {
    const ts = position && position.timestamp ? Number(position.timestamp) : Date.now();
    return Number.isFinite(ts) ? ts : Date.now();
}

function normalizeHeading(heading) {
    const value = Number(heading);
    if (!Number.isFinite(value)) return null;
    return ((value % 360) + 360) % 360;
}

function computeBearingDegrees(lat1, lon1, lat2, lon2) {
    const toRad = deg => deg * Math.PI / 180;
    const toDeg = rad => rad * 180 / Math.PI;
    const phi1 = toRad(lat1);
    const phi2 = toRad(lat2);
    const dLon = toRad(lon2 - lon1);
    const y = Math.sin(dLon) * Math.cos(phi2);
    const x = Math.cos(phi1) * Math.sin(phi2) -
        Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLon);
    return normalizeHeading(toDeg(Math.atan2(y, x)));
}

function normalizeGeoPosition(position) {
    if (!position || !position.coords) return null;
    const lat = Number(position.coords.latitude);
    const lon = Number(position.coords.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

    const accuracy = Math.max(0, toNumber(position.coords.accuracy, 999));
    const speed = Number.isFinite(Number(position.coords.speed)) ? Math.max(0, Number(position.coords.speed)) : null;
    const heading = normalizeHeading(position.coords.heading);
    return {
        lat,
        lon,
        accuracy,
        speed,
        heading,
        timestamp: getPositionTimestamp(position)
    };
}

function logNavigation(message, payload = {}) {
    if (!GEOLOCATION_DEBUG_ENABLED) return;
    console.log(`[RoadSafe NAV] ${message}`, payload);
}

function shouldRejectGeoPosition(raw) {
    if (!raw) return "좌표가 비어 있습니다.";

    if (!lastAcceptedGeoPosition) return "";

    const elapsedSec = Math.max(0.001, (raw.timestamp - lastAcceptedGeoPosition.timestamp) / 1000);
    const movedMeters = haversineDistanceMeters(
        lastAcceptedGeoPosition.lat,
        lastAcceptedGeoPosition.lon,
        raw.lat,
        raw.lon
    );
    const speedMps = movedMeters / elapsedSec;

    if (movedMeters >= GEOLOCATION_JUMP_DISTANCE_M && speedMps >= GEOLOCATION_JUMP_SPEED_MPS) {
        return `비정상 위치 튐 감지: ${formatDistance(movedMeters)}, ${speedMps.toFixed(1)}m/s`;
    }

    return "";
}

function enrichNavigationPosition(raw) {
    if (!raw) return null;

    const rejectReason = shouldRejectGeoPosition(raw);
    if (rejectReason) {
        lastRejectedLocationReason = rejectReason;
        logNavigation("위치값 제외", { reason: rejectReason, raw });
        return null;
    }

    const previous = lastAcceptedGeoPosition;
    let heading = raw.heading;
    let speed = raw.speed;

    if (previous) {
        const movedMeters = haversineDistanceMeters(previous.lat, previous.lon, raw.lat, raw.lon);
        const elapsedSec = Math.max(0.001, (raw.timestamp - previous.timestamp) / 1000);

        if (heading === null && movedMeters >= 2) {
            heading = computeBearingDegrees(previous.lat, previous.lon, raw.lat, raw.lon);
        }

        if (speed === null && elapsedSec > 0 && movedMeters >= 1) {
            speed = movedMeters / elapsedSec;
        }
    }

    if (heading !== null) lastHeadingDeg = heading;
    if (speed !== null) lastSpeedMps = speed;

    const routeMatch = getSnappedPointOnActiveRoute(raw.lat, raw.lon);
    const shouldSnap = routeMatch && routeMatch.distance_m <= ROUTE_SNAP_MAX_DISTANCE_M;

    const display = shouldSnap
        ? {
            lat: routeMatch.lat,
            lon: routeMatch.lon,
            matchedToRoute: true,
            routeDistanceM: routeMatch.distance_m,
            routeProgressM: routeMatch.progress_m,
            routeSegmentIndex: routeMatch.segment_index
        }
        : {
            lat: raw.lat,
            lon: raw.lon,
            matchedToRoute: false,
            routeDistanceM: routeMatch ? routeMatch.distance_m : Infinity,
            routeProgressM: routeMatch ? routeMatch.progress_m : null,
            routeSegmentIndex: routeMatch ? routeMatch.segment_index : null
        };

    lastAcceptedGeoPosition = {
        ...raw,
        displayLat: display.lat,
        displayLon: display.lon,
        heading,
        speed
    };
    lastLocationUpdateAt = Date.now();

    return {
        ...display,
        rawLat: raw.lat,
        rawLon: raw.lon,
        accuracy: raw.accuracy,
        heading,
        speed,
        timestamp: raw.timestamp,
        lowAccuracy: raw.accuracy >= GEOLOCATION_ACCURACY_WARN_M
    };
}

function getRouteTotalDistanceMeters(routePoints) {
    if (!Array.isArray(routePoints) || routePoints.length < 2) return 0;
    let total = 0;
    for (let i = 0; i < routePoints.length - 1; i += 1) {
        total += haversineDistanceMeters(
            toNumber(routePoints[i].lat),
            toNumber(routePoints[i].lon),
            toNumber(routePoints[i + 1].lat),
            toNumber(routePoints[i + 1].lon)
        );
    }
    return total;
}

function getRoutePointAtDistance(routePoints, targetDistanceM) {
    if (!Array.isArray(routePoints) || routePoints.length === 0) return null;
    if (routePoints.length === 1) {
        return {
            lat: toNumber(routePoints[0].lat),
            lon: toNumber(routePoints[0].lon),
            bearing: lastHeadingDeg
        };
    }

    let passed = 0;
    const clampedTarget = Math.max(0, targetDistanceM);

    for (let i = 0; i < routePoints.length - 1; i += 1) {
        const a = routePoints[i];
        const b = routePoints[i + 1];
        const aLat = toNumber(a.lat);
        const aLon = toNumber(a.lon);
        const bLat = toNumber(b.lat);
        const bLon = toNumber(b.lon);
        const segmentDistance = haversineDistanceMeters(aLat, aLon, bLat, bLon);

        if (passed + segmentDistance >= clampedTarget) {
            const t = segmentDistance === 0 ? 0 : clamp((clampedTarget - passed) / segmentDistance, 0, 1);
            return {
                lat: aLat + (bLat - aLat) * t,
                lon: aLon + (bLon - aLon) * t,
                bearing: computeBearingDegrees(aLat, aLon, bLat, bLon),
                segmentIndex: i
            };
        }

        passed += segmentDistance;
    }

    const last = routePoints[routePoints.length - 1];
    const prev = routePoints[routePoints.length - 2];
    return {
        lat: toNumber(last.lat),
        lon: toNumber(last.lon),
        bearing: computeBearingDegrees(toNumber(prev.lat), toNumber(prev.lon), toNumber(last.lat), toNumber(last.lon)),
        segmentIndex: routePoints.length - 2
    };
}

function getClosestPointOnRoute(lat, lon, routePoints) {
    if (!Array.isArray(routePoints) || routePoints.length < 2) return null;

    let best = null;
    let progressed = 0;

    for (let i = 0; i < routePoints.length - 1; i += 1) {
        const a = routePoints[i];
        const b = routePoints[i + 1];
        const aLat = toNumber(a.lat);
        const aLon = toNumber(a.lon);
        const bLat = toNumber(b.lat);
        const bLon = toNumber(b.lon);

        const refLat = ((lat + aLat + bLat) / 3) * Math.PI / 180;
        const meterPerLat = 111320;
        const meterPerLon = 111320 * Math.cos(refLat);

        const px = lon * meterPerLon;
        const py = lat * meterPerLat;
        const ax = aLon * meterPerLon;
        const ay = aLat * meterPerLat;
        const bx = bLon * meterPerLon;
        const by = bLat * meterPerLat;
        const dx = bx - ax;
        const dy = by - ay;

        const segmentDistance = Math.hypot(dx, dy);
        const t = segmentDistance === 0
            ? 0
            : clamp(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0, 1);

        const snappedX = ax + dx * t;
        const snappedY = ay + dy * t;
        const distance = Math.hypot(px - snappedX, py - snappedY);
        const snappedLon = snappedX / meterPerLon;
        const snappedLat = snappedY / meterPerLat;

        if (!best || distance < best.distance_m) {
            best = {
                lat: snappedLat,
                lon: snappedLon,
                distance_m: distance,
                progress_m: progressed + segmentDistance * t,
                segment_index: i
            };
        }

        progressed += segmentDistance;
    }

    return best;
}

function getSnappedPointOnActiveRoute(lat, lon) {
    if (!activeRoutePathPoints || activeRoutePathPoints.length < 2) return null;
    return getClosestPointOnRoute(lat, lon, activeRoutePathPoints);
}

function updateNavigationControlButtons() {
    if (followModeButton) {
        followModeButton.textContent = navigationFollowMode === "follow" ? "지도 따라가기 ON" : "지도 따라가기 OFF";
        followModeButton.setAttribute("aria-pressed", navigationFollowMode === "follow" ? "true" : "false");
    }
    if (simulationButton) {
        simulationButton.textContent = simulationRunning ? "시연 주행 정지" : "시연 주행 시작";
        simulationButton.disabled = !activeRoutePathPoints.length && !simulationRunning;
    }
}

function setNavigationFollowMode(mode) {
    navigationFollowMode = mode === "free" ? "free" : "follow";
    if (navigationFollowMode === "follow" && currentUserPosition && map) {
        lastMapFollowPosition = null;
        map.panTo(createLatLng(currentUserPosition.lat, currentUserPosition.lon));
    }
    updateNavigationControlButtons();
}

function createNavControlButton(id, text) {
    const button = document.createElement("button");
    button.type = "button";
    button.id = id;
    button.className = "navigation-control-button";
    button.textContent = text;
    return button;
}

function ensureNavigationControls() {
    if (!mapShell) return;

    navigationControlDock = document.getElementById("navigationControlDock");
    if (!navigationControlDock) {
        navigationControlDock = document.createElement("div");
        navigationControlDock.id = "navigationControlDock";
        navigationControlDock.className = "navigation-control-dock";
        mapShell.appendChild(navigationControlDock);
    }

    let wrapper = navigationControlDock.querySelector("#navigationControlBar");
    const staleWrapper = document.getElementById("navigationControlBar");
    if (staleWrapper && staleWrapper.parentElement !== navigationControlDock) {
        staleWrapper.remove();
    }

    if (!wrapper) {
        wrapper = document.createElement("div");
        wrapper.id = "navigationControlBar";
        wrapper.className = "navigation-control-bar";

        followModeButton = createNavControlButton("followModeButton", "지도 따라가기 ON");
        simulationButton = createNavControlButton("simulationButton", "시연 주행 시작");

        followModeButton.addEventListener("click", () => {
            setNavigationFollowMode(navigationFollowMode === "follow" ? "free" : "follow");
        });

        simulationButton.addEventListener("click", () => {
            if (simulationRunning) {
                stopRouteSimulation(true);
            } else {
                startRouteSimulation();
            }
        });

        wrapper.appendChild(followModeButton);
        wrapper.appendChild(simulationButton);
        navigationControlDock.appendChild(wrapper);
    } else {
        followModeButton = wrapper.querySelector("#followModeButton");
        simulationButton = wrapper.querySelector("#simulationButton");
    }

    navigationControlDock.classList.add("show");
    navigationControlDock.setAttribute("aria-label", "주행 제어 버튼");
    updateNavigationControlButtons();
    requestUiLayoutSync();
}

async function requestNavigationWakeLock() {
    if (!("wakeLock" in navigator)) return;
    try {
        wakeLock = await navigator.wakeLock.request("screen");
        wakeLock.addEventListener("release", () => {
            wakeLock = null;
        });
    } catch (error) {
        logNavigation("화면 유지 Wake Lock 요청 실패", { message: error.message || String(error) });
    }
}

async function releaseNavigationWakeLock() {
    if (!wakeLock) return;
    try {
        await wakeLock.release();
    } catch (error) {
        logNavigation("화면 유지 Wake Lock 해제 실패", { message: error.message || String(error) });
    } finally {
        wakeLock = null;
    }
}

function primeSpeechSynthesis() {
    if (speechPrimed || !window.speechSynthesis) return;
    try {
        window.speechSynthesis.getVoices();
        speechPrimed = true;
    } catch (error) {
        logNavigation("음성 엔진 초기화 실패", { message: error.message || String(error) });
    }
}

function handleGeolocationPosition(position, options = {}) {
    const raw = normalizeGeoPosition(position);
    const display = enrichNavigationPosition(raw);
    if (!display) return null;

    logNavigation("위치 갱신", {
        rawLat: display.rawLat,
        rawLon: display.rawLon,
        lat: display.lat,
        lon: display.lon,
        accuracy: display.accuracy,
        speed: display.speed,
        heading: display.heading,
        matchedToRoute: display.matchedToRoute,
        routeDistanceM: Number.isFinite(display.routeDistanceM) ? Math.round(display.routeDistanceM) : null,
        time: new Date(display.timestamp).toLocaleTimeString()
    });

    updateUserRiskTracking(display.lat, display.lon, display.accuracy, {
        ...options,
        rawLat: display.rawLat,
        rawLon: display.rawLon,
        speed: display.speed,
        heading: display.heading,
        matchedToRoute: display.matchedToRoute,
        routeDistanceM: display.routeDistanceM,
        lowAccuracy: display.lowAccuracy,
        keepMessage: options.keepMessage !== false
    });

    return display;
}

function startRouteSimulation() {
    if (!activeRoutePathPoints || activeRoutePathPoints.length < 2) {
        setMapMessage("경로 분석을 먼저 완료한 뒤 시연 주행을 시작해 주세요.");
        return;
    }

    stopRouteSimulation(false);

    if (userWatchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(userWatchId);
        userWatchId = null;
    }

    simulationRunning = true;
    setNavigationFollowMode("free");
    requestNavigationWakeLock();

    const totalDistanceM = getRouteTotalDistanceMeters(activeRoutePathPoints);
    routeProgressState = {
        totalDistanceM,
        distanceM: 0,
        lastTick: window.performance ? window.performance.now() : Date.now()
    };

    setMapMessage(`<div class="auto-risk-alert" style="--alert-color:#2563eb;"><strong>시연 주행 시작</strong><span>경로를 따라 현재 위치와 위험 알림을 테스트합니다.</span></div>`);
    updateNavigationControlButtons();

    const tick = timestamp => {
        if (!simulationRunning || !routeProgressState) return;

        const now = timestamp || Date.now();
        const elapsedMs = now - routeProgressState.lastTick;
        if (elapsedMs < ROUTE_SIMULATION_MIN_FRAME_MS) {
            simulationFrameId = window.requestAnimationFrame(tick);
            return;
        }
        routeProgressState.lastTick = now;
        routeProgressState.distanceM = Math.min(
            routeProgressState.totalDistanceM,
            routeProgressState.distanceM + ROUTE_SIMULATION_SPEED_MPS * (elapsedMs / 1000)
        );

        const point = getRoutePointAtDistance(activeRoutePathPoints, routeProgressState.distanceM);
        if (point) {
            updateUserRiskTracking(point.lat, point.lon, 5, {
                center: false,
                follow: false,
                keepMessage: true,
                rawLat: point.lat,
                rawLon: point.lon,
                speed: ROUTE_SIMULATION_SPEED_MPS,
                heading: point.bearing,
                matchedToRoute: true,
                routeDistanceM: 0,
                simulated: true
            });
        }

        if (routeProgressState.distanceM >= routeProgressState.totalDistanceM) {
            stopRouteSimulation(false);
            setMapMessage(`<div class="auto-risk-alert" style="--alert-color:#16a34a;"><strong>시연 주행 완료</strong><span>목적지 경로 주행 테스트가 끝났습니다.</span></div>`);
            speakMessage("시연 주행이 완료되었습니다.");
            return;
        }

        simulationFrameId = window.requestAnimationFrame(tick);
    };

    simulationFrameId = window.requestAnimationFrame(tick);
}

function stopRouteSimulation(resumeWatch = false) {
    if (simulationFrameId) {
        window.cancelAnimationFrame(simulationFrameId);
        simulationFrameId = null;
    }
    simulationRunning = false;
    routeProgressState = null;
    releaseNavigationWakeLock();
    updateNavigationControlButtons();

    if (resumeWatch && !nearestTrackingPaused) {
        startUserRiskWatch();
    }
}

function pointSegmentDistanceMeters(pointLat, pointLon, aLat, aLon, bLat, bLon) {
    const refLat = ((pointLat + aLat + bLat) / 3) * Math.PI / 180;
    const meterPerLat = 111320;
    const meterPerLon = 111320 * Math.cos(refLat);
    const px = pointLon * meterPerLon;
    const py = pointLat * meterPerLat;
    const ax = aLon * meterPerLon;
    const ay = aLat * meterPerLat;
    const bx = bLon * meterPerLon;
    const by = bLat * meterPerLat;
    const dx = bx - ax;
    const dy = by - ay;
    if (dx === 0 && dy === 0) return Math.hypot(px - ax, py - ay);
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function minDistanceToRouteMeters(lat, lon, routePoints) {
    if (!Array.isArray(routePoints) || routePoints.length === 0) return Infinity;
    if (routePoints.length === 1) {
        return haversineDistanceMeters(lat, lon, toNumber(routePoints[0].lat), toNumber(routePoints[0].lon));
    }
    let best = Infinity;
    for (let i = 0; i < routePoints.length - 1; i += 1) {
        const a = routePoints[i];
        const b = routePoints[i + 1];
        const distance = pointSegmentDistanceMeters(lat, lon, toNumber(a.lat), toNumber(a.lon), toNumber(b.lat), toNumber(b.lon));
        if (distance < best) best = distance;
    }
    return best;
}

function getRiskWeightedItemsByDistance(lat, lon) {
    return getValidItems(riskData)
        .map(item => {
            const distance = haversineDistanceMeters(lat, lon, toNumber(item.lat), toNumber(item.lon));
            return { ...item, distance_m: distance };
        })
        .sort((a, b) => {
            const distanceDiff = a.distance_m - b.distance_m;
            if (Math.abs(distanceDiff) > 1) return distanceDiff;

            const gradeDiff = gradePriority.indexOf(a.grade) - gradePriority.indexOf(b.grade);
            if (gradeDiff !== 0) return gradeDiff;

            return toNumber(b.score, 0) - toNumber(a.score, 0);
        });
}

function setUserLocationPosition(lat, lon, accuracy = 0) {
    const latlng = createLatLng(lat, lon);
    const radius = Math.max(50, Math.min(toNumber(accuracy, 50), 500));

    if (!userOverlay) {
        const content = '<div class="user-location-dot"><span></span></div>';
        userOverlay = new kakao.maps.CustomOverlay({
            position: latlng,
            content,
            yAnchor: 0.5,
            zIndex: 300
        });
        userOverlay.setMap(map);
    } else {
        userOverlay.setPosition(latlng);
    }

    if (!userAccuracyCircle) {
        userAccuracyCircle = new kakao.maps.Circle({
            center: latlng,
            radius,
            strokeWeight: 2,
            strokeColor: "#2563eb",
            strokeOpacity: 0.75,
            fillColor: "#2563eb",
            fillOpacity: 0.08
        });
        userAccuracyCircle.setMap(map);
    } else {
        if (typeof userAccuracyCircle.setPosition === "function") {
            userAccuracyCircle.setPosition(latlng);
        } else if (typeof userAccuracyCircle.setOptions === "function") {
            userAccuracyCircle.setOptions({ center: latlng });
        }
        if (typeof userAccuracyCircle.setRadius === "function") {
            userAccuracyCircle.setRadius(radius);
        } else if (typeof userAccuracyCircle.setOptions === "function") {
            userAccuracyCircle.setOptions({ radius });
        }
    }
}

function drawUserLocation(lat, lon, accuracy = 0, options = {}) {
    const target = { lat: toNumber(lat), lon: toNumber(lon), accuracy: toNumber(accuracy, 50) };

    if (options.immediate) {
        if (userLocationAnimationId) {
            window.cancelAnimationFrame(userLocationAnimationId);
            userLocationAnimationId = null;
        }
        renderedUserPosition = target;
        setUserLocationPosition(target.lat, target.lon, target.accuracy);
        return;
    }

    if (!renderedUserPosition) {
        renderedUserPosition = target;
        setUserLocationPosition(target.lat, target.lon, target.accuracy);
        return;
    }

    const start = { ...renderedUserPosition };
    const movedMeters = haversineDistanceMeters(start.lat, start.lon, target.lat, target.lon);
    if (movedMeters < 1) {
        renderedUserPosition = target;
        setUserLocationPosition(target.lat, target.lon, target.accuracy);
        return;
    }

    if (userLocationAnimationId) {
        window.cancelAnimationFrame(userLocationAnimationId);
        userLocationAnimationId = null;
    }

    const startedAt = window.performance ? window.performance.now() : Date.now();
    const animate = timestamp => {
        const now = timestamp || Date.now();
        const progress = Math.min(1, (now - startedAt) / USER_LOCATION_ANIMATION_MS);
        const eased = progress < 0.5
            ? 2 * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        const nextLat = start.lat + (target.lat - start.lat) * eased;
        const nextLon = start.lon + (target.lon - start.lon) * eased;
        const nextAccuracy = start.accuracy + (target.accuracy - start.accuracy) * eased;
        renderedUserPosition = { lat: nextLat, lon: nextLon, accuracy: nextAccuracy };
        setUserLocationPosition(nextLat, nextLon, nextAccuracy);

        if (progress < 1) {
            userLocationAnimationId = window.requestAnimationFrame(animate);
        } else {
            renderedUserPosition = target;
            userLocationAnimationId = null;
        }
    };

    userLocationAnimationId = window.requestAnimationFrame(animate);
}

function maybeFollowUserPosition(userLatLng, lat, lon, options = {}) {
    if (!options.follow || !map || isDetailOverlayOpen()) return;
    if (navigationFollowMode !== "follow") return;

    const minMove = options.simulated ? 1 : USER_FOLLOW_PAN_MIN_MOVE_M;

    if (!lastMapFollowPosition) {
        lastMapFollowPosition = { lat, lon };
        map.panTo(userLatLng);
        return;
    }

    const movedMeters = haversineDistanceMeters(lastMapFollowPosition.lat, lastMapFollowPosition.lon, lat, lon);
    if (movedMeters >= minMove) {
        lastMapFollowPosition = { lat, lon };
        map.panTo(userLatLng);
    }
}

function showNearestPanel(lat, lon, nearestItems = [], options = {}) {
    if (!nearestPanel) return;

    latestNearestItems = Array.isArray(nearestItems) ? nearestItems : [];
    const topList = latestNearestItems.slice(0, NEAREST_LIST_COUNT);
    const titleText = `내 위치 기준 위험구간 ${topList.length}개`;
    nearestPanel.classList.add("show");
    nearestPanel.classList.toggle("collapsed", nearestPanelCollapsed);
    nearestPanel.classList.toggle("tracking-paused", nearestTrackingPaused);
    if (nearestPanelCollapsed) {
            nearestPanel.innerHTML = `
            <button type="button" class="nearest-collapsed-trigger" id="nearestOpenBtn" aria-label="주변 위험구간 열기">
                <span>${titleText}</span>
                <small>${nearestTrackingPaused ? "일시정지" : "열기"}</small>
            </button>
        `;
        const openBtn = document.getElementById("nearestOpenBtn");
        if (openBtn) openBtn.addEventListener("click", openNearestPanel);
        requestUiLayoutSync();
        return;
    }

    const rows = topList.map((item, index) => {
        const gradeColor = colorByGrade[item.grade] || "#94a3b8";
        return `
            <button type="button" class="nearest-item" data-index="${index}" style="--item-color:${gradeColor};">
                <span class="nearest-index" style="background:${gradeColor};">${index + 1}</span>
                <span class="nearest-main">
                    <strong>${escapeHtml(item.location_name || item.region || "위험구간")}</strong>
                    <small><span class="mini-grade-dot" style="background:${gradeColor};"></span>${formatDistance(item.distance_m)} · ${escapeHtml(item.grade)} · 점수 ${escapeHtml(item.score)}</small>
                </span>
            </button>
        `;
    }).join("");

    nearestPanel.innerHTML = `
        <div class="nearest-header">
            <div class="nearest-title-block">
                <span class="nearest-title">${titleText}</span>
            </div>
            <button type="button" class="nearest-pause-btn" id="nearestPauseBtn" aria-label="위치 추적 일시정지 또는 재시작">${nearestTrackingPaused ? "재시작" : "일시정지"}</button>
            <button type="button" class="overlay-close-btn" id="nearestCloseBtn" aria-label="주변 위험구간 접기">×</button>
        </div>
        <div class="nearest-list">${rows}</div>
    `;

    const closeBtn = document.getElementById("nearestCloseBtn");
    const pauseBtn = document.getElementById("nearestPauseBtn");
    if (closeBtn) closeBtn.addEventListener("click", closeNearestPanel);
    if (pauseBtn) pauseBtn.addEventListener("click", toggleNearestTrackingPause);

    nearestPanel.querySelectorAll(".nearest-item").forEach(button => {
        button.addEventListener("click", function () {
            const index = Number(this.dataset.index);
            const item = topList[index];
            const state = markerStates.find(candidate => candidate.item.zone_id === item.zone_id);
            if (state) openStateInfo(state);
        });
    });
    requestUiLayoutSync();
}


function getAutoAlertCandidate(nearestItems) {
    return nearestItems.find(item => {
        const distance = toNumber(item.distance_m, Infinity);
        const radius = Math.max(AUTO_ALERT_DISTANCE_M, toNumber(item.radius_m, AUTO_ALERT_DISTANCE_M));
        return distance <= radius && AUTO_ALERT_GRADES.has(item.grade);
    });
}

function showAutoRiskAlert(item) {
    if (!item || item.zone_id === lastRiskAlertZoneId) return;
    lastRiskAlertZoneId = item.zone_id;

    const gradeColor = colorByGrade[item.grade] || "#ef4444";
    const distanceText = formatDistance(item.distance_m);
    const title = `${item.grade} 위험구간 진입`;
    const placeName = item.location_name || item.region || "위험구간";
    const voiceMessage = `${item.grade} 위험구간에 진입했습니다. ${Math.round(toNumber(item.distance_m, 0))}미터 이내입니다. 감속하고 주변을 주의해 주세요.`;

    setMapMessage(`
        <div class="auto-risk-alert" style="--alert-color:${gradeColor};">
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(placeName)} · ${distanceText} 이내</span>
        </div>
    `);
    speakMessage(voiceMessage);
}

function updateUserRiskTracking(lat, lon, accuracy = 0, options = {}) {
    currentUserPosition = {
        lat,
        lon,
        accuracy,
        rawLat: options.rawLat ?? lat,
        rawLon: options.rawLon ?? lon,
        speed: options.speed ?? lastSpeedMps,
        heading: options.heading ?? lastHeadingDeg,
        matchedToRoute: !!options.matchedToRoute,
        routeDistanceM: options.routeDistanceM,
        simulated: !!options.simulated,
        lowAccuracy: !!options.lowAccuracy
    };
    rawUserPosition = {
        lat: currentUserPosition.rawLat,
        lon: currentUserPosition.rawLon,
        accuracy,
        speed: currentUserPosition.speed,
        heading: currentUserPosition.heading
    };
    const userLatLng = createLatLng(lat, lon);
    const nearestItems = getRiskWeightedItemsByDistance(lat, lon);
    const displayItems = nearestItems.slice(0, NEAREST_DISPLAY_COUNT);

    const now = Date.now();
    const renderKey = displayItems.map(item => `${item.zone_id || item.location_name}-${item.grade}`).join("|");
    const shouldRedrawRisks = !lastNearestRenderKey
        || renderKey !== lastNearestRenderKey
        || now - lastNearestRenderAt >= NEAREST_REFRESH_INTERVAL_MS
        || !!options.forceRedraw;

    if (shouldRedrawRisks) {
        drawRiskItems(displayItems, {
            fitBounds: false,
            keepUserLocation: true,
            keepNearestPanel: true,
            keepDetailPanel: isDetailOverlayOpen()
        });
        lastNearestRenderKey = renderKey;
        lastNearestRenderAt = now;
    }

    drawUserLocation(lat, lon, accuracy, { immediate: !!options.simulated });
    showNearestPanel(lat, lon, nearestItems);
    updateSummary(displayItems, "내 위치 주변 위험구간");

    if (options.center !== false) {
        map.panTo(userLatLng);
        map.setLevel(5);
        lastMapFollowPosition = { lat, lon };
    } else {
        maybeFollowUserPosition(userLatLng, lat, lon, options);
    }

    checkNavigationAlerts(lat, lon);
    maybeAutoReroute(lat, lon);

    const alertTarget = getAutoAlertCandidate(nearestItems);
    if (alertTarget && !activeRouteRiskItems.length) {
        showAutoRiskAlert(alertTarget);
    } else if (!alertTarget && !activeRouteRiskItems.length) {
        lastRiskAlertZoneId = null;
    }
    if (!options.keepMessage) {
        const matchText = currentUserPosition.matchedToRoute ? " · 경로 보정 적용" : "";
        const accuracyText = Number.isFinite(accuracy) ? ` · 정확도 ${formatDistance(accuracy)}` : "";
        toolbarValue.textContent = `현재 위치 추적 중${matchText}${accuracyText} · 주변 위험구간 ${displayItems.length}개 확인`;
    }

    updateNavigationControlButtons();
    return displayItems;
}

function startUserRiskWatch() {
    if (nearestTrackingPaused || simulationRunning) return;
    if (!navigator.geolocation || userWatchId !== null) return;

    requestNavigationWakeLock();

    userWatchId = navigator.geolocation.watchPosition(
        position => {
            handleGeolocationPosition(position, {
                center: false,
                follow: true,
                keepMessage: true,
                fromWatch: true
            });
        },
        error => {
            const messageByCode = {
                1: "브라우저 위치 권한이 거부되었습니다.",
                2: "현재 위치를 확인할 수 없습니다.",
                3: "위치 갱신 시간이 초과되었습니다."
            };
            logNavigation("위치 추적 오류", {
                code: error.code,
                message: messageByCode[error.code] || error.message || "알 수 없는 위치 오류"
            });
        },
        {
            enableHighAccuracy: true,
            timeout: GEOLOCATION_TIMEOUT_MS,
            maximumAge: GEOLOCATION_MAXIMUM_AGE_MS
        }
    );
}

function setDestinationResult(message) {
    if (!destinationResultBox) return;
    destinationResultBox.innerHTML = message || "";
}

function setNavigationLoading(active, message = "") {
    if (routeLoadingBar) {
        routeLoadingBar.classList.toggle("show", !!active);
    }
    [destinationSearchBtn, routeAnalyzeBtn].forEach(button => {
        if (!button) return;
        button.disabled = !!active;
        button.classList.toggle("is-loading", !!active);
    });
    if (message) setDestinationResult(message);
}

function getCurrentPositionOnce() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("현재 브라우저에서 위치 정보 기능을 지원하지 않습니다."));
            return;
        }
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: GEOLOCATION_TIMEOUT_MS,
            maximumAge: GEOLOCATION_MAXIMUM_AGE_MS
        });
    });
}

async function ensureCurrentUserPosition() {
    if (currentUserPosition) return currentUserPosition;
    if (!isMapReady || !map) {
        throw new Error("지도가 준비된 뒤 경로 분석을 사용할 수 있습니다.");
    }

    const position = await getCurrentPositionOnce();
    handleGeolocationPosition(position, { center: false, follow: true, keepMessage: true });
    startUserRiskWatch();
    return currentUserPosition;
}

function clearRouteObjects() {
    if (routePolyline) {
        routePolyline.setMap(null);
        routePolyline = null;
    }
    routeRiskMarkers.forEach(marker => marker.setMap(null));
    routeRiskMarkers = [];
}

function clearDestinationOverlay() {
    if (destinationOverlay) {
        destinationOverlay.setMap(null);
        destinationOverlay = null;
    }
}

function clearRouteSession(options = {}) {
    stopRouteSimulation(false);
    activeRouteRiskItems = [];
    activeRoutePathPoints = [];
    lastRouteOriginPosition = null;
    routeAlertStateByZone = new Map();
    lastVoiceAlertKey = null;
    clearRouteObjects();
    if (!options.keepDestination) {
        selectedDestination = null;
        clearDestinationOverlay();
    }
    if (!options.keepPanel && routePanel) {
        routePanel.classList.remove("show");
        routePanel.innerHTML = "";
    }
}

function drawDestinationOverlay(destination) {
    if (!isMapReady || !map || !destination) return;
    clearDestinationOverlay();
    destinationOverlay = new kakao.maps.CustomOverlay({
        position: createLatLng(destination.lat, destination.lon),
        yAnchor: 1,
        zIndex: 450,
        content: `<div class="destination-pin"><span>목적지</span>${escapeHtml(destination.name || "선택 위치")}</div>`
    });
    destinationOverlay.setMap(map);
}

function drawRoutePolyline(routePoints) {
    if (!isMapReady || !map || !Array.isArray(routePoints) || routePoints.length < 2) return;
    if (routePolyline) routePolyline.setMap(null);

    const path = routePoints.map(point => createLatLng(point.lat, point.lon));
    routePolyline = new kakao.maps.Polyline({
        path,
        strokeWeight: 6,
        strokeColor: "#2563eb",
        strokeOpacity: 0.85,
        strokeStyle: "solid"
    });
    routePolyline.setMap(map);

    const bounds = new kakao.maps.LatLngBounds();
    path.forEach(latlng => bounds.extend(latlng));
    map.setBounds(bounds);
}

function drawRouteRiskMarkers(items) {
    if (!isMapReady || !map) return;
    routeRiskMarkers.forEach(marker => marker.setMap(null));
    routeRiskMarkers = [];

    items.slice(0, 120).forEach(item => {
        const lat = toNumber(item.lat, null);
        const lon = toNumber(item.lon, null);
        if (lat === null || lon === null) return;
        const color = colorByGrade[item.grade] || "#ef4444";
        const sourceClass = item.source === "destination" ? " destination-source" : " route-source";
        const label = item.grade || "위험";
        const marker = new kakao.maps.CustomOverlay({
            position: createLatLng(lat, lon),
            yAnchor: 0.5,
            zIndex: 420,
            content: `<button type="button" class="route-risk-pin${sourceClass}" data-route-index="${routeRiskMarkers.length}" style="--pin-color:${color};" title="${escapeHtml(item.location_name)}">${escapeHtml(label)}</button>`
        });
        marker.setMap(map);
        routeRiskMarkers.push(marker);
    });
}

function formatDuration(seconds) {
    const value = toNumber(seconds, 0);
    if (!value) return "-";
    const minutes = Math.round(value / 60);
    if (minutes >= 60) return `${Math.floor(minutes / 60)}시간 ${minutes % 60}분`;
    return `${minutes}분`;
}

function openRouteRiskDetail(item) {
    if (!item) return;
    closeOverlapOverlay();
    suppressNearestPanelForDetail();
    const detailItem = {
        ...item,
        mode: "live",
        static_score: item.score,
        static_grade: item.grade,
        change_status: item.change_status || (item.source === "destination" ? "목적지 주변 위험구간" : "경로상 위험구간"),
        change_reason: item.change_reason || (item.source === "destination" ? `목적지에서 ${formatDistance(toNumber(item.distance_to_destination_m, Infinity))} 지점에 위치` : `경로에서 ${formatDistance(toNumber(item.distance_to_route_m, Infinity))} 지점에 위치`),
        radius_m: item.radius_m || 300,
        weather: item.weather || "-",
        time_band: item.time_band || "-",
        weather_api_status: item.weather_api_status || "",
        weather_fallback_region: item.weather_fallback_region || "",
        weather_fallback_distance_m: item.weather_fallback_distance_m || "",
        weather_fallback_note: item.weather_fallback_note || "",
        incident_weight: item.incident_weight || "",
        incident_reason: item.incident_reason || "",
        nearest_incident_distance_m: item.nearest_incident_distance_m || "",
        nearest_incident_type: item.nearest_incident_type || "",
        nearest_incident_road: item.nearest_incident_road || "",
        nearest_incident_message: item.nearest_incident_message || ""
    };
    overlapPanel = document.createElement("div");
    overlapPanel.className = "detail-modal-backdrop show";
    overlapPanel.appendChild(buildDetailSidePanel(detailItem));
    mapShell.appendChild(overlapPanel);
    if (isMapReady && map && item.lat !== undefined && item.lon !== undefined) {
        map.panTo(createLatLng(item.lat, item.lon));
    }
}

function renderRoutePanel(payload, options = {}) {
    if (!routePanel) return;

    latestRoutePayload = payload;
    if (options.resetCollapsed !== false) routePanelCollapsed = false;

    const routeRisks = payload.route_risks || [];
    const destinationRisks = payload.destination_risks || [];
    const risks = payload.all_risks || [...routeRisks, ...destinationRisks];
    const summary = payload.summary || {};
    const routeBuffer = payload.route_match_buffer_m || 500;
    const destinationRadius = payload.destination_nearby_radius_m || 1500;

    routePanel.classList.add("show");
    routePanel.classList.toggle("collapsed", routePanelCollapsed);

    if (routePanelCollapsed) {
        routePanel.innerHTML = `
            <button type="button" class="route-panel-collapsed-trigger" id="routePanelOpenBtn" aria-label="경로 위험 분석 결과 열기">
                <span>경로/목적지 위험 분석 ${risks.length}개</span>
                <small>열기</small>
            </button>
        `;
        const openBtn = document.getElementById("routePanelOpenBtn");
        if (openBtn) {
            openBtn.addEventListener("click", () => {
                routePanelCollapsed = false;
                renderRoutePanel(latestRoutePayload, { resetCollapsed: false });
            });
        }
        requestUiLayoutSync();
        return;
    }

    const renderRows = (items, sectionType) => items.map(item => {
        const index = risks.findIndex(candidate => candidate.zone_id === item.zone_id && candidate.source === item.source);
        const color = colorByGrade[item.grade] || "#94a3b8";
        const distanceText = sectionType === "destination"
            ? `목적지에서 ${formatDistance(toNumber(item.distance_to_destination_m, Infinity))}`
            : `경로에서 ${formatDistance(toNumber(item.distance_to_route_m, Infinity))}`;
        return `
            <button type="button" class="route-risk-item" data-route-index="${index}" style="--item-color:${color};">
                <span class="route-risk-rank">${index + 1}</span>
                <span>
                    <strong>${escapeHtml(item.location_name || item.region || "위험구간")}</strong>
                    <small>${escapeHtml(item.grade)} · 점수 ${escapeHtml(item.score)} · ${distanceText} · 알림반경 ${escapeHtml(item.radius_m)}m</small>
                </span>
            </button>
        `;
    }).join("");

    const routeRows = renderRows(routeRisks, "route");
    const destinationRows = renderRows(destinationRisks, "destination");

    routePanel.innerHTML = `
        <div class="route-panel-head">
            <div class="route-panel-title">경로/목적지 위험 분석 결과</div>
            <button type="button" class="route-panel-close" id="routePanelCloseBtn" aria-label="경로 위험 분석 결과 접기">×</button>
        </div>
        <div class="route-summary-row">
            <span>총거리 ${formatDistance(summary.distance_m)}</span>
            <span>예상시간 ${formatDuration(summary.duration_sec)}</span>
        </div>
        <div class="route-status-note">API 상태: ${escapeHtml(payload.api_status || "-")} · 전체 ${risks.length}개 · 경로 ${routeRisks.length}개 · 목적지 ${destinationRisks.length}개 · 분석 데이터 ${escapeHtml(payload.risk_dataset_rows || riskData.length)}개</div>
        <div class="route-section">
            <div class="route-section-title"><strong>1. 가는 길 주변 위험구간</strong><span>${routeRisks.length}개</span></div>
            <div class="route-section-desc">경로선 기준 ${routeBuffer}m 이내 또는 위험구간 알림반경 기준</div>
            ${routeRows || "<div class='route-empty'>현재 경로 주변에 매칭된 위험구간이 없습니다.</div>"}
        </div>
        <div class="route-section">
            <div class="route-section-title"><strong>2. 목적지 주변 위험구간</strong><span>${destinationRisks.length}개</span></div>
            <div class="route-section-desc">목적지 반경 ${formatDistance(destinationRadius)} 이내</div>
            ${destinationRows || "<div class='route-empty'>목적지 주변에 매칭된 위험구간이 없습니다.</div>"}
        </div>
    `;

    const closeBtn = document.getElementById("routePanelCloseBtn");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            routePanelCollapsed = true;
            renderRoutePanel(latestRoutePayload, { resetCollapsed: false });
        });
    }
    routePanel.querySelectorAll(".route-risk-item").forEach(button => {
        button.addEventListener("click", function () {
            const index = Number(this.dataset.routeIndex);
            openRouteRiskDetail(risks[index]);
        });
    });
    requestUiLayoutSync();
}

function speakMessage(message) {
    if (!voiceToggle || !voiceToggle.checked) return;
    if (!window.speechSynthesis || !message) return;
    primeSpeechSynthesis();
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
}

function getSearchCenter() {
    if (currentUserPosition) {
        return createLatLng(currentUserPosition.lat, currentUserPosition.lon);
    }
    if (map && typeof map.getCenter === "function") {
        return map.getCenter();
    }
    return createLatLng(defaultCenter.lat, defaultCenter.lon);
}

function searchPlaces(query, options = {}) {
    return new Promise(resolve => {
        const places = new kakao.maps.services.Places();
        places.keywordSearch(query, function (results, status) {
            resolve({ results: results || [], status });
        }, options);
    });
}

function searchAddress(query) {
    return new Promise(resolve => {
        const geocoder = new kakao.maps.services.Geocoder();
        geocoder.addressSearch(query, function (results, status) {
            resolve({ results: results || [], status });
        });
    });
}

function pickBestPlace(results) {
    if (!results || !results.length) return null;
    return results[0];
}

function uniqueSearchValues(values) {
    const seen = new Set();
    return values
        .map(value => String(value || "").replace(/\s+/g, " ").trim())
        .filter(value => {
            if (!value || seen.has(value)) return false;
            seen.add(value);
            return true;
        });
}

function buildDestinationSearchQueries(query) {
    const normalized = String(query || "").replace(/\s+/g, " ").trim();
    if (!normalized) return [];

    const candidates = [normalized];
    const selectedSido = sidoSelect ? sidoSelect.value.trim() : "";
    const selectedSigungu = sigunguSelect ? sigunguSelect.value.trim() : "";

    if (selectedSigungu) candidates.push(`${selectedSigungu} ${normalized}`);
    if (selectedSido && selectedSigungu) candidates.push(`${selectedSido} ${selectedSigungu} ${normalized}`);
    if (selectedSido) candidates.push(`${selectedSido} ${normalized}`);

    DESTINATION_SEARCH_CANDIDATE_PREFIXES.forEach(prefix => {
        candidates.push(`${prefix}${normalized}`);
    });

    return uniqueSearchValues(candidates);
}

function makeDestinationFromPlace(place) {
    return {
        name: place.place_name || place.road_address_name || place.address_name || "검색 위치",
        lat: Number(place.y),
        lon: Number(place.x),
        address: place.road_address_name || place.address_name || "",
        search_type: "place"
    };
}

function makeDestinationFromAddress(addressResult, fallbackName = "주소 검색 위치") {
    const roadAddress = addressResult.road_address ? addressResult.road_address.address_name : "";
    const addressName = addressResult.address_name || (addressResult.address ? addressResult.address.address_name : "");
    return {
        name: roadAddress || addressName || fallbackName,
        lat: Number(addressResult.y),
        lon: Number(addressResult.x),
        address: addressName || roadAddress || "",
        search_type: "address"
    };
}

function isValidDestination(destination) {
    return destination && Number.isFinite(destination.lat) && Number.isFinite(destination.lon);
}


function setMarkerItemAsDestination(item) {
    if (!item) return;
    const lat = toNumber(item.lat, null);
    const lon = toNumber(item.lon, null);
    if (lat === null || lon === null) return;
    const name = item.location_name || item.region || "선택 위험구간";
    clearRouteSession({ keepDestination: true });
    selectedDestination = {
        name,
        lat,
        lon,
        address: item.region || "위험구간 마커 선택"
    };
    if (destinationSearchInput) destinationSearchInput.value = name;
    drawDestinationOverlay(selectedDestination);
    setDestinationResult(`위험구간 목적지 선택: <strong>${escapeHtml(name)}</strong><br><small>Enter 또는 검색 버튼을 누르면 경로 분석을 시작합니다.</small>`);
}

function setSelectedDestination(destination, messagePrefix = "선택 목적지") {
    clearRouteSession({ keepDestination: true });
    selectedDestination = destination;
    if (destinationSearchInput) destinationSearchInput.value = destination.name || "";
    drawDestinationOverlay(destination);
    setDestinationResult(`${messagePrefix}: <strong>${escapeHtml(destination.name || "선택 위치")}</strong><br><small>${escapeHtml(destination.address || "")}</small>`);
    if (map) map.panTo(createLatLng(destination.lat, destination.lon));
}

async function findDestinationByKeyword(query) {
    if (!window.kakao || !kakao.maps || !kakao.maps.services) {
        throw new Error("카카오 장소/주소 검색 서비스가 아직 준비되지 않았습니다.");
    }

    const center = getSearchCenter();
    const localOptions = {
        location: center,
        radius: DESTINATION_SEARCH_RADIUS_M,
        sort: kakao.maps.services.SortBy.DISTANCE
    };
    const candidates = buildDestinationSearchQueries(query);

    const localPlaceResult = await searchPlaces(query, localOptions);
    if (localPlaceResult.status === kakao.maps.services.Status.OK && localPlaceResult.results.length) {
        const destination = makeDestinationFromPlace(pickBestPlace(localPlaceResult.results));
        if (isValidDestination(destination)) return destination;
    }

    for (const candidate of candidates) {
        const addressResult = await searchAddress(candidate);
        if (addressResult.status === kakao.maps.services.Status.OK && addressResult.results.length) {
            const destination = makeDestinationFromAddress(addressResult.results[0], candidate);
            if (isValidDestination(destination)) return destination;
        }
    }

    for (const candidate of candidates) {
        const placeResult = await searchPlaces(candidate, localOptions);
        if (placeResult.status === kakao.maps.services.Status.OK && placeResult.results.length) {
            const destination = makeDestinationFromPlace(pickBestPlace(placeResult.results));
            if (isValidDestination(destination)) return destination;
        }
    }

    const globalPlaceResult = await searchPlaces(query);
    if (globalPlaceResult.status === kakao.maps.services.Status.OK && globalPlaceResult.results.length) {
        const destination = makeDestinationFromPlace(pickBestPlace(globalPlaceResult.results));
        if (isValidDestination(destination)) return destination;
    }

    for (const candidate of candidates) {
        const placeResult = await searchPlaces(candidate);
        if (placeResult.status === kakao.maps.services.Status.OK && placeResult.results.length) {
            const destination = makeDestinationFromPlace(pickBestPlace(placeResult.results));
            if (isValidDestination(destination)) return destination;
        }
    }

    throw new Error("검색 결과가 없습니다. 예: 두정동 1484, 충남 천안시 서북구 두정동 1484처럼 지번/도로명 주소를 함께 입력하거나 지도에서 목적지를 직접 클릭해 주세요.");
}

function getInputQuery() {
    return destinationSearchInput ? destinationSearchInput.value.trim() : "";
}

function hasInputChangedFromSelected(query) {
    if (!query || !selectedDestination) return true;
    return query !== selectedDestination.name && query !== selectedDestination.address;
}

async function performDestinationSearch(options = {}) {
    const query = getInputQuery();
    if (!query) {
        setDestinationResult("목적지를 입력하거나 지도에서 위치를 클릭해 주세요.");
        return null;
    }

    try {
        setNavigationLoading(true, "목적지 검색 중...");
        const destination = await findDestinationByKeyword(query);
        setSelectedDestination(destination);
        if (options.analyzeAfterSearch) {
            await analyzeRouteRisk({ skipSearch: true });
        }
        return destination;
    } catch (error) {
        setDestinationResult(escapeHtml(error.message || String(error)));
        return null;
    } finally {
        setNavigationLoading(false);
    }
}

function reverseGeocodeDestination(latlng) {
    return new Promise(resolve => {
        if (!window.kakao || !kakao.maps || !kakao.maps.services) {
            resolve(null);
            return;
        }
        const geocoder = new kakao.maps.services.Geocoder();
        geocoder.coord2Address(latlng.getLng(), latlng.getLat(), function (results, status) {
            if (status !== kakao.maps.services.Status.OK || !results.length) {
                resolve(null);
                return;
            }
            const result = results[0];
            const road = result.road_address ? result.road_address.address_name : "";
            const address = result.address ? result.address.address_name : "";
            resolve(road || address || null);
        });
    });
}

async function handleMapDestinationClick(latlng) {
    if (!latlng || !isMapReady || !map) return;
    const lat = latlng.getLat();
    const lon = latlng.getLng();
    try {
        setNavigationLoading(true, "선택한 위치를 목적지로 설정하는 중...");
        const address = await reverseGeocodeDestination(latlng);
        const name = address || `선택 위치 ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
        setSelectedDestination({ name, lat, lon, address: address || "지도에서 선택한 위치" }, "지도 선택 목적지");
        await analyzeRouteRisk({ skipSearch: true });
    } catch (error) {
        setDestinationResult(`지도 선택 목적지 분석 실패: ${escapeHtml(error.message || String(error))}`);
    } finally {
        setNavigationLoading(false);
    }
}

async function analyzeRouteRisk(options = {}) {
    if (routeAnalyzeInProgress) return;

    const query = getInputQuery();
    if (!options.skipSearch && hasInputChangedFromSelected(query)) {
        const destination = await performDestinationSearch({ analyzeAfterSearch: false });
        if (!destination) return;
    }

    if (!selectedDestination) {
        setDestinationResult("목적지를 검색하거나 지도에서 목적지를 클릭해 주세요.");
        return;
    }

    routeAnalyzeInProgress = true;

    try {
        if (!currentUserPosition) {
            setNavigationLoading(true, "현재 위치를 확인하는 중...");
            await ensureCurrentUserPosition();
        }

        const origin = `${currentUserPosition.lon},${currentUserPosition.lat}`;
        const destination = `${selectedDestination.lon},${selectedDestination.lat}`;
        const url = `${NAVIGATION_API_ROUTE}?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&priority=${encodeURIComponent(ROUTE_PRIORITY)}`;

        setNavigationLoading(true, options.autoReroute ? "현재 위치 기준 최단 경로를 다시 분석하는 중..." : "자동차 최단 경로와 위험구간을 분석하는 중...");
        const response = await fetch(url, { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok || payload.api_status === "ERROR") {
            throw new Error(payload.message || "경로 분석에 실패했습니다.");
        }

        activeRoutePathPoints = payload.route_points || [];
        activeRouteRiskItems = payload.all_risks || [...(payload.route_risks || []), ...(payload.destination_risks || [])];
        lastRouteOriginPosition = { ...currentUserPosition };
        lastAutoRerouteAt = Date.now();
        routeAlertStateByZone = new Map();

        clearRouteObjects();
        drawRoutePolyline(activeRoutePathPoints);
        drawRouteRiskMarkers(activeRouteRiskItems);
        drawDestinationOverlay(selectedDestination);
        renderRoutePanel(payload);
        ensureNavigationControls();
        setNavigationFollowMode("follow");
        setDestinationResult(`<strong>${escapeHtml(selectedDestination.name)}</strong>까지 자동차 최단 경로 분석 완료`);
        startUserRiskWatch();
    } catch (error) {
        setDestinationResult(`경로 분석 실패: ${escapeHtml(error.message || String(error))}<br><small>python src/navigation_server.py로 실행했는지 확인해 주세요.</small>`);
    } finally {
        routeAnalyzeInProgress = false;
        setNavigationLoading(false);
    }
}

function getRouteAlertCandidate(lat, lon) {
    let best = null;
    activeRouteRiskItems.forEach(item => {
        const itemLat = toNumber(item.lat, null);
        const itemLon = toNumber(item.lon, null);
        if (itemLat === null || itemLon === null || !ROUTE_ALERT_GRADES.has(item.grade)) return;
        const distance = haversineDistanceMeters(lat, lon, itemLat, itemLon);
        const radius = Math.max(120, toNumber(item.radius_m, 300));
        const approachRadius = radius + ROUTE_APPROACH_EXTRA_M;
        if (distance <= approachRadius && (!best || distance < best.distance_m)) {
            best = { ...item, distance_m: distance, alert_radius_m: radius, approach_radius_m: approachRadius };
        }
    });
    return best;
}

function clearRouteAlertStates(lat, lon) {
    routeAlertStateByZone.forEach((state, zoneId) => {
        const item = activeRouteRiskItems.find(candidate => candidate.zone_id === zoneId);
        if (!item) {
            routeAlertStateByZone.delete(zoneId);
            return;
        }
        const itemLat = toNumber(item.lat, null);
        const itemLon = toNumber(item.lon, null);
        if (itemLat === null || itemLon === null) return;
        const radius = Math.max(120, toNumber(item.radius_m, 300));
        const clearDistance = radius + ROUTE_APPROACH_EXTRA_M + ROUTE_CLEAR_EXTRA_M;
        const distance = haversineDistanceMeters(lat, lon, itemLat, itemLon);
        if (distance > clearDistance) routeAlertStateByZone.delete(zoneId);
    });
}

function showRouteAlert(item, phase) {
    const zoneId = item.zone_id || item.location_name;
    if (!zoneId) return;
    const prevPhase = routeAlertStateByZone.get(zoneId);
    if (prevPhase === phase || (prevPhase === "entry" && phase === "approach")) return;

    routeAlertStateByZone.set(zoneId, phase);
    const gradeColor = colorByGrade[item.grade] || "#ef4444";
    const title = phase === "entry" ? `${item.grade} 위험구간 진입` : `${item.grade} 위험구간 접근`;
    const message = phase === "entry"
        ? `${item.grade} 위험구간에 진입했습니다. 감속하고 주변 차량과 보행자를 주의해 주세요.`
        : `${item.grade} 위험구간 ${Math.round(item.distance_m)}미터 전방입니다. 감속하고 전방을 주의해 주세요.`;

    setMapMessage(`<div class="auto-risk-alert" style="--alert-color:${gradeColor};"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(item.location_name)} · ${formatDistance(item.distance_m)}</span></div>`);
    const voiceKey = `${zoneId}-${phase}`;
    if (voiceKey !== lastVoiceAlertKey) {
        lastVoiceAlertKey = voiceKey;
        speakMessage(message);
    }
}

function checkNavigationAlerts(lat, lon) {
    if (!activeRouteRiskItems.length) return;
    clearRouteAlertStates(lat, lon);
    const riskTarget = getRouteAlertCandidate(lat, lon);
    if (!riskTarget) return;
    const phase = riskTarget.distance_m <= riskTarget.alert_radius_m ? "entry" : "approach";
    showRouteAlert(riskTarget, phase);
}

function shouldAutoReroute(lat, lon) {
    if (!selectedDestination || !activeRoutePathPoints.length || routeAnalyzeInProgress) return false;
    const now = Date.now();
    if (now - lastAutoRerouteAt < ROUTE_REROUTE_COOLDOWN_MS) return false;

    const distanceFromRoute = minDistanceToRouteMeters(lat, lon, activeRoutePathPoints);
    if (distanceFromRoute >= ROUTE_DEVIATION_REROUTE_M) return true;

    if (!lastRouteOriginPosition) return false;
    const movedFromOrigin = haversineDistanceMeters(lat, lon, lastRouteOriginPosition.lat, lastRouteOriginPosition.lon);
    return movedFromOrigin >= ROUTE_DEPARTURE_MOVE_REROUTE_M;
}

function maybeAutoReroute(lat, lon) {
    if (!shouldAutoReroute(lat, lon)) return;
    lastAutoRerouteAt = Date.now();
    analyzeRouteRisk({ skipSearch: true, autoReroute: true, keepMessage: true });
}

function locateUser() {
    setError("");

    if (!isMapReady || !map) {
        setError("지도가 준비된 뒤 내 위치 기능을 사용할 수 있습니다.");
        return;
    }

    if (!navigator.geolocation) {
        setError("현재 브라우저에서 위치 정보 기능을 지원하지 않습니다.");
        return;
    }

    if (locateBtn) locateBtn.disabled = true;
    if (locateBtn) locateBtn.textContent = "위치 확인 중...";

    navigator.geolocation.getCurrentPosition(
        position => {
            stopRouteSimulation(false);
            setNavigationFollowMode("follow");
            handleGeolocationPosition(position, { center: true, follow: true, keepMessage: false });
            startUserRiskWatch();

            if (locateBtn) locateBtn.disabled = false;
            if (locateBtn) locateBtn.textContent = "내 위치 위험 추적 중";
        },
        error => {
            const messageByCode = {
                1: "브라우저 위치 권한이 거부되었습니다. 주소창 왼쪽 자물쇠/정보 아이콘에서 위치 권한을 허용해 주세요.",
                2: "현재 위치를 확인할 수 없습니다. 네트워크 또는 장치 위치 설정을 확인해 주세요.",
                3: "위치 확인 시간이 초과되었습니다. 다시 시도해 주세요."
            };
            setError(messageByCode[error.code] || "위치 확인 중 알 수 없는 오류가 발생했습니다.");
            if (locateBtn) locateBtn.disabled = false;
            if (locateBtn) locateBtn.textContent = "내 위치 주변 위험 확인";
        },
        {
            enableHighAccuracy: true,
            timeout: GEOLOCATION_TIMEOUT_MS,
            maximumAge: GEOLOCATION_MAXIMUM_AGE_MS
        }
    );
}


async function runDestinationInputAnalysis() {
    const query = getInputQuery();
    if (!query) {
        setDestinationResult("목적지를 입력하거나 지도에서 위치를 클릭해 주세요.");
        return;
    }
    if (selectedDestination && !hasInputChangedFromSelected(query)) {
        await analyzeRouteRisk({ skipSearch: true });
        return;
    }
    await performDestinationSearch({ analyzeAfterSearch: true });
}

function bindEvents() {
    panelToggle.addEventListener("click", toggleSidebar);
    document.addEventListener("click", function (event) {
        const pin = event.target.closest(".route-risk-pin");
        if (!pin) return;
        event.preventDefault();
        event.stopPropagation();
        const index = Number(pin.dataset.routeIndex);
        openRouteRiskDetail(activeRouteRiskItems[index]);
    });

    sidoSelect.addEventListener("change", function (event) {
        populateSigunguOptions(event.target.value);
        sigunguSelect.value = "";
    });

    document.getElementById("applyBtn").addEventListener("click", renderMap);
    document.getElementById("resetBtn").addEventListener("click", resetFilters);
    if (locateBtn) locateBtn.addEventListener("click", locateUser);
    if (destinationSearchBtn) destinationSearchBtn.addEventListener("click", () => runDestinationInputAnalysis());
    if (destinationSearchInput) {
        destinationSearchInput.addEventListener("keydown", event => {
            if (event.key === "Enter") {
                event.preventDefault();
                runDestinationInputAnalysis();
            }
        });
    }
    if (routeAnalyzeBtn) routeAnalyzeBtn.addEventListener("click", () => analyzeRouteRisk());
    if (voiceToggle) voiceToggle.addEventListener("change", primeSpeechSynthesis);

    ["click", "keydown", "touchstart"].forEach(eventName => {
        document.addEventListener(eventName, primeSpeechSynthesis, { once: true, passive: true });
    });

    window.addEventListener("resize", requestUiLayoutSync);

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && (userWatchId !== null || simulationRunning)) {
            requestNavigationWakeLock();
        }
    });

    window.addEventListener("beforeunload", () => {
        stopRouteSimulation(false);
        if (userWatchId !== null && navigator.geolocation) {
            navigator.geolocation.clearWatch(userWatchId);
            userWatchId = null;
        }
    });

    ensureNavigationControls();

    window.addEventListener("resize", function () {
        if (!isMapReady || !map) return;
        const center = map.getCenter();
        window.setTimeout(() => {
            map.relayout();
            map.setCenter(center);
        }, 120);
    });
}

function bootstrap() {
    initializePageText();
    populateSidoOptions();
    populateSigunguOptions("");
    updateSummary([]);
    bindEvents();
    initMap();
    syncToolbarWithSidebar();
}

bootstrap();
