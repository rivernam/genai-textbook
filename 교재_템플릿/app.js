// 교재 화면 동작: 화면 밝기, 목차, 탭, 코드 복사, 찾기.
(function () {
  var root = document.documentElement;

  // 화면 밝기. 기억해 둔 값이 없으면 기기 설정을 따른다.
  var themeButton = document.querySelector('.theme');
  function stored() { try { return localStorage.getItem('theme'); } catch (e) { return null; } }
  function setTheme(name) {
    root.setAttribute('data-theme', name);
    themeButton.textContent = name === 'dark' ? '밝은 화면' : '어두운 화면';
  }
  setTheme(stored() || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  themeButton.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('theme', next); } catch (e) { /* 저장하지 못해도 화면은 바뀐다 */ }
  });

  // 본문 폭. 기본은 읽기 편한 폭, "넓게 보기"는 표와 코드를 넓게 본다.
  var widthButton = document.querySelector('.width');
  function setWidth(name) {
    root.setAttribute('data-width', name);
    widthButton.textContent = name === 'wide' ? '기본 폭으로' : '넓게 보기';
  }
  var savedWidth = null;
  try { savedWidth = localStorage.getItem('width'); } catch (e) { /* 무시 */ }
  setWidth(savedWidth === 'wide' ? 'wide' : 'normal');
  widthButton.addEventListener('click', function () {
    var next = root.getAttribute('data-width') === 'wide' ? 'normal' : 'wide';
    setWidth(next);
    try { localStorage.setItem('width', next); } catch (e) { /* 저장하지 못해도 화면은 바뀐다 */ }
  });

  // 좁은 화면의 목차 열고 닫기
  var side = document.getElementById('side');
  var menu = document.querySelector('.menu');
  menu.addEventListener('click', function () {
    var open = side.classList.toggle('open');
    menu.setAttribute('aria-expanded', open);
  });
  side.addEventListener('click', function (event) {
    if (event.target.closest('a')) { side.classList.remove('open'); menu.setAttribute('aria-expanded', false); }
  });

  // 이어진 탭을 한 묶음으로 만든다
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  tabs.forEach(function (tab) {
    if (tab.classList.contains('ready')) return;
    var group = [tab];
    var next = tab.nextElementSibling;
    while (next && next.classList.contains('tab')) { group.push(next); next = next.nextElementSibling; }
    var wrap = document.createElement('div');
    wrap.className = 'tabs';
    var list = document.createElement('div');
    list.className = 'tablist';
    list.setAttribute('role', 'tablist');
    tab.parentNode.insertBefore(wrap, tab);
    wrap.appendChild(list);
    group.forEach(function (panel, index) {
      panel.classList.add('ready');
      var button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('role', 'tab');
      button.textContent = panel.getAttribute('data-tab');
      button.addEventListener('click', function () { choose(panel.getAttribute('data-tab')); });
      list.appendChild(button);
      wrap.appendChild(panel);
      panel.hidden = index !== 0;
      button.setAttribute('aria-selected', index === 0);
    });
  });
  // 탭 하나를 고르면 같은 이름의 탭이 쪽 전체에서 함께 바뀐다
  function choose(name) {
    document.querySelectorAll('.tabs').forEach(function (wrap) {
      var panels = wrap.querySelectorAll(':scope > .tab');
      var has = Array.prototype.some.call(panels, function (p) { return p.getAttribute('data-tab') === name; });
      if (!has) return;
      panels.forEach(function (p) { p.hidden = p.getAttribute('data-tab') !== name; });
      wrap.querySelectorAll('.tablist button').forEach(function (b) {
        b.setAttribute('aria-selected', b.textContent === name);
      });
    });
    try { localStorage.setItem('tab', name); } catch (e) { /* 무시 */ }
  }
  try { var savedTab = localStorage.getItem('tab'); if (savedTab) choose(savedTab); } catch (e) { /* 무시 */ }

  // 코드 복사 단추
  document.querySelectorAll('.codehilite').forEach(function (block) {
    if (block.closest('.result') || !navigator.clipboard) return;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy';
    button.textContent = '복사';
    button.addEventListener('click', function () {
      navigator.clipboard.writeText(block.querySelector('pre').innerText).then(function () {
        button.textContent = '복사했습니다';
        setTimeout(function () { button.textContent = '복사'; }, 1500);
      });
    });
    block.appendChild(button);
  });

  // 지금 읽는 절을 목차에 표시한다
  var links = {};
  document.querySelectorAll('.toc a').forEach(function (a) { links[decodeURIComponent(a.hash.slice(1))] = a; });
  var headings = Array.prototype.slice.call(document.querySelectorAll('main h1[id], main h2[id], main h3[id]'));
  function mark() {
    var current = headings[0];
    headings.forEach(function (h) { if (h.getBoundingClientRect().top < 120) current = h; });
    Object.keys(links).forEach(function (id) { links[id].classList.remove('now'); });
    if (current && links[current.id]) links[current.id].classList.add('now');
  }
  window.addEventListener('scroll', mark, { passive: true });
  mark();

  // 이 쪽에서 찾기: 절 단위로 찾아 목차 자리에 보여 준다
  var input = document.querySelector('.search input');
  var hits = document.querySelector('.hits');
  var toc = document.querySelector('.toc');
  var sections = headings.map(function (h) {
    var text = '';
    var node = h.nextElementSibling;
    while (node && !/^H[123]$/.test(node.tagName)) { text += ' ' + node.textContent; node = node.nextElementSibling; }
    return { id: h.id, title: h.childNodes[0].textContent.trim(), text: (h.textContent + text).toLowerCase(), raw: text };
  });
  input.addEventListener('input', function () {
    var query = input.value.trim().toLowerCase();
    if (!query) { hits.hidden = true; toc.hidden = false; return; }
    var found = sections.filter(function (s) { return s.text.indexOf(query) !== -1; });
    hits.textContent = '';
    var summary = document.createElement('p');
    summary.textContent = found.length ? '찾은 절 ' + found.length + '개' : '찾는 내용이 없습니다. 다른 낱말로 찾아 보세요.';
    hits.appendChild(summary);
    found.forEach(function (s) {
      var a = document.createElement('a');
      a.href = '#' + s.id;
      a.textContent = s.title;
      var at = s.raw.toLowerCase().indexOf(query);
      if (at !== -1) {
        var small = document.createElement('small');
        small.textContent = '…' + s.raw.slice(Math.max(0, at - 20), at + 40).replace(/\s+/g, ' ') + '…';
        a.appendChild(small);
      }
      hits.appendChild(a);
    });
    hits.hidden = false;
    toc.hidden = true;
  });
})();
