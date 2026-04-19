'use strict';

/* ═══════════════════════════════════════════════
   STICKY NAV — add .scrolled at 80px
═══════════════════════════════════════════════ */
const header = document.getElementById('header');

window.addEventListener('scroll', () => {
  header.classList.toggle('scrolled', window.scrollY > 80);
}, { passive: true });

/* ═══════════════════════════════════════════════
   HAMBURGER MENU
═══════════════════════════════════════════════ */
const hamburger     = document.getElementById('hamburger');
const mobileOverlay = document.getElementById('mobile-overlay');
const mobileLinks   = document.querySelectorAll('.mobile-link');

function closeMobileMenu() {
  hamburger.classList.remove('open');
  mobileOverlay.classList.remove('open');
  document.body.style.overflow = '';
}

hamburger.addEventListener('click', () => {
  const isOpen = hamburger.classList.toggle('open');
  mobileOverlay.classList.toggle('open', isOpen);
  document.body.style.overflow = isOpen ? 'hidden' : '';
});

mobileLinks.forEach(link => link.addEventListener('click', closeMobileMenu));

// Close on overlay click (outside nav)
mobileOverlay.addEventListener('click', (e) => {
  if (e.target === mobileOverlay) closeMobileMenu();
});

/* ═══════════════════════════════════════════════
   SMOOTH SCROLL — offset for fixed header
═══════════════════════════════════════════════ */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const href = this.getAttribute('href');
    if (!href || href === '#') return;
    const target = document.querySelector(href);
    if (!target) return;
    e.preventDefault();
    const offset = 72;
    const top = target.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: 'smooth' });
  });
});

/* ═══════════════════════════════════════════════
   TAB SWITCHER
═══════════════════════════════════════════════ */
const tabBtns     = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    const target = document.getElementById('tab-' + btn.dataset.tab);
    if (target) target.classList.add('active');
  });
});

/* ═══════════════════════════════════════════════
   FORM VALIDATION
═══════════════════════════════════════════════ */
function validateForm(form) {
  let valid = true;
  form.querySelectorAll('[required]').forEach(field => {
    field.classList.remove('error');
    if (!field.value.trim()) {
      field.classList.add('error');
      valid = false;
    }
  });
  return valid;
}

function handleSubmit(form, successText) {
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!validateForm(this)) return;
    const btn = this.querySelector('button[type="submit"]');
    const original = btn.textContent;
    btn.textContent = successText;
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = original;
      btn.disabled = false;
      this.reset();
    }, 3500);
  });
}

handleSubmit(
  document.getElementById('skup-form'),
  'Wysłano! Skontaktujemy się wkrótce.'
);
handleSubmit(
  document.getElementById('kontakt-form'),
  'Wysłano! Odezwiemy się wkrótce.'
);

// Clear error state on interaction
document.querySelectorAll('input, select, textarea').forEach(field => {
  field.addEventListener('input',  () => field.classList.remove('error'));
  field.addEventListener('change', () => field.classList.remove('error'));
});
