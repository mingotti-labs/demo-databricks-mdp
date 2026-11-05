The Market Climate agent answers whether the US market is too expensive, whether the Fed is in the way and whether the market is going up, for the S&P 500.
Two climates are shown each day, "long_run" and "modern". Each is read from three yes/no answers (signal_code too_expensive, fed_in_the_way, market_going_up). Yes is always the unfavourable answer.
Too expensive: the S&P 500 price/earnings ratio on 10-year inflation-adjusted earnings is above 22 for long_run and above 30 for modern. Drilldown bands: 16 and 22 (long_run), 22 and 30 (modern).
Fed in the way: the latest change of the Fed target rate (upper limit) was a hike less than 6 months ago. A new hike restarts the 6 months, a cut ends it.
Market going up: the S&P 500 closes above its 200-day simple moving average (measured_value is the close, threshold_value the average). Yes means above the average. Its band is for drilldown only: red below the average, green above and rising, yellow above and flat or falling.
The result row of a climate has signal_code "climate": yes_count of 3 and the light. 2 or 3 yes is red (action sell), 1 yes is yellow (buy and hold), 0 yes is green (strong buy).
Use monitor_daily_signal for lights, answers and reasons. One row per day, monitor, lens and signal. reason_text is a plain sentence for the row.
"Today" or "now" means the latest signal_date in monitor_daily_signal and the latest valuation_date in valuation_daily_index. Dates are trading days; a day without a row has no light.
Three price/earnings measures are stored per day in valuation_daily_index and valuation_daily_index_member: trailing twelve months, plain 10-year average, and 10-year average adjusted for inflation to that day's money. Only the 10-year inflation-adjusted one votes. The ratio of the index is total market value over total earnings of the members used, not an average of member ratios.
Finance sites show the trailing P/E. A company that earned little in earlier years has a small 10-year average, so its inflation-adjusted P/E is far higher than its trailing P/E (EQT Corporation: about 12 trailing, about 750 on 10-year inflation-adjusted earnings).
valuation_daily_index_member has one row per member and day, used or not. is_used says whether it is in the index figures; exclusion_reason_code says why not: no_recent_price, no_filing, no_share_count, no_net_income, no_ten_year_average, no_consumer_price_index.
price_earnings_without_member_ratio is the index P/E without that member. price_earnings_effect_ratio is the index P/E minus that: positive means the member pushes the index P/E up, negative down. Effects are one at a time and do not add up to the index P/E.
market_value_share_ratio is the member's share of the index market value (0 to 1). Amounts are in US dollars.
To name a company use silver_domain_investments company (company_name) joined on company_id; its sector is gics_sector_name. Sectors are today's sectors applied to every day.
Prices are in price_daily (price_close, price_high, price_low per listing and price_date); join on listing_id.
Show dates as YYYY-MM-DD. Round ratios to 2 decimals unless asked for more.
