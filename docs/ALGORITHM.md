# Trading Algorithm

Details of the momentum-based trading algorithm used in the demo.

## Overview

This demo implements a simple momentum trading strategy that generates buy/sell signals based on hourly price movements and evaluates trade quality by comparing predictions with actual subsequent price changes.

**Note**: This is a simplified demonstration algorithm. Real trading strategies would be significantly more sophisticated and would consider factors like volume, volatility, market conditions, risk management, and more.

## Strategy Details

### 1. Price Change Calculation

For each hourly timestamp, we calculate:

```python
price_change = current_price - previous_price
price_change_pct = (price_change / previous_price) * 100
```

### 2. Signal Generation

Signals are generated based on price momentum thresholds:

| Condition                  | Signal   | Rationale                |
| -------------------------- | -------- | ------------------------ |
| `price_change_pct > 0.5%`  | **BUY**  | Strong upward momentum   |
| `price_change_pct < -0.5%` | **SELL** | Strong downward momentum |
| Otherwise                  | **HOLD** | Weak or no momentum      |

**Parameters**:
- Buy threshold: 0.5% increase
- Sell threshold: 0.5% decrease
- These are configurable in the code

### 3. Trade Quality Evaluation

After generating signals, we evaluate whether the trade would have been profitable by looking at the next period's price movement:

```python
next_price_change_pct = next_period_price_change

if signal == 'buy' and next_price_change_pct > 0:
    quality = 'good'  # Bought before price increase
elif signal == 'sell' and next_price_change_pct < 0:
    quality = 'good'  # Sold before price decrease
elif signal == 'buy' and next_price_change_pct < 0:
    quality = 'bad'   # Bought before price decrease
elif signal == 'sell' and next_price_change_pct > 0:
    quality = 'bad'   # Sold before price increase
else:
    quality = 'neutral'  # Hold or inconclusive
```

## Metrics

For each contract, we calculate:

### Trade Statistics
- **Total Trades**: Count of non-hold signals
- **Good Trades**: Profitable signals count
- **Bad Trades**: Unprofitable signals count
- **Success Rate**: `(good_trades / total_trades) * 100`

### Output Data
Each contract's analysis includes:
- Timestamp
- Price at each hour
- Price change (absolute and percentage)
- Signal (buy/sell/hold)
- Next period's price change
- Trade quality (good/bad/neutral)
- Summary statistics

## Example

Given hourly prices for AAPL:

```
Time    Price   Change%  Signal  Next%   Quality
09:30   150.00    -        -       -        -
10:30   151.00   +0.67%   BUY    +0.33%   GOOD
11:30   151.50   +0.33%   HOLD   -0.66%   NEUTRAL
12:30   150.50   -0.66%   SELL   -0.33%   GOOD
13:30   150.00   -0.33%   HOLD   +0.67%   NEUTRAL
14:30   151.00   +0.67%   BUY    -0.33%   BAD
15:30   150.50   -0.33%   HOLD     -      NEUTRAL
```

Summary:
- Total Trades: 3 (2 buy, 1 sell)
- Good Trades: 2
- Bad Trades: 1
- Success Rate: 66.67%

## Limitations & Disclaimers

### This is a Demo Algorithm
⚠️ **Not for real trading**: This algorithm is purely for demonstrating Prefect's orchestration capabilities, not for actual trading decisions.

### Known Limitations
1. **No Risk Management**: No stop losses, position sizing, or risk limits
2. **No Market Context**: Ignores market conditions, news, fundamentals
3. **Hindsight Bias**: Evaluates trades with future data (look-ahead bias)
4. **Transaction Costs**: Ignores fees, slippage, spreads
5. **Simple Thresholds**: Fixed 0.5% threshold may not suit all contracts
6. **No Time Decay**: Doesn't consider holding periods
7. **Single Indicator**: Only uses price momentum
8. **No Portfolio Management**: Analyzes contracts independently

## Extending the Algorithm

The architecture supports more sophisticated strategies:

### Task A: Load & Prepare
Enhance data loading to include:
- Volume data
- Technical indicators
- Market indices
- News sentiment

### Task B: Analyze Trades
Implement advanced strategies:
- Multiple timeframe analysis
- Machine learning models
- Statistical arbitrage
- Mean reversion
- Pairs trading

### Task C: Aggregate & Save
Add more output:
- Risk metrics (Sharpe ratio, max drawdown)
- Portfolio-level statistics
- Performance attribution
- Backtesting results

## Code Location

The algorithm is implemented in:
- **File**: `flows/analyze_contract_flow.py`
- **Function**: `analyze_trades()`
- **Lines**: ~70-110

To modify the strategy, edit the `analyze_trades` task:

```python
@task(tags=["analyze"])
def analyze_trades(contract: str, df: pd.DataFrame):
    # Your custom algorithm here
    pass
```

## Resources

For learning about real algorithmic trading:
- [QuantConnect](https://www.quantconnect.com/)
- [Zipline](https://www.zipline.io/)
- [Backtrader](https://www.backtrader.com/)
- [Alpaca Markets](https://alpaca.markets/)

