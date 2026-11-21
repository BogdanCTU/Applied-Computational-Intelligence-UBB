"""Unit and integration tests for Roslyn v2.0 class, struct, record, and multi-class file analysis."""
from __future__ import annotations

import pytest
from services.analyzer.roslyn_client import RoslynClient


@pytest.fixture
def roslyn():
    return RoslynClient()


def test_single_class_metrics_and_metadata(roslyn):
    code = """namespace Billing.Domain
{
    public class InvoiceCalculator
    {
        private readonly decimal _taxRate;

        public InvoiceCalculator(decimal taxRate)
        {
            _taxRate = taxRate;
        }

        public decimal TaxRate => _taxRate;

        public decimal ComputeTotal(decimal subtotal, bool applyDiscount)
        {
            if (subtotal < 0)
            {
                throw new ArgumentException("Negative");
            }
            decimal total = subtotal;
            if (applyDiscount && subtotal > 100m)
            {
                total *= 0.9m;
            }
            return total * (1m + _taxRate);
        }
    }
}
"""
    res = roslyn.analyze_source(code=code)
    assert res["success"] is True
    assert res["file_metadata"]["class_count"] == 1
    assert "Billing.Domain" in res["file_metadata"]["namespaces"]

    cls = res["classes"][0]
    assert cls["class_name"] == "InvoiceCalculator"
    assert cls["qualified_class_name"] == "Billing.Domain.InvoiceCalculator"
    assert cls["namespace_name"] == "Billing.Domain"
    assert cls["type_kind"] == "class"
    assert cls["start_line"] == 3
    assert cls["end_line"] == 27

    m = cls["metrics"]
    assert m["method_count"] == 1
    assert m["constructor_count"] == 1
    assert m["property_count"] == 1
    assert m["field_count"] == 1
    assert m["nested_type_count"] == 0
    assert m["total_if_count"] == 2
    assert m["total_throw_count"] == 1
    assert m["total_cyclomatic_complexity"] >= 4
    assert m["class_loc"] >= 15


def test_multiple_classes_in_one_file(roslyn):
    code = """namespace MultiTypes
{
    public class Alpha
    {
        public int RunA(int x)
        {
            if (x > 0) return x;
            return 0;
        }
    }

    public class Beta
    {
        public string RunB(string s) => s.Trim();
    }
}
"""
    classes = roslyn.extract_classes(code=code)
    assert len(classes) == 2
    names = {c["class_name"]: c for c in classes}
    assert "Alpha" in names and "Beta" in names
    assert names["Alpha"]["start_line"] < names["Beta"]["start_line"]
    assert names["Alpha"]["metrics"]["total_if_count"] == 1
    assert names["Beta"]["metrics"]["total_if_count"] == 0


def test_nested_class_not_double_counted_in_outer_class(roslyn):
    code = """namespace NestedDemo
{
    public class OuterService
    {
        public int OuterWork(int x)
        {
            return x + 1;
        }

        private class InnerHelper
        {
            public int DeepWork(int a, int b)
            {
                if (a > b)
                {
                    for (int i = 0; i < 5; i++)
                    {
                        a += i;
                    }
                }
                return a;
            }
        }
    }
}
"""
    classes = roslyn.extract_classes(code=code)
    assert len(classes) == 2
    by_name = {c["class_name"]: c for c in classes}

    outer = by_name["OuterService"]
    inner = by_name["InnerHelper"]

    assert outer["is_nested"] is False
    assert inner["is_nested"] is True
    assert inner["enclosing_type_name"] == "OuterService"
    assert inner["qualified_class_name"] == "NestedDemo.OuterService.InnerHelper"

    # Outer class must ONLY see OuterWork, NOT InnerHelper's loop/if/methods
    assert outer["metrics"]["nested_type_count"] == 1
    assert outer["metrics"]["method_count"] == 1
    assert outer["metrics"]["total_loop_count"] == 0
    assert outer["metrics"]["total_if_count"] == 0
    assert outer["metrics"]["total_cyclomatic_complexity"] == 1

    # Inner class owns its own loop and if
    assert inner["metrics"]["method_count"] == 1
    assert inner["metrics"]["total_loop_count"] == 1
    assert inner["metrics"]["total_if_count"] == 1
    assert inner["metrics"]["total_cyclomatic_complexity"] >= 3


def test_records_structs_generics_and_async_modern_syntax(roslyn):
    code = """namespace ModernCSharp;

public record OrderItem(string Sku, int Quantity);

public readonly struct Money
{
    public decimal Amount { get; }
    public Money(decimal amount) => Amount = amount;
}

public class GenericProcessor<T>
{
    public async Task<int> ProcessAsync(IEnumerable<T> items)
    {
        int count = 0;
        foreach (var item in items)
        {
            count += item is not null ? 1 : 0;
        }
        await Task.Yield();
        return count;
    }

    public static string Classify(int code) => code switch
    {
        200 => "OK",
        404 => "Missing",
        _ => "Other",
    };
}
"""
    classes = roslyn.extract_classes(code=code)
    by_name = {c["class_name"]: c for c in classes}

    assert by_name["OrderItem"]["type_kind"] == "record"
    assert by_name["OrderItem"]["namespace_name"] == "ModernCSharp"
    assert by_name["OrderItem"]["metrics"]["constructor_count"] == 1
    assert by_name["OrderItem"]["metrics"]["total_parameter_count"] == 2

    assert by_name["Money"]["type_kind"] == "struct"
    assert by_name["Money"]["metrics"]["property_count"] == 1
    assert by_name["Money"]["metrics"]["constructor_count"] == 1

    gp = by_name["GenericProcessor"]
    assert gp["is_generic"] is True
    assert gp["metrics"]["async_method_count"] == 1
    assert gp["metrics"]["static_method_count"] == 1
    assert gp["metrics"]["total_switch_count"] == 1
    assert gp["metrics"]["total_loop_count"] == 1
    assert gp["metrics"]["total_conditional_expression_count"] == 1


def test_empty_class_and_malformed_source(roslyn):
    empty_code = "public class MarkerAttribute {}"
    empty_classes = roslyn.extract_classes(code=empty_code)
    assert len(empty_classes) == 1
    assert empty_classes[0]["metrics"]["method_count"] == 0
    assert empty_classes[0]["metrics"]["class_loc"] >= 1
    assert empty_classes[0]["metrics"]["total_cyclomatic_complexity"] == 1

    bad_code = "namespace Broken { public class HalfDone { public void Foo( { if (x) "
    resp = roslyn.analyze_source(code=bad_code)
    assert resp["success"] is True
    assert len(resp["parsing_diagnostics"]) > 0
    assert len(resp["extraction_warnings"]) > 0


def test_batch_stdin_execution(roslyn):
    items = [
        {"id": "c1", "code": "public class One { public void A() {} }"},
        {"id": "c2", "code": "public class Two { public int B(int x) => x > 0 ? x : -x; }"},
    ]
    res = roslyn.analyze_batch(items)
    assert set(res.keys()) == {"c1", "c2"}
    assert res["c1"]["classes"][0]["class_name"] == "One"
    assert res["c2"]["classes"][0]["class_name"] == "Two"
    assert res["c2"]["classes"][0]["metrics"]["total_conditional_expression_count"] == 1


def test_local_functions_and_lambdas_isolated_in_class_metrics(roslyn):
    code = """public class OuterWorker
{
    public int Run(int x)
    {
        int LocalHelper(int y)
        {
            if (y > 0) return y * 2;
            return 0;
        }
        System.Func<int, int> fn = v => { if (v < 0) return -v; return v; };
        return LocalHelper(x) + fn(x);
    }
}
"""
    cls = roslyn.extract_classes(code=code)[0]
    m = cls["metrics"]
    assert m["method_count"] == 1
    assert m["total_if_count"] == 0
    assert m["total_return_count"] == 1
    assert m["total_cyclomatic_complexity"] == 1
