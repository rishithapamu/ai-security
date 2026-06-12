# 004 — Registry Design Notes

## Status
Accepted

## Context
The registry separates attack analysis into two orthogonal dimensions:
primitives (technique) and behaviors (objective). This separation allows
coverage analysis to identify gaps where a technique has never been
observed targeting a particular objective.

## Primitive vs Behavior

A primitive describes HOW an attack is constructed:
- instruction_override — directly commands the model to ignore rules
- roleplay_jailbreak — uses fictional personas to bypass restrictions
- prompt_manipulation — exploits instruction parsing through structure
- content_extraction — attempts to retrieve protected content
- sensitive_information_extraction — targets private user/system data
- emotional_engagement — uses relational framing to influence responses
- content_policy_circumvention — obfuscates restricted requests
- misinformation_generation — frames false information as factual

A behavior describes WHAT harm the attacker is trying to cause:
- criminal_assistance, cybercrime_enablement, fraud_and_deception,
  misinformation_generation, hateful_or_violent_content,
  sexual_content_generation, dangerous_materials_assistance,
  self_harm_enablement, harassment_enablement, harmful_advice,
  economic_manipulation, reputational_manipulation,
  content_policy_circumvention

## Consequences
Each cluster is assigned both a primitive and a behavior in
cluster_assignments.yaml. The coverage matrix is built from this
two-dimensional assignment.
