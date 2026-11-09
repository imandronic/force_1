// Общее меню. Без JavaScript ссылки остаются открытыми.
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#main-nav');
const mobileScreen = window.matchMedia('(max-width: 1024px)');

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

// Для старых браузеров без нативной группы details[name].
// Раскрытие и клавиатура остаются нативными, без перехвата нажатий summary.
if (!('name' in document.createElement('details'))) {
  const serviceDetails = [...document.querySelectorAll('.service-details')];
  serviceDetails.forEach((details) => {
    details.addEventListener('toggle', () => {
      if (details.open) serviceDetails.forEach((other) => {
        if (other !== details) other.open = false;
      });
    });
  });
}

// Сохраняем место закрытой карточки, а раскрытый блок рисуем поверх сетки.
// Без JS карточки остаются в обычном потоке и полностью доступны.
function initServiceLayers() {
  const grid = document.querySelector('.services-grid');
  if (!grid) return;
  const cards = [...grid.querySelectorAll('.service-card')];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const duration = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-duration')) || 200;
  const layers = cards.map((card) => {
    const slot = document.createElement('div');
    slot.className = 'service-card-slot';
    card.before(slot);
    slot.append(card);
    return { card, slot, details: card.querySelector('.service-details'), closeTimer: null };
  });

  function measure({ card, slot, details }) {
    const summary = details.querySelector('summary');
    const style = getComputedStyle(details);
    const borders = (parseFloat(style.borderTopWidth) || 0) + (parseFloat(style.borderBottomWidth) || 0);
    // Вычитаем только раскрываемое содержимое, включая промежуточные кадры.
    const closedHeight = Math.ceil(card.getBoundingClientRect().height
      - details.getBoundingClientRect().height + summary.getBoundingClientRect().height + borders);
    const value = `${closedHeight}px`;
    if (slot.style.getPropertyValue('--service-card-height') !== value) {
      slot.style.setProperty('--service-card-height', value);
    }
  }

  layers.forEach((layer) => {
    const { card, slot, details } = layer;
    measure(layer);
    details.addEventListener('toggle', () => {
      window.clearTimeout(layer.closeTimer);
      slot.classList.toggle('is-expanded', details.open);
      if (details.open) slot.classList.add('is-raised');
      else layer.closeTimer = window.setTimeout(() => {
        if (!details.open) slot.classList.remove('is-raised');
      }, reducedMotion.matches ? 0 : duration);
    });
    // При Tab за пределы карточки закрываем перекрытие над новым фокусом.
    card.addEventListener('focusout', () => window.requestAnimationFrame(() => {
      if (details.open && !card.contains(document.activeElement)) details.open = false;
    }));
  });
  grid.classList.add('is-layered');
  if (typeof ResizeObserver === 'function') {
    const byCard = new Map(layers.map((layer) => [layer.card, layer]));
    const observer = new ResizeObserver((entries) => entries.forEach((entry) => measure(byCard.get(entry.target))));
    layers.forEach(({ card }) => observer.observe(card));
  }
  window.addEventListener('resize', () => layers.forEach(measure));
  grid.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const expanded = layers.find(({ details }) => details.open);
    if (expanded) {
      expanded.details.open = false;
      expanded.details.querySelector('summary').focus();
      event.preventDefault();
    }
  });
  document.addEventListener('click', (event) => {
    layers.forEach(({ card, details }) => {
      if (details.open && !card.contains(event.target)) details.open = false;
    });
  });
}
initServiceLayers();

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

// Журнал: категория и все слова запроса должны совпасть одновременно.
const blog = document.querySelector('[data-blog]');
if (blog) {
  const controls = blog.querySelector('#blog-controls');
  const search = controls.querySelector('#blog-search');
  const buttons = [...controls.querySelectorAll('[data-blog-filter]')];
  const status = blog.querySelector('#blog-status');
  const empty = blog.querySelector('#blog-empty');
  let category = 'all';

  function normalizeBlogText(text) {
    return text.toLocaleLowerCase('ru-RU').replace(/ё/g, 'е').trim().replace(/\s+/g, ' ');
  }

  // Текст берётся прямо из карточек: нет второго списка статей в JavaScript.
  const entries = [...blog.querySelectorAll('[data-blog-category]')].map((card) => ({
    card,
    category: card.dataset.blogCategory,
    text: normalizeBlogText(`${card.querySelector('.journal-card-title').textContent} ${card.querySelector('.journal-card-description').textContent}`),
  }));

  function filterArticles() {
    const terms = normalizeBlogText(search.value).split(' ').filter(Boolean);
    let found = 0;
    entries.forEach((entry) => {
      const matchesCategory = category === 'all' || entry.category === category;
      const matchesSearch = terms.every((term) => entry.text.includes(term));
      entry.card.hidden = !(matchesCategory && matchesSearch);
      if (!entry.card.hidden) found += 1;
    });
    buttons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.blogFilter === category));
    });
    empty.hidden = found !== 0;
    status.textContent = `Найдено статей: ${found} из ${entries.length}.`;
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      category = button.dataset.blogFilter;
      filterArticles();
    });
  });
  search.addEventListener('input', filterArticles);
  // Enter в поиске не отправляет форму и не перезагружает страницу.
  controls.addEventListener('submit', (event) => {
    event.preventDefault();
    filterArticles();
  });
  controls.addEventListener('reset', () => {
    window.setTimeout(() => {
      category = 'all';
      filterArticles();
    }, 0);
  });
  filterArticles();
  controls.hidden = false;
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
  const turnDuration = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-book-duration')) || 180;
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
    ], { duration: turnDuration, easing: 'cubic-bezier(.45, 0, .2, 1)', fill: 'forwards' });

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
  // Принимаем только известный тип проекта, не подставляя URL в CSS-селектор.
  const requestedProject = new URLSearchParams(window.location.search).get('project');
  const initialProject = Object.hasOwn(PROJECT_PRICES, requestedProject) ? requestedProject : 'landing';
  calculatorForm.querySelectorAll('[name="project"]').forEach((input) => {
    // defaultChecked задаёт исходный вариант для нативного form.reset().
    input.defaultChecked = input.value === initialProject;
    input.checked = input.defaultChecked;
  });
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
  const params = new URLSearchParams(window.location.search);
  const importedEstimate = estimateFromSearch(params);
  const supportRequested = !params.has('source') && params.get('service') === 'support';
  const message = contactForm.querySelector('[name="message"]');
  // Не перезаписываем уже введённое или восстановленное браузером сообщение.
  if (message && !message.value) {
    if (importedEstimate) {
      message.value = estimateMessage(importedEstimate);
      message.setAttribute('aria-describedby', 'estimate-prefill-note');
      document.querySelector('#estimate-prefill-note').hidden = false;
    } else if (supportRequested) {
      // Это ежемесячная услуга, она не участвует в разовом расчёте.
      message.value = [
        'Здравствуйте! Хочу обсудить поддержку и развитие сайта.',
        'Ориентировочный бюджет — от 8 000 ₽ в месяц. Объём работ и условия хочу согласовать отдельно.',
        '',
        'Сайт и задачи поддержки:',
      ].join('\n');
      message.setAttribute('aria-describedby', 'support-prefill-note');
      document.querySelector('#support-prefill-note').hidden = false;
    }
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

// Декоративное появление: до инициализации ничего не скрываем.
// При отсутствии API, ошибке или reduced-motion содержимое читается сразу.
function initSectionReveal() {
  if (typeof window.IntersectionObserver !== 'function' || typeof Element.prototype.animate !== 'function') return;
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const activeAnimations = new Set();
  const duration = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-reveal-duration')) || 240;
  let observer;
  try {
    observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        // Не сдвигаем секцию, которую читатель уже прокрутил к верхнему краю.
        if (motionPreference.matches || entry.boundingClientRect.top < 64) return;
        try {
          const animation = entry.target.animate([
            { opacity: .85, transform: 'translateY(12px)' },
            { opacity: 1, transform: 'translateY(0)' },
          ], { duration, easing: 'ease-out' });
          activeAnimations.add(animation);
          const release = () => activeAnimations.delete(animation);
          animation.onfinish = release;
          animation.oncancel = release;
        } catch {
          // Это необязательный эффект: ошибка не меняет видимость или навигацию.
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px -32px 0px' });
    document.querySelectorAll('main > .section:not(.hero):not(.calculator-section):not(.journal-section):not(.portfolio-section):not(.contact-section) > .container').forEach((section) => observer.observe(section));
    motionPreference.addEventListener('change', () => {
      if (motionPreference.matches) activeAnimations.forEach((animation) => animation.cancel());
    });
  } catch {
    if (observer) observer.disconnect();
  }
}
initSectionReveal();
