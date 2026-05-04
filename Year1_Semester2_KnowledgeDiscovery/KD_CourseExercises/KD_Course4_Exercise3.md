---

# Course 4 Exercise 3

## Introduction

ToscanaJ is an open-source Java tool for building and navigating Conceptual Information Systems (CIS). A CIS consists of a many-valued context together with a set of pre-defined scales and a nested-line-diagram view. Users can interactively zoom into subscales and query the object set associated with any concept node.

## Context

Consider a library database modelled as a many-valued context with M = {Year, Subject, Length (pages)} and the following value ranges:
- Year: 1980 to 2024 (numeric);
- Subject: {Mathematics, Computer Science, Physics, Biology};
- Length: short (< 150 pp.), medium (150-400 pp.), long (> 400 pp.)

## a) 
**Request**: Define an appropriate scale for each attribute. For Year, propose an interordinal scale distinguishing the decades (1980s, 1990s, 2000s, 2010s, and 2020s) and draw its cross-table.

### Solution

We define one conceptual scale for each attribute:
 1. **Scale for Subject**: Since **Subject** is an _unordered categorical attribute_, the appropriate scale is a **nominal scale**. Each subject becomes one binary attribute.

| Subject value | Mathematics | Computer Science | Physics | Biology |
|---|:---:|:---:|:---:|:---:|
| Mathematics | X |  |  |  |
| Computer Science |  | X |  |  |
| Physics |  |  | X |  |
| Biology |  |  |  | X |

 2. **Scale for Length**: Values have a natural order ("_short < medium < long_"), therefore, an **ordinal scale** is appropriate. As an example, a book book with length **medium** receives the binary attributes "at least medium" and "at least long".

| Length value | at least short | at least medium | at least long |
|---|:---:|:---:|:---:|
| short | X | X | X |
| medium |  | X | X |
| long |  |  | X |

 3. **Scale for Year**: The **Year** attribute is numeric and ordered. The exercise asks for an **interordinal scale** (_a scale that scale uses both lower-bound and upper-bound attributes_).

| Year decade | ≤ 1980s | ≤ 1990s | ≤ 2000s | ≤ 2010s | ≤ 2020s | ≥ 1980s | ≥ 1990s | ≥ 2000s | ≥ 2010s | ≥ 2020s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1980s | X | X | X | X | X | X |  |  |  |  |
| 1990s |  | X | X | X | X | X | X |  |  |  |
| 2000s |  |  | X | X | X | X | X | X |  |  |
| 2010s |  |  |  | X | X | X | X | X | X |  |
| 2020s |  |  |  |  | X | X | X | X | X | X |


The derived binary context replaces the original many-valued attributes with scaled binary attributes:

### Subject-derived attributes

- Subject: Mathematics
- Subject: Computer Science
- Subject: Physics
- Subject: Biology

### Length-derived attributes

- Length: at least short
- Length: at least medium
- Length: at least long

### Year-derived attributes

- Year ≤ 1980s
- Year ≤ 1990s
- Year ≤ 2000s
- Year ≤ 2010s
- Year ≤ 2020s
- Year ≥ 1980s
- Year ≥ 1990s
- Year ≥ 2000s
- Year ≥ 2010s
- Year ≥ 2020s

---

## b)
Describe step by step how you would set up this CIS in ToscanaJ: which file formats are used for the context and the scale definitions and how scales are assigned to attributes in the .csx project file.

### Solution

First, start by following the ToscanaJ instructions profivded from UBB Faculty at [UBB-ToscanaJ](https://math.ubbcluj.ro/~csacarea/wordpress/wp-content/uploads/aboutToscanaJ.pdf)).

Second, since the online tool provided on the previous instructions for creating a SQL file doe not work due to restricted access (tool [UBB-SQL-TOOL](https://math.ubbcluj.ro/~csacarea/wordpress/wp-content/uploads/aboutToscanaJ.pdf)), create a SQL file locally and manually insert the needed table and values:

```sql
CREATE TABLE Books (
	name varchar,
	subject varchar,
	length integer,
	year integer
);
INSERT INTO Books VALUES ('B1','Mathematics',123,1989);
INSERT INTO Books VALUES ('B2','Mathematics',456,1999);
INSERT INTO Books VALUES ('B2','Computer Science',100,2003);
INSERT INTO Books VALUES ('B3','Biology',500,1989);
INSERT INTO Books VALUES ('B4','Physics',250,2024);
INSERT INTO Books VALUES ('B5','Physics',340,2011);
```

Open Elba by running the appropriate `.bat` file on windows connect to the local database file (as described on the online guide):
<img width="506" height="363" alt="image" src="https://github.com/user-attachments/assets/9f904317-c8f1-46c8-95a7-87ca527b95f6" />
<img width="392" height="402" alt="image" src="https://github.com/user-attachments/assets/fa354f29-6937-4e90-9dba-9dd30228d410" />

Now:
1. Create a **Nomianl Scale** for **Books**;
<img width="639" height="380" alt="image" src="https://github.com/user-attachments/assets/379eae7a-c160-4afe-a1e8-3ff7ff3d588e" />
<img width="957" height="509" alt="image" src="https://github.com/user-attachments/assets/fca2dbf8-051e-45b6-92c6-a2558fac1bc8" />

2. Create an **Ordinal Scale** for **Length**;
<img width="480" height="595" alt="image" src="https://github.com/user-attachments/assets/74a684a3-c62a-46f2-8c6f-822fec391f5f" />
<img width="956" height="509" alt="image" src="https://github.com/user-attachments/assets/7e5ee926-dc2f-4036-ae53-62b0a9735613" />
<img width="689" height="495" alt="image" src="https://github.com/user-attachments/assets/fd03ece5-4551-49c6-af8b-a3204c211546" />
<img width="958" height="513" alt="image" src="https://github.com/user-attachments/assets/e1358011-c110-47d0-8505-3be350dac435" />
<img width="953" height="1029" alt="image" src="https://github.com/user-attachments/assets/22bdf314-0748-4db4-855f-9e05c494bf64" />

3. Create an **Interordinal Scale** for **Year**
<img width="479" height="595" alt="image" src="https://github.com/user-attachments/assets/2a933ac1-89dd-4efb-94f8-2d119f4b08d9" />
<img width="957" height="513" alt="image" src="https://github.com/user-attachments/assets/01d9b4bd-9782-4153-920e-0b12af7c7c0a" />

Than go to "_File_" ➡️ "Save As" ➡️ Give the file a name and select "_.csx_" format.
<img width="533" height="409" alt="image" src="https://github.com/user-attachments/assets/ff2a0b64-0b02-43a4-b9e9-79b3a80af0b1" />

Run "**ToscanaJ**" by executing the appropriate `.bat` file on Windows system. Go to "_File_" ➡️ "Open" ➡️ select te previously created "_.csx_" file.
<img width="528" height="457" alt="image" src="https://github.com/user-attachments/assets/c9954724-dc58-4470-a452-37126579ad6b" />

---

## c)
A user navigates to the concept node labelled "Computer Science /\ long":
i. What does the _extent_ of this node represent in terms of the library database?
ii. Explain what happens in ToscanaJ when the user performs a zoom into theYear subscale at this node.







