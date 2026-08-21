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

