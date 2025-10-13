const assert = require('assert');
const path = require('path');

const utils = require(path.join('..', 'frontend', 'js', 'popupUtils.js'));

function rect({ left, top, width, height }) {
    return {
        left,
        top,
        right: left + width,
        bottom: top + height,
        width,
        height
    };
}

(function testNoShiftWhenInside() {
    const mapRect = rect({ left: 0, top: 0, width: 800, height: 600 });
    const popupRect = rect({ left: 100, top: 100, width: 200, height: 150 });
    const shift = utils.computePopupShift(mapRect, popupRect, { margin: 60, maxShift: { x: 200, y: 200 } });
    assert.deepStrictEqual(shift, { x: 0, y: 0 });
})();

(function testTopOverflow() {
    const mapRect = rect({ left: 0, top: 0, width: 800, height: 600 });
    const popupRect = rect({ left: 200, top: -40, width: 200, height: 150 });
    const shift = utils.computePopupShift(mapRect, popupRect, { margin: 60, maxShift: { x: 200, y: 200 } });
    assert(shift.y < 0, 'Expected negative Y shift to push popup downward');
})();

(function testBottomOverflow() {
    const mapRect = rect({ left: 0, top: 0, width: 800, height: 600 });
    const popupRect = rect({ left: 200, top: 520, width: 200, height: 150 });
    const shift = utils.computePopupShift(mapRect, popupRect, { margin: 60, maxShift: { x: 200, y: 200 } });
    assert(shift.y > 0, 'Expected positive Y shift to push popup upward');
})();

(function testClamp() {
    const mapRect = rect({ left: 0, top: 0, width: 800, height: 600 });
    const popupRect = rect({ left: -400, top: -300, width: 200, height: 150 });
    const shift = utils.computePopupShift(mapRect, popupRect, { margin: 60, maxShift: { x: 100, y: 120 } });
    assert.strictEqual(shift.x, -100);
    assert.strictEqual(shift.y, -120);
})();

console.log('popupUtils tests passed');
