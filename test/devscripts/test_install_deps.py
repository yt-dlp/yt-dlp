import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from devscripts import install_deps


class TestInstallDeps(unittest.TestCase):

    @mock.patch('devscripts.install_deps.parse_toml')
    @mock.patch('devscripts.install_deps.read_file')
    @mock.patch('devscripts.install_deps.subprocess.call')
    def test_print_option(self, mock_call, mock_read_file, mock_parse_toml):
        # Mock the parse_toml function to return a project table with dependencies
        mock_parse_toml.return_value = {
            'project': {
                'name': 'yt-dlp',
                'dependencies': ['dep1', 'dep2'],
                'optional-dependencies': {
                    'default': ['opt1', 'opt2'],
                    'test': ['test1', 'test2'],
                    'dev': ['dev1', 'dev2'],
                },
            },
        }

        # Mock sys.argv to simulate command line arguments
        with mock.patch('sys.argv', ['install_deps.py', '--print']):
            # Redirect stdout to capture the output
            from io import StringIO
            import sys
            original_stdout = sys.stdout
            try:
                output = StringIO()
                sys.stdout = output

                # Execute the main function
                install_deps.main()

                # Get the captured output
                printed_deps = output.getvalue().strip().split('\n')

                # Check that default dependencies are included
                # 2 from dependencies + default dependencies
                self.assertEqual(len(printed_deps), 4)
                self.assertIn('dep1', printed_deps)
                self.assertIn('dep2', printed_deps)
                self.assertIn('opt1', printed_deps)
                self.assertIn('opt2', printed_deps)

            finally:
                sys.stdout = original_stdout

        # Call was not made because we used --print
        mock_call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
