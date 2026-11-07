<?php
// Run only from a fresh /home/fldadmin/sphere-review-demo/moodle checkout.
$base = '/home/fldadmin/sphere-review-demo';
if (getcwd() !== "$base/moodle" || file_exists('config.php')) {
    fwrite(STDERR, "Requires the fresh isolated demo directory without config.php.\n");
    exit(1);
}
umask(0077);
if (!is_dir("$base/private")) { mkdir("$base/private", 0700, true); }
if (!is_dir("$base/moodle-data")) { mkdir("$base/moodle-data", 0700, true); }
if (file_exists("$base/private/access.json")) { exit("Demo credentials already exist; refusing to overwrite.\n"); }
$secret = fn() => 'Aa9!' . bin2hex(random_bytes(16));
$access = [
    'moodle_user' => 'sphere.reviewer',
    'moodle_password' => $secret(),
    'admin_user' => 'demo.admin',
    'admin_password' => $secret(),
    'db_password' => bin2hex(random_bytes(24)),
    'sphere_email' => 'reviewer@sphere.example',
    'sphere_password' => $secret(),
];
file_put_contents("$base/private/access.json", json_encode($access, JSON_PRETTY_PRINT));
chmod("$base/private/access.json", 0600);
$sql = "CREATE DATABASE sphere_store_demo DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
    . "CREATE USER 'sphere_store_demo'@'localhost' IDENTIFIED BY '" . $access['db_password'] . "';\n"
    . "GRANT ALL PRIVILEGES ON sphere_store_demo.* TO 'sphere_store_demo'@'localhost';\n";
$process = proc_open(['sudo', '-n', '/usr/bin/mariadb'], [['pipe','r'], STDOUT, STDERR], $pipes);
fwrite($pipes[0], $sql);
fclose($pipes[0]);
if (proc_close($process) !== 0) { exit("Could not create the isolated database.\n"); }
$argv = [
    'admin/cli/install.php', '--non-interactive', '--agree-license',
    '--lang=en', '--wwwroot=https://fld-mini.tail4ccaba.ts.net:8443',
    "--dataroot=$base/moodle-data", '--dbtype=mariadb', '--dbhost=localhost',
    '--dbname=sphere_store_demo', '--dbuser=sphere_store_demo', '--dbpass=' . $access['db_password'],
    '--fullname=Sphere Reviewer Demonstration', '--shortname=Sphere Demo',
    '--adminuser=' . $access['admin_user'], '--adminpass=' . $access['admin_password'],
    '--adminemail=demo-admin@sphere.example',
];
$_SERVER['argv'] = $argv;
require 'admin/cli/install.php';
