/* imgSlideBox — 슬라이드 이미지 박스 동작 스크립트 (§ 9.1)
   정적 빌드(scripts/markdown.py _simulate_imgslidebox)는 폴더의 모든
   이미지를 <img class="slide"> 로 펼치고 첫 장에만 .active 를 준다.
   이 스크립트가 .active 를 옮겨 한 장씩 보이게 하고, 사이트의
   .pagination-nav 와 같은 절제된 톤의 점(dot) 인디케이터를 이미지
   하단 중앙에 만든다(‹ prev · 점들 · next ›). 내비게이션은 런타임
   생성이므로 정적 HTML(빌드 산출물)은 한 글자도 바뀌지 않는다. */
(function () {
  'use strict';

  function initSlideBox(box) {
    var slides = box.querySelectorAll('.slide');
    if (slides.length === 0) return;

    var current = 0;
    var prev = box.querySelector('.prev');
    var next = box.querySelector('.next');

    function show(idx) {
      slides[current].classList.remove('active');
      if (dots[current]) dots[current].classList.remove('active');
      current = (idx + slides.length) % slides.length;
      slides[current].classList.add('active');
      if (dots[current]) dots[current].classList.add('active');
    }

    /* 이미지 하단 중앙 내비게이션: 기존 정적 prev/next 를 한 줄로
       모으고 그 사이에 슬라이드 수만큼 점을 만든다. */
    var nav = document.createElement('div');
    nav.className = 'slide-nav';

    var dots = [];
    if (prev) {
      prev.setAttribute('aria-label', '이전 이미지');
      nav.appendChild(prev);
    }
    for (var i = 0; i < slides.length; i++) {
      var dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'slide-dot';
      dot.setAttribute('aria-label', (i + 1) + '번째 이미지');
      (function (idx) {
        dot.addEventListener('click', function () { show(idx); });
      }(i));
      nav.appendChild(dot);
      dots.push(dot);
    }
    if (next) {
      next.setAttribute('aria-label', '다음 이미지');
      nav.appendChild(next);
    }
    box.appendChild(nav);

    dots[0].classList.add('active');

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
