<?php
/**
 * siheonlee.com SSG v0.3 — Parsedown CLI shim.
 *
 * stdin  : raw Markdown (UTF-8)
 * stdout : rendered HTML (UTF-8)
 * stderr : Parsedown errors
 *
 * Used by parsers/parsedown.py via subprocess.run(['php', ...]).
 *
 * The Parsedown.php source is the same one shipped in
 * lama_website-main/PHP/parsedown/Parsedown.php.
 */

require __DIR__ . '/Parsedown.php';

$input = stream_get_contents(STDIN);
if ($input === false) {
    fwrite(STDERR, "[parsedown/run.php] failed to read stdin\n");
    exit(1);
}

try {
    $Parsedown = new Parsedown();
    $html = $Parsedown->text($input);
} catch (Throwable $e) {
    fwrite(STDERR, "[parsedown/run.php] " . $e->getMessage() . "\n");
    exit(2);
}

echo $html;
