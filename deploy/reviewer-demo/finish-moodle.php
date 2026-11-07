<?php
$base = '/home/fldadmin/sphere-review-demo';
if (getcwd() !== "$base/moodle") { exit(1); }
$access = json_decode(file_get_contents("$base/private/access.json"), true);
if (file_exists('config.php')) {
    $argv = ['admin/cli/install_database.php', '--agree-license',
        '--fullname=Sphere Reviewer Demonstration', '--shortname=Sphere Demo',
        '--adminuser=' . $access['admin_user'], '--adminpass=' . $access['admin_password'],
        '--adminemail=demo-admin@sphere.example'];
    $_SERVER['argv'] = $argv;
    require 'admin/cli/install_database.php';
} else {
    $argv = ['admin/cli/install.php', '--non-interactive', '--agree-license', '--lang=en',
        '--wwwroot=https://fld-mini.tail4ccaba.ts.net:8443', "--dataroot=$base/moodle-data",
        '--dbtype=mariadb', '--dbhost=localhost', '--dbname=sphere_store_demo',
        '--dbuser=sphere_store_demo', '--dbpass=' . $access['db_password'],
        '--fullname=Sphere Reviewer Demonstration', '--shortname=Sphere Demo',
        '--adminuser=' . $access['admin_user'], '--adminpass=' . $access['admin_password'],
        '--adminemail=demo-admin@sphere.example'];
    $_SERVER['argv'] = $argv;
    require 'admin/cli/install.php';
}
