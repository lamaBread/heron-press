/* Heron — DOM-based pagination (v0.4.5, gallery support v0.5.3)
 *
 * 모든 항목은 서버에서 렌더된다 (SEO 친화). 이 스크립트는 클라이언트에서
 * DOM 을 hide/show 만 한다.
 *
 * 마크업 규약:
 *   <section class="paginated [listup-gallery]" data-pagination-group="<key>" data-per-page="N">
 *       <div class="listup_module_div">...</div>     <!-- list layout -->
 *       <a class="gallery-tile">...</a>              <!-- gallery layout (v0.5.3) -->
 *       ...
 *   </section>
 *   <nav class="pagination-nav" data-pagination-group="<key>" data-total-pages="P">
 *       <button class="pagi-btn pagi-prev">‹</button>
 *       <span class="pagi-info">
 *           <span class="pagi-current">1</span> / <span class="pagi-total">P</span>
 *       </span>
 *       <button class="pagi-btn pagi-next">›</button>
 *   </nav>
 *
 * - 같은 페이지 안에 여러 페이지네이션이 공존할 수 있으므로 group key 로 짝짓는다.
 * - 직접 자식 중 페이지네이션 대상은 .listup_module_div 또는 .gallery-tile.
 */
(function () {
    'use strict';

    function show(item) {
        item.style.display = '';
    }
    function hide(item) {
        item.style.display = 'none';
    }

    function isPaginatedChild(el) {
        return el.classList && (
            el.classList.contains('listup_module_div') ||
            el.classList.contains('gallery-tile')
        );
    }

    function setupGroup(section, nav) {
        var perPage = parseInt(section.getAttribute('data-per-page') || '0', 10);
        if (!perPage || perPage < 1) return;

        var items = Array.prototype.filter.call(
            section.children,
            isPaginatedChild
        );
        if (items.length === 0) return;

        var totalPages = Math.ceil(items.length / perPage);
        if (totalPages <= 1) {
            if (nav) nav.style.display = 'none';
            return;
        }

        var currentPage = 1;
        var prevBtn = nav ? nav.querySelector('.pagi-prev') : null;
        var nextBtn = nav ? nav.querySelector('.pagi-next') : null;
        var curLabel = nav ? nav.querySelector('.pagi-current') : null;
        var totLabel = nav ? nav.querySelector('.pagi-total') : null;

        function render() {
            var start = (currentPage - 1) * perPage;
            var end = start + perPage;
            for (var i = 0; i < items.length; i++) {
                (i >= start && i < end) ? show(items[i]) : hide(items[i]);
            }
            if (curLabel) curLabel.textContent = String(currentPage);
            if (totLabel) totLabel.textContent = String(totalPages);
            if (prevBtn) prevBtn.disabled = (currentPage <= 1);
            if (nextBtn) nextBtn.disabled = (currentPage >= totalPages);
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                if (currentPage > 1) { currentPage--; render(); }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                if (currentPage < totalPages) { currentPage++; render(); }
            });
        }

        render();
    }

    function init() {
        var sections = document.querySelectorAll('section.paginated[data-pagination-group]');
        for (var i = 0; i < sections.length; i++) {
            var sec = sections[i];
            var key = sec.getAttribute('data-pagination-group');
            var nav = document.querySelector(
                'nav.pagination-nav[data-pagination-group="' + key + '"]'
            );
            setupGroup(sec, nav);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
