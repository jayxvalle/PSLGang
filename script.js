document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.nav-links a');
  const sections = Array.from(document.querySelectorAll('section[id]'));
  const backToTop = document.querySelector('.back-to-top');

  const setActive = () => {
    const offset = window.scrollY + 120;
    const active = sections.findLast(section => section.offsetTop <= offset);
    links.forEach(link => {
      if (active && link.getAttribute('href') === `#${active.id}`) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  };

  links.forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  window.addEventListener('scroll', () => {
    setActive();
    if (backToTop) {
      backToTop.classList.toggle('visible', window.scrollY > 320);
    }
  });

  backToTop?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  setActive();
});
