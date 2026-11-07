import configparser
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoRecoveryTests(unittest.TestCase):
    def unit(self, name):
        config = configparser.ConfigParser(strict=False, interpolation=None)
        config.read(ROOT / 'deploy/reviewer-demo' / name)
        return config

    def test_demo_units_retry_with_backoff_without_exhausting_start_limit(self):
        for name in ('sphere-review-demo.service', 'sphere-review-demo-moodle.service'):
            with self.subTest(unit=name):
                config = self.unit(name)
                self.assertEqual(config['Service']['Restart'], 'always')
                self.assertEqual(config['Service']['RestartSec'], '5s')
                self.assertEqual(config['Unit']['StartLimitIntervalSec'], '0')
                self.assertEqual(config['Install']['WantedBy'], 'default.target')

    def test_php_failure_does_not_stop_gateway(self):
        config = self.unit('sphere-review-demo.service')
        self.assertEqual(config['Unit'].get('Wants'), 'sphere-review-demo-moodle.service')
        self.assertNotIn('Requires', config['Unit'])
        self.assertIn('sphere-review-demo-moodle.service', config['Unit']['After'])

    def test_units_remain_isolated_from_live_pilot(self):
        for name, port in (('sphere-review-demo.service', '8023'), ('sphere-review-demo-moodle.service', '8091')):
            config = self.unit(name)
            self.assertTrue(config['Service']['WorkingDirectory'].startswith('/home/fldadmin/sphere-review-demo/'))
            command = config['Service']['ExecStart']
            self.assertIn(port, command)
            self.assertNotIn('8017', command)
            self.assertEqual(config['Service']['NoNewPrivileges'], 'true')


if __name__ == '__main__':
    unittest.main()
