/* ═══════════════════════════════════════════════════
   Pardus Lock System — Ana JavaScript Dosyası
   ═══════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Navbar scroll efekti ── */
  const navbar = document.querySelector('.navbar');
  const onScroll = () => {
    if (window.scrollY > 20) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ── Mobile menu ── */
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
    // Linklere tıklayınca kapat
    navLinks.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        toggle.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  /* ── Active nav link (scroll spy) ── */
  const sections = document.querySelectorAll('section[id], div[id]');
  const navAnchors = document.querySelectorAll('.nav-links a[href^="#"]');
  const observerNav = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        navAnchors.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id);
        });
      }
    });
  }, { rootMargin: '-40% 0px -55% 0px' });
  sections.forEach(s => observerNav.observe(s));

  /* ── Scroll reveal ── */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        // Kademeli gecikme: aynı parent'taki kardeşler için
        const siblings = Array.from(e.target.parentElement.children).filter(
          c => c.classList.contains('reveal') || c.classList.contains('reveal-left') || c.classList.contains('reveal-right')
        );
        const idx = siblings.indexOf(e.target);
        setTimeout(() => {
          e.target.classList.add('visible');
        }, idx * 90);
        revealObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => {
    revealObserver.observe(el);
  });

  /* ── Stats sayaç animasyonu ── */
  const statNums = document.querySelectorAll('.stat-num[data-target]');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const target = parseFloat(el.dataset.target);
      const suffix = el.dataset.suffix || '';
      const duration = 1200;
      const start = performance.now();
      const isFloat = String(target).includes('.');

      const tick = (now) => {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = target * eased;
        el.textContent = (isFloat ? current.toFixed(1) : Math.floor(current)) + suffix;
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      counterObserver.unobserve(el);
    });
  }, { threshold: 0.5 });
  statNums.forEach(el => counterObserver.observe(el));

  /* ── Smooth scroll for anchor links ── */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const offset = 72;
      window.scrollTo({
        top: target.getBoundingClientRect().top + window.scrollY - offset,
        behavior: 'smooth'
      });
    });
  });

  /* ── İletişim formu ── */
  const form = document.getElementById('contactForm');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Gönderiliyor...';

      const payload = {
        name:    form.querySelector('[name="name"]').value.trim(),
        email:   form.querySelector('[name="email"]').value.trim(),
        role:    (form.querySelector('[name="role"]') || {}).value || '',
        subject: form.querySelector('[name="subject"]').value,
        school:  (form.querySelector('[name="school"]') || {}).value || '',
        message: form.querySelector('[name="message"]').value.trim(),
      };

      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
        clearTimeout(timeout);
        const data = await res.json();
        const successEl = document.getElementById('formSuccess');
        const errorEl   = document.getElementById('formError');
        if (res.ok && data.status === 'ok') {
          if (successEl) { successEl.style.display = 'block'; setTimeout(() => { successEl.style.display = 'none'; }, 5000); }
          form.reset();
        } else {
          if (errorEl) { errorEl.style.display = 'block'; setTimeout(() => { errorEl.style.display = 'none'; }, 5000); }
        }
      } catch {
        const errorEl = document.getElementById('formError');
        if (errorEl) { errorEl.style.display = 'block'; setTimeout(() => { errorEl.style.display = 'none'; }, 5000); }
      }

      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> Mesajı Gönder`;
    });
  }

  /* ── Nav versiyon badge ── */
  fetch('/api/version')
    .then(r => r.json())
    .then(data => {
      if (data.version) {
        document.querySelectorAll('.badge-open').forEach(el => {
          el.textContent = 'v' + data.version;
        });
      }
    })
    .catch(() => { /* sessizce geç */ });

  /* ── Aktif sayfa nav linkini işaretle ── */
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href && href.includes(currentPage)) {
      a.classList.add('active');
    }
  });


});
