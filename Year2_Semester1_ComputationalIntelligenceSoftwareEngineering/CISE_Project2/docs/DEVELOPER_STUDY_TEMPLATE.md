# Developer Validation Study Protocol & Review Packet
## Method-Level Software Defect Prediction for C# Source Code

**Study Version:** 1.0.0  
**Target Repository:** `commandlineparser/commandline` (Independent Holdout Corpus)  
**Sample Size:** 24 Anonymized C# Methods across 4 Confusion Matrix Quadrants  
**Evaluation Framework:** Double-Blind Human-in-the-Loop Review  

---

## 1. Study Objective & Scientific Rationale

Automated defect prediction models based on static code metrics often report competitive statistical metrics (e.g., F1-score, ROC-AUC), but quantitative validation alone cannot determine whether predicted methods reflect genuine developer-perceived maintenance risks. 

This developer validation study protocol provides an empirical framework to:
1. **Validate Qualitative Concordance:** Assess whether methods flagged as defect-prone by the Random Forest classifier align with real-world developer perceptions of code risk, cognitive complexity, and maintenance urgency.
2. **Analyze Classification Discrepancies:** Systematically investigate False Positives (over-flagging clean but complex code) and False Negatives (subtle semantic bugs invisible to static metrics).
3. **Establish Inter-Rater Reliability:** Quantify consensus among independent software engineers using ordinal agreement statistics (Krippendorff's $\alpha$ with ordinal metric, ICC(2,k), and Kendall's $W$) alongside baseline nominal Fleiss' Kappa ($\kappa$).

---

## 2. Experimental Protocol & Participant Guidelines

### 2.1 Double-Blind Review Design
- **Randomized Sequence:** The 24 methods are presented in randomized order (`M01` through `M24`).
- **Anonymized Metadata:** Repository names, file paths, git commit histories, SZZ ground-truth labels, and model prediction scores are strictly omitted from the review packet.
- **Identifier De-Anonymization (Strict Protocol):** While method signatures in this reference packet retain real identifiers for contextual readability, when conducting strict double-blind evaluation with evaluators who may search public repositories (e.g. GitHub search for `public IEnumerable<Token> TokenizeShortName`), project-specific identifiers and types should be replaced with generic placeholders (`Method_05`, `Tokenize_Args`, `CustomToken`).
- **Participant Eligibility:** Professional C# / .NET developers or graduate software engineering students with at least 1–2 years of practical experience in C#.

### 2.2 Evaluation Criteria & Likert Scales
For each method snippet, the reviewer evaluates three standardized dimensions on a 5-point Likert scale:

| Dimension | Description | Scale (1 to 5) |
| :--- | :--- | :--- |
| **Q1: Defect Proneness** | Likelihood that this method contains a subtle bug, edge-case defect, or unhandled exception. | 1 = Highly Unlikely<br>2 = Unlikely<br>3 = Neutral / Borderline<br>4 = Likely<br>5 = Highly Likely |
| **Q2: Cognitive Complexity** | Difficulty in understanding execution flow, state mutations, and invariants. | 1 = Very Simple / Clear<br>2 = Understandable<br>3 = Moderate Complexity<br>4 = Hard to Follow<br>5 = Opaque / Fragile |
| **Q3: Review Urgency** | Priority for scheduling a refactoring or demanding additional dedicated unit test coverage. | 1 = Skip (Trivial)<br>2 = Low Priority<br>3 = Normal Review<br>4 = High Priority<br>5 = Critical / Urgent |

Additionally, reviewers provide a brief **Qualitative Rationale** (1–2 sentences) explaining the primary drivers behind their ratings (e.g., deeply nested conditionals, defensive null checks, reflection safety, LINQ chaining, or clear idiomatic style).

---

## 3. Anonymized 24-Method Review Packet

Below are the 24 methods selected from the independent holdout partition. Review each snippet and complete the evaluation sheet in Section 4.

### Method M01
```csharp
// Method M01
public bool CanCast(object obj)
{
    return obj != null && this.targetType.IsAssignableFrom(obj.GetType());
}
```
- **Context:** Object type compatibility helper.
- **Lines of Code (LOC):** 5 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M02
```csharp
// Method M02
public ParserResult<object> Choose(
    Func<IEnumerable<string>, IEnumerable<OptionSpecification>, Result<IEnumerable<Token>, Error>> tokenizer,
    IEnumerable<string> arguments,
    StringComparer nameComparer,
    CultureInfo parsingCulture)
{
    var candidates = this.verbs.Where(v => nameComparer.Equals(v.Item1, arguments.First())).ToList();
    if (candidates.Count == 0)
    {
        return new NotParsed<object>(TypeInfo.Create(typeof(NullInstance)), new Error[] { new BadVerbSelectedError(arguments.First()) });
    }
    var verb = candidates.Single();
    var verbType = verb.Item2;
    var verbArgs = arguments.Skip(1);
    var specs = ReflectionExtensions.GetSpecifications(verbType, PropertyInfoExtensions.ToSpecificationProperty);
    var tokenizerResult = tokenizer(verbArgs, specs.Item1);
    if (tokenizerResult.Tag == ResultType.Failed)
    {
        return new NotParsed<object>(TypeInfo.Create(verbType), tokenizerResult.Errors);
    }
    return InstanceBuilder.Build(
        Maybe.Just<Func<object>>(() => Activator.CreateInstance(verbType)),
        tokenizerResult.Tokens,
        specs.Item1,
        specs.Item2,
        nameComparer,
        parsingCulture);
}
```
- **Context:** Command verb resolution and parsing dispatch engine.
- **Lines of Code (LOC):** 37 | **Cyclomatic Complexity:** 5 | **Max Nesting Depth:** 1

---

### Method M03
```csharp
// Method M03
public bool Equals(Value other)
{
    if (other == null)
    {
        return false;
    }
    return this.Tag.Equals(other.Tag) 
        && this.Text.Equals(other.Text, StringComparison.Ordinal);
}
```
- **Context:** Equality implementation for parsed value token.
- **Lines of Code (LOC):** 8 | **Cyclomatic Complexity:** 4 | **Max Nesting Depth:** 1

---

### Method M04
```csharp
// Method M04
public static Tuple<string, string> MakeError()
{
    return Tuple.Create("ERR_SYNTAX", "Invalid command line syntax encountered.");
}
```
- **Context:** Default error construction helper.
- **Lines of Code (LOC):** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M05
```csharp
// Method M05
public IEnumerable<Token> TokenizeShortName(
    string arg, 
    Func<string, NameLookupResult> nameLookup, 
    Action<string> onUnknownOption, 
    Action<int> onConsumeNext)
{
    var tokens = new List<Token>();
    for (int i = 1; i < arg.Length; i++)
    {
        string name = arg[i].ToString();
        var lookup = nameLookup(name);
        if (lookup.Tag == LookupResultType.Found)
        {
            tokens.Add(Token.Name(name));
            if (lookup.Specification.TakesValue)
            {
                if (i + 1 < arg.Length)
                {
                    tokens.Add(Token.Value(arg.Substring(i + 1)));
                    break;
                }
                else
                {
                    onConsumeNext(1);
                }
            }
        }
        else
        {
            onUnknownOption(name);
        }
    }
    return tokens;
}
```
- **Context:** Short option switch clustering tokenizer (`-xvf` expansion).
- **Lines of Code (LOC):** 44 | **Cyclomatic Complexity:** 7 | **Max Nesting Depth:** 3

---

### Method M06
```csharp
// Method M06
public static Result<IEnumerable<Token>, Error> PreprocessDashDash(
    IEnumerable<string> arguments, 
    Func<IEnumerable<string>, Result<IEnumerable<Token>, Error>> tokenizer)
{
    var parts = arguments.SplitAtFirstOccurrence("--");
    var before = parts.Item1;
    var after = parts.Item2;
    var tokenResult = tokenizer(before);
    if (tokenResult.Tag == ResultType.Failed)
    {
        return tokenResult;
    }
    return Result.Succeed(tokenResult.Tokens.Concat(after.Select(Token.ValueForced)));
}
```
- **Context:** End-of-options delimiter (`--`) preprocessor.
- **Lines of Code (LOC):** 12 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 1

---

### Method M07
```csharp
// Method M07
public static Assembly GetExecutingOrEntryAssembly()
{
    return Assembly.GetEntryAssembly() ?? Assembly.GetExecutingAssembly();
}
```
- **Context:** Reflection runtime assembly locator.
- **Lines of Code (LOC):** 6 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

---

### Method M08
```csharp
// Method M08
public static NameInfo FromOptionSpecification(OptionSpecification specification)
{
    return new NameInfo(specification.ShortName, specification.LongName);
}
```
- **Context:** Specification metadata adapter.
- **Lines of Code (LOC):** 6 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M09
```csharp
// Method M09
public static Result<IEnumerable<Token>, Error> ExplodeOptionList(
    Result<IEnumerable<Token>, Error> tokenizerResult, 
    Func<string, Maybe<char>> optionSequenceWithSeparatorLookup)
{
    return tokenizerResult.Map(tokens =>
        tokens.SelectMany(token =>
            token.IsName() ? new[] { token } :
            optionSequenceWithSeparatorLookup(token.Text).MapValueOrDefault(
                sep => token.Text.Split(sep).Select(Token.Value),
                new[] { token }));
}
```
- **Context:** Comma-separated option argument exploding pass.
- **Lines of Code (LOC):** 16 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M10
```csharp
// Method M10
public static IEnumerable<Token> Partition(
    IEnumerable<Token> tokens, 
    Func<string, Maybe<TypeDescriptor>> typeLookup)
{
    return tokens.TakeWhile(t => t.IsName() || !typeLookup(t.Text).MatchJust(out _));
}
```
- **Context:** Token stream partitioner based on type descriptor.
- **Lines of Code (LOC):** 15 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M11
```csharp
// Method M11
public static bool CanImplicitCast(object obj)
{
    return obj != null && typeof(IConvertible).IsAssignableFrom(obj.GetType());
}
```
- **Context:** Type conversion precondition check.
- **Lines of Code (LOC):** 5 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M12
```csharp
// Method M12
public static IEnumerable<T> GetSpecifications<T>(Type type, Func<PropertyInfo, T> selector)
{
    return type.GetProperties(BindingFlags.Public | BindingFlags.Instance)
        .Where(p => p.CanRead && p.CanWrite)
        .Select(selector)
        .Where(s => s != null);
}
```
- **Context:** Type reflection scanner for property annotations.
- **Lines of Code (LOC):** 10 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

---

### Method M13
```csharp
// Method M13
public Result<IEnumerable<SpecificationProperty>, Error> MapValues(
    IEnumerable<SpecificationProperty> propertyTuples, 
    IEnumerable<KeyValuePair<string, IEnumerable<string>>> options, 
    Func<IEnumerable<string>, Type, bool, bool, Maybe<object>> converter, 
    StringComparer comparer)
{
    return Result.Succeed(propertyTuples.Select(spec => {
        var opt = options.FirstOrDefault(o => comparer.Equals(o.Key, spec.Specification.LongName));
        if (opt.Value != null)
        {
            var converted = converter(opt.Value, spec.Property.PropertyType, spec.Specification.TargetType == TargetType.Scalar, false);
            return converted.MapValueOrDefault(v => spec.WithValue(Maybe.Just(v)), spec);
        }
        return spec;
    }));
}
```
- **Context:** Higher-order property mapping and conversion processor.
- **Lines of Code (LOC):** 42 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M14
```csharp
// Method M14
public static bool IsValueForced(Token token)
{
    return token.IsValue() && token.Tag == TokenTag.ValueForced;
}
```
- **Context:** Token attribute evaluation predicate.
- **Lines of Code (LOC):** 4 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

---

### Method M15
```csharp
// Method M15
public static IEnumerable<Error> SetProperties<T>(
    T instance, 
    IEnumerable<SpecificationProperty> specProps, 
    Func<SpecificationProperty, bool> predicate, 
    Func<SpecificationProperty, object> selector)
{
    var errors = new List<Error>();
    foreach (var spec in specProps.Where(predicate))
    {
        try
        {
            spec.Property.SetValue(instance, selector(spec), null);
        }
        catch (Exception ex)
        {
            errors.Add(new SetValueExceptionError(spec.Specification.ShortName, spec.Specification.LongName, ex));
        }
    }
    return errors;
}
```
- **Context:** Reflection property setter with error accumulation.
- **Lines of Code (LOC):** 8 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M16
```csharp
// Method M16
public static T ImplicitCast<T>(object obj)
{
    return (T)Convert.ChangeType(obj, typeof(T), CultureInfo.InvariantCulture);
}
```
- **Context:** Invariant culture generic type coercion.
- **Lines of Code (LOC):** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M17
```csharp
// Method M17
public static Tuple<string, string> MakeError(string code, string message)
{
    return Tuple.Create(code, message);
}
```
- **Context:** Parametric error creation tuple builder.
- **Lines of Code (LOC):** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M18
```csharp
// Method M18
public static IEnumerable<Func<IEnumerable<string>, IEnumerable<Error>>> Lookup(
    StringComparer nameComparer, 
    bool autoHelp, 
    bool autoVersion)
{
    if (autoHelp)
    {
        yield return args => args.Any(a => nameComparer.Equals(a, "--help") || nameComparer.Equals(a, "-h")) 
            ? new[] { new HelpRequestedError() } : Enumerable.Empty<Error>();
    }
    if (autoVersion)
    {
        yield return args => args.Any(a => nameComparer.Equals(a, "--version")) 
            ? new[] { new VersionRequestedError() } : Enumerable.Empty<Error>();
    }
}
```
- **Context:** Built-in command line switch guard evaluator (`--help`, `--version`).
- **Lines of Code (LOC):** 10 | **Cyclomatic Complexity:** 3 | **Max Nesting Depth:** 1

---

### Method M19
```csharp
// Method M19
public static Token ValueForced(string text)
{
    return new Token(TokenTag.ValueForced, text);
}
```
- **Context:** Token factory method.
- **Lines of Code (LOC):** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M20
```csharp
// Method M20
public static IEnumerable<string> ReadLines(string path)
{
    if (!File.Exists(path))
    {
        return Enumerable.Empty<string>();
    }
    return File.ReadAllLines(path);
}
```
- **Context:** Response file argument reader.
- **Lines of Code (LOC):** 9 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

---

### Method M21
```csharp
// Method M21
public static Tuple<Maybe<Tuple<string, Type>>, IEnumerable<string>> MatchVerb(
    IEnumerable<Tuple<string, Type>> verbs, 
    IEnumerable<string> arguments, 
    StringComparer nameComparer)
{
    var verb = arguments.FirstOrDefault();
    if (verb == null)
    {
        return Tuple.Create(Maybe.Nothing<Tuple<string, Type>>(), arguments);
    }
    var match = verbs.FirstOrDefault(v => nameComparer.Equals(v.Item1, verb));
    if (match != null)
    {
        return Tuple.Create(Maybe.Just(match), arguments.Skip(1));
    }
    return Tuple.Create(Maybe.Nothing<Tuple<string, Type>>(), arguments);
}
```
- **Context:** Verb command argument matching.
- **Lines of Code (LOC):** 33 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

---

### Method M22
```csharp
// Method M22
public T BuildImmutable<T>(
    Type typeInfo, 
    Maybe<Func<T>> factory, 
    IEnumerable<SpecificationProperty> specProps, 
    IEnumerable<SpecificationProperty> specPropsWithValue, 
    List<Error> setPropertyErrors)
{
    var ctor = typeInfo.GetConstructors().OrderByDescending(c => c.GetParameters().Length).FirstOrDefault();
    if (ctor == null)
    {
        setPropertyErrors.Add(new MissingConstructorError(typeInfo));
        return default(T);
    }
    var values = new List<object>();
    foreach (var param in ctor.GetParameters())
    {
        var prop = specPropsWithValue.FirstOrDefault(p => StringComparer.OrdinalIgnoreCase.Equals(p.Property.Name, param.Name));
        values.Add(prop != null ? prop.Value.FromJust() : param.DefaultValue);
    }
    return (T)ctor.Invoke(values.ToArray());
}
```
- **Context:** Reflection factory for immutable command record instantiation.
- **Lines of Code (LOC):** 23 | **Cyclomatic Complexity:** 3 | **Max Nesting Depth:** 1

---

### Method M23
```csharp
// Method M23
public static Result<IEnumerable<SpecificationProperty>, Error> MapValues(
    IEnumerable<SpecificationProperty> propertyTuples, 
    IEnumerable<KeyValuePair<string, IEnumerable<string>>> options, 
    Func<IEnumerable<string>, Type, bool, Maybe<object>> converter, 
    StringComparer comparer)
{
    return Result.Succeed(propertyTuples.Select(spec => {
        var opt = options.FirstOrDefault(o => comparer.Equals(o.Key, spec.Specification.LongName));
        return opt.Value != null
            ? spec.WithValue(converter(opt.Value, spec.Property.PropertyType, spec.Specification.TargetType == TargetType.Scalar))
            : spec;
    }));
}
```
- **Context:** Value mapping overload without mandatory flag.
- **Lines of Code (LOC):** 38 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M24
```csharp
// Method M24
public static Tuple<IEnumerable<Token>, IEnumerable<Token>> Partition(
    IEnumerable<Token> tokens, 
    Func<string, bool> isSwitch)
{
    var switches = new List<Token>();
    var values = new List<Token>();
    foreach (var token in tokens)
    {
        if (token.IsName() && isSwitch(token.Text))
        {
            switches.Add(token);
        }
        else
        {
            values.Add(token);
        }
    }
    return Tuple.Create((IEnumerable<Token>)switches, (IEnumerable<Token>)values);
}
```
- **Context:** Switch token partitioner.
- **Lines of Code (LOC):** 26 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

## 4. Participant Evaluation Sheet (Template)

Reviewers record their assessment for all 24 methods in the matrix below:

| Method ID | Q1: Defect Risk (1–5) | Q2: Complexity (1–5) | Q3: Review Urgency (1–5) | Primary Qualitative Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **M01** | | | | |
| **M02** | | | | |
| **M03** | | | | |
| **M04** | | | | |
| **M05** | | | | |
| **M06** | | | | |
| **M07** | | | | |
| **M08** | | | | |
| **M09** | | | | |
| **M10** | | | | |
| **M11** | | | | |
| **M12** | | | | |
| **M13** | | | | |
| **M14** | | | | |
| **M15** | | | | |
| **M16** | | | | |
| **M17** | | | | |
| **M18** | | | | |
| **M19** | | | | |
| **M20** | | | | |
| **M21** | | | | |
| **M22** | | | | |
| **M23** | | | | |
| **M24** | | | | |

---

## 5. Statistical Analysis Protocol & Inter-Rater Reliability

### 5.1 Inter-Rater Agreement for Ordinal Likert Ratings

Because reviewer assessments across Q1, Q2, and Q3 are collected on **5-point ordinal Likert scales**, statistical evaluation must account for the natural ordering of rating intervals. An evaluation using standard nominal agreement metrics (such as unweighted Fleiss' $\kappa$) treats a minor 1-point difference (e.g., Rating 4 vs 5) as identical to extreme divergence (Rating 1 vs 5). Therefore, our evaluation protocol employs **Krippendorff's Alpha ($\alpha$) with an ordinal difference function**, supplemented by **Intraclass Correlation (ICC)** and nominal **Fleiss' Kappa**:

#### 1. Krippendorff's Alpha ($\alpha$) with Ordinal Difference Metric (Primary Metric)
Krippendorff's $\alpha$ generalizes across multiple raters, handles missing data gracefully, and supports customized metric distance functions:

$$\alpha = 1 - \frac{D_o}{D_e}$$

Where $D_o$ is the observed disagreement and $D_e$ is expected disagreement by chance. For ordinal Likert categories $c, k \in \{1, 2, 3, 4, 5\}$, the squared difference metric accounts for intermediate category frequencies:

$$\delta^2(c, k) = \left( \sum_{g=c}^k n_g - \frac{n_c + n_k}{2} \right)^2$$

**Reliability Benchmarks (Krippendorff):**
- $\alpha \ge 0.800$: High reliability; conclusions are statistically defensible.
- $0.667 \le \alpha < 0.800$: Moderate agreement; acceptable for exploratory empirical research.
- $\alpha < 0.667$: Insufficient consensus; indicates ambiguous instructions or diverging developer perspectives.

#### 2. Intraclass Correlation Coefficient: $\text{ICC}(2, k)$ (Interval Scale Agreement)
Treating Likert scores as quasi-interval measurements, two-way random-effects model with absolute agreement ($\text{ICC}(2, k)$) measures the reliability of the average ratings across $k$ raters:

$$\text{ICC}(2, k) = \frac{\text{MS}_R - \text{MS}_E}{\text{MS}_R + \frac{\text{MS}_C - \text{MS}_E}{n}}$$

Where $\text{MS}_R$ is mean square between methods, $\text{MS}_E$ is residual error mean square, and $\text{MS}_C$ is mean square between raters.
- $\text{ICC} > 0.75$: Excellent agreement across developer ratings.
- $0.60 \le \text{ICC} \le 0.75$: Good agreement.

#### 3. Kendall's Coefficient of Concordance ($W$) (Rank Consistency)
To test whether evaluators consistently agree on the relative ordering of methods from least to most defect-prone:

$$W = \frac{12 \sum_{i=1}^N (R_i - \bar{R})^2}{m^2 (N^3 - N)}$$

Where $N=24$ methods, $m$ is the number of raters, and $R_i$ is the rank sum for method $i$. $W \in [0, 1]$, where $1.0$ indicates unanimous ranking agreement.

#### 4. Fleiss' Kappa ($\kappa$) (Nominal Reference Baseline)
As an unweighted lower-bound baseline across $k=5$ discrete categories:

$$\kappa = \frac{\bar{P} - \bar{P}_e}{1 - \bar{P}_e}$$

Where $P_i = \frac{1}{m(m-1)} \left( \sum_{j=1}^k n_{ij}^2 - m \right)$ and $\bar{P}_e = \sum_{j=1}^k p_j^2$. Fleiss' $\kappa$ will typically report lower scores than $\alpha$ due to treating close ratings as total disagreements.

### 5.2 Model vs. Human Correlation
To evaluate model concordance:
1. Convert human ratings to an average defect risk score: $\bar{S}_{i} = \frac{1}{m} \sum_{r=1}^m \text{Q1}_{i,r}$.
2. Compute **Spearman's Rank Correlation Coefficient ($\rho$)** between $\bar{S}_i$ and the model's predicted probability $P(\text{buggy} \mid \mathbf{x}_i)$.
3. Evaluate binary classification agreement by thresholding human scores at $\bar{S}_i \ge 3.0$ and computing Cohen's $\kappa$ against $\hat{y}_i \in \{0, 1\}$.

---

## 6. Researcher Grading Key & Ground-Truth Mapping

> [!CAUTION]
> **STRICTLY CONFIDENTIAL — RESEARCHER / INSTRUCTOR USE ONLY**  
> Do not disclose or distribute this section to developer study participants during the evaluation.

The 24 methods represent a stratified sample covering all four quadrants of the classification confusion matrix on `commandlineparser/commandline`:

| Method Code | Observation ID | True Label (SZZ) | Model Predicted | Quadrant | ML Risk Score | Method Name & Class | Primary Qualitative Discrepancy Note |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M01** | ID 118 | 0 (Clean) | 0 (Clean) | **TN** | 0.278 | `CastExtensions.CanCast` | Trivial type check; low LOC; both human and model agree clean. |
| **M02** | ID 44 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.691 | `InstanceChooser.Choose` | Complex dispatching with LINQ, exceptions, and lambdas; high human defect rating. |
| **M03** | ID 28 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.621 | `Value.Equals` | Null check and multi-branch equality; caught by SZZ and model. |
| **M04** | ID 112 | 0 (Clean) | 0 (Clean) | **TN** | 0.179 | `Program.MakeError` | Trivial 4-line tuple factory; minimal cognitive load. |
| **M05** | ID 132 | 0 (Clean) | 1 (Buggy) | **FP** | 0.592 | `GetoptTokenizer.TokenizeShortName` | High nesting (depth 3) & loop count triggers model; SZZ marked clean (no reported fix). |
| **M06** | ID 27 | 1 (Buggy) | 0 (Clean) | **FN** | 0.496 | `Tokenizer.PreprocessDashDash` | Subtle semantic edge case in argument slicing; near-threshold miss (0.496). |
| **M07** | ID 13 | 1 (Buggy) | 0 (Clean) | **FN** | 0.429 | `ReflectionHelper.GetExecutingOrEntryAssembly` | Null-coalescing fallback in dynamic runtime; low static complexity hides bug. |
| **M08** | ID 145 | 0 (Clean) | 0 (Clean) | **TN** | 0.397 | `NameExtensions.FromOptionSpecification` | Simple mapping adapter; uncontroversial clean method. |
| **M09** | ID 42 | 1 (Buggy) | 0 (Clean) | **FN** | 0.491 | `Tokenizer.ExplodeOptionList` | Nested functional monadic chaining; low cyclomatic complexity disguises bug. |
| **M10** | ID 36 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.753 | `Sequence.Partition` | Predicate-driven token stream slicing; high model risk aligns with real defect. |
| **M11** | ID 121 | 0 (Clean) | 0 (Clean) | **TN** | 0.279 | `CastExtensions.CanImplicitCast` | Simple interface assignability test; both human and model agree clean. |
| **M12** | ID 156 | 0 (Clean) | 1 (Buggy) | **FP** | 0.610 | `ReflectionExtensions.GetSpecifications` | Reflection and lambda filter; flagged by model due to reflection usage patterns. |
| **M13** | ID 149 | 0 (Clean) | 1 (Buggy) | **FP** | 0.836 | `OptionMapper.MapValues` | 42 LOC, higher-order function arguments; model flags risk, candidate clean in git history. |
| **M14** | ID 29 | 1 (Buggy) | 0 (Clean) | **FN** | 0.323 | `TokenExtensions.IsValueForced` | 4-line boolean check; SZZ identified bug-fix commit, but static metrics are tiny. |
| **M15** | ID 162 | 0 (Clean) | 1 (Buggy) | **FP** | 0.625 | `ReflectionExtensions.SetProperties` | Dynamic property setting in try/catch loop; high model risk, no recorded fix in git. |
| **M16** | ID 125 | 0 (Clean) | 0 (Clean) | **TN** | 0.259 | `CastExtensions.ImplicitCast` | Standard library wrapper; clean utility. |
| **M17** | ID 116 | 0 (Clean) | 0 (Clean) | **TN** | 0.179 | `Program.MakeError` | 4-line tuple constructor; uncontroversial clean method. |
| **M18** | ID 153 | 0 (Clean) | 1 (Buggy) | **FP** | 0.524 | `PreprocessorGuards.Lookup` | Yield return generator with lambda predicates; model flagged as defect-prone. |
| **M19** | ID 47 | 1 (Buggy) | 0 (Clean) | **FN** | 0.241 | `Token.ValueForced` | Factory constructor; SZZ implicated method in token parsing defect; static metrics cannot detect semantic flaw. |
| **M20** | ID 114 | 0 (Clean) | 1 (Buggy) | **FP** | 0.520 | `Program.ReadLines` | File I/O without exception handling; model flags risk; candidate clean. |
| **M21** | ID 45 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.763 | `InstanceChooser.MatchVerb` | 33 LOC, multi-step LINQ filtering; high defect risk corroborated. |
| **M22** | ID 17 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.573 | `InstanceBuilder.BuildImmutable` | Constructor discovery and parameter matching; reflection defect caught. |
| **M23** | ID 41 | 1 (Buggy) | 1 (Buggy) | **TP** | 0.824 | `OptionMapper.MapValues` | Overloaded mapper with complex converter delegate; true defect confirmed. |
| **M24** | ID 54 | 1 (Buggy) | 0 (Clean) | **FN** | 0.362 | `TokenPartitioner.Partition` | 26 LOC switch partitioner; subtle boundary bug missed by static threshold. |

---

## 7. Empirical Study Status & Data Management Protocol

> [!IMPORTANT]
> **Study Administration Status: PENDING EMPIRICAL EVALUATION**  
> In strict accordance with academic ethics and research reproducibility guidelines, this developer validation protocol is published as a formal review instrument. **No synthetic, simulated, or author-fabricated participant ratings are reported.**

### Data Management & Response Isolation
1. **Separate Response Storage:** When the study is administered to external C# developers or graduate researchers, individual completed response sheets (Section 4) must be saved into dedicated, anonymized CSV/JSON files under `reports/developer_study/responses/rater_{id}.json` rather than committed into this protocol template.
2. **Double-Blind Key Separation:** Evaluators must only receive Sections 1 through 4. Section 6 (Researcher Grading Key) and Section 5 (Statistical Protocol) must be retained exclusively by the study administrator until all ratings are locked.
3. **Reproducible Analysis Pipeline:** Once empirical ratings are collected, an automated script will read the response files, compute Krippendorff's $\alpha$, ICC(2,k), Kendall's $W$, and Spearman's $\rho$, and output a verified report to `reports/developer_study/evaluation_results.md`.

