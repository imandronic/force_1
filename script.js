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

// ID задаётся в contact.html. До подключения данные никуда не отправляются.
const contactForm = document.querySelector('#contact-form');
if (contactForm) {
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
