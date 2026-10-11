"""Portfolio accounting independent of market and UI services."""
import csv
import io
import math
import re
from collections import defaultdict, deque
from datetime import date


def read_transactions(data, today=None):
    today = today or date.today()
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    required = {'date', 'symbol', 'action', 'quantity', 'price'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError('CSV requires date,symbol,action,quantity,price; fees is optional.')
    rows = []
    for number, raw in enumerate(reader, 2):
        try:
            day = date.fromisoformat(raw['date'].strip())
            symbol = raw['symbol'].strip().upper()
            action = raw['action'].strip().upper()
            quantity, price = float(raw['quantity']), float(raw['price'])
            fees = float(raw.get('fees', '') or 0)
            if day > today or not re.fullmatch(r'[A-Z][A-Z0-9.\-^]{0,14}', symbol):
                raise ValueError('invalid date or ticker')
            if action not in ('BUY', 'SELL') or not all(math.isfinite(v) for v in (quantity, price, fees)):
                raise ValueError('invalid action or numeric value')
            if quantity <= 0 or price <= 0 or fees < 0 or (action == 'SELL' and fees > quantity * price):
                raise ValueError('quantity and price must be positive; fees must be nonnegative and below sale value')
            rows.append(dict(date=day, symbol=symbol, action=action, quantity=quantity, price=price, fees=fees))
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            raise ValueError(f'Row {number}: {exc}') from exc
    if not rows:
        raise ValueError('CSV contains no transactions.')
    rows.sort(key=lambda row: row['date'])  # Stable: same-day CSV order is preserved.
    account(rows, {})  # Validate chronological ownership before requesting prices.
    return rows


def xirr(flows):
    """Return a unique annualized root; None for absent or ambiguous roots."""
    grouped = defaultdict(float)
    for day, value in flows:
        grouped[day] += value
    flows = sorted((d, v) for d, v in grouped.items() if abs(v) > 1e-10)
    if len(flows) < 2 or not any(v < 0 for _, v in flows) or not any(v > 0 for _, v in flows):
        return None
    origin = flows[0][0]
    times = [((d - origin).days / 365.0, v) for d, v in flows]
    def npv(log_rate):
        return sum(v * math.exp(max(-700, min(700, -log_rate * t))) for t, v in times)
    roots = []
    left, fleft = -14.0, npv(-14.0)
    for i in range(1, 561):
        right = -14 + i * .05
        fright = npv(right)
        if fleft == 0:
            roots.append(left)
        elif fleft * fright < 0:
            lo, hi = left, right
            for _ in range(80):
                mid = (lo + hi) / 2
                if npv(lo) * npv(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            roots.append((lo + hi) / 2)
        left, fleft = right, fright
    unique = []
    for root in roots:
        if not unique or abs(root - unique[-1]) > 1e-6:
            unique.append(root)
    return math.expm1(unique[0]) if len(unique) == 1 else None


def account(rows, prices, as_of=None):
    lots = defaultdict(deque)
    realized = defaultdict(float)
    invested = proceeds = 0.0
    flows = []
    for row in rows:
        symbol, qty = row['symbol'], row['quantity']
        gross = qty * row['price']
        if row['action'] == 'BUY':
            cost = gross + row['fees']
            lots[symbol].append([qty, cost / qty])
            invested += cost
            flows.append((row['date'], -cost))
        else:
            if qty > sum(lot[0] for lot in lots[symbol]) + 1e-8:
                raise ValueError(f"{row['date']}: sale of {symbol} exceeds shares owned. Short positions are unsupported.")
            remaining, basis = qty, 0.0
            while remaining > 1e-8:
                lot = lots[symbol][0]
                used = min(remaining, lot[0])
                basis += used * lot[1]
                remaining -= used
                lot[0] -= used
                if lot[0] < 1e-8:
                    lots[symbol].popleft()
            net = gross - row['fees']
            realized[symbol] += net - basis
            proceeds += net
            flows.append((row['date'], net))
    holdings, missing = [], []
    for symbol in sorted(lots):
        qty = sum(lot[0] for lot in lots[symbol])
        if qty < 1e-8:
            continue
        basis = sum(lot[0] * lot[1] for lot in lots[symbol])
        price = prices.get(symbol)
        if price is None or not math.isfinite(price) or price <= 0:
            price = None
            missing.append(symbol)
        value = qty * price if price is not None else None
        holdings.append(dict(symbol=symbol, shares=qty, cost_basis=basis, price=price, value=value,
                             unrealized_gain=None if value is None else value-basis,
                             realized_gain=realized[symbol]))
    value = sum(h['value'] or 0 for h in holdings)
    terminal_day = as_of or date.today()
    if terminal_day < rows[-1]['date']:
        raise ValueError('Valuation date precedes the final transaction.')
    profit = None if missing else value + proceeds - invested
    return dict(holdings=holdings, missing=missing, invested=invested, proceeds=proceeds,
                priced_value=value, value=None if missing else value,
                realized_gain=sum(realized.values()), profit=profit,
                return_pct=profit/invested if profit is not None and invested else None,
                xirr=None if missing else xirr(flows + [(terminal_day, value)]))
