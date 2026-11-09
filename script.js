// Общее меню. Без JavaScript ссылки остаются открытыми.
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#main-nav');
const mobileScreen = window.matchMedia('(max-width: 760px)');

if (menuButton && navigation) {
  function closeMenu(returnFocus = false) {
    navigation.classList.remove('is-open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.querySelector('.menu-label').textContent = 'Меню';
    if (returnFocus) menuButton.focus();
  }

  menuButton.addEventListener('click', () => {
    const isOpen = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(isOpen));
    menuButton.querySelector('.menu-label').textContent = isOpen ? 'Закрыть' : 'Меню';
    navigation.classList.toggle('is-open', isOpen);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') closeMenu(true);
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.site-header')) closeMenu();
  });
  document.querySelector('.site-header').addEventListener('focusout', () => {
    window.requestAnimationFrame(() => {
      if (!document.activeElement.closest('.site-header')) closeMenu();
    });
  });
  mobileScreen.addEventListener('change', () => {
    const focusWasInMenu = navigation.contains(document.activeElement);
    closeMenu(mobileScreen.matches && focusWasInMenu);
  });
  menuButton.hidden = false;
  document.documentElement.classList.add('js');
}

document.querySelectorAll('[data-year]').forEach((element) => {
  element.textContent = new Date().getFullYear();
});

// Фильтры работают только на странице портфолио; остальные страницы не затрагиваются.
const portfolio = document.querySelector('[data-portfolio]');
if (portfolio) {
  const filters = portfolio.querySelector('.portfolio-filters');
  const filterButtons = [...filters.querySelectorAll('[data-filter]')];
  const projectCards = [...portfolio.querySelectorAll('[data-category]')];
  const resultStatus = portfolio.querySelector('#portfolio-status');

  function filterProjects(selectedButton) {
    const category = selectedButton.dataset.filter;
    let visibleCount = 0;

    projectCards.forEach((card) => {
      const isVisible = category === 'all' || card.dataset.category === category;
      card.hidden = !isVisible;
      if (isVisible) visibleCount += 1;
    });

    filterButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button === selectedButton));
    });
    resultStatus.textContent = `Показано проектов: ${visibleCount} из ${projectCards.length}. Категория: ${selectedButton.textContent.trim()}.`;
  }

  // Нативные кнопки поддерживают Tab, Enter и пробел без отдельных обработчиков клавиш.
  filterButtons.forEach((button) => {
    button.addEventListener('click', () => filterProjects(button));
  });
  filterProjects(filterButtons[0]);
  filters.hidden = false;
}

// Учебные цены калькулятора. Суммы считаются в рублях, без округлений.
const PROJECT_PRICES = {
  landing: { name: 'Лендинг', price: 35000 },
  corporate: { name: 'Корпоративный сайт', price: 80000 },
  design: { name: 'Дизайн интерфейса', price: 30000 },
  layout: { name: 'Адаптивная вёрстка', price: 25000 },
  redesign: { name: 'Редизайн', price: 45000 },
};
const EXTRA_PRICES = {
  animations: { name: 'Анимации', price: 10000 },
  form: { name: 'Контактная форма', price: 5000 },
  seo: { name: 'Расширенное SEO', price: 12000 },
};
const ADDITIONAL_PAGE_PRICE = 5000;
const rubles = new Intl.NumberFormat('ru-RU', {
  style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
});

function calculateEstimate(projectId, pageCount, extraIds) {
  if (!Object.hasOwn(PROJECT_PRICES, projectId)
    || !Number.isInteger(pageCount) || pageCount < 1 || pageCount > 15) return null;

  const project = PROJECT_PRICES[projectId];
  // Учитываем только известные опции, каждую — один раз.
  const extras = Object.keys(EXTRA_PRICES).filter((id) => extraIds.includes(id));
  const additionalPagesPrice = (pageCount - 1) * ADDITIONAL_PAGE_PRICE;
  const extrasPrice = extras.reduce((sum, id) => sum + EXTRA_PRICES[id].price, 0);

  return {
    projectId, project, pageCount, extras, additionalPagesPrice,
    total: project.price + additionalPagesPrice + extrasPrice,
  };
}

function estimateLineItems(estimate) {
  return [
    { name: `${estimate.project.name} — базовая цена`, price: estimate.project.price },
    { name: `Доп. страницы (${estimate.pageCount - 1} × ${rubles.format(ADDITIONAL_PAGE_PRICE)})`, price: estimate.additionalPagesPrice },
    ...estimate.extras.map((id) => EXTRA_PRICES[id]),
  ];
}

// Книжка перелистывает по одной странице к последнему значению ползунка.
// Быстрые движения меняют цель, не накапливая очередь устаревших перелистываний.
function createPageBook(book, initialPage) {
  if (!book) return () => {};

  const spread = book.querySelector('.book-spread');
  const number = book.querySelector('[data-book-number]');
  const leaf = book.querySelector('.book-leaf');
  const leafNumber = book.querySelector('[data-book-leaf-number]');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let currentPage = initialPage;
  let targetPage = initialPage;
  let animation = null;

  function paintPage() {
    number.textContent = String(currentPage).padStart(2, '0');
    spread.dataset.bookPage = String(currentPage);
  }

  function turnNextPage() {
    if (animation || currentPage === targetPage) return;
    const forward = targetPage > currentPage;
    const nextPage = currentPage + (forward ? 1 : -1);
    leafNumber.textContent = String(forward ? currentPage : nextPage).padStart(2, '0');
    leaf.hidden = false;
    animation = leaf.animate([
      { transform: forward ? 'rotateY(0deg)' : 'rotateY(-180deg)' },
      { transform: forward ? 'rotateY(-180deg)' : 'rotateY(0deg)' },
    ], { duration: 180, easing: 'cubic-bezier(.45, 0, .2, 1)', fill: 'forwards' });

    const activeAnimation = animation;
    activeAnimation.onfinish = () => {
      if (animation !== activeAnimation) return;
      animation = null;
      leaf.hidden = true;
      activeAnimation.cancel();
      currentPage = nextPage;
      paintPage();
      turnNextPage();
    };
  }

  function showPage(page, animate = true) {
    targetPage = page;
    if (!animate || reducedMotion.matches || typeof leaf.animate !== 'function') {
      const previousAnimation = animation;
      animation = null;
      if (previousAnimation) previousAnimation.cancel();
      leaf.hidden = true;
      currentPage = targetPage;
      paintPage();
      return;
    }
    turnNextPage();
  }

  reducedMotion.addEventListener('change', () => showPage(targetPage, false));
  paintPage();
  return showPage;
}

const calculatorForm = document.querySelector('#calculator-form');
if (calculatorForm) {
  const pageCount = calculatorForm.querySelector('#page-count');
  const pageCountOutput = calculatorForm.querySelector('#page-count-output');
  const breakdown = document.querySelector('#estimate-breakdown');
  const total = document.querySelector('#estimate-total');
  const discussLink = document.querySelector('#discuss-estimate');
  const bookButtons = [...calculatorForm.querySelectorAll('[data-book-step]')];
  const updateBook = createPageBook(calculatorForm.querySelector('[data-page-book]'), Number(pageCount.value));

  function updateEstimate(animateBook = true) {
    const projectId = calculatorForm.querySelector('[name="project"]:checked').value;
    const extras = [...calculatorForm.querySelectorAll('[name="extra"]:checked')].map((input) => input.value);
    const estimate = calculateEstimate(projectId, Number(pageCount.value), extras);
    if (!estimate) return;

    pageCountOutput.value = String(estimate.pageCount);
    updateBook(estimate.pageCount, animateBook);
    bookButtons.forEach((button) => {
      button.disabled = Number(button.dataset.bookStep) < 0
        ? estimate.pageCount <= Number(pageCount.min)
        : estimate.pageCount >= Number(pageCount.max);
    });
    total.value = rubles.format(estimate.total);
    const rows = estimateLineItems(estimate).map((item) => {
      const row = document.createElement('div');
      const label = document.createElement('dt');
      const price = document.createElement('dd');
      label.textContent = item.name;
      price.textContent = rubles.format(item.price);
      row.append(label, price);
      return row;
    });
    breakdown.replaceChildren(...rows);

    const params = new URLSearchParams({
      source: 'calculator', project: estimate.projectId, pages: String(estimate.pageCount),
    });
    estimate.extras.forEach((id) => params.set(id, '1'));
    discussLink.setAttribute('href', `./contact.html?${params.toString()}`);
  }

  // Кнопки книги меняют тот же ползунок: единый расчёт, анимация и ссылка.
  bookButtons.forEach((button) => {
    button.addEventListener('click', () => {
      pageCount.stepUp(Number(button.dataset.bookStep));
      pageCount.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });
  calculatorForm.addEventListener('input', () => updateEstimate());
  calculatorForm.addEventListener('change', () => updateEstimate());
  calculatorForm.addEventListener('submit', (event) => event.preventDefault());
  // Событие reset приходит до восстановления исходных значений полей.
  calculatorForm.addEventListener('reset', () => window.setTimeout(() => updateEstimate(false), 0));
  updateEstimate(false);
  calculatorForm.querySelector('#calculator-controls').disabled = false;
}

// Параметры URL могут быть изменены вручную: сначала проверяем их.
function estimateFromSearch(params) {
  if (params.get('source') !== 'calculator') return null;
  const pages = params.get('pages') || '';
  if (!/^(?:[1-9]|1[0-5])$/.test(pages)) return null;

  const extras = [];
  for (const id of Object.keys(EXTRA_PRICES)) {
    const value = params.get(id);
    if (value !== null && value !== '0' && value !== '1') return null;
    if (value === '1') extras.push(id);
  }
  return calculateEstimate(params.get('project'), Number(pages), extras);
}

function estimateMessage(estimate) {
  return [
    'Здравствуйте! Хочу обсудить проект по расчёту из калькулятора.',
    `Тип проекта: ${estimate.project.name}.`,
    `Количество страниц: ${estimate.pageCount}.`,
    '',
    'Расшифровка:',
    ...estimateLineItems(estimate).map((item) => `${item.name}: ${rubles.format(item.price)}.`),
    ...(estimate.extras.length === 0 ? ['Дополнительные опции: не выбраны.'] : []),
    `Ориентировочная стоимость: ${rubles.format(estimate.total)}.`,
    'Цены и надбавки учебные; расчёт не является коммерческим предложением.',
    '',
    'Дополнительно о проекте:',
  ].join('\n');
}

// ID задаётся в contact.html. До подключения данные никуда не отправляются.
const contactForm = document.querySelector('#contact-form');
if (contactForm) {
  const importedEstimate = estimateFromSearch(new URLSearchParams(window.location.search));
  const message = contactForm.querySelector('[name="message"]');
  // Не перезаписываем уже введённое или восстановленное браузером сообщение.
  if (importedEstimate && message && !message.value) {
    message.value = estimateMessage(importedEstimate);
    document.querySelector('#estimate-prefill-note').hidden = false;
  }

  const formId = contactForm.dataset.formspreeId.trim();
  const isConfigured = /^[a-zA-Z0-9]+$/.test(formId);
  const status = document.querySelector('#form-status');
  const note = document.querySelector('#form-note');

  if (isConfigured) {
    contactForm.action = `https://formspree.io/f/${encodeURIComponent(formId)}`;
    note.textContent = 'При отправке имя, email и сообщение будут переданы сервису Formspree для обработки заявки. Подтверждение отправки покажет сам сервис.';
  }

  contactForm.querySelector('button[type="submit"]').disabled = false;
  contactForm.addEventListener('submit', (event) => {
    if (!isConfigured) {
      event.preventDefault();
      status.textContent = 'Сообщение не отправлено: форма пока не подключена. Владельцу сайта нужно указать свой идентификатор Formspree в contact.html.';
    }
    // После подключения — обычная HTML-отправка POST и переход в Formspree.
    // Результат покажет сам сервис; сайт не обещает успех заранее.
  });
}
