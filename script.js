document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');

  if (toggle && nav) {
    const setOpen = (open) => {
      nav.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', String(open));
    };

    toggle.addEventListener('click', () => {
      setOpen(!nav.classList.contains('open'));
    });

    nav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => setOpen(false));
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') setOpen(false);
    });

    document.addEventListener('click', event => {
      if (window.innerWidth <= 700 &&
          nav.classList.contains('open') &&
          !nav.contains(event.target) &&
          event.target !== toggle) {
        setOpen(false);
      }
    });

    window.addEventListener('resize', () => {
      if (window.innerWidth > 700) setOpen(false);
    });
  }

  document.querySelectorAll('.repair-toc').forEach(toc => {
    const btn = toc.querySelector('.repair-toc-toggle');
    if (btn) btn.addEventListener('click', () => toc.classList.toggle('open'));

    const links = [...toc.querySelectorAll('a[data-target]')];
    const sections = links.map(a => document.getElementById(a.dataset.target)).filter(Boolean);
    if (!sections.length) return;

    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          links.forEach(a => a.classList.toggle('active', a.dataset.target === entry.target.id));
        }
      });
    }, { rootMargin: '-18% 0px -68% 0px', threshold: 0 });

    sections.forEach(section => obs.observe(section));
    links.forEach(a => a.addEventListener('click', () => {
      if (window.innerWidth <= 900) toc.classList.remove('open');
    }));
  });

  // Botones "Copiar" usados en la biblioteca MikroTik.
  document.querySelectorAll('.copy-inline, .copy-code').forEach(button => {
    button.addEventListener('click', async () => {
      const code = button.parentElement?.querySelector('code');
      if (!code) return;

      try {
        await navigator.clipboard.writeText(code.textContent.trim());
        const original = button.textContent;
        button.textContent = 'Copiado';
        button.classList.add('copied');
        setTimeout(() => {
          button.textContent = original;
          button.classList.remove('copied');
        }, 1400);
      } catch {
        button.textContent = 'No disponible';
        setTimeout(() => { button.textContent = 'Copiar'; }, 1400);
      }
    });
  });
});
