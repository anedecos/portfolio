from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from update_contributions import parse_calendar, refresh

NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def public_calendar():
    start = NOW.date() - timedelta(days=365)
    html = ['<h2 id="js-contribution-activity-description">1,001 contributions in the last year</h2>']
    for index in reversed(range(366)):
        count = 1000 if index == 365 else 1 if index == 364 else 0
        count_label = 'No contributions' if not count else f'{count:,} contribution' + ('s' if count != 1 else '')
        html.append(f'<td id="day-{index}" class="ContributionCalendar-day" data-date="{start + timedelta(days=index)}" data-level="{4 if count == 1000 else 1 if count else 0}"></td>')
        html.append(f'<tool-tip for="day-{index}">{count_label} on October 7th.</tool-tip>')
    return ''.join(html)


class CalendarTests(unittest.TestCase):
    def test_public_counts_and_chronological_dates(self):
        data = parse_calendar(public_calendar(), NOW)
        self.assertEqual(data['total'], 1001)
        self.assertEqual(data['days'][-2]['count'], 1)
        self.assertEqual(data['days'][-1]['count'], 1000)
        self.assertEqual(set(data), {'username', 'source', 'retrievedAt', 'total', 'days'})
        self.assertEqual(set(data['days'][0]), {'date', 'count', 'level'})

    def test_rejects_login_or_empty_response(self):
        for html in ['', '<html>Please sign in</html>']:
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_calendar(html, NOW)

    def test_rejects_mismatched_count_missing_tooltip_and_duplicate_date(self):
        original = public_calendar()
        invalid = [
            original.replace('1,001 contributions in the last year', '1,002 contributions in the last year'),
            original.replace('for="day-0"', 'for="missing"'),
            original.replace('2026-10-06', '2026-10-07'),
            original.replace('data-level="4"', 'data-level="5"'),
        ]
        for html in invalid:
            with self.subTest(html=html[-100:]), self.assertRaises(ValueError):
                parse_calendar(html, NOW)

    def test_rejects_stale_calendar(self):
        with self.assertRaises(ValueError):
            parse_calendar(public_calendar(), NOW + timedelta(days=3))

    def test_failure_preserves_last_good_snapshot(self):
        with tempfile.TemporaryDirectory() as directory, patch('update_contributions.time.sleep'):
            output = Path(directory) / 'contributions.json'
            output.write_text('last good snapshot')
            with self.assertRaises(ValueError):
                refresh(output, fetch=lambda: '<html>Unavailable</html>')
            self.assertEqual(output.read_text(), 'last good snapshot')
            self.assertEqual(list(output.parent.iterdir()), [output])


if __name__ == '__main__':
    unittest.main()
