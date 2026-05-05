import unittest

from run_daily_workflow import drive_query_literal


class RunDailyWorkflowTests(unittest.TestCase):
    def test_drive_query_literal_escapes_quotes_and_backslashes(self) -> None:
        self.assertEqual(drive_query_literal(r"folder\id's"), r"folder\\id\'s")


if __name__ == "__main__":
    unittest.main()
