(function () {
  var root = document.documentElement;
  var button = document.querySelector('.theme-toggle');

  if (!button) return;

  function updateButton(theme) {
    var next = theme === 'dark' ? 'light' : 'dark';
    button.setAttribute('aria-label', 'Switch to ' + next + ' theme');
  }

  updateButton(root.dataset.theme || 'light');

  button.addEventListener('click', function () {
    var current = root.dataset.theme || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;

    try {
      localStorage.setItem('qz-theme', next);
    } catch (error) {}

    updateButton(next);
  });
}());

(function () {
  var venues = Array.from(document.querySelectorAll('.publication__venue'));
  var rows = venues.map(function (venue) {
    return {
      venue: venue,
      text: venue.querySelector('.publication__venue-text'),
      links: venue.querySelector('.publication__links')
    };
  }).filter(function (row) {
    return row.text && row.links;
  });
  if (!rows.length) return;

  var frame;

  function alignLinks() {
    frame = null;
    // Measure natural inline wrapping before adding any alignment space.
    rows.forEach(function (row) {
      row.links.style.removeProperty('--publication-link-offset');
    });
    var offsets = rows.map(function (row) {
      var range = document.createRange();
      range.selectNodeContents(row.text);
      var lines = range.getClientRects();
      var lastLine = lines[lines.length - 1];
      var links = row.links.getBoundingClientRect();
      var sharesLine = lastLine && links.top < lastLine.bottom
        && links.bottom > lastLine.top;
      // Leave half a pixel for fractional layout rounding at the right edge.
      return sharesLine
        ? Math.max(0, row.venue.getBoundingClientRect().right - links.right - 0.5)
        : 0;
    });
    rows.forEach(function (row, index) {
      row.links.style.setProperty('--publication-link-offset', offsets[index] + 'px');
    });
  }

  function scheduleAlignment() {
    if (!frame) frame = requestAnimationFrame(alignLinks);
  }

  window.addEventListener('resize', scheduleAlignment);
  if (typeof ResizeObserver === 'function') {
    var observer = new ResizeObserver(scheduleAlignment);
    rows.forEach(function (row) { observer.observe(row.venue); });
  }
  if (document.fonts) document.fonts.ready.then(scheduleAlignment);
  scheduleAlignment();
}());

(function () {
  var link = document.querySelector('[data-wechat-open]');
  var dialog = document.querySelector('#wechat-dialog');
  if (!link || !dialog || typeof dialog.showModal !== 'function') return;

  link.setAttribute('aria-haspopup', 'dialog');
  link.setAttribute('aria-controls', dialog.id);

  link.addEventListener('click', function (event) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    dialog.showModal();
  });

  dialog.addEventListener('click', function (event) {
    if (event.target !== dialog) return;
    var bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right
        || event.clientY < bounds.top || event.clientY > bounds.bottom) {
      dialog.close();
    }
  });
}());
