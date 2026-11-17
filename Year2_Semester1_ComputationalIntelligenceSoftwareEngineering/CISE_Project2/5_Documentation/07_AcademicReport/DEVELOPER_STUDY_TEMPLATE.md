# Developer Validation Study Protocol and Review Packet
## Method-Level Software Defect Prediction for C# Source Code

**Study Version:** 1.0.0  
**Target Repository:** `commandlineparser/commandline`  
**Sample Size:** 24 C# Methods across 4 Confusion Matrix Quadrants  
**Evaluation Design:** Double-Blind Review Protocol (Unadministered Instrument)  

---

## 1. Study Objective

This protocol defines an empirical procedure to evaluate concordance between Random Forest defect-proneness predictions and developer assessments of code risk:
1. Measure correlation between model risk scores and developer ratings of defect proneness, cognitive complexity, and review urgency.
2. Inspect False Positives (complex candidate-clean methods) and False Negatives (concise methods with semantic defects).
3. Quantify inter-rater agreement using ordinal Krippendorff's $\alpha$, Intraclass Correlation $\text{ICC}(2,k)$, Kendall's $W$, and nominal Fleiss' $\kappa$.

---

## 2. Protocol Design

### 2.1 Double-Blind Conditions
- **Presentation Order:** 24 methods (`M01`–`M24`) ordered randomly.
- **Blinding:** Repository names, file paths, commit hashes, SZZ labels, and model probabilities are omitted from participant sheets. For strict blinding against repository search, project-specific identifiers can be replaced with generic placeholders.
- **Participant Profile:** C# / .NET developers or graduate software engineering students.

### 2.2 Rating Scales (1–5 Likert)

| Dimension | Definition | Scale |
| :--- | :--- | :--- |
| Q1: Defect Proneness | Likelihood that the method contains a defect or unhandled edge case | 1 = Highly Unlikely, 2 = Unlikely, 3 = Neutral, 4 = Likely, 5 = Highly Likely |
| Q2: Cognitive Complexity | Difficulty of understanding control flow and state transitions | 1 = Very Simple, 2 = Simple, 3 = Moderate, 4 = Complex, 5 = Opaque |
| Q3: Review Urgency | Priority for code review, refactoring, or unit testing | 1 = Trivial, 2 = Low, 3 = Normal, 4 = High, 5 = Urgent |

---

## 3. 24-Method Review Packet

### Method M01
```csharp
// Method M01
public bool CanCast(object obj)
{
    return obj != null && this.targetType.IsAssignableFrom(obj.GetType());
}
```
- **Context:** Object type compatibility helper.
- **LOC:** 5 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Command verb resolution and parsing dispatch.
- **LOC:** 37 | **Cyclomatic Complexity:** 5 | **Max Nesting Depth:** 1

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
- **Context:** Equality check for parsed value token.
- **LOC:** 8 | **Cyclomatic Complexity:** 4 | **Max Nesting Depth:** 1

---

### Method M04
```csharp
// Method M04
public static Tuple<string, string> MakeError()
{
    return Tuple.Create("ERR_SYNTAX", "Invalid command line syntax encountered.");
}
```
- **Context:** Default error tuple factory.
- **LOC:** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Short option switch clustering tokenizer.
- **LOC:** 44 | **Cyclomatic Complexity:** 7 | **Max Nesting Depth:** 3

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
- **LOC:** 12 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 1

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
- **LOC:** 6 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

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
- **LOC:** 6 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Separator-delimited option argument expansion.
- **LOC:** 16 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Token stream partitioner.
- **LOC:** 15 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **LOC:** 5 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Reflection scanner for property specifications.
- **LOC:** 10 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

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
- **Context:** Higher-order property value mapper.
- **LOC:** 42 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M14
```csharp
// Method M14
public static bool IsValueForced(Token token)
{
    return token.IsValue() && token.Tag == TokenTag.ValueForced;
}
```
- **Context:** Token tag predicate.
- **LOC:** 4 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

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
- **Context:** Reflection property setter with exception capture.
- **LOC:** 8 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M16
```csharp
// Method M16
public static T ImplicitCast<T>(object obj)
{
    return (T)Convert.ChangeType(obj, typeof(T), CultureInfo.InvariantCulture);
}
```
- **Context:** Invariant culture generic type conversion.
- **LOC:** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

### Method M17
```csharp
// Method M17
public static Tuple<string, string> MakeError(string code, string message)
{
    return Tuple.Create(code, message);
}
```
- **Context:** Error tuple constructor.
- **LOC:** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Built-in switch guard evaluator (`--help`, `--version`).
- **LOC:** 10 | **Cyclomatic Complexity:** 3 | **Max Nesting Depth:** 1

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
- **LOC:** 4 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **Context:** Response file reader.
- **LOC:** 9 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

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
- **Context:** Verb argument matcher.
- **LOC:** 33 | **Cyclomatic Complexity:** 2 | **Max Nesting Depth:** 0

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
- **Context:** Reflection factory for immutable record instantiation.
- **LOC:** 23 | **Cyclomatic Complexity:** 3 | **Max Nesting Depth:** 1

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
- **Context:** Value mapping overload.
- **LOC:** 38 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

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
- **LOC:** 26 | **Cyclomatic Complexity:** 1 | **Max Nesting Depth:** 0

---

## 4. Participant Evaluation Sheet

| Method ID | Q1: Defect Risk (1–5) | Q2: Complexity (1–5) | Q3: Review Urgency (1–5) | Primary Rationale |
| :--- | :--- | :--- | :--- | :--- |
| M01 | | | | |
| M02 | | | | |
| M03 | | | | |
| M04 | | | | |
| M05 | | | | |
| M06 | | | | |
| M07 | | | | |
| M08 | | | | |
| M09 | | | | |
| M10 | | | | |
| M11 | | | | |
| M12 | | | | |
| M13 | | | | |
| M14 | | | | |
| M15 | | | | |
| M16 | | | | |
| M17 | | | | |
| M18 | | | | |
| M19 | | | | |
| M20 | | | | |
| M21 | | | | |
| M22 | | | | |
| M23 | | | | |
| M24 | | | | |

---

## 5. Statistical Analysis Protocol

### 5.1 Inter-Rater Reliability Metrics

| Metric | Formula | Scale Type | Interpretation |
| :--- | :--- | :--- | :--- |
| Krippendorff's $\alpha$ | $\alpha = 1 - \frac{D_o}{D_e}$, $\delta^2(c, k) = \left( \sum_{g=c}^k n_g - \frac{n_c + n_k}{2} \right)^2$ | Ordinal | $\ge 0.800$ high; $0.667\text{--}0.800$ moderate; $< 0.667$ low |
| $\text{ICC}(2, k)$ | $\frac{\text{MS}_R - \text{MS}_E}{\text{MS}_R + (\text{MS}_C - \text{MS}_E)/n}$ | Quasi-interval | $> 0.75$ high; $0.60\text{--}0.75$ moderate |
| Kendall's $W$ | $\frac{12 \sum_{i=1}^N (R_i - \bar{R})^2}{m^2 (N^3 - N)}$ | Rank order | $[0, 1]$ concordance across $m$ raters |
| Fleiss' $\kappa$ | $\frac{\bar{P} - \bar{P}_e}{1 - \bar{P}_e}$ | Nominal | Unweighted categorical agreement baseline |

### 5.2 Model Concordance
1. Compute mean human defect rating per method: $\bar{S}_i = \frac{1}{m}\sum_{r=1}^m \text{Q1}_{i,r}$.
2. Compute Spearman rank correlation ($\rho$) between $\bar{S}_i$ and model probability $P(\text{defect-prone} \mid \mathbf{x}_i)$.
3. Compute Cohen's $\kappa$ between binarized human ratings ($\bar{S}_i \ge 3.0$) and model classification $\hat{y}_i \in \{0, 1\}$.

---

## 6. Reference Mapping Key

> [!CAUTION]
> **RESEARCHER REFERENCE KEY**  
> Omit this section when distributing the review packet to study participants.

| Method | Obs ID | SZZ Label | Predicted | Quadrant | Risk Score | Method Name | Discrepancy / Context Note |
| :--- | :---: | :---: | :---: | :---: | ---: | :--- | :--- |
| M01 | 118 | 0 | 0 | TN | 0.278 | `CastExtensions.CanCast` | Short type check; low complexity. |
| M02 | 44 | 1 | 1 | TP | 0.691 | `InstanceChooser.Choose` | Multi-step dispatch with reflection and LINQ. |
| M03 | 28 | 1 | 1 | TP | 0.621 | `Value.Equals` | Null check and multi-branch equality. |
| M04 | 112 | 0 | 0 | TN | 0.179 | `Program.MakeError` | Four-line tuple factory. |
| M05 | 132 | 0 | 1 | FP | 0.592 | `GetoptTokenizer.TokenizeShortName` | Nesting depth 3 and loop count trigger alert; no recorded fix in Git. |
| M06 | 27 | 1 | 0 | FN | 0.496 | `Tokenizer.PreprocessDashDash` | Near-threshold miss (0.496) at $\tau=0.50$. |
| M07 | 13 | 1 | 0 | FN | 0.429 | `ReflectionHelper.GetExecutingOrEntryAssembly` | Runtime assembly fallback defect; low static complexity. |
| M08 | 145 | 0 | 0 | TN | 0.397 | `NameExtensions.FromOptionSpecification` | Simple mapping adapter. |
| M09 | 42 | 1 | 0 | FN | 0.491 | `Tokenizer.ExplodeOptionList` | Monadic LINQ chain; low cyclomatic complexity. |
| M10 | 36 | 1 | 1 | TP | 0.753 | `Sequence.Partition` | Predicate token stream slicing. |
| M11 | 121 | 0 | 0 | TN | 0.279 | `CastExtensions.CanImplicitCast` | Interface assignability check. |
| M12 | 156 | 0 | 1 | FP | 0.610 | `ReflectionExtensions.GetSpecifications` | Reflection and chained LINQ predicates; candidate-clean in Git. |
| M13 | 149 | 0 | 1 | FP | 0.836 | `OptionMapper.MapValues` | 42 LOC higher-order mapper; candidate-clean in Git. |
| M14 | 29 | 1 | 0 | FN | 0.323 | `TokenExtensions.IsValueForced` | Four-line boolean check; semantic defect not visible to AST metrics. |
| M15 | 162 | 0 | 1 | FP | 0.625 | `ReflectionExtensions.SetProperties` | Reflection setter in `try-catch` loop; candidate-clean in Git. |
| M16 | 125 | 0 | 0 | TN | 0.259 | `CastExtensions.ImplicitCast` | Single-line conversion wrapper. |
| M17 | 116 | 0 | 0 | TN | 0.179 | `Program.MakeError` | Four-line tuple constructor. |
| M18 | 153 | 0 | 1 | FP | 0.524 | `PreprocessorGuards.Lookup` | Iterator (`yield return`) with nested lambdas. |
| M19 | 47 | 1 | 0 | FN | 0.241 | `Token.ValueForced` | Four-line factory method; low static complexity. |
| M20 | 114 | 0 | 1 | FP | 0.520 | `Program.ReadLines` | File I/O helper; borderline risk score. |
| M21 | 45 | 1 | 1 | TP | 0.763 | `InstanceChooser.MatchVerb` | 33 LOC verb matcher. |
| M22 | 17 | 1 | 1 | TP | 0.573 | `InstanceBuilder.BuildImmutable` | Reflection constructor invocation and parameter matching. |
| M23 | 41 | 1 | 1 | TP | 0.824 | `OptionMapper.MapValues` | 38 LOC mapper with converter delegate. |
| M24 | 54 | 1 | 0 | FN | 0.362 | `TokenPartitioner.Partition` | 26 LOC partition loop; missed at $\tau=0.50$. |

---

## 7. Administration Status

> [!IMPORTANT]
> **Status: Unadministered Research Protocol**  
> No human participant ratings were collected or fabricated. If administered in a future study, participant response files should be stored separately under `3_TestResults/DeveloperStudy/responses/` with Sections 5 and 6 withheld until data collection is complete.
