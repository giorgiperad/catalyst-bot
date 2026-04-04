"""
Market price models for simulation.

Each model implements generate(n_ticks, starting_price) -> List[float].
Models can be composed for complex scenarios (e.g. trending + volatile).

All models are purely stdlib — no numpy, no pandas.
"""

import math
import random
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Base protocol / interface
# ---------------------------------------------------------------------------

class PriceModel:
    """Abstract base class for price models.

    Subclasses must implement generate(n_ticks, starting_price).
    """

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a list of n_ticks prices starting near starting_price.

        Args:
            n_ticks: Number of price ticks to generate.
            starting_price: The initial reference price.

        Returns:
            List of floats, length == n_ticks.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. RandomWalk
# ---------------------------------------------------------------------------

class RandomWalk(PriceModel):
    """Geometric Brownian motion — the simplest realistic price model.

    At each tick the price is multiplied by exp(sigma * Z) where Z ~ N(0,1).
    Price is floored at 1% of starting_price to prevent blow-up to zero.
    """

    def __init__(self, volatility_pct_per_tick: float = 0.005):
        """Initialise the random walk.

        Args:
            volatility_pct_per_tick: Standard deviation of log-returns per
                tick, expressed as a fraction (0.005 = 0.5% per tick).
        """
        self.volatility = volatility_pct_per_tick

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a Brownian-motion price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.01
        for _ in range(n_ticks):
            shock = random.gauss(0.0, self.volatility)
            price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)
        return prices


# ---------------------------------------------------------------------------
# 2. TrendedWalk
# ---------------------------------------------------------------------------

class TrendedWalk(PriceModel):
    """Directional drift (trend) plus Gaussian noise.

    A positive drift_pct_per_tick produces an uptrend; negative = downtrend.
    Under the hood this is GBM with a non-zero mean log-return.
    """

    def __init__(
        self,
        drift_pct_per_tick: float = 0.001,
        volatility_pct_per_tick: float = 0.004,
    ):
        """Initialise the trended walk.

        Args:
            drift_pct_per_tick: Mean log-return per tick (positive = uptrend).
            volatility_pct_per_tick: Std-dev of log-returns per tick.
        """
        self.drift = drift_pct_per_tick
        self.volatility = volatility_pct_per_tick

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a trended Brownian price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001
        for _ in range(n_ticks):
            shock = random.gauss(self.drift, self.volatility)
            price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)
        return prices


# ---------------------------------------------------------------------------
# 3. MeanReverting
# ---------------------------------------------------------------------------

class MeanReverting(PriceModel):
    """Ornstein-Uhlenbeck mean-reverting process.

    Price is pulled back toward mean_price at each step with speed
    reversion_speed, then a Gaussian noise term is added.

    dp = reversion_speed * (mean - p) + volatility * dW
    """

    def __init__(
        self,
        mean_price: Optional[float] = None,
        reversion_speed: float = 0.05,
        volatility: float = 0.004,
    ):
        """Initialise the mean-reverting model.

        Args:
            mean_price: Long-run equilibrium price. Defaults to starting_price
                if None.
            reversion_speed: Strength of pull toward the mean (0–1). Higher
                values revert faster.
            volatility: Std-dev of the noise term per tick.
        """
        self.mean_price = mean_price
        self.reversion_speed = reversion_speed
        self.volatility = volatility

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate an Ornstein-Uhlenbeck price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        mean = self.mean_price if self.mean_price is not None else starting_price
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.01
        for _ in range(n_ticks):
            drift = self.reversion_speed * (mean - price)
            noise = random.gauss(0.0, self.volatility) * price
            price = price + drift + noise
            price = max(price, floor)
            prices.append(price)
        return prices


# ---------------------------------------------------------------------------
# 4. SuddenCrash
# ---------------------------------------------------------------------------

class SuddenCrash(PriceModel):
    """Normal random walk that suddenly crashes and then slowly recovers.

    Three phases:
      1. Pre-crash: standard Brownian motion.
      2. Crash: price drops crash_pct% over crash_duration ticks.
      3. Post-crash: slow upward drift (recovery) with normal noise.
    """

    def __init__(
        self,
        crash_tick_fraction: float = 0.3,
        crash_pct: float = 0.40,
        crash_duration: int = 5,
        recovery_pct_per_tick: float = 0.002,
        pre_volatility: float = 0.004,
    ):
        """Initialise the crash model.

        Args:
            crash_tick_fraction: Fraction of total ticks at which the crash
                begins (0.3 = 30% through the series).
            crash_pct: Fractional price drop during the crash (0.40 = 40%
                drop from pre-crash level).
            crash_duration: Number of ticks over which the crash unfolds.
            recovery_pct_per_tick: Mean log-return during post-crash recovery
                phase (positive drift).
            pre_volatility: Volatility during the pre-crash random walk.
        """
        self.crash_tick_fraction = crash_tick_fraction
        self.crash_pct = crash_pct
        self.crash_duration = crash_duration
        self.recovery_pct_per_tick = recovery_pct_per_tick
        self.pre_volatility = pre_volatility

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a crash-and-recovery price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        crash_start = int(n_ticks * self.crash_tick_fraction)
        crash_end = crash_start + self.crash_duration
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001

        for tick in range(n_ticks):
            if tick < crash_start:
                # Pre-crash: normal random walk
                shock = random.gauss(0.0, self.pre_volatility)
                price = price * math.exp(shock)
            elif tick < crash_end:
                # Crash phase: linear step-down each tick
                step_drop = self.crash_pct / self.crash_duration
                price = price * (1.0 - step_drop)
                noise = random.gauss(0.0, self.pre_volatility * 0.5)
                price = price * math.exp(noise)
            else:
                # Recovery phase: slow positive drift with normal noise
                shock = random.gauss(self.recovery_pct_per_tick, self.pre_volatility)
                price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 5. SuddenPump
# ---------------------------------------------------------------------------

class SuddenPump(PriceModel):
    """Normal random walk followed by a sudden price pump and slow decay.

    Three phases:
      1. Pre-pump: standard Brownian motion.
      2. Pump: price rises pump_pct% over pump_duration ticks.
      3. Post-pump: slow downward drift (decay) with normal noise.
    """

    def __init__(
        self,
        pump_tick_fraction: float = 0.3,
        pump_pct: float = 0.60,
        pump_duration: int = 3,
        decay_pct_per_tick: float = 0.003,
        pre_volatility: float = 0.004,
    ):
        """Initialise the pump model.

        Args:
            pump_tick_fraction: Fraction of total ticks at which the pump
                begins.
            pump_pct: Fractional price rise during the pump (0.60 = 60%
                gain from pre-pump level).
            pump_duration: Number of ticks over which the pump unfolds.
            decay_pct_per_tick: Mean log-return during post-pump decay
                phase (negative drift applied as positive decay).
            pre_volatility: Volatility during the pre-pump random walk.
        """
        self.pump_tick_fraction = pump_tick_fraction
        self.pump_pct = pump_pct
        self.pump_duration = pump_duration
        self.decay_pct_per_tick = decay_pct_per_tick
        self.pre_volatility = pre_volatility

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a pump-and-decay price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        pump_start = int(n_ticks * self.pump_tick_fraction)
        pump_end = pump_start + self.pump_duration
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001

        for tick in range(n_ticks):
            if tick < pump_start:
                shock = random.gauss(0.0, self.pre_volatility)
                price = price * math.exp(shock)
            elif tick < pump_end:
                step_gain = self.pump_pct / self.pump_duration
                price = price * (1.0 + step_gain)
                noise = random.gauss(0.0, self.pre_volatility * 0.5)
                price = price * math.exp(noise)
            else:
                # Slow decay back toward fair value
                shock = random.gauss(-self.decay_pct_per_tick, self.pre_volatility)
                price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 6. PumpAndDump
# ---------------------------------------------------------------------------

class PumpAndDump(PriceModel):
    """Classic pump-then-dump: sharp rise followed by a sharper crash.

    Three phases:
      1. Pre-pump: quiet random walk.
      2. Pump: rapid price rise over pump_duration ticks.
      3. Dump: price crashes from the peak over dump_duration ticks.
      4. Post-dump: residual random walk at depressed price.
    """

    def __init__(
        self,
        pump_tick_fraction: float = 0.25,
        pump_pct: float = 0.80,
        dump_tick_fraction: float = 0.45,
        dump_pct: float = 0.70,
        pump_duration: int = 5,
        dump_duration: int = 8,
        pre_volatility: float = 0.003,
    ):
        """Initialise the pump-and-dump model.

        Args:
            pump_tick_fraction: Fraction of total ticks at which the pump
                begins.
            pump_pct: Fractional price rise during the pump (0.80 = 80%).
            dump_tick_fraction: Fraction of total ticks at which the dump
                begins (must be > pump_tick_fraction + pump_duration/n).
            dump_pct: Fractional price drop from the pump peak (0.70 = 70%).
            pump_duration: Ticks over which the pump unfolds.
            dump_duration: Ticks over which the dump unfolds.
            pre_volatility: Background volatility throughout.
        """
        self.pump_tick_fraction = pump_tick_fraction
        self.pump_pct = pump_pct
        self.dump_tick_fraction = dump_tick_fraction
        self.dump_pct = dump_pct
        self.pump_duration = pump_duration
        self.dump_duration = dump_duration
        self.pre_volatility = pre_volatility

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a pump-and-dump price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        pump_start = int(n_ticks * self.pump_tick_fraction)
        pump_end = pump_start + self.pump_duration
        dump_start = int(n_ticks * self.dump_tick_fraction)
        dump_end = dump_start + self.dump_duration

        # Ensure dump starts after pump ends
        dump_start = max(dump_start, pump_end + 1)
        dump_end = dump_start + self.dump_duration

        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001

        for tick in range(n_ticks):
            if tick < pump_start:
                shock = random.gauss(0.0, self.pre_volatility)
                price = price * math.exp(shock)
            elif tick < pump_end:
                step_gain = self.pump_pct / self.pump_duration
                price = price * (1.0 + step_gain)
                noise = random.gauss(0.0, self.pre_volatility * 0.3)
                price = price * math.exp(noise)
            elif tick < dump_start:
                # Plateau with light noise at the top
                shock = random.gauss(0.0, self.pre_volatility * 0.5)
                price = price * math.exp(shock)
            elif tick < dump_end:
                step_drop = self.dump_pct / self.dump_duration
                price = price * (1.0 - step_drop)
                noise = random.gauss(0.0, self.pre_volatility * 0.5)
                price = price * math.exp(noise)
            else:
                # Post-dump residual walk at depressed price
                shock = random.gauss(0.0, self.pre_volatility)
                price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 7. SteppedPrice
# ---------------------------------------------------------------------------

class SteppedPrice(PriceModel):
    """Discrete step price model — common for thin/illiquid tokens.

    The price remains constant for ticks_per_step ticks, then jumps up or
    down by exactly step_size_pct.  Direction of each jump is random.
    This mimics a market where the only price changes come from taker orders
    hitting a thin book.
    """

    def __init__(
        self,
        step_size_pct: float = 0.01,
        ticks_per_step: int = 5,
    ):
        """Initialise the stepped price model.

        Args:
            step_size_pct: Fractional price movement per step (0.01 = 1%).
            ticks_per_step: Number of ticks between each price jump.
        """
        self.step_size_pct = step_size_pct
        self.ticks_per_step = max(1, ticks_per_step)

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a stepped price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001

        for tick in range(n_ticks):
            if tick > 0 and tick % self.ticks_per_step == 0:
                direction = 1 if random.random() < 0.5 else -1
                price = price * (1.0 + direction * self.step_size_pct)
                price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 8. RegimeSwitching
# ---------------------------------------------------------------------------

class RegimeSwitching(PriceModel):
    """Alternates between low-volatility and high-volatility regimes.

    Each regime lasts approximately regime_length_ticks ticks (exact boundary
    is fixed, not random, so results are reproducible per seed).
    Good for testing how the circuit breaker recovers after a spike.
    """

    def __init__(
        self,
        low_vol: float = 0.002,
        high_vol: float = 0.015,
        regime_length_ticks: int = 50,
    ):
        """Initialise the regime-switching model.

        Args:
            low_vol: Volatility in the calm regime.
            high_vol: Volatility in the turbulent regime.
            regime_length_ticks: Approximate number of ticks per regime.
        """
        self.low_vol = low_vol
        self.high_vol = high_vol
        self.regime_length_ticks = max(1, regime_length_ticks)

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a regime-switching price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.001

        for tick in range(n_ticks):
            regime_index = tick // self.regime_length_ticks
            # Even regimes = low vol, odd regimes = high vol
            vol = self.low_vol if regime_index % 2 == 0 else self.high_vol
            shock = random.gauss(0.0, vol)
            price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 9. DeadMarket
# ---------------------------------------------------------------------------

class DeadMarket(PriceModel):
    """Extremely quiet market — near-zero price movement.

    Tests requote stagnation: the bot should not churn through coins
    when the price barely moves.  The tiny positive drift represents
    the natural cost-of-carry / spread widening that occurs even in
    dead markets.
    """

    def __init__(
        self,
        drift: float = 0.0001,
        noise: float = 0.0001,
    ):
        """Initialise the dead market model.

        Args:
            drift: Mean log-return per tick (essentially zero).
            noise: Std-dev of log-returns per tick (essentially zero).
        """
        self.drift = drift
        self.noise = noise

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a near-motionless price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.5  # High floor: price shouldn't drift far

        for _ in range(n_ticks):
            shock = random.gauss(self.drift, self.noise)
            price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# 10. LiquidityCrisis
# ---------------------------------------------------------------------------

class LiquidityCrisis(PriceModel):
    """Normal market with a sudden liquidity spike representing a crisis.

    The crisis is modelled as a volatility explosion for crisis_duration
    ticks, during which price can swing wildly (wide bid-ask spread in a
    real market maps to erratic prints here).  After the crisis, volatility
    returns to the normal level and the market stabilises.
    """

    def __init__(
        self,
        crisis_tick_fraction: float = 0.5,
        crisis_vol_multiplier: float = 8.0,
        crisis_duration: int = 20,
        normal_volatility: float = 0.004,
    ):
        """Initialise the liquidity crisis model.

        Args:
            crisis_tick_fraction: Fraction of ticks at which the crisis
                begins.
            crisis_vol_multiplier: How many times the normal volatility
                spikes during the crisis.
            crisis_duration: Duration of the crisis in ticks.
            normal_volatility: Background volatility outside the crisis.
        """
        self.crisis_tick_fraction = crisis_tick_fraction
        self.crisis_vol_multiplier = crisis_vol_multiplier
        self.crisis_duration = crisis_duration
        self.normal_volatility = normal_volatility

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate a liquidity-crisis price series.

        Args:
            n_ticks: Number of ticks.
            starting_price: Initial price.

        Returns:
            List of prices length n_ticks.
        """
        crisis_start = int(n_ticks * self.crisis_tick_fraction)
        crisis_end = crisis_start + self.crisis_duration
        crisis_vol = self.normal_volatility * self.crisis_vol_multiplier

        prices: List[float] = []
        price = starting_price
        floor = starting_price * 0.01

        for tick in range(n_ticks):
            if crisis_start <= tick < crisis_end:
                vol = crisis_vol
            else:
                vol = self.normal_volatility
            shock = random.gauss(0.0, vol)
            price = price * math.exp(shock)
            price = max(price, floor)
            prices.append(price)

        return prices


# ---------------------------------------------------------------------------
# CompositeModel
# ---------------------------------------------------------------------------

class CompositeModel(PriceModel):
    """Concatenates multiple models, each running for a specified number of ticks.

    The starting price of each segment is the last price of the previous
    segment, so prices chain together continuously.

    Example::

        model = CompositeModel([
            (TrendedWalk(drift_pct_per_tick=0.002), 200),   # uptrend
            (SuddenCrash(crash_pct=0.5), 300),               # then crash
            (MeanReverting(), 200),                           # then stabilise
        ])
        prices = model.generate(700, 0.001)
    """

    def __init__(self, segments: List[Tuple[PriceModel, int]]):
        """Initialise a composite model.

        Args:
            segments: List of (model, n_ticks) tuples.  The total tick count
                passed to generate() is ignored — each segment contributes
                exactly its own n_ticks.  Pass n_ticks=0 to generate() when
                using CompositeModel (the value is unused).
        """
        self.segments = segments

    def generate(self, n_ticks: int, starting_price: float) -> List[float]:
        """Generate prices by chaining segment outputs.

        Args:
            n_ticks: Ignored — each segment contributes its own tick count.
                Pass 0 or any value; the result length = sum of segment ticks.
            starting_price: Starting price for the first segment.

        Returns:
            Concatenated list of prices from all segments.
        """
        all_prices: List[float] = []
        price = starting_price
        for model, seg_ticks in self.segments:
            if seg_ticks <= 0:
                continue
            segment_prices = model.generate(seg_ticks, price)
            all_prices.extend(segment_prices)
            if segment_prices:
                price = segment_prices[-1]
        return all_prices


# ---------------------------------------------------------------------------
# historical_replay
# ---------------------------------------------------------------------------

def historical_replay(prices: List[float]) -> List[float]:
    """Return a pre-recorded price series unchanged.

    Use this to feed real Dexie/TibetSwap price data into the simulation
    engine instead of a synthetic model.

    Args:
        prices: List of historical prices in chronological order.

    Returns:
        The same list (no transformation applied).
    """
    return list(prices)


# ---------------------------------------------------------------------------
# PRESET_MODELS
# ---------------------------------------------------------------------------

PRESET_MODELS = {
    "random_walk": RandomWalk(),
    "uptrend": TrendedWalk(drift_pct_per_tick=0.002),
    "downtrend": TrendedWalk(drift_pct_per_tick=-0.002),
    "mean_reverting": MeanReverting(),
    "crash": SuddenCrash(),
    "pump": SuddenPump(),
    "pump_and_dump": PumpAndDump(),
    "stepped": SteppedPrice(),
    "regime_switching": RegimeSwitching(),
    "dead": DeadMarket(),
    "liquidity_crisis": LiquidityCrisis(),
}
"""Preset model instances with sensible defaults.

Keys map directly to scenario names understood by the simulation runner.
"""
