import { test } from 'node:test';
import assert from 'node:assert/strict';
import { updateForestPanel, initForestPanel } from './forestPanel.js';
import { getHotspotById } from './data/forestCatalog.js';

function createMockDom() {
  const elements = new Map();
  const mockDoc = {
    getElementById(id) {
      if (!elements.has(id)) {
        const el = {
          id,
          value: '',
          textContent: '',
          className: '',
          style: {},
          children: [],
          classList: {
            classes: new Set(),
            add(c) { this.classes.add(c); },
            remove(c) { this.classes.delete(c); },
            toggle(c, force) {
              if (force === undefined) {
                if (this.classes.has(c)) this.classes.delete(c);
                else this.classes.add(c);
              } else if (force) {
                this.classes.add(c);
              } else {
                this.classes.delete(c);
              }
            },
            contains(c) { return this.classes.has(c); },
          },
          appendChild(child) {
            this.children.push(child);
            return child;
          },
          addEventListener(event, fn) {
            this._listeners = this._listeners || {};
            this._listeners[event] = fn;
          },
        };
        elements.set(id, el);
      }
      return elements.get(id);
    },
    createElement(tag) {
      return {
        tag,
        value: '',
        textContent: '',
        className: '',
        style: {},
        children: [],
        appendChild(c) {
          this.children.push(c);
          return c;
        },
      };
    },
  };
  return { mockDoc, elements };
}

test('forestPanel: updateForestPanel populates DOM elements with catalog hotspot metrics', () => {
  const { mockDoc, elements } = createMockDom();
  const originalDoc = globalThis.document;
  globalThis.document = mockDoc;

  try {
    updateForestPanel('amazon-rondonia');

    const lossEl = elements.get('forest-loss-val');
    assert.ok(lossEl.textContent.startsWith('-') && lossEl.textContent.endsWith('%'));

    const coverEl = elements.get('forest-cover-val');
    assert.ok(coverEl.textContent.includes('%'));

    const riskEl = elements.get('forest-risk-val');
    assert.ok(riskEl.textContent.length > 0);

    const xaiSummary = elements.get('forest-xai-summary');
    assert.ok(xaiSummary.textContent.length > 10);
  } finally {
    globalThis.document = originalDoc;
  }
});

test('forestPanel: initForestPanel wires up zone select, focus, and slider', () => {
  const { mockDoc, elements } = createMockDom();
  const originalDoc = globalThis.document;
  const originalWindow = globalThis.window;
  globalThis.document = mockDoc;
  globalThis.window = new EventTarget();

  const selectedZones = [];
  const timelineYears = [];
  const mockLayer = {
    selectZone(id) { selectedZones.push(id); },
    setTimelineYear(y) { timelineYears.push(y); },
  };

  try {
    initForestPanel({ viewer: {}, forestLayer: mockLayer });

    // Test zone select change listener
    const zoneSelect = elements.get('forest-zone-select');
    assert.ok(zoneSelect._listeners?.change);
    zoneSelect._listeners.change({ target: { value: 'congo-salonga' } });
    assert.equal(selectedZones[0], 'congo-salonga');

    // Test focus button listener
    const focusBtn = elements.get('forest-focus-btn');
    assert.ok(focusBtn._listeners?.click);
    focusBtn._listeners.click();
    assert.equal(selectedZones[1], 'congo-salonga');

    // Test timeline slider input listener
    const slider = elements.get('forest-timeline-slider');
    assert.ok(slider._listeners?.input);
    slider._listeners.input({ target: { value: 2024 } });
    assert.equal(timelineYears[0], 2024);
  } finally {
    globalThis.document = originalDoc;
    globalThis.window = originalWindow;
  }
});
