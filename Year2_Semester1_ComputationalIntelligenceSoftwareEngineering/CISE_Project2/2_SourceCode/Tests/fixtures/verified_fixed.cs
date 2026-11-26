using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

namespace Fixtures.Fixed
{
    public class SampleFixedService
    {
        public string? ReadFirstLineSafe(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                throw new ArgumentException("Path cannot be empty.", nameof(path));
            }
            using var reader = new StreamReader(path);
            return reader.ReadLine();
        }

        public int GetUserNameLength(IEnumerable<UserRecord> users, int targetId)
        {
            if (users is null)
            {
                return 0;
            }
            var match = users.FirstOrDefault(u => u.Id == targetId);
            return match?.Name?.Length ?? 0;
        }

        public int SafeCastLength(object? payload)
        {
            if (payload is not string text)
            {
                return 0;
            }
            return text.Trim().Length;
        }
    }

    public class UserRecord
    {
        public int Id { get; set; }
        public string? Name { get; set; }
    }
}
