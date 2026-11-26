import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

from src.database.seeds import seed_users


class SeedTests(unittest.TestCase):
    def test_seed_users_skips_without_passwords_and_reports_why(self):
        cursor = Mock()

        for configured_passwords in ({}, {"BB_OWNER_PASSWORD": "test-owner-password"}):
            output = StringIO()
            with self.subTest(configured_passwords=configured_passwords):
                with patch.dict(os.environ, configured_passwords, clear=True):
                    with redirect_stdout(output):
                        seed_users(cursor)

                self.assertIn("Skipping user seeding", output.getvalue())
                cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
