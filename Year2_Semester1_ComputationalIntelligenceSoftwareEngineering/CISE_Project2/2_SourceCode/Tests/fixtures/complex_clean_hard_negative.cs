using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Fixtures.HardNegatives
{
    public sealed class BoundedLineProcessor
    {
        public IReadOnlyList<string> ParseValidEntries(string filePath, int maxLines)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("File path is required.", nameof(filePath));
            }
            if (maxLines <= 0)
            {
                return Array.Empty<string>();
            }
            if (!File.Exists(filePath))
            {
                return Array.Empty<string>();
            }

            var results = new List<string>(Math.Min(maxLines, 64));
            using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            using var reader = new StreamReader(stream, Encoding.UTF8);
            while (results.Count < maxLines)
            {
                var line = reader.ReadLine();
                if (line is null)
                {
                    break;
                }
                var trimmed = line.Trim();
                if (trimmed.Length == 0 || trimmed.StartsWith('#'))
                {
                    continue;
                }
                results.Add(trimmed);
            }
            return results;
        }
    }
}
