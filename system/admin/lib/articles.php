<?php
// Articles/ 트리 스캔 (admin v1.1.0).
// 빌더의 글/카테고리 구분과 동일: content.md|content.html 있으면 '글',
// meta.yaml 만 있으면 '카테고리'. '.' 접두는 숨김(빌더 제외 — .trash 등)
// 이라 admin 목록에서도 제외. '_' 접두(비공개)는 admin 이 관리·복구
// 해야 하므로 hidden 배지를 달아 그대로 노출한다.

declare(strict_types=1);
require_once __DIR__ . '/fs.php';
require_once __DIR__ . '/metayaml.php';

/** 경로 세그먼트 중 '_' 접두가 있으면 비공개로 간주. */
function admin_rel_is_hidden(string $rel): bool {
    foreach (explode('/', $rel) as $seg) {
        if ($seg !== '' && $seg[0] === '_') return true;
    }
    return false;
}

/**
 * 전체 스캔. 반환:
 *   ['posts' => [ {id,name,title,parent,hidden,ext,both}... ],
 *    'categories' => [ rel, ... ]  // 이동/새글 대상 (''=톱레벨 포함)]
 */
function admin_scan(): array {
    $root = admin_articles_dir();
    $posts = [];
    $categories = ['']; // '' = Articles 루트(톱레벨)

    $walk = function (string $absDir, string $rel) use (&$walk, &$posts, &$categories, $root) {
        $entries = @scandir($absDir);
        if ($entries === false) return;
        sort($entries, SORT_NATURAL | SORT_FLAG_CASE);
        foreach ($entries as $e) {
            if ($e === '.' || $e === '..') continue;
            $abs = $absDir . DIRECTORY_SEPARATOR . $e;
            if (!is_dir($abs)) continue;
            if ($e[0] === '.') continue;          // 숨김(.trash/.git 등) 제외
            $childRel = $rel === '' ? $e : ($rel . '/' . $e);

            if (admin_is_post_dir($abs)) {
                $md = is_file($abs . DIRECTORY_SEPARATOR . 'content.md');
                $html = is_file($abs . DIRECTORY_SEPARATOR . 'content.html');
                $title = $e;
                $mp = $abs . DIRECTORY_SEPARATOR . 'meta.yaml';
                if (is_file($mp)) {
                    $c = meta_read_core((string)@file_get_contents($mp));
                    if (trim($c['title']) !== '') $title = $c['title'];
                }
                $posts[] = [
                    'id'     => $childRel,
                    'name'   => $e,
                    'title'  => $title,
                    'parent' => $rel,
                    'hidden' => admin_rel_is_hidden($childRel),
                    'ext'    => $md ? 'md' : ($html ? 'html' : 'none'),
                    'both'   => ($md && $html),
                ];
                // 글 폴더 안은 더 내려가지 않는다 (자산/슬라이드 폴더).
                continue;
            }

            // 카테고리(또는 구조 폴더) — 이동/새글 대상이 되고 재귀.
            $categories[] = $childRel;
            $walk($abs, $childRel);
        }
    };
    $walk($root, '');

    usort($posts, fn($a, $b) =>
        strnatcasecmp($a['parent'].'/'.$a['name'], $b['parent'].'/'.$b['name']));
    sort($categories, SORT_NATURAL | SORT_FLAG_CASE);
    return ['posts' => $posts, 'categories' => $categories];
}

/** 휴지통(.trash) 안의 항목 목록 (복구 안내용 표시). */
function admin_scan_trash(): array {
    $t = admin_trash_dir();
    if (!is_dir($t)) return [];
    $out = [];
    foreach (scandir($t) ?: [] as $e) {
        if ($e === '.' || $e === '..') continue;
        if (is_dir($t . DIRECTORY_SEPARATOR . $e)) $out[] = $e;
    }
    sort($out, SORT_NATURAL | SORT_FLAG_CASE);
    return $out;
}
