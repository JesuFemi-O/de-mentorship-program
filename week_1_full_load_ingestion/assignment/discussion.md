# Week 1 Discussion - Full-Load in the Wild

Find a real system, dataset, or workflow - from your job, a side project, or something you've read about - where full-load is either the right pattern or the wrong one.

Come to the next session ready to present in 2-3 minutes. Use the prompts below to structure your thinking. Fill in your answers here before the session.

---

## 1. What is the source?

> Describe the data: what it contains, how it is delivered (API, file drop, database export, etc.), how often it is published, and roughly how large it is.

_Your answer here._

---

## 2. Why does full-load fit - or not fit?

> Think about:
> - **Size** - is it cheap to reload everything, or would that be prohibitive?
> - **Frequency** - how often does the source publish, and does that match how often you need fresh data?
> - **History** - does the source give you the complete current state, or only changes since last time?
> - **Change information** - does the source tell you what changed (CDC, delta files), or only the current snapshot?

_Your answer here._

---

## 3. What breaks if you get the pattern wrong?

> Pick the wrong pattern and reason through the failure mode:
> - If full-load is correct but you tried incremental - what goes wrong?
> - If incremental is correct but you used full-load - what goes wrong?

_Your answer here._

---

## Example (do not copy - find your own)

**Source:** A retail point-of-sale system exports a nightly `products.csv` - all active SKUs, current prices, and stock levels as of close of business.

**Why full-load fits:** The file is always a complete snapshot (not a delta). Stock levels fluctuate continuously, so yesterday's values in the table would be stale by morning anyway. The file is ~50 000 rows - cheap to reload. There is no change feed available.

**What breaks if you get it wrong:** If you try incremental, you need a way to detect which rows changed. The source gives you none. You would have to diff the entire file yourself, which is more complex than a simple truncate-and-reload and still requires keeping the previous snapshot around. Full-load is simpler and correct here.
