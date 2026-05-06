/* imgSlideBox — 슬라이드 이미지 박스 동작 스크립트 (§ 9.1) */
(function () {
  'use strict';

  function initSlideBox(box) {
    var slides = box.querySelectorAll('.slide');
    if (slides.length === 0) return;

    var current = 0;

    function show(idx) {
      slides[current].classList.remove('active');
      current = (idx + slides.length) % slides.length;
      slides[current].classList.add('active');
    }

    var prev = box.querySelector('.prev');
    var next = box.querySelector('.next');

    if (prev) {
      prev.addEventListener('click', function () { show(current - 1); });
    }
    if (next) {
      next.addEventListener('click', function () { show(current + 1); });
    }

    /* 키보드 */
    box.setAttribute('tabindex', '0');
    box.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft')  show(current - 1);
      if (e.key === 'ArrowRight') show(current + 1);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var boxes = document.querySelectorAll('.imgSlideBox');
    for (var i = 0; i < boxes.length; i++) {
      initSlideBox(boxes[i]);
    }
  });
}());
