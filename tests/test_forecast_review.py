"""Replay tests use only stdlib and synthetic evidence; no network or credentials."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from harness.forecast_review import REQUIRED, review_ledger

AS_OF = '2026-10-10T12:00:00+00:00'


def forecast(**changes):
    row = {k: '' for k in REQUIRED}
    row.update(market='US', venue='TEST', ticker='SYNTH', forecast_id='case-1', report_date='2026-09-30',
               as_of='2026-09-30T14:00:00Z', horizon_type='week_end',
               reference_close_date='2026-09-29', reference_close='100',
               reference_source='fixture:reference', forecast_target_date='2026-10-09',
               forecast_direction='up', forecast_range_low='105', forecast_range_high='110',
               probability_up='0.8', actual_close_date='2026-10-09', actual_close='110',
               actual_source='fixture:actual', actual_available_at='2026-10-09T22:00:00Z',
               status='pending', realized_return_pct='999', direction_hit='false', range_hit='false')
    row.update(changes)
    return row


class ForecastReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / 'ledger.csv'

    def write(self, rows):
        headers = sorted(set().union(*(row.keys() for row in rows)))
        with self.ledger.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        return self.ledger

    def review(self, rows, as_of=AS_OF):
        return review_ledger(self.write(rows), as_of)

    def test_recomputes_outcomes_and_horizon_denominators(self):
        result = self.review([forecast(), forecast(forecast_id='next', horizon_type='next_session',
                            forecast_direction='flat', probability_up='', actual_close='105')])
        self.assertTrue(result['valid'])
        self.assertAlmostEqual(result['rows'][0]['realized_return_pct'], 10)
        self.assertTrue(result['rows'][0]['direction_hit'])
        self.assertTrue(result['rows'][0]['range_hit'])
        self.assertAlmostEqual(result['rows'][0]['brier_score'], .04)
        self.assertIsNone(result['rows'][1]['direction_hit'])
        self.assertEqual(result['by_horizon']['next_session']['direction']['denominator'], 0)
        self.assertEqual(result['summary']['direction']['denominator'], 1)
        self.assertEqual(result['summary']['range']['hits'], 2)

    def test_down_zero_and_missing_range(self):
        rows = [forecast(forecast_id='down', forecast_direction='down', actual_close='90'),
                forecast(forecast_id='zero', actual_close='100', forecast_range_low='', forecast_range_high='')]
        result = self.review(rows)
        self.assertTrue(result['rows'][0]['direction_hit'])
        self.assertFalse(result['rows'][1]['direction_hit'])
        self.assertIsNone(result['rows'][1]['brier_score'])
        self.assertEqual(result['summary']['range']['denominator'], 1)

    def test_pending_mature_and_abstentions(self):
        empty = dict(actual_close='', actual_close_date='', actual_source='', actual_available_at='')
        rows = [forecast(forecast_id='pending', forecast_target_date='2026-10-20', **empty),
                forecast(forecast_id='mature', **empty),
                forecast(forecast_id='abstain', status='abstain'),
                forecast(forecast_id='unavailable', forecast_direction='data_unavailable',
                         reference_close='', reference_close_date='', reference_source='', **empty)]
        result = self.review(rows)
        self.assertTrue(result['valid'])
        self.assertEqual([r['status'] for r in result['rows']], ['pending', 'not_scored', 'abstain', 'data_unavailable'])
        self.assertEqual(result['summary']['direction']['denominator'], 0)
        self.assertEqual(result['summary']['coverage']['fraction'], 0)

    def test_same_day_target_stays_pending_until_target_close(self):
        row = forecast(report_date='2026-10-10', as_of='2026-10-10T15:00:00+08:00',
                       forecast_target_date='2026-10-10',
                       forecast_target_close_at='2026-10-10T16:00:00+08:00',
                       actual_close_date='', actual_close='', actual_source='', actual_available_at='')
        before_close = self.review([row], '2026-10-10T15:59:59+08:00')
        self.assertTrue(before_close['valid'])
        self.assertEqual(before_close['rows'][0]['status'], 'pending')
        at_close = self.review([row], '2026-10-10T16:00:00+08:00')
        self.assertTrue(at_close['valid'])
        self.assertEqual(at_close['rows'][0]['status'], 'not_scored')
        self.assertIn('no actual data', at_close['rows'][0]['reason'])

    def test_same_day_target_requires_close_and_preclose_forecast(self):
        base = dict(report_date='2026-10-10', forecast_target_date='2026-10-10',
                    actual_close_date='', actual_close='', actual_source='', actual_available_at='')
        no_close = self.review([forecast(**base)], '2026-10-10T15:59:00+08:00')
        self.assertFalse(no_close['valid'])
        self.assertIn('requires forecast_target_close_at', no_close['errors'][0]['error'])

        close = '2026-10-10T16:00:00+08:00'
        for issued_at in ('2026-10-10T16:00:00+08:00', '2026-10-10T16:00:01+08:00'):
            with self.subTest(issued_at=issued_at):
                result = self.review([forecast(**base, as_of=issued_at,
                                               forecast_target_close_at=close)],
                                     '2026-10-10T16:01:00+08:00')
                self.assertFalse(result['valid'])
                self.assertIn('must be before forecast_target_close_at', result['errors'][0]['error'])

    def test_target_close_uses_its_own_local_date_and_requires_timezone(self):
        base = dict(report_date='2026-10-10', as_of='2026-10-10T15:00:00+08:00',
                    forecast_target_date='2026-10-10', actual_close_date='', actual_close='',
                    actual_source='', actual_available_at='')
        for close in ('2026-10-09T23:59:00-04:00', '2026-10-10T16:00:00'):
            with self.subTest(close=close):
                result = self.review([forecast(**base, forecast_target_close_at=close)],
                                     '2026-10-10T15:30:00+08:00')
                self.assertFalse(result['valid'])

    def test_actual_availability_cannot_precede_target_close(self):
        row = forecast(report_date='2026-10-10', as_of='2026-10-10T15:00:00+08:00',
                       forecast_target_date='2026-10-10',
                       forecast_target_close_at='2026-10-10T16:00:00+08:00',
                       actual_close_date='2026-10-10', actual_close='110', actual_source='fixture:actual',
                       actual_available_at='2026-10-10T15:59:00+08:00')
        result = self.review([row], '2026-10-10T16:01:00+08:00')
        self.assertFalse(result['valid'])
        self.assertIn('actual_available_at is before forecast_target_close_at', result['errors'][0]['error'])

        row['actual_available_at'] = '2026-10-10T16:00:00+08:00'
        result = self.review([row], '2026-10-10T16:01:00+08:00')
        self.assertTrue(result['valid'])
        self.assertEqual(result['rows'][0]['status'], 'scored')

    def test_future_target_without_close_timestamp_remains_pending(self):
        result = self.review([forecast(forecast_target_date='2026-10-20',
                                       actual_close_date='', actual_close='', actual_source='',
                                       actual_available_at='')], '2026-10-10T12:00:00Z')
        self.assertTrue(result['valid'])
        self.assertEqual(result['rows'][0]['status'], 'pending')

    def test_close_availability_and_ambiguous_basis(self):
        result = self.review([forecast(actual_available_at=''),
                              forecast(forecast_id='my', scoring_notes='US intraday snapshot; MY close')])
        self.assertTrue(result['valid'])
        self.assertEqual([r['status'] for r in result['rows']], ['not_scored', 'not_scored'])
        self.assertIn('availability', result['rows'][0]['reason'])
        self.assertIn('ambiguous', result['rows'][1]['reason'])
        pending = forecast(actual_close='', actual_close_date='', actual_source='', actual_available_at='', scoring_notes='intraday')
        self.assertEqual(self.review([pending], '2026-10-01T12:00:00Z')['rows'][0]['status'], 'pending')

    def test_invalid_numbers_dates_probabilities_ranges_and_status(self):
        bad = [dict(reference_close='nan'), dict(actual_close='inf'), dict(reference_close='0'),
               dict(actual_close='-1'), dict(probability_up='nan'), dict(probability_up='1.1'),
               dict(probability_up='-0.1'), dict(forecast_range_low='111'), dict(forecast_range_high=''),
               dict(forecast_range_low='inf'), dict(actual_close_date='2026-10-08'),
               dict(actual_close_date='20261009'), dict(forecast_target_date='2026-09-30'),
               dict(reference_close_date='2026-10-01'), dict(as_of='2026-09-30T14:00:00'),
               dict(as_of='2026-11-01T00:00:00Z'), dict(actual_available_at='2026-11-01T00:00:00Z'),
               dict(actual_available_at='2026-10-08T00:00:00Z'), dict(actual_available_at='2026-10-09T22:00:00'),
               dict(actual_source=''), dict(horizon_type='forever'), dict(status='made_up'),
               dict(reference_source=''), dict(forecast_direction='buy')]
        for changes in bad:
            with self.subTest(changes=changes):
                result = self.review([forecast(**changes)])
                self.assertFalse(result['valid'])
                self.assertEqual(result['rows'][0]['status'], 'invalid')
                self.assertEqual(result['summary']['direction']['denominator'], 0)
        self.assertFalse(self.review([forecast()], '2026-10-08T12:00:00Z')['valid'])

    def test_correlated_vintages_are_warned_without_deduplication(self):
        result = self.review([forecast(), forecast(forecast_id='revision')])
        self.assertTrue(result['valid'])
        self.assertEqual(result['summary']['total'], 2)
        self.assertEqual(result['summary']['unique_instrument_targets'], 1)
        self.assertEqual(result['warnings'][0]['issuance_count'], 2)
        self.assertEqual(result['summary']['direction']['denominator'], 2)

    def test_duplicate_ids_invalidate_both_rows(self):
        result = self.review([forecast(), forecast()])
        self.assertEqual(result['summary']['counts']['invalid'], 2)
        self.assertEqual(len(result['errors']), 2)
        self.assertFalse(self.review([forecast(forecast_id='')])['valid'])

    def test_malformed_csv_and_headers(self):
        self.write([forecast()])
        with self.ledger.open('a') as stream:
            stream.write('too,few,columns\n')
        self.assertFalse(review_ledger(self.ledger, AS_OF)['valid'])
        self.ledger.write_text('forecast_id,forecast_id\na,b\n')
        self.assertFalse(review_ledger(self.ledger, AS_OF)['valid'])
        self.write([forecast()])
        with self.ledger.open('a') as stream:
            stream.write('"unterminated\n')
        self.assertFalse(review_ledger(self.ledger, AS_OF)['valid'])

    def test_empty_ledger_and_missing_identity_are_invalid(self):
        self.write([forecast()])
        header = self.ledger.read_text().splitlines()[0]
        self.ledger.write_text(header + '\n')
        result = review_ledger(self.ledger, AS_OF)
        self.assertFalse(result['valid'])
        self.assertIn('no forecast rows', result['errors'][0]['error'])
        for field in ('market', 'venue', 'ticker'):
            with self.subTest(field=field):
                self.assertFalse(self.review([forecast(**{field: ''})])['valid'])

    def test_review_timestamp_requires_timezone(self):
        self.write([forecast()])
        with self.assertRaises(ValueError):
            review_ledger(self.ledger, '2026-10-10T12:00:00')

    def test_cli_json_output_exit_status_and_read_only(self):
        self.write([forecast()])
        original = self.ledger.read_bytes()
        output = Path(self.temp.name) / 'summary.json'
        command = [sys.executable, '-m', 'harness.forecast_review', '--ledger', str(self.ledger), '--as-of', AS_OF]
        run = subprocess.run(command + ['--output', str(output)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), json.loads(output.read_text()))
        self.assertEqual(self.ledger.read_bytes(), original)
        run = subprocess.run(command + ['--output', str(self.ledger)], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(self.ledger.read_bytes(), original)
        alias = Path(self.temp.name) / 'alias.csv'
        os.link(self.ledger, alias)
        run = subprocess.run(command + ['--output', str(alias)], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(self.ledger.read_bytes(), original)
        self.write([forecast(actual_source='')])
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertFalse(json.loads(run.stdout)['valid'])
        run = subprocess.run(command[:-1] + ['2026-10-10'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)


if __name__ == '__main__':
    unittest.main()
