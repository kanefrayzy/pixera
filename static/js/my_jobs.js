(function(){
  // Hover overlay (desktop only)
  function enhanceCardHovers(){
    const mql = window.matchMedia('(hover: hover)');
    if (!mql.matches) return; // skip on touch-first
    document.querySelectorAll('.group').forEach(card => {
      const overlay = card.querySelector('.absolute.inset-0');
      if (!overlay) return;
      card.addEventListener('mouseenter', () => {
        overlay.style.backgroundColor = 'rgba(0,0,0,0.2)';
      });
      card.addEventListener('mouseleave', () => {
        overlay.style.backgroundColor = 'rgba(0,0,0,0)';
      });
    });
  }

  // Mobile touch target tweaks
  // function tuneTouchTargets(){
  //   if (window.innerWidth > 640) return;
  //   document.querySelectorAll('.btn').forEach(b => {
  //     b.style.minHeight = '44px';
  //   });
  //   document.querySelectorAll('.w-8.h-8').forEach(el => {
  //     el.style.width = '40px';
  //     el.style.height = '40px';
  //   });
  // }

  function isolateOverlayClicks(){
    document.addEventListener('click', (e) => {
      const ctrl = e.target.closest('.group .absolute [href], .group .absolute button');
      if (ctrl) {
        e.stopPropagation();
      }
    }, true);
  }

  document.addEventListener('DOMContentLoaded', () => {
    enhanceCardHovers();
    // tuneTouchTargets(); // Закомментировано - функция не определена
    isolateOverlayClicks();
  });
})();
