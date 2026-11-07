<?php
/**
 * Plugin Name: Fyucha FC Player Profiles
 * Description: Core WordPress foundation for REEP-powered Fyucha FC player profiles.
 * Version: 0.6.0
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