using System;
using System.Threading.Tasks;

namespace Fixtures.Constructs
{
    public struct Point2D
    {
        public double X { get; }
        public double Y { get; }
        public Point2D(double x, double y)
        {
            X = x;
            Y = y;
        }
        public double Magnitude() => Math.Sqrt(X * X + Y * Y);
    }

    public record AuditEntry(string Actor, string Action)
    {
        public string Format() => $"{Actor}:{Action}";
    }

    public class OuterService
    {
        public static T Identity<T>(T value) => value;

        public int Overload(int x) => x + 1;
        public int Overload(int x, int y) => x + y;

        public async Task<int> ComputeAsync(int seed)
        {
            await Task.Yield();
            return seed * 2;
        }

        public class NestedHelper
        {
            public bool IsPositive(int value)
            {
                return value > 0;
            }
        }
    }
}
