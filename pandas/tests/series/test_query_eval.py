import pytest
import numpy as np
from pandas import Series, eval
import pandas._testing as tm

class TestSeriesEval:
    # smaller hits python, larger hits numexpr
    @pytest.mark.parametrize("n", [4, 4000])
    @pytest.mark.parametrize(
        "op_str,op,rop",
        [
            ("+", "__add__", "__radd__"),
            ("-", "__sub__", "__rsub__"),
            ("*", "__mul__", "__rmul__"),
            ("/", "__truediv__", "__rtruediv__"),
        ],
    )

    def test_ops(self, op_str, op, rop, n):
        # tst ops and reversed ops in evaluation
        # GH7198
        series = Series(1, index=range(n))
        series.iloc[0] = 2
        m = series.mean()

        base = Series(np.tile(m, n))

        expected = eval(f"base {op_str} series")

        # ops as strings
        result = eval(f"m {op_str} series")
        tm.assert_series_equal(result, expected)

        # these are commutative
        if op in ["+", "*"]:
            result = getattr(series, op)(m)
            tm.assert_series_equal(result, expected)

        # these are not
        elif op in ["-", "/"]:
            result = getattr(series, rop)(m)
            tm.assert_series_equal(result, expected)

    def test_series_sub_numexpr_path(self):
        # GH7192: Note we need a large number of rows to ensure this
        # goes through the numexpr path
        series = Series(np.random.randn(25000))
        series.iloc[0:5] = np.nan
        expected = 1 - np.isnan(series.iloc[0:25])
        result = (1 - np.isnan(series)).iloc[0:25]
        tm.assert_series_equal(result, expected)
    
    def test_query_non_str(self):
        # GH 11485
        series = Series({"A": [1, 2, 3]})

        msg = "expr must be a string to be evaluated"
        with pytest.raises(ValueError, match=msg):
            series.query(lambda x: x.A == 1)

        with pytest.raises(ValueError, match=msg):
            series.query(111)

    def test_query_empty_string(self):
        # GH 13139
        series = Series({"A": [1, 2, 3]})

        msg = "expr cannot be an empty string"
        with pytest.raises(ValueError, match=msg):
            series.query("")

    def test_eval_resolvers_as_list(self):
        # GH 14095
        series = Series(np.random.randn(10))
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        assert series.eval("a + b", resolvers=[dict1, dict2]) == dict1["a"] + dict2["b"]
        assert eval("a + b", resolvers=[dict1, dict2]) == dict1["a"] + dict2["b"]


class TestSeriesEvalWithSeries:
    def setup_method(self, method):
        self.series = Series(np.random.randn(3), index=["a", "b", "c"])

    def teardown_method(self, method):
        del self.series

    def test_simple_expr(self, parser, engine):
        res = self.series.eval("a + b", engine=engine, parser=parser)
        expect = self.series.a + self.series.b
        tm.assert_series_equal(res, expect)

    def test_bool_arith_expr(self, parser, engine):
        res = self.series.eval("a[a < 1] + b", engine=engine, parser=parser)
        expect = self.series.a[self.series.a < 1] + self.series.b
        tm.assert_series_equal(res, expect)

    @pytest.mark.parametrize("op", ["+", "-", "*", "/"])
    def test_invalid_type_for_operator_raises(self, parser, engine, op):
        series = Series({"a": [1, 2], "b": ["c", "d"]})
        msg = r"unsupported operand type\(s\) for .+: '.+' and '.+'"

        with pytest.raises(TypeError, match=msg):
            series.eval(f"a {op} b", engine=engine, parser=parser)
