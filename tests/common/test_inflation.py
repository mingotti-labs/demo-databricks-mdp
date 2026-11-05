from common.inflation import RATINGS, rating, ratings_values_sql


def test_rating_is_the_stars_on():
    assert [rating(n, 2.0) for n in range(5)] == [0, 1, 2, 3, 4]


def test_minus_one_only_with_no_star_and_prices_below_a_year_ago():
    assert rating(0, -0.1) == -1
    assert rating(0, 0.0) == 0
    assert rating(1, -3.0) == 1


def test_every_rating_has_a_band_and_a_label():
    assert sorted(RATINGS) == [-1, 0, 1, 2, 3, 4]
    assert RATINGS[-1] == ("blue", "Deflation")
    assert RATINGS[4][1] == "Increasing Inflation"


def test_values_sql_lists_every_rating():
    sql = ratings_values_sql()
    assert sql.count("(") == 6 and "'Deflation'" in sql
