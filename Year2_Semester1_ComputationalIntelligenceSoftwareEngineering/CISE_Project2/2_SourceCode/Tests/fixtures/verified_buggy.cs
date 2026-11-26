using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

namespace Fixtures.Buggy
{
    public class SampleBuggyService
    {
        public string ReadFirstLineLeak(string path)
        {
            var reader = new StreamReader(path);
            return reader.ReadLine();
        }

        public int GetUserNameLength(IEnumerable<UserRecord> users, int targetId)
        {
            var match = users.FirstOrDefault(u => u.Id == targetId);
            return match.Name.Length;
        }

        public int UnsafeCastLength(object payload)
        {
            var text = payload as string;
            return text.Trim().Length;
        }
    }

    public class UserRecord
    {
        public int Id { get; set; }
        public string? Name { get; set; }
    }
}
