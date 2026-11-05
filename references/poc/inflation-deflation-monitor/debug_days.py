"""Debug (read only): which star limits the rated days."""
import sys
from pathlib import Path

from probe import run

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from common.inflation_signals_sql import inflation_signal_query  # noqa: E402
from common.inflation_sql import market_rate_indicator_query  # noqa: E402

domain = "mdp_prd.silver_domain_investments"
q = inflation_signal_query(domain, f"({market_rate_indicator_query(domain + '.')})")
q = q.replace("HAVING count(*) = 4", "").replace("FROM stars s JOIN rated c ON c.signal_date = s.signal_date", "FROM stars s")
q = q.replace("""    ), rated AS (""", """    ), rated AS (""")
print(run("DEFAULT", f"SELECT signal_code, year(signal_date) y, count(*) FROM ({q}) WHERE signal_code <> 'rating' AND year(signal_date) IN (2010, 2024) GROUP BY 1, 2 ORDER BY 2, 1"))
print(run("DEFAULT", f"SELECT rate_code, year(indicator_date), count(*), count_if(observation_date >= date_sub(indicator_date, 7)) FROM ({market_rate_indicator_query(domain + '.')}) WHERE year(indicator_date) IN (2010, 2024) GROUP BY 1, 2 ORDER BY 2, 1"))
