"""Unit tests for Roslyn static code metrics calculation."""
import pytest
from src.analyzer.roslyn_client import RoslynClient


@pytest.fixture
def roslyn():
    return RoslynClient()


def test_basic_metrics_controlled_snippet(roslyn):
    code = """public class Sample
{
    public int Compute(int a, int b)
    {
        int x = a + 1;
        int y = b * 2;
        int sum = x + y;
        return sum;
    }
}
"""
    metrics = roslyn.calculate_method_metrics(code)
    assert metrics is not None
    assert metrics["parameter_count"] == 2
    assert metrics["local_variable_count"] == 3
    assert metrics["return_count"] == 1
    assert metrics["cyclomatic_complexity"] == 1
    assert metrics["max_nesting_depth"] == 0
    assert metrics["is_static"] is False


def test_complexity_and_nesting_depth(roslyn):
    code = """public class Sample
{
    public void ComplexProcess(int n)
    {
        if (n > 0)
        {
            while (n > 1)
            {
                if (n % 2 == 0)
                {
                    n = n / 2;
                }
                else
                {
                    n = 3 * n + 1;
                }
            }
        }
    }
}
"""
    metrics = roslyn.calculate_method_metrics(code)
    assert metrics is not None
    # 1 base + 2 if + 1 while = 4
    assert metrics["cyclomatic_complexity"] == 4
    # if -> while -> if = nesting depth 3
    assert metrics["max_nesting_depth"] == 3
    assert metrics["loop_count"] == 1
    assert metrics["if_count"] == 2


def test_expression_bodied_method(roslyn):
    code = "public int Square(int x) => x * x;"
    metrics = roslyn.calculate_method_metrics(code)
    assert metrics is not None
    assert metrics["parameter_count"] == 1
    assert metrics["return_count"] == 1
    assert metrics["cyclomatic_complexity"] == 1
    assert metrics["max_nesting_depth"] == 0


def test_local_functions_and_lambdas_not_counted_as_enclosing_statements(roslyn):
    code = """public class Sample
{
    public int Wrapper(int x)
    {
        int LocalHelper(int a) { return a * 2; }
        Func<int, int> lambda = y => y + 10;
        return LocalHelper(x) + lambda(x);
    }
}
"""
    metrics = roslyn.calculate_method_metrics(code)
    assert metrics is not None
    # Return inside LocalHelper should not be counted as enclosing method's return
    assert metrics["return_count"] == 1
    assert metrics["parameter_count"] == 1


def test_empty_method(roslyn):
    code = "public void DoNothing() {}"
    metrics = roslyn.calculate_method_metrics(code)
    assert metrics is not None
    assert metrics["statement_count"] == 0
    assert metrics["return_count"] == 0
    assert metrics["cyclomatic_complexity"] == 1
    assert metrics["max_nesting_depth"] == 0


def test_malformed_source_handled_gracefully(roslyn):
    # Missing closing brace and syntax errors
    code = "public int Bad( { broken syntax @@@"
    methods = roslyn.extract_methods(code=code)
    # Should not crash or hang; either returns empty or partial AST without throwing
    assert isinstance(methods, list)

