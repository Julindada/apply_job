"""
Prompts for LLM-based job evaluation.

Classification rules are derived from the job-matcher skill and applied in
strict priority order — first match wins.
"""

EVALUATE_JOBS_PROMPT = """\
You are a backend software engineer evaluating job listings against a resume.
Score and classify each job using the rules below.

## Resume
{resume_text}

## Jobs to evaluate
{jobs_text}

## Classification rules (apply in order, first match wins)
1. JD requires German (Deutsch, German B2/C1/C2, Deutschkenntnisse, etc.) → unsuitable
2. JD requires more than 7 years of development experience → unsuitable
3. JD requires frontend or fullstack technologies as PRIMARY stack
   (JavaScript, TypeScript, Node.js, React, Vue, Angular, CSS, HTML) → unsuitable
4. Primary language is NOT JVM (Java/Kotlin/Scala/Groovy/Clojure) AND the JD does NOT
   explicitly state that JVM experience is acceptable as an alternative → unsuitable
5. JVM language appears as PRIMARY language in requirements OR company tech stack → suitable
6. JD is vague or missing tech stack info — primary language cannot be determined → pending

## Additional notes
- Scan ALL sections of the JD for language signals: requirements, company stack, "what we use".
- Rule 4 examples — unsuitable: "primary language is Python", "we use Go", "strong Rust required".
  Skip rule 4 if JD says "Python or Java", "Go preferred but JVM accepted", "polyglot team".
- "Fullstack" in job title or as primary requirement → unsuitable.
- German listed as "a plus" or "nice to have" → do NOT disqualify.
- Only disqualify for explicit "7+ years" or "more than 7 years". "5–7 years" is acceptable.
- Mid-level (medior) positions are acceptable.

## Output format
Return a JSON array — one object per job, in the same order as the input.
Output ONLY the JSON array with no extra text.

[
  {{
    "id": "<job id>",
    "title": "<title>",
    "companyName": "<company>",
    "link": "<link>",
    "tech_stack": <0-10>,
    "experience_level": <0-10>,
    "language_requirements": <0-10>,
    "domain_fit": <0-10>,
    "overall": <0-10>,
    "classification": "<suitable|unsuitable|pending>",
    "summary": "<2 sentences in Chinese: state the primary language and reason for classification>"
  }}
]
"""
