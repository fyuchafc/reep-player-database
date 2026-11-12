<?php
/**
 * Plugin Name: Fyucha FC Player Profiles
 * Description: Core WordPress foundation for REEP-powered Fyucha FC player profiles.
 * Version: 0.11.1
 * Author: Fyucha FC
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

final class Fyucha_FC_Player_Profiles {

    const POST_TYPE = 'fyucha_player';

    const REEP_META = '_fyucha_reep_id';
    const VERSION_META = '_fyucha_profile_feed_version';

    public static function init() {

        add_action(
            'init',
            [__CLASS__, 'register_post_type']
        );

        add_action(
            'rest_api_init',
            [__CLASS__, 'register_rest_routes']
        );

        add_filter(
            'the_content',
            [__CLASS__, 'append_profile'],
            20
        );

        add_action(
            'rest_api_init',
            [__CLASS__, 'register_search_route']
        );

        add_shortcode(
            'fyucha_player_directory',
            [__CLASS__, 'directory_shortcode']
        );
    }

    /**
     * Register Fyucha Player custom post type.
     */
    public static function register_post_type() {

        register_post_type(
            self::POST_TYPE,
            [

                'labels' => [
                    'name' => 'Players',
                    'singular_name' => 'Player',
                    'add_new_item' => 'Add Player',
                    'edit_item' => 'Edit Player',
                    'new_item' => 'New Player',
                    'view_item' => 'View Player',
                    'search_items' => 'Search Players',
                ],

                'public' => true,

                'show_ui' => true,

                'show_in_rest' => true,

                'has_archive' => true,

                'rewrite' => [
                    'slug' => 'player',
                    'with_front' => false,
                ],

                'supports' => [
                    'title',
                    'editor',
                    'thumbnail',
                    'excerpt',
                    'custom-fields',
                ],

                'menu_icon' => 'dashicons-groups',
            ]
        );
    }

    /**
     * Register Fyucha REST routes.
     */
    public static function register_rest_routes() {

        /*
         * Public player lookup by permanent REEP ID.
         */
        register_rest_route(
            'fyucha/v1',
            '/player/(?P<reep_id>[^/]+)',
            [
                'methods' => WP_REST_Server::READABLE,

                'callback' => [
                    __CLASS__,
                    'get_player'
                ],

                'permission_callback' => '__return_true',
            ]
        );

        /*
         * Authenticated metadata synchronization endpoint.
         *
         * This deliberately bypasses WordPress's standard REST
         * custom-field writer because REEP metadata uses protected
         * underscore-prefixed keys.
         */
        register_rest_route(
            'fyucha/v1',
            '/player/(?P<post_id>[0-9]+)/sync',
            [
                'methods' => WP_REST_Server::CREATABLE,

                'callback' => [
                    __CLASS__,
                    'sync_player'
                ],

                'permission_callback' => function () {

                    return current_user_can('edit_posts');
                },
            ]
        );
    }

    /**
     * Find a player by permanent REEP ID.
     */
    public static function get_player(
        WP_REST_Request $request
    ) {

        $reep_id = sanitize_text_field(
            $request['reep_id']
        );

        if (!$reep_id) {

            return new WP_Error(
                'fyucha_invalid_reep_id',
                'REEP ID is required.',
                [
                    'status' => 400
                ]
            );
        }

        $query = new WP_Query(
            [

                'post_type' => self::POST_TYPE,

                'post_status' => 'publish',

                'posts_per_page' => 1,

                'meta_query' => [
                    [
                        'key' => self::REEP_META,
                        'value' => $reep_id,
                        'compare' => '=',
                    ],
                ],

                'no_found_rows' => true,
            ]
        );

        if (!$query->have_posts()) {

            return new WP_Error(
                'fyucha_player_not_found',
                'Player not found.',
                [
                    'status' => 404
                ]
            );
        }

        $post = $query->posts[0];

        return [

            'id' => $post->ID,

            'reep_id' => get_post_meta(
                $post->ID,
                self::REEP_META,
                true
            ),

            'title' => get_the_title($post),

            'url' => get_permalink($post),

            'status' => get_post_status($post),

            'profile_feed_version' => get_post_meta(
                $post->ID,
                self::VERSION_META,
                true
            ),

            // New keys (v0.6.0). The keys above must stay unchanged:
            // the importer depends on id and reep_id.
            'gender' => self::read_meta($post->ID, '_fyucha_gender'),

            'primary_position' => self::read_meta($post->ID, '_fyucha_primary_position'),

            'secondary_positions' => self::split_list(
                self::read_meta($post->ID, '_fyucha_secondary_positions')
            ),

            'position_status' => self::read_meta($post->ID, '_fyucha_position_status'),

            'alias_count' => (int) get_post_meta($post->ID, '_fyucha_alias_count', true),

            'external_id_count' => (int) get_post_meta($post->ID, '_fyucha_external_id_count', true),

            'club_evidence' => self::read_meta($post->ID, '_fyucha_club_evidence'),
        ];
    }

    /**
     * Turn 'A | B' text into a list. Arrays and null pass through.
     */
    private static function split_list($value) {

        if ($value === null || is_array($value)) {
            return $value;
        }

        $parts = array_values(array_filter(array_map('trim', explode('|', $value)), 'strlen'));

        return $parts ? $parts : null;
    }

    /**
     * Append a profile section to single player pages.
     * Reads stored metadata only; blank fields are left out.
     */
    public static function append_profile($content) {

        if (!is_singular(self::POST_TYPE) || !in_the_loop() || !is_main_query()) {
            return $content;
        }

        $id = get_the_ID();
        $rows = [];
        $club_note = false;

        $gender = self::read_meta($id, '_fyucha_gender');
        if (is_string($gender) && $gender !== '') {
            $rows['Gender'] = ucfirst($gender);
        }

        $primary = self::read_meta($id, '_fyucha_primary_position');
        if (is_string($primary) && $primary !== '') {
            $rows['Position'] = $primary;
        }

        $secondary = self::split_list(self::read_meta($id, '_fyucha_secondary_positions'));
        if (is_array($secondary) && $secondary) {
            $rows['Also plays'] = implode(', ', array_map('strval', $secondary));
        }

        $clubs = self::read_meta($id, '_fyucha_club_evidence');
        if (is_array($clubs) && !empty($clubs['observed_clubs'])) {
            $text = (string) $clubs['observed_clubs'];
            $first = isset($clubs['first_observed_season']) ? (string) $clubs['first_observed_season'] : '';
            $last = isset($clubs['last_observed_season']) ? (string) $clubs['last_observed_season'] : '';
            if ($first !== '') {
                $text .= ' (' . $first . (($last !== '' && $last !== $first) ? "\u{2013}" . $last : '') . ')';
            }
            $rows['Observed clubs'] = $text;
            $club_note = true;
        }

        $reep = (string) get_post_meta($id, self::REEP_META, true);
        $front = [];
        $photo_html = '';
        $about_html = '';

        $b = self::birthday_data($reep);
        if ($b) {

            $conflicted = (($b['dob_status'] ?? '') === 'conflicted');

            if (!empty($b['description'])) {
                $front['Description'] = (string) $b['description'];
            }

            if ($conflicted) {
                $front['Date of birth'] = 'Conflicting birth-date evidence';
            } else {
                $dob = self::format_date($b['dob'] ?? '');
                if ($dob !== null) {
                    $front['Date of birth'] = $dob;
                    if (($b['dob_status'] ?? '') === 'supported_preferred') {
                        $front['Birth-date status'] = 'Preferred supported birth date';
                    }
                }
            }

            $died = isset($b['died']) ? trim((string) $b['died']) : '';
            if ($died === 'unknown') {
                $front['Died'] = 'Date not known';
            } elseif ($died !== '') {
                $died_text = self::format_date($died);
                if ($died_text !== null) {
                    $front['Died'] = $died_text;
                }
            }

            $file = isset($b['commons_file']) ? trim((string) $b['commons_file']) : '';
            if ($file !== '') {
                $enc = rawurlencode(str_replace(' ', '_', $file));
                $photo_html = '<figure class="fyp-photo">'
                    . '<img src="' . esc_url('https://commons.wikimedia.org/wiki/Special:FilePath/' . $enc . '?width=400') . '"'
                    . ' alt="' . esc_attr(get_the_title($id)) . '" loading="lazy" width="200">'
                    . '<figcaption><a href="' . esc_url('https://commons.wikimedia.org/wiki/File:' . $enc) . '"'
                    . ' target="_blank" rel="noopener">Photo: Wikimedia Commons</a></figcaption>'
                    . '</figure>';
            }

            $about = isset($b['about']) ? trim((string) $b['about']) : '';
            if (!$conflicted && $about !== '') {
                $about_html = '<h2>About ' . esc_html(get_the_title($id)) . '</h2><p class="fyp-about">' . esc_html($about) . '</p><p class="fyp-credit">';
                $wiki = isset($b['enwiki_title']) ? trim((string) $b['enwiki_title']) : '';
                if ($wiki !== '') {
                    $about_html .= '<a href="' . esc_url('https://en.wikipedia.org/wiki/' . $wiki) . '"'
                        . ' target="_blank" rel="noopener">From Wikipedia (CC BY-SA 4.0)</a>';
                } else {
                    $about_html .= 'From Wikipedia (CC BY-SA 4.0)';
                }
                $about_html .= '</p>';
            }
        }

        $rows = array_merge($front, $rows);

        if (!$rows && $photo_html === '' && $about_html === '') {
            return $content;
        }

        $desc = isset($rows['Description']) ? (string) $rows['Description'] : '';
        unset($rows['Description']);

        $chips = [];
        if (isset($rows['Position'])) {
            $chips[] = $rows['Position'];
        }
        if (isset($rows['Date of birth'])) {
            $chips[] = ($rows['Date of birth'] === 'Conflicting birth-date evidence')
                ? $rows['Date of birth']
                : 'Born ' . $rows['Date of birth'];
        }

        $css = '<style>'
            . '.fyp{color:#14213d;margin:1.5em 0}.fyp *{box-sizing:border-box}'
            . '.fyp-head{display:flex;flex-wrap:wrap;gap:24px;align-items:center;background:#fff;border:1px solid #dbe3ee;border-top:6px solid #1d4ed8;border-radius:12px;padding:24px}'
            . '.fyp-photo{margin:0;width:200px}.fyp-photo img{display:block;width:200px;height:auto;border-radius:10px}'
            . '.fyp-photo figcaption{font-size:12px;margin-top:6px}'
            . '.fyp-avatar{width:96px;height:96px;border-radius:50%;background:#e2e8f0;display:flex;align-items:center;justify-content:center}'
            . '.fyp-headmain{flex:1 1 280px;min-width:0}'
            . '.fyp-kicker{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#1d4ed8}'
            . '.fyp-desc{font-size:17px;color:#334155;margin:6px 0 14px}'
            . '.fyp .fyp-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0!important;padding:0!important;list-style:none!important}'
            . '.fyp .fyp-chips li{background:#e8efff;color:#1e3a8a;font-weight:600;font-size:13px;padding:6px 12px!important;border-radius:999px;margin:0!important;list-style:none!important}'
            . '.fyp-cols{display:flex;flex-wrap:wrap;gap:20px;margin-top:20px;align-items:flex-start}'
            . '.fyp-main{flex:999 1 520px;min-width:0}.fyp-side{flex:1 1 280px;min-width:0}'
            . '.fyp-card{background:#fff;border:1px solid #dbe3ee;border-radius:12px;padding:22px}'
            . '.fyp-card h2{margin:0 0 12px;font-size:20px;color:#0b1f44}'
            . '.fyp-about{font-size:16px;line-height:1.65;margin:0 0 10px}'
            . '.fyp-credit,.fyp-note{font-size:13px;color:#475569;margin:0}'
            . '.fyp .fyp-note{margin:14px 0 0}'
            . '.fyp-dl{display:grid;grid-template-columns:auto 1fr;gap:10px 16px;margin:0}'
            . '.fyp-dl dt{color:#475569;font-weight:400;margin:0}.fyp-dl dd{margin:0;font-weight:600}'
            . '</style>';

        $html = '<section class="fyp">' . $css;
        $html .= '<div class="fyp-head">';
        if ($photo_html !== '') {
            $html .= $photo_html;
        } else {
            $html .= '<div class="fyp-avatar" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.6"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg></div>';
        }
        $html .= '<div class="fyp-headmain"><div class="fyp-kicker">Football player</div>';
        if ($desc !== '') {
            $html .= '<p class="fyp-desc">' . esc_html($desc) . '</p>';
        }
        if ($chips) {
            $html .= '<ul class="fyp-chips">';
            foreach ($chips as $chip) {
                $html .= '<li>' . esc_html($chip) . '</li>';
            }
            $html .= '</ul>';
        }
        $html .= '</div></div>';

        $html .= '<div class="fyp-cols">';
        if ($about_html !== '') {
            $html .= '<div class="fyp-main"><div class="fyp-card">' . $about_html . '</div></div>';
        }
        if ($rows) {
            $html .= '<aside class="fyp-side"><div class="fyp-card"><h2>Key facts</h2><dl class="fyp-dl">';
            foreach ($rows as $label => $value) {
                $html .= '<dt>' . esc_html($label) . '</dt><dd>' . esc_html($value) . '</dd>';
            }
            $html .= '</dl>';
            if ($club_note) {
                $html .= '<p class="fyp-note">Observed clubs show where this player appears in match coverage; this is not a complete career history.</p>';
            }
            $html .= '</div></aside>';
        }
        $html .= '</div></section>';

        return $content . $html;
    }

    /**
     * Look up Birthday Tool data for one player by REEP ID.
     * Returns null if the player has no row or the tables are missing.
     */
    private static function birthday_data($reep) {

        global $wpdb;

        if ($reep === '') {
            return null;
        }

        $p = $wpdb->prefix;
        $previous = $wpdb->suppress_errors(true);

        $row = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT dob, dob_status FROM {$p}fyucha_birthday_players WHERE reep_id = %s LIMIT 1",
                $reep
            ),
            ARRAY_A
        );

        if (!$row) {
            $wpdb->suppress_errors($previous);
            return null;
        }

        // Each table is read on its own, so a missing table only drops its own fields.
        $extra = [
            "SELECT commons_file FROM {$p}fyucha_birthday_photos WHERE reep_id = %s LIMIT 1",
            "SELECT description, enwiki_title, died FROM {$p}fyucha_birthday_fame WHERE reep_id = %s LIMIT 1",
            "SELECT about FROM {$p}fyucha_birthday_about WHERE reep_id = %s LIMIT 1",
        ];

        foreach ($extra as $sql) {
            $more = $wpdb->get_row($wpdb->prepare($sql, $reep), ARRAY_A);
            if (is_array($more)) {
                $row = array_merge($row, $more);
            }
        }

        $wpdb->suppress_errors($previous);

        return $row;
    }

    /**
     * Format a YYYY-MM-DD string as "9 April 1956". Returns null if invalid.
     */
    private static function format_date($value) {

        $value = trim((string) $value);

        if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $value)) {
            return null;
        }

        $d = DateTime::createFromFormat('!Y-m-d', $value, new DateTimeZone('UTC'));

        if (!$d || $d->format('Y-m-d') !== $value) {
            return null;
        }

        return $d->format('j F Y');
    }

    /**
     * Register the public, read-only player search route.
     */
    public static function register_search_route() {

        register_rest_route(
            'fyucha/v1',
            '/search',
            [
                'methods' => WP_REST_Server::READABLE,
                'callback' => [__CLASS__, 'search_players'],
                'permission_callback' => '__return_true',
                'args' => [
                    'q' => [
                        'required' => true,
                        'type' => 'string',
                    ],
                ],
            ]
        );
    }

    /**
     * Search players by name and by Birthday Tool aliases.
     * Whole-word matches first, then fame, then name. Read-only.
     */
    public static function search_players(WP_REST_Request $request) {

        global $wpdb;

        $q = trim(sanitize_text_field((string) $request->get_param('q')));
        $q = mb_substr($q, 0, 80);

        if (mb_strlen($q) < 3) {
            return new WP_Error(
                'fyucha_search_too_short',
                'Enter at least 3 characters.',
                ['status' => 400]
            );
        }

        $norm = trim((string) preg_replace('/[^a-z0-9]+/', ' ', strtolower(remove_accents($q))));
        $source = ($norm !== '') ? $norm : mb_strtolower($q);
        $tokens = array_slice(array_values(array_filter(preg_split('/\s+/', $source))), 0, 4);

        if (!$tokens) {
            return ['query' => $q, 'total' => 0, 'results' => []];
        }

        $cache_key = 'fyucha_search_v2_' . md5($source);
        $cached = get_transient($cache_key);
        if (is_array($cached)) {
            $cached['query'] = $q;
            return $cached;
        }

        if (self::rate_limited()) {
            return new WP_Error(
                'fyucha_search_rate_limited',
                'Too many searches. Please wait a minute and try again.',
                ['status' => 429]
            );
        }

        $lit = function ($s) use ($wpdb) {
            return $wpdb->prepare('%s', $s);
        };
        $like = function ($s) use ($wpdb) {
            return $wpdb->esc_like($s);
        };
        $whole = function ($col, $t) use ($lit, $like) {
            $e = $like($t);
            return '(' . $col . ' = ' . $lit($t)
                . ' OR ' . $col . ' LIKE ' . $lit($e . ' %')
                . ' OR ' . $col . ' LIKE ' . $lit('% ' . $e)
                . ' OR ' . $col . ' LIKE ' . $lit('% ' . $e . ' %') . ')';
        };

        $title_all = [];
        $title_whole = [];
        foreach ($tokens as $t) {
            $title_all[] = 'p.post_title LIKE ' . $lit('%' . $like($t) . '%');
            $title_whole[] = $whole('p.post_title', $t);
        }
        $title_all_sql = '(' . implode(' AND ', $title_all) . ')';
        $title_whole_sql = '(' . implode(' AND ', $title_whole) . ')';
        $alias_cond = ($norm !== '') ? $whole('alias_norm', $norm) : '1=0';

        $pp = $wpdb->prefix;

        $sql = "SELECT p.ID, p.post_title, m.meta_value AS reep_id, f.description,
                       COALESCE(f.sitelinks, 0) AS fame,
                       CASE WHEN {$title_whole_sql} OR al.reep_id IS NOT NULL THEN 0 ELSE 1 END AS rank_group
                FROM {$wpdb->posts} p
                JOIN {$wpdb->postmeta} m ON m.post_id = p.ID AND m.meta_key = '_fyucha_reep_id'
                LEFT JOIN {$pp}fyucha_birthday_fame f ON f.reep_id = m.meta_value
                LEFT JOIN (SELECT DISTINCT reep_id FROM {$pp}fyucha_birthday_aliases WHERE {$alias_cond}) al
                       ON al.reep_id = m.meta_value
                WHERE p.post_type = 'fyucha_player' AND p.post_status = 'publish'
                  AND ({$title_all_sql} OR al.reep_id IS NOT NULL)
                ORDER BY rank_group ASC, fame DESC, p.post_title ASC
                LIMIT 20";

        // Fallback if the fame or alias tables are missing: names only.
        $fallback = "SELECT p.ID, p.post_title, m.meta_value AS reep_id, '' AS description, 0 AS fame,
                            CASE WHEN {$title_whole_sql} THEN 0 ELSE 1 END AS rank_group
                     FROM {$wpdb->posts} p
                     JOIN {$wpdb->postmeta} m ON m.post_id = p.ID AND m.meta_key = '_fyucha_reep_id'
                     WHERE p.post_type = 'fyucha_player' AND p.post_status = 'publish'
                       AND {$title_all_sql}
                     ORDER BY rank_group ASC, p.post_title ASC
                     LIMIT 20";

        $previous = $wpdb->suppress_errors(true);

        $rows = $wpdb->get_results($sql, ARRAY_A);
        if ($wpdb->last_error !== '') {
            $rows = $wpdb->get_results($fallback, ARRAY_A);
        }

        $failed = ($wpdb->last_error !== '');
        $wpdb->suppress_errors($previous);

        if ($failed) {
            return new WP_Error(
                'fyucha_search_failed',
                'Search is unavailable right now.',
                ['status' => 500]
            );
        }

        if (!is_array($rows)) {
            $rows = [];
        }

        // Keep only the most relevant matches when there are enough of them.
        $strong = array_values(array_filter($rows, function ($r) {
            return (int) $r['rank_group'] === 0;
        }));
        if (count($strong) >= 3) {
            $rows = $strong;
        }

        $ids = array_map('intval', wp_list_pluck($rows, 'ID'));
        if ($ids) {
            update_meta_cache('post', $ids);
        }

        $results = [];
        foreach ($rows as $r) {
            $post_id = (int) $r['ID'];
            $position = get_post_meta($post_id, '_fyucha_primary_position', true);
            $results[] = [
                'name' => (string) $r['post_title'],
                'url' => get_permalink($post_id),
                'reep_id' => (string) $r['reep_id'],
                'description' => !empty($r['description']) ? (string) $r['description'] : null,
                'position' => ($position !== '' && $position !== null) ? (string) $position : null,
            ];
        }

        $response = [
            'query' => $q,
            'total' => count($results),
            'results' => $results,
        ];

        set_transient($cache_key, $response, 10 * MINUTE_IN_SECONDS);

        return $response;
    }

    /**
     * Shortcode [fyucha_player_directory]: a search box that calls the search route.
     */
    public static function directory_shortcode() {

        $endpoint = esc_url_raw(rest_url('fyucha/v1/search'));
        $uid = 'fyucha-dir-' . wp_generate_password(6, false);

        ob_start();
        ?>
        <div class="fyucha-player-directory" id="<?php echo esc_attr($uid); ?>">
            <form class="fyucha-dir-form" style="display:flex;gap:.5em;flex-wrap:wrap;margin-bottom:1em">
                <input type="search" name="q" minlength="3" maxlength="80" required
                       placeholder="Search players by name or nickname" aria-label="Search players"
                       style="flex:1;min-width:220px;padding:.6em">
                <button type="submit" style="padding:.6em 1.2em">Search</button>
            </form>
            <p class="fyucha-dir-status" aria-live="polite"></p>
            <div class="fyucha-dir-results"></div>
        </div>
        <script>
        (function () {
            var root = document.getElementById(<?php echo wp_json_encode($uid); ?>);
            if (!root) { return; }
            var endpoint = <?php echo wp_json_encode($endpoint); ?>;
            var form = root.querySelector('.fyucha-dir-form');
            var input = form.querySelector('input');
            var status = root.querySelector('.fyucha-dir-status');
            var box = root.querySelector('.fyucha-dir-results');

            form.addEventListener('submit', function (e) {
                e.preventDefault();
                var q = input.value.trim();
                box.textContent = '';
                if (q.length < 3) {
                    status.textContent = 'Enter at least 3 characters.';
                    return;
                }
                status.textContent = 'Searching...';
                var url = endpoint + (endpoint.indexOf('?') === -1 ? '?' : '&') + 'q=' + encodeURIComponent(q);
                fetch(url, { credentials: 'same-origin' })
                    .then(function (r) {
                        return r.json().then(function (d) { return { ok: r.ok, data: d }; });
                    })
                    .then(function (res) {
                        if (!res.ok) {
                            status.textContent = (res.data && res.data.message) || 'Search failed.';
                            return;
                        }
                        var list = res.data.results || [];
                        status.textContent = list.length
                            ? 'Showing ' + list.length + ' result' + (list.length === 1 ? '' : 's') + ' for ' + q
                            : 'No players found for ' + q;
                        list.forEach(function (item) {
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:.75em 0;border-bottom:1px solid #e3e8ee';
                            var link = document.createElement('a');
                            link.href = item.url;
                            link.textContent = item.name;
                            link.style.fontWeight = '600';
                            card.appendChild(link);
                            var bits = [];
                            if (item.description) { bits.push(item.description); }
                            if (item.position) { bits.push(item.position); }
                            if (bits.length) {
                                var small = document.createElement('div');
                                small.style.fontSize = '.9em';
                                small.textContent = bits.join(' \u00b7 ');
                                card.appendChild(small);
                            }
                            box.appendChild(card);
                        });
                    })
                    .catch(function () {
                        status.textContent = 'Search failed. Please try again.';
                    });
            });
        })();
        </script>
        <?php
        return ob_get_clean();
    }

    /**
     * Allow at most 20 uncached searches per minute per visitor (by IP address).
     */
    private static function rate_limited() {

        $ip = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : 'unknown';
        $key = 'fyucha_rl_' . md5($ip);
        $now = time();

        $state = get_transient($key);
        if (!is_array($state) || !isset($state['t'], $state['n']) || ($now - (int) $state['t']) >= 60) {
            $state = ['t' => $now, 'n' => 0];
        }

        $state['n']++;
        set_transient($key, $state, 120);

        return $state['n'] > 20;
    }

    /**
     * Read one metadata value. Blank becomes null; JSON arrays are decoded.
     */
    private static function read_meta($post_id, $key) {

        $value = get_post_meta($post_id, $key, true);

        if ($value === '' || $value === null) {
            return null;
        }

        $decoded = json_decode($value, true);

        if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
            return $decoded;
        }

        return $value;
    }

    /**
     * Synchronize REEP profile metadata.
     *
     * Metadata is written directly using update_post_meta().
     */
    public static function sync_player(
        WP_REST_Request $request
    ) {

        $post_id = absint(
            $request['post_id']
        );

        if (!$post_id) {

            return new WP_Error(
                'fyucha_invalid_post_id',
                'WordPress player ID is required.',
                [
                    'status' => 400
                ]
            );
        }

        $post = get_post($post_id);

        if (
            !$post ||
            $post->post_type !== self::POST_TYPE
        ) {

            return new WP_Error(
                'fyucha_player_not_found',
                'WordPress player not found.',
                [
                    'status' => 404
                ]
            );
        }

        if (
            !current_user_can(
                'edit_post',
                $post_id
            )
        ) {

            return new WP_Error(
                'fyucha_forbidden',
                'You are not allowed to edit this player.',
                [
                    'status' => 403
                ]
            );
        }

        $params = $request->get_json_params();

        if (!is_array($params)) {

            return new WP_Error(
                'fyucha_invalid_payload',
                'Invalid JSON payload.',
                [
                    'status' => 400
                ]
            );
        }

        $reep_id = isset($params['reep_id'])
            ? sanitize_text_field(
                $params['reep_id']
            )
            : '';

        if (!$reep_id) {

            return new WP_Error(
                'fyucha_invalid_reep_id',
                'REEP ID is required.',
                [
                    'status' => 400
                ]
            );
        }

        /*
         * Store REEP ID.
         */
        update_post_meta(
            $post_id,
            self::REEP_META,
            $reep_id
        );

        /*
         * Store all remaining profile metadata.
         */
        $meta_map = [

            '_fyucha_profile_feed_version' =>
                'profile_feed_version',

            '_fyucha_reep_schema_version' =>
                'schema_version',

            '_fyucha_status' =>
                'status',

            '_fyucha_gender' =>
                'gender',

            '_fyucha_country' =>
                'country',

            '_fyucha_primary_position' =>
                'primary_position',

            '_fyucha_secondary_positions' =>
                'secondary_positions',

            '_fyucha_position_status' =>
                'position_status',

            '_fyucha_position_evidence_count' =>
                'position_evidence_count',

            '_fyucha_position_provider_count' =>
                'position_provider_count',

            '_fyucha_club_evidence' =>
                'club_evidence',

            '_fyucha_alias_count' =>
                'alias_count',

            '_fyucha_external_id_count' =>
                'external_id_count',
        ];

        foreach ($meta_map as $meta_key => $param_key) {

            if (!array_key_exists(
                $param_key,
                $params
            )) {
                continue;
            }

            $value = $params[$param_key];

            /*
             * Arrays/objects are stored as JSON.
             */
            if (is_array($value) || is_object($value)) {

                $value = wp_json_encode(
                    $value,
                    JSON_UNESCAPED_UNICODE
                );

            } elseif (
                is_bool($value)
            ) {

                $value = $value ? '1' : '0';

            } elseif (
                $value === null
            ) {

                $value = '';

            } else {

                $value = (string) $value;
            }

            update_post_meta(
                $post_id,
                $meta_key,
                $value
            );
        }

        return [

            'success' => true,

            'id' => $post_id,

            'reep_id' => get_post_meta(
                $post_id,
                self::REEP_META,
                true
            ),

            'profile_feed_version' => get_post_meta(
                $post_id,
                self::VERSION_META,
                true
            ),
        ];
    }
}

Fyucha_FC_Player_Profiles::init();