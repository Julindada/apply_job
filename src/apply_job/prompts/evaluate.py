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
2. JD requires 7 or more years of development experience (e.g. "7+ years", "8+ years", "10+ years", "at least 7 years") → unsuitable
3. JD requires frontend or fullstack technologies as PRIMARY stack
   (JavaScript, TypeScript, Node.js, React, Vue, Angular, CSS, HTML) → unsuitable
4. JD explicitly names a non-JVM language as the sole/primary language (e.g. "we use Python",
   "primary language is Go", "strong Rust required") AND does NOT mention any JVM language
   (Java/Kotlin/Scala) anywhere in requirements or tech stack → unsuitable
5. Any JVM language (Java/Kotlin/Scala) appears ANYWHERE in the required
   skills, preferred skills, or company tech stack — even alongside other languages → suitable
6. JD contains zero language signals and tech stack cannot be determined at all → pending

## Additional notes
- Scan ALL sections of the JD for language signals: requirements, company stack, "what we use".
- Rule 4 examples — unsuitable: "primary language is Python with no Java/Kotlin mention",
  "we use Go exclusively". Skip rule 4 if Java/Kotlin appears anywhere in the JD.
- Rule 5 examples — suitable: "Java or Python", "Kotlin preferred", "experience in Java is a plus",
  "our stack includes Java/Spring", "polyglot team using Kotlin and Go".
- "Fullstack" in job title or as primary requirement → unsuitable.
- German listed as "a plus" or "nice to have" → do NOT disqualify.
- Disqualify for any explicit threshold ≥ 7 years: "7+ years", "8+ years", "10+ years", "at least 7 years", etc. "5–6 years" is acceptable.
- Mid-level (medior) positions are acceptable.
- When in doubt between suitable and pending, choose suitable if any JVM language is visible.

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
