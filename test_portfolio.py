import unittest
from datetime import date
from portfolio import account, read_transactions, xirr


class AccountingTests(unittest.TestCase):
    def parse(self, body):
        return read_transactions(('date,symbol,action,quantity,price,fees\n'+body).encode())

    def test_fifo_fees_and_partial_sale(self):
        rows = self.parse('2023-01-01,AAPL,BUY,10,100,10\n2023-02-01,AAPL,BUY,10,200,0\n2024-01-01,AAPL,SELL,15,250,5')
        result = account(rows, {'AAPL':300}, date(2024,1,2))
        self.assertAlmostEqual(result['holdings'][0]['cost_basis'],1000)
        self.assertAlmostEqual(result['realized_gain'],1735)
        self.assertAlmostEqual(result['profit'],2235)

    def test_oversell(self):
        with self.assertRaises(ValueError):
            self.parse('2023-01-01,AAPL,SELL,1,100,0')

    def test_missing_quote(self):
        result = account(self.parse('2023-01-01,AAPL,BUY,1,100,0'), {})
        self.assertIsNone(result['profit'])
        self.assertIsNone(result['xirr'])

    def test_closed_position(self):
        result = account(self.parse('2023-01-01,AAPL,BUY,1,100,0\n2024-01-01,AAPL,SELL,1,110,0'), {})
        self.assertEqual(result['holdings'], [])
        self.assertAlmostEqual(result['xirr'], .1)

    def test_xirr(self):
        self.assertAlmostEqual(xirr([(date(2023,1,1),-100),(date(2024,1,1),110)]), .1)
        self.assertIsNone(xirr([(date(2023,1,1),-100)]))
        self.assertIsNone(xirr([(date(2023,1,1),-100),(date(2024,1,1),230),(date(2024,12,31),-132)]))

    def test_invalid_numbers(self):
        for value in ('nan','inf','-1','0'):
            with self.assertRaises(ValueError):
                self.parse(f'2023-01-01,AAPL,BUY,{value},100,0')


if __name__ == '__main__':
    unittest.main()
