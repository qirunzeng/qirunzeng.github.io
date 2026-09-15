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
  var game = document.querySelector('[data-bandit]');
  if (!game) return;

  var setup = game.querySelector('[data-bandit-setup]');
  var roundsInput = game.querySelector('[data-bandit-rounds]');
  var armButtons = Array.prototype.slice.call(game.querySelectorAll('[data-bandit-arm]'));
  var roundOutput = game.querySelector('[data-bandit-round]');
  var rewardOutput = game.querySelector('[data-bandit-reward]');
  var regretOutput = game.querySelector('[data-bandit-regret]');
  var progress = game.querySelector('[data-bandit-progress]');
  var feedback = game.querySelector('[data-bandit-feedback]');
  var history = game.querySelector('[data-bandit-history]');
  var state;

  function plural(value, word) {
    return value + ' ' + word + (value === 1 ? '' : 's');
  }

  function boundedRounds() {
    var value = Number.parseInt(roundsInput.value, 10);
    if (!Number.isFinite(value)) value = 10;
    value = Math.min(100, Math.max(1, value));
    roundsInput.value = value;
    return value;
  }

  function hiddenProbabilities() {
    var stronger = 0.64 + Math.random() * 0.21;
    var weaker = 0.22 + Math.random() * 0.25;
    return Math.random() < 0.5
      ? { a: stronger, b: weaker }
      : { a: weaker, b: stronger };
  }

  function armElement(selector, arm) {
    return game.querySelector('[' + selector + '="' + arm + '"]');
  }

  function render() {
    var finished = state.round >= state.rounds;
    roundOutput.textContent = state.round + ' / ' + state.rounds;
    rewardOutput.textContent = state.reward;
    regretOutput.textContent = finished ? state.regret.toFixed(2) : 'hidden';
    progress.style.width = ((state.round / state.rounds) * 100) + '%';

    ['a', 'b'].forEach(function (arm) {
      armElement('data-bandit-pulls', arm).textContent = plural(state.pulls[arm], 'pull');
      armElement('data-bandit-wins', arm).textContent = plural(state.wins[arm], 'reward');
      armElement('data-bandit-chance', arm).textContent = finished
        ? Math.round(state.probabilities[arm] * 100) + '% true probability'
        : 'probability hidden';
    });
  }

  function finishGame() {
    var bestArm = state.probabilities.a > state.probabilities.b ? 'a' : 'b';
    var otherArm = bestArm === 'a' ? 'b' : 'a';
    var bestButton = armElement('data-bandit-arm', bestArm);

    game.classList.add('is-finished');
    bestButton.classList.add('is-best');
    armButtons.forEach(function (button) {
      var arm = button.getAttribute('data-bandit-arm');
      button.disabled = true;
      button.setAttribute(
        'aria-label',
        'Arm ' + arm.toUpperCase() + ': '
          + Math.round(state.probabilities[arm] * 100) + '% true probability'
          + (arm === bestArm ? ', better arm' : '')
      );
    });

    feedback.textContent = 'Arm ' + bestArm.toUpperCase() + ' was stronger ('
      + Math.round(state.probabilities[bestArm] * 100) + '% vs '
      + Math.round(state.probabilities[otherArm] * 100) + '%). You chose it '
      + state.pulls[bestArm] + ' of ' + state.rounds + ' times and earned '
      + plural(state.reward, 'reward') + '.';
  }

  function addHistoryToken(arm, reward) {
    var token = document.createElement('li');
    token.textContent = arm.toUpperCase() + (reward ? '+1' : '·');
    token.title = 'Round ' + state.round + ': arm ' + arm.toUpperCase()
      + (reward ? ' returned one reward' : ' returned no reward');
    if (reward) token.classList.add('is-reward');
    history.appendChild(token);
  }

  function pull(arm) {
    if (state.round >= state.rounds) return;

    var reward = Math.random() < state.probabilities[arm] ? 1 : 0;
    var bestProbability = Math.max(state.probabilities.a, state.probabilities.b);
    state.round += 1;
    state.reward += reward;
    state.pulls[arm] += 1;
    state.wins[arm] += reward;
    state.regret += bestProbability - state.probabilities[arm];

    addHistoryToken(arm, reward);
    render();

    if (state.round >= state.rounds) {
      finishGame();
    } else {
      var remaining = state.rounds - state.round;
      feedback.textContent = reward
        ? 'Arm ' + arm.toUpperCase() + ' paid out. +' + reward + ' reward; ' + plural(remaining, 'round') + ' left.'
        : 'No reward from arm ' + arm.toUpperCase() + ' this time; ' + plural(remaining, 'round') + ' left.';
    }
  }

  function newGame(shouldFocus) {
    state = {
      rounds: boundedRounds(),
      round: 0,
      reward: 0,
      regret: 0,
      probabilities: hiddenProbabilities(),
      pulls: { a: 0, b: 0 },
      wins: { a: 0, b: 0 }
    };

    game.classList.remove('is-finished');
    armButtons.forEach(function (button) {
      var arm = button.getAttribute('data-bandit-arm');
      button.disabled = false;
      button.classList.remove('is-best');
      button.setAttribute('aria-label', 'Pull arm ' + arm.toUpperCase());
    });
    history.replaceChildren();
    feedback.textContent = 'Choose an arm to begin. The probabilities stay fixed for this game.';
    render();
    if (shouldFocus) armButtons[0].focus();
  }

  setup.addEventListener('submit', function (event) {
    event.preventDefault();
    newGame(true);
  });

  armButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      pull(button.getAttribute('data-bandit-arm'));
    });
  });

  game.addEventListener('keydown', function (event) {
    if (event.target === roundsInput || event.metaKey || event.ctrlKey || event.altKey) return;
    var arm = event.key.toLowerCase();
    if ((arm === 'a' || arm === 'b') && state.round < state.rounds) {
      event.preventDefault();
      pull(arm);
    }
  });

  newGame(false);
}());
