from datetime import date

import pytest

from quantdesk.market.membership import load_membership

TODAY_NSE = ['ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE',
             'BEL', 'BHARTIARTL', 'BSE', 'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'ETERNAL', 'GRASIM', 'HCLTECH',
             'HDFCBANK', 'HDFCLIFE', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'INDIGO', 'INFY', 'ITC', 'JIOFIN',
             'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 'MAXHEALTH', 'NESTLEIND', 'NTPC', 'ONGC', 'POWERGRID',
             'RELIANCE', 'SBILIFE', 'SBIN', 'SHRIRAMFIN', 'SUNPHARMA', 'TATACONSUM', 'TATASTEEL', 'TCS', 'TECHM',
             'TITAN', 'TMPV', 'TRENT', 'ULTRACEMCO']  # NSE's ind_nifty50list.csv, 21 Oct 2026


@pytest.fixture(scope="module")
def membership():
    return load_membership()


def test_replaying_every_change_gives_todays_nse_list(membership):
    assert sorted(membership.members_on(date(2026, 10, 21))) == sorted(TODAY_NSE)


def test_the_index_has_fifty_members_on_every_day(membership):
    day = date(2019, 1, 1)
    while day <= date(2026, 10, 21):
        assert len(membership.members_on(day)) == 50, day
        day = date.fromordinal(day.toordinal() + 1)


def test_a_change_applies_from_its_effective_date(membership):
    assert "HDFC" in membership.members_on(date(2023, 7, 12))
    assert "HDFC" not in membership.members_on(date(2023, 7, 13))
    assert "LTIM" in membership.members_on(date(2023, 7, 13))


def test_backfill_symbols_use_todays_listing_and_skip_the_delisted(membership):
    symbols = membership.backfill_symbols()
    assert {"SAMMAANCAP", "INDUSTOWER", "LTM", "WIPRO", "YESBANK"} <= set(symbols)
    assert "HDFC" not in symbols and "LTIM" not in symbols
    assert membership.listing("INFRATEL") == "INDUSTOWER"
