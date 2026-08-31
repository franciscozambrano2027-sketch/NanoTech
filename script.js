document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  if (toggle && nav) { toggle.addEventListener('click', () => { const open=nav.classList.toggle('open'); toggle.setAttribute('aria-expanded',String(open)); }); }
  document.querySelectorAll('.repair-toc').forEach(toc=>{
    const btn=toc.querySelector('.repair-toc-toggle');
    if(btn) btn.addEventListener('click',()=>toc.classList.toggle('open'));
    const links=[...toc.querySelectorAll('a[data-target]')];
    const sections=links.map(a=>document.getElementById(a.dataset.target)).filter(Boolean);
    if(!sections.length) return;
    const obs=new IntersectionObserver(entries=>{
      entries.forEach(e=>{ if(e.isIntersecting){ links.forEach(a=>a.classList.toggle('active',a.dataset.target===e.target.id)); } });
    },{rootMargin:'-25% 0px -60% 0px',threshold:0});
    sections.forEach(s=>obs.observe(s));
    links.forEach(a=>a.addEventListener('click',()=>{ if(window.innerWidth<=900) toc.classList.remove('open'); }));
  });
});
