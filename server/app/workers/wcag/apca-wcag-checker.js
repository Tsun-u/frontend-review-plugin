// MIT License — extracted from tsunumon html_renderer.py APCA logic, extended
// Usage: playwright page.evaluate(source) then call window.__apcaWcagCheck()

(function() {
  'use strict';

  const sRGBtoY = (r, g, b) => 0.2126729 * Math.pow(r / 255, 2.4)
                              + 0.7151522 * Math.pow(g / 255, 2.4)
                              + 0.0721750 * Math.pow(b / 255, 2.4);

  const APCAcontrast = (txtY, bgY) => {
    const normBG = Math.pow(bgY, 0.56);
    const normTXT = Math.pow(txtY, 0.57);
    const raw = (normBG - normTXT) * 1.14;
    if (Math.abs(raw) < 0.1) return 0;
    return (raw > 0 ? raw - 0.027 : raw + 0.027) * 100;
  };

  const wcag2Luminance = (r, g, b) => {
    const norm = c => {
      const s = c / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * norm(r) + 0.7152 * norm(g) + 0.0722 * norm(b);
  };

  const wcag2Ratio = (fg, bg) => {
    const lFg = wcag2Luminance(...fg);
    const lBg = wcag2Luminance(...bg);
    const lighter = Math.max(lFg, lBg);
    const darker = Math.min(lFg, lBg);
    return (lighter + 0.05) / (darker + 0.05);
  };

  const getEffectiveBg = (el) => {
    let node = el;
    while (node && node !== document.documentElement) {
      const bg = getComputedStyle(node).backgroundColor;
      const m = bg.match(/(\d+)/g);
      if (m) {
        const [r, g, b, a] = m.map(Number);
        if (a === undefined || a > 0.1) {
          return [r, g, b];
        }
      }
      node = node.parentElement;
    }
    return [255, 255, 255];
  };

  const parseFg = (el) => {
    const c = getComputedStyle(el).color;
    const m = c.match(/(\d+)/g);
    return m ? m.slice(0, 3).map(Number) : [0, 0, 0];
  };

  const getSelector = (el) => {
    if (el.id) return '#' + el.id;
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && parts.length < 4) {
      let s = n.tagName.toLowerCase();
      if (n.className && typeof n.className === 'string') {
        s += '.' + n.className.trim().split(/\s+/).slice(0, 2).join('.');
      }
      parts.unshift(s);
      n = n.parentElement;
    }
    return parts.join(' > ');
  };

  const getBbox = (el) => {
    const r = el.getBoundingClientRect();
    return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
  };

  const checkContrast = (el, violations) => {
    if (!el.textContent || !el.textContent.trim()) return;
    const fg = parseFg(el);
    const bg = getEffectiveBg(el);
    const fontSize = parseFloat(getComputedStyle(el).fontSize);
    const fontWeight = parseInt(getComputedStyle(el).fontWeight) || 400;

    const apcaLc = Math.abs(APCAcontrast(sRGBtoY(...fg), sRGBtoY(...bg)));
    const w2 = wcag2Ratio(fg, bg);
    const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);

    const apcaPass = isLarge ? apcaLc >= 45 : apcaLc >= 60;
    const w2AA = isLarge ? w2 >= 3 : w2 >= 4.5;

    if (!apcaPass || !w2AA) {
      violations.push({
        rule: 'contrast',
        element_selector: getSelector(el),
        fg: 'rgb(' + fg.join(',') + ')',
        bg: 'rgb(' + bg.join(',') + ')',
        apca: { lc: Math.round(apcaLc), verdict: apcaPass ? 'pass' : (isLarge ? 'fail_large_text' : 'fail_body_text') },
        wcag2: {
          ratio: Math.round(w2 * 100) / 100,
          aa_normal: !isLarge && w2 >= 4.5,
          aa_large: isLarge && w2 >= 3,
          aaa_normal: !isLarge && w2 >= 7,
          aaa_large: isLarge && w2 >= 4.5,
          large_text: isLarge,
        },
        severity: w2 < 3 ? 'critical' : (w2 < 4.5 ? 'major' : 'minor'),
        bbox: getBbox(el),
      });
    }
  };

  const checkTapTarget = (el, violations, isMobile) => {
    if (!isMobile) return;
    const tag = el.tagName.toLowerCase();
    const isInteractive = tag === 'button' || tag === 'a' ||
      (tag === 'input' && ['button', 'submit', 'checkbox', 'radio'].includes(el.type));
    if (!isInteractive) return;
    const r = el.getBoundingClientRect();
    if (r.width < 44 || r.height < 44) {
      violations.push({
        rule: 'tap_target',
        element_selector: getSelector(el),
        current_size: [Math.round(r.width), Math.round(r.height)],
        expected_size: [44, 44],
        severity: 'major',
        bbox: getBbox(el),
      });
    }
  };

  const checkFontSize = (el, violations) => {
    if (!el.textContent || !el.textContent.trim()) return;
    const fontSize = parseFloat(getComputedStyle(el).fontSize);
    const tag = el.tagName.toLowerCase();
    const isBody = ['p', 'span', 'li', 'div'].includes(tag);
    if (isBody && fontSize < 14) {
      violations.push({
        rule: 'font_size',
        element_selector: getSelector(el),
        current: fontSize + 'px',
        expected: '>= 16px (body) or >= 14px (secondary)',
        severity: fontSize < 12 ? 'major' : 'minor',
        bbox: getBbox(el),
      });
    }
  };

  const checkLineHeight = (el, violations) => {
    if (!el.textContent || !el.textContent.trim()) return;
    const cs = getComputedStyle(el);
    const fontSize = parseFloat(cs.fontSize);
    const lh = cs.lineHeight === 'normal' ? fontSize * 1.2 : parseFloat(cs.lineHeight);
    if (lh / fontSize < 1.5) {
      violations.push({
        rule: 'line_height',
        element_selector: getSelector(el),
        current: Math.round(lh) + 'px (' + (lh / fontSize).toFixed(2) + 'x)',
        expected: '>= 1.5x font-size',
        severity: 'minor',
        bbox: getBbox(el),
      });
    }
  };

  const checkFocusIndicator = (el, violations) => {
    const tag = el.tagName.toLowerCase();
    if (!['button', 'a', 'input', 'select', 'textarea'].includes(tag)) return;
    const cs = getComputedStyle(el);
    if (cs.outlineStyle === 'none' && cs.boxShadow === 'none') {
      violations.push({
        rule: 'focus_indicator_missing',
        element_selector: getSelector(el),
        note: 'outline:none without box-shadow alternative',
        severity: 'major',
        bbox: getBbox(el),
      });
    }
  };

  const checkTextOverflow = (el, violations) => {
    const cs = getComputedStyle(el);
    if (cs.textOverflow === 'ellipsis' && cs.overflow === 'hidden' && !el.title) {
      violations.push({
        rule: 'text_overflow_no_title',
        element_selector: getSelector(el),
        text_preview: el.textContent.slice(0, 50),
        severity: 'minor',
        bbox: getBbox(el),
      });
    }
  };

  window.__apcaWcagCheck = function(opts) {
    opts = opts || {};
    var isMobile = opts.viewport === 'mobile';
    var violations = [];
    var skipSelectors = opts.skipSelectors || [];

    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (skipSelectors.some(function(s) { return el.matches(s); })) continue;
      checkContrast(el, violations);
      checkTapTarget(el, violations, isMobile);
      checkFontSize(el, violations);
      checkLineHeight(el, violations);
      checkFocusIndicator(el, violations);
      checkTextOverflow(el, violations);
    }

    var bySeverity = { critical: 0, major: 0, minor: 0 };
    for (var j = 0; j < violations.length; j++) {
      bySeverity[violations[j].severity] = (bySeverity[violations[j].severity] || 0) + 1;
    }

    return {
      summary: {
        violations_count: violations.length,
        by_severity: bySeverity,
      },
      violations: violations,
    };
  };
})();
