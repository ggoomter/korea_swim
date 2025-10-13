(function (global) {
    function clamp(value, min, max) {
        if (value < min) return min;
        if (value > max) return max;
        return value;
    }

    function computePopupShift(mapRect, popupRect, options) {
        const margin = (options && options.margin) || 60;
        const maxShift = (options && options.maxShift) || { x: 260, y: 240 };
        const shift = { x: 0, y: 0 };

        const leftOverlap = (mapRect.left + margin) - popupRect.left;
        if (leftOverlap > 0) {
            shift.x -= leftOverlap;
        }

        const rightOverlap = popupRect.right - (mapRect.right - margin);
        if (rightOverlap > 0) {
            shift.x += rightOverlap;
        }

        const topOverlap = (mapRect.top + margin) - popupRect.top;
        if (topOverlap > 0) {
            shift.y -= topOverlap;
        }

        const bottomOverlap = popupRect.bottom - (mapRect.bottom - margin);
        if (bottomOverlap > 0) {
            shift.y += bottomOverlap;
        }

        shift.x = clamp(shift.x, -maxShift.x, maxShift.x);
        shift.y = clamp(shift.y, -maxShift.y, maxShift.y);

        return shift;
    }

    const exported = { clamp, computePopupShift };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    } else {
        global.SwimPopupUtils = exported;
    }
})(typeof window !== 'undefined' ? window : globalThis);
