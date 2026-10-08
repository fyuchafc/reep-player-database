<?php
/**
 * Plugin Name: Fyucha FC Player Profiles
 * Description: Core WordPress foundation for REEP-powered Fyucha FC player profiles.
 * Version: 0.1.0
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
        add_action('init', [__CLASS__, 'register_post_type']);
        add_action('rest_api_init', [__CLASS__, 'register_rest_routes']);
    }

    public static function register_post_type() {
        register_post_type(self::POST_TYPE, [
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
        ]);
    }

    public static function register_rest_routes() {
        register_rest_route('fyucha/v1', '/player/(?P<reep_id>[^/]+)', [
            'methods' => WP_REST_Server::READABLE,
            'callback' => [__CLASS__, 'get_player'],
            'permission_callback' => '__return_true',
        ]);
    }

    public static function get_player(WP_REST_Request $request) {
        $reep_id = sanitize_text_field($request['reep_id']);

        $query = new WP_Query([
            'post_type' => self::POST_TYPE,
            'post_status' => 'publish',
            'posts_per_page' => 1,
            'meta_key' => self::REEP_META,
            'meta_value' => $reep_id,
            'no_found_rows' => true,
        ]);

        if (!$query->have_posts()) {
            return new WP_Error(
                'fyucha_player_not_found',
                'Player not found.',
                ['status' => 404]
            );
        }

        $post = $query->posts[0];

        return [
            'id' => $post->ID,
            'reep_id' => $reep_id,
            'title' => get_the_title($post),
            'url' => get_permalink($post),
            'status' => get_post_status($post),
            'profile_feed_version' => get_post_meta(
                $post->ID,
                self::VERSION_META,
                true
            ),
        ];
    }
}

Fyucha_FC_Player_Profiles::init();
