import unittest
import json
import sys

loader = unittest.defaultTestLoader
suite = loader.loadTestsFromName('tests.test_project')
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

summary = {
    'success': result.wasSuccessful(),
    'failures': len(result.failures),
    'errors': len(result.errors),
    'testsRun': result.testsRun,
}

with open('test_results_summary.json', 'w') as f:
    json.dump(summary, f)

print('WROTE test_results_summary.json')
sys.exit(0 if result.wasSuccessful() else 1)
