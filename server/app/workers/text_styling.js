// text-styling extractor — selective computed style extraction
// Usage: playwright page.evaluate(source) then call window.__extractTextStyling()

(function() {
  'use strict';

  var getSelector = function(el) {
    if (el.id) return '#' + el.id;
    var parts = [];
    var n = el;
    while (n && n.nodeType === 1 && parts.length < 4) {
      var s = n.tagName.toLowerCase();
      if (n.className && typeof n.className === 'string') {
        s += '.' + n.className.trim().split(/\s+/).slice(0, 2).join('.');
      }
      parts.unshift(s);
      n = n.parentElement;
    }
    return parts.join(' > ');
  };

  window.__extractTextStyling = function() {
    var elements = [];
    var linksTotal = 0;
    var linksWithoutUnderline = 0;
    var lineThroughCount = 0;
    var boldCount = 0;
    var italicCount = 0;

    var all = document.querySelectorAll('a, span, p, li, h1, h2, h3, h4, h5, h6, div, td, th, label, button, strong, em, s, del, b, i, u');

    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var text = (el.textContent || '').trim();
      if (!text) continue;

      // leaf-only: skip elements with text-bearing children to avoid double-counting
      var hasTextChild = false;
      var kids = el.querySelectorAll('*');
      for (var k = 0; k < kids.length; k++) {
        if ((kids[k].textContent || '').trim() !== '') { hasTextChild = true; break; }
      }
      if (hasTextChild) continue;

      var cs = getComputedStyle(el);
      var tag = el.tagName.toLowerCase();
      var isLink = tag === 'a';
      var decorLine = cs.textDecorationLine || 'none';
      var fontWeight = parseInt(cs.fontWeight) || 400;
      var fontStyle = cs.fontStyle || 'normal';
      var textTransform = cs.textTransform || 'none';
      var letterSpacing = cs.letterSpacing || 'normal';

      if (isLink) linksTotal++;

      var notable = false;

      if (isLink) {
        notable = true;
        if (decorLine.indexOf('underline') === -1) linksWithoutUnderline++;
      }
      if (decorLine.indexOf('line-through') !== -1) {
        notable = true;
        lineThroughCount++;
      }
      if (fontWeight >= 600) {
        notable = true;
        boldCount++;
      }
      if (fontStyle === 'italic') {
        notable = true;
        italicCount++;
      }
      if (textTransform === 'uppercase') {
        notable = true;
      }
      if (letterSpacing !== 'normal' && letterSpacing !== '0px') {
        notable = true;
      }

      if (!notable) continue;

      elements.push({
        selector: getSelector(el),
        text: text.slice(0, 30),
        text_decoration_line: decorLine,
        font_weight: String(fontWeight),
        font_style: fontStyle,
        text_transform: textTransform,
        letter_spacing: letterSpacing,
        is_link: isLink,
      });
    }

    return {
      summary: {
        links_total: linksTotal,
        links_without_underline: linksWithoutUnderline,
        line_through_count: lineThroughCount,
        bold_count: boldCount,
        italic_count: italicCount,
      },
      elements: elements,
    };
  };
})();
