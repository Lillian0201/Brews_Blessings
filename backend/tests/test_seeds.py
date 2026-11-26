import os
import unittest
from unittest.mock import Mock, patch

from src.database.seeds import seed_users


class SeedTests(unittest.TestCase):
    def test_seed_users_requires_passwords_in_environment(self):
        cursor = Mock()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BB_OWNER_PASSWORD"):
                seed_users(cursor)
        cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
