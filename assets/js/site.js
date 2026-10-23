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
