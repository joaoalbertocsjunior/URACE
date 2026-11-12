"""Tests for PROVIDER_RATE_TABLE and provider_rate."""
import unittest


class TestProviderRateTable(unittest.TestCase):
    def test_anthropic_sonnet(self):
        from urace.cost_model import PROVIDER_RATE_TABLE
        rates = PROVIDER_RATE_TABLE['anthropic']['claude-sonnet-4-6']
        self.assertEqual(rates['input_per_1m'], 3.0)
        self.assertEqual(rates['output_per_1m'], 15.0)

    def test_openai_gpt4o(self):
        from urace.cost_model import PROVIDER_RATE_TABLE
        rates = PROVIDER_RATE_TABLE['openai']['gpt-4o']
        self.assertEqual(rates['input_per_1m'], 5.0)
        self.assertEqual(rates['output_per_1m'], 15.0)

    def test_mistral_large(self):
        from urace.cost_model import PROVIDER_RATE_TABLE
        rates = PROVIDER_RATE_TABLE['mistral']['mistral-large-latest']
        self.assertEqual(rates['input_per_1m'], 4.0)
        self.assertEqual(rates['output_per_1m'], 12.0)

    def test_all_have_required_keys(self):
        from urace.cost_model import PROVIDER_RATE_TABLE
        for provider, models in PROVIDER_RATE_TABLE.items():
            for model, rates in models.items():
                self.assertIn('input_per_1m', rates, f"{provider}/{model} missing input_per_1m")
                self.assertIn('output_per_1m', rates, f"{provider}/{model} missing output_per_1m")


class TestProviderRate(unittest.TestCase):
    def test_known(self):
        from urace.cost_model import provider_rate
        r = provider_rate('openai', 'gpt-4-turbo')
        self.assertIsNotNone(r)
        self.assertEqual(r['input_per_1m'], 10.0)

    def test_unknown_provider(self):
        from urace.cost_model import provider_rate
        self.assertIsNone(provider_rate('unknown-provider', 'model'))

    def test_unknown_model(self):
        from urace.cost_model import provider_rate
        self.assertIsNone(provider_rate('openai', 'gpt-99'))

    def test_haiku(self):
        from urace.cost_model import provider_rate
        r = provider_rate('anthropic', 'claude-haiku-4-5')
        self.assertIsNotNone(r)
        self.assertEqual(r['input_per_1m'], 0.8)

    def test_mistral_small(self):
        from urace.cost_model import provider_rate
        r = provider_rate('mistral', 'mistral-small-latest')
        self.assertEqual(r['output_per_1m'], 3.0)


if __name__ == '__main__':
    unittest.main()
