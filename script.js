// Без JavaScript ссылки и описания проектов тоже работают.
// Кнопку мобильного меню показываем, только когда её обработчики готовы.
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#main-nav');
const navigationLinks = [...navigation.querySelectorAll('a')];
const mobileScreen = window.matchMedia('(max-width: 760px)');

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

navigationLinks.forEach((link) => {
  link.addEventListener('click', () => {
    closeMenu();
    // На телефоне переносим фокус из закрытого меню в выбранный раздел.
    if (mobileScreen.matches) {
      const section = document.querySelector(link.hash);
      section.setAttribute('tabindex', '-1');
      section.focus({ preventScroll: true });
    }
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
    closeMenu(true);
  }
});

document.addEventListener('click', (event) => {
  if (!event.target.closest('.site-header')) closeMenu();
});

mobileScreen.addEventListener('change', () => closeMenu());
menuButton.hidden = false;
document.documentElement.classList.add('js');

// Подсвечиваем раздел, который сейчас виден под фиксированной шапкой.
const sections = [...document.querySelectorAll('main > section[id]')];
let scrollScheduled = false;

function updateActiveLink() {
  let activeSection = sections[0];
  const headerHeight = document.querySelector('.site-header').offsetHeight;
  for (const section of sections) {
    if (section.getBoundingClientRect().top <= headerHeight + 80) activeSection = section;
  }
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
    activeSection = sections[sections.length - 1];
  }
  navigationLinks.forEach((link) => {
    if (link.hash === `#${activeSection.id}`) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
  scrollScheduled = false;
}

window.addEventListener('scroll', () => {
  if (!scrollScheduled) {
    scrollScheduled = true;
    window.requestAnimationFrame(updateActiveLink);
  }
}, { passive: true });
window.addEventListener('resize', updateActiveLink);
updateActiveLink();

// Год в подвале обновляется автоматически.
document.querySelector('#year').textContent = new Date().getFullYear();
