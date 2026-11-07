<?php
define('CLI_SCRIPT', true);
$base = '/home/fldadmin/sphere-review-demo';
$config = "$base/moodle/config.php";
$text = file_get_contents($config);
if (!str_contains($text, 'Sphere isolated demo proxy')) {
    $text = preg_replace('/^(require_once.*setup\.php.*)$/m', "\$CFG->sslproxy = true; // Sphere isolated demo proxy\n\$CFG->sessioncookie = 'SphereDemo';\n$1", $text, 1, $changed);
    if ($changed !== 1) { throw new Exception('Cannot configure the demo TLS proxy'); }
    file_put_contents($config, $text);
}
if (!str_contains($text, "\$CFG->sessioncookie = 'SphereDemo'")) {
    $text = preg_replace('/^(require_once.*setup\.php.*)$/m', "\$CFG->sessioncookie = 'SphereDemo';\n$1", $text, 1);
    file_put_contents($config, $text);
}
if (!str_contains($text, "\$CFG->reverseproxy = true")) {
    $text = preg_replace('/^(require_once.*setup\.php.*)$/m', "\$CFG->reverseproxy = true;\n$1", $text, 1);
    file_put_contents($config, $text);
}
if (!str_contains($text, "\$CFG->noemailever = true")) {
    $text = preg_replace('/^(require_once.*setup\.php.*)$/m', "\$CFG->noemailever = true;\n$1", $text, 1);
    file_put_contents($config, $text);
}
require "$base/moodle/config.php";
require_once "$CFG->dirroot/course/lib.php";
require_once "$CFG->dirroot/user/lib.php";
require_once "$CFG->libdir/enrollib.php";
$access = json_decode(file_get_contents("$base/private/access.json"), true);
// Empty demo installation only: never load production or existing Moodle config.
if ($CFG->dbname !== 'sphere_store_demo') { throw new Exception('Not the demo database'); }
set_config('forcelogin', 1);
set_config('registerauth', '');
set_config('auth', 'manual');
set_config('noreplyaddress', 'no-reply@sphere.example');
set_config('supportemail', 'rcadavies@gmail.com');
set_config('messaging', 0);
set_config('enablewebservices', 0);
set_config('enablemobilewebservice', 0);
set_config('cronclionly', 1);
set_config('allowthemechangeonurl', 0);
if (!$DB->record_exists('user', ['username' => $access['moodle_user']])) {
    $user = (object)[
        'username' => $access['moodle_user'], 'password' => $access['moodle_password'],
        'firstname' => 'Google', 'lastname' => 'Reviewer', 'email' => 'reviewer@sphere.example',
        'auth' => 'manual', 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
        'emailstop' => 1, 'city' => 'Demo', 'country' => 'NZ',
    ];
    $userid = user_create_user($user);
} else { $userid = $DB->get_field('user', 'id', ['username' => $access['moodle_user']]); }
$teacher = $DB->get_field('role', 'id', ['shortname' => 'teacher'], MUST_EXIST);
$manual = enrol_get_plugin('manual');
$category = $DB->get_field('course_categories', 'id', [], IGNORE_MULTIPLE);
$courses = [];
foreach (['A', 'B'] as $letter) {
    $short = "SPHERE-DEMO-$letter";
    $course = $DB->get_record('course', ['shortname' => $short]);
    if (!$course) {
        $course = create_course((object)[
            'fullname' => "Sphere Demo Course $letter", 'shortname' => $short,
            'category' => $category, 'format' => 'topics', 'numsections' => 2,
            'summary' => '<p>This isolated course contains fictional content for testing Sphere. Do not enter personal or confidential information.</p>',
        ]);
    }
    $instance = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual']);
    if (!$instance) { $instanceid = $manual->add_instance($course); } else { $instanceid = $instance->id; }
    $manual->enrol_user($DB->get_record('enrol', ['id' => $instanceid]), $userid, $teacher);
    $section = course_create_sections_if_missing($course, [1]);
    $DB->set_field('course_sections', 'name', 'Sample lesson and review tasks', ['course' => $course->id, 'section' => 1]);
    $DB->set_field('course_sections', 'summary', '<h2>Welcome to the Sphere review demo</h2><p>All content here is fictional. Select a sentence and add a Sphere highlight comment, or use Add comment marker to leave an area comment.</p><h3>A sample statement to review</h3><p>Good feedback is specific, respectful, and actionable. It explains what could be improved and why.</p><p>This sentence deliberately contains a small spelling eror for reviewers to discuss.</p><h3>Try the workflow</h3><ol><li>Add a highlight comment.</li><li>Open the comment from the Comments list.</li><li>Reply and resolve it.</li><li>Switch to the other demo course and back.</li></ol>', ['course' => $course->id, 'section' => 1]);
    rebuild_course_cache($course->id, true);
    $courses[] = ['id' => (int)$course->id, 'title' => $course->fullname];
    echo "Demo course $letter id={$course->id}\n";
}
file_put_contents("$base/private/courses.json", json_encode($courses));
chmod("$base/private/courses.json", 0600);
