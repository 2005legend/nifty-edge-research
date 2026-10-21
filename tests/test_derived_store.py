import duckdb
import pandas as pd

from quantdesk.derived.store import DerivedStore


def frame(rows):
    return pd.DataFrame(rows, columns=["target", "x"])


def test_written_tables_read_back_with_rows_and_hash_in_the_manifest(tmp_path):
    store = DerivedStore(tmp_path)
    store.write_frame("t", frame([("A", 1), ("B", 2)]))
    assert store.read("t").sort_values("x")["x"].tolist() == [1, 2]
    entry = store.manifest()["t"]
    assert entry["rows"] == 2 and len(entry["hash"]) == 16


def test_the_hash_ignores_row_order_but_not_content(tmp_path):
    one, two, three = DerivedStore(tmp_path / "1"), DerivedStore(tmp_path / "2"), DerivedStore(tmp_path / "3")
    one.write_frame("t", frame([("A", 1), ("B", 2)]))
    two.write_frame("t", frame([("B", 2), ("A", 1)]))
    three.write_frame("t", frame([("A", 1), ("B", 3)]))
    assert one.manifest()["t"]["hash"] == two.manifest()["t"]["hash"]
    assert one.manifest()["t"]["hash"] != three.manifest()["t"]["hash"]
    assert one.data_hash() == two.data_hash() != three.data_hash()


def test_a_query_can_write_a_partitioned_table(tmp_path):
    store = DerivedStore(tmp_path)
    con = duckdb.connect()
    con.register("src", pd.DataFrame({"year": [2019, 2019, 2020], "v": [1, 2, 3]}))
    store.write_query("p", con, "select * from src", partition_by="year")
    assert sorted(store.read("p")["v"]) == [1, 2, 3]
    assert store.read("p", where="year = 2020")["v"].tolist() == [3]
    assert store.manifest()["p"]["rows"] == 3


def test_rewriting_a_table_replaces_it(tmp_path):
    store = DerivedStore(tmp_path)
    store.write_frame("t", frame([("A", 1)]))
    store.write_frame("t", frame([("B", 2)]))
    assert store.read("t")["target"].tolist() == ["B"]
