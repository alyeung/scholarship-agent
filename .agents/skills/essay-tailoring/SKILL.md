---
name: essay-tailoring
description: >-
  Use this skill when drafting, outlining, or revising graduate scholarship
  personal statements, research proposals, or fellowship application essays.
---

# Graduate Fellowship Essay Tailoring Skill

Follow this runbook when helping the user draft or refine scholarship essays.

## Steps

1. **Fetch Combined Prompt & Profile Context**:
   - Call `get_essay_prompt_context(scholarship_id)` to retrieve the target scholarship's mission, evaluation rubric, essay prompt, and the user's relevant projects, research interests, and leadership roles from `profile.yaml`.
2. **Structure the Essay**:
   - **Hook & Motivation**: Connect a concrete project or lived experience from `profile.yaml` to the student's graduate research agenda.
   - **Intellectual Merit / Technical Depth**: Highlight specific methodologies, projects (`publications_or_projects`), and alignment with `academics.target_universities`.
   - **Broader Impacts / Leadership**: Tie in mentorship and community work (`leadership_and_service`) and geographic/community impact (`geographies`).
   - **Why This Fellowship**: Explicitly align with the foundation's stated mission and criteria.
3. **Save Draft Artifact**:
   - Save the structured outline and full draft to `data/essays/` using `save_essay_draft()`.
