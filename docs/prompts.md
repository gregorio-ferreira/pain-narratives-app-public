# Prompts and Questionnaires

This document summarizes the prompts used by AINarratives to evaluate pain
narratives and to run questionnaire-style assessments with LLMs. The canonical
prompt definitions live in:

- `src/pain_narratives/config/default_prompts.yaml`
- `src/pain_narratives/config/simplified_v1_prompts.yaml`

The default prompt set is the original research-oriented version. It asks for
scores, brief explanations, and model reasoning. The `simplified_v1` prompt set
is used for revision and batch experiments where only structured numeric
answers are needed.

## Narratives and Dimension Evaluations

The narrative evaluation prompt asks the LLM to act as an expert in chronic pain
evaluation. The narratives are expected to be written in Spanish, and the model
is asked to analyze the described pain experience without inflating scores.

The default prompt is assembled from four parts:

1. A system role describing the model as an expert evaluator of chronic pain.
2. A list of active evaluation dimensions.
3. A base prompt reminding the model to account for severity, disability,
   coping mechanisms, resilience, support systems, and adaptive behaviors.
4. A JSON response schema followed by the `{narrative}` placeholder.

The default dimensions are:

| Dimension | Scale | Meaning |
|---|---:|---|
| `Severidad del dolor` | 0-10 | Perceived magnitude of the pain and general suffering described by the person. |
| `Discapacidad` | 0-10 | Perceived degree to which pain disrupts usual activities and daily life. |

Example prompt fragment:

```text
Please analyze the following narrative and provide scores for these dimensions as specified:

1. **Severidad del dolor**: La magnitud percibida del problema de salud descrito por la persona en relación con el dolor y el sufrimiento general, donde 0 representa "nada" y 10 "el nivel máximo". (Score range: 0-10)
2. **Discapacidad**: El grado percibido en que el problema de salud descrito por la persona altera sus actividades habituales y su vida, siendo 0 "nada" y 10 "el nivel máximo posible" (Score range: 0-10)

Scores should accurately reflect the levels described in patient narratives without inflation.
...
Patient narrative:
{narrative}
```

Example synthetic narrative:

```text
Desde hace varios años tengo dolor lumbar casi todos los días. Algunos días es
muy intenso y tengo que descansar, pero puedo trabajar a media jornada y caminar
despacio. Me frustra no poder hacer deporte como antes, aunque los ejercicios
suaves y el apoyo de mi familia me ayudan a seguir con mis rutinas.
```

Example default output:

```json
{
  "severidad_del_dolor": 7,
  "severidad_del_dolor_explanation": "The narrative describes chronic daily pain with some intense episodes, but also periods where the person remains active with adaptations.",
  "discapacidad": 5,
  "discapacidad_explanation": "Pain limits work capacity and sport participation, but the person still maintains part-time work, walking, and routines with support.",
  "reasoning": "The scores balance persistent pain and meaningful limitations against coping strategies and preserved daily functioning."
}
```

In `simplified_v1`, the same task is reduced to numeric structured fields only:

```json
{
  "severidad_del_dolor": 7,
  "discapacidad": 5
}
```

## Questionnaires with Narrative Author Impersonation

The questionnaire prompts ask the LLM to impersonate the author of the pain
narrative and answer standardized questionnaire items as if it were that person.
The questionnaire items are kept in Spanish to preserve the validated wording,
while the default prompt asks free-text fields such as persona traits and model
reasoning to be written in English.

The supported questionnaires are:

| Questionnaire | Target construct | Response scale |
|---|---|---|
| `PCS` | Pain Catastrophizing Scale: rumination, magnification, helplessness. | 13 items scored 0-4. |
| `BPI-IS` | Brief Pain Inventory: pain interference and pain intensity. | Interference and intensity items scored 0-10. |
| `TSK-11SV` | Tampa Scale of Kinesiophobia short version: fear of movement and activity avoidance. | 11 items scored 1-4. |

Each questionnaire prompt has two main parts:

1. A system role identifying the questionnaire and asking the model to answer on
   behalf of the narrative author.
2. Instructions containing the questionnaire wording, response scale, the
   `{narrative}` placeholder, and the expected JSON schema.

Example system role for the PCS prompt:

```text
You are an expert in psychological assessment. Your task is to impersonate the
person who wrote the following pain narrative, and answer the "Pain
Catastrophizing Scale" (PCS) questionnaire as if you were that person. The PCS
evaluates an individual's negative cognitive and emotional responses to pain. It
specifically assesses three components: rumination (constantly thinking about
pain), magnification (exaggerating the threat of pain), and helplessness
(feeling unable to cope with the pain).
```

Example synthetic narrative:

```text
Cuando aparece el dolor cervical me asusto porque pienso que puede empeorar.
A veces no puedo dejar de pensar en ello y me cuesta dormir. Intento hacer mis
ejercicios, pero si noto un pinchazo paro enseguida porque temo hacerme daño.
```

Example PCS output using the default prompt:

```json
{
  "questionnaire_id": "PCS",
  "persona": {
    "name": "Cautious pain narrator",
    "traits": "Anxious about symptom escalation, vigilant toward pain sensations, and somewhat avoidant when pain increases."
  },
  "scores": {
    "1": 3,
    "2": 2,
    "3": 3,
    "4": 2,
    "5": 2,
    "6": 3,
    "7": 2,
    "8": 3,
    "9": 3,
    "10": 2,
    "11": 3,
    "12": 1,
    "13": 3
  },
  "model_reasoning": "The narrative suggests frequent worry, difficulty disengaging from pain-related thoughts, sleep disruption, and fear that symptoms may worsen, while still showing some active coping through exercises."
}
```

Example BPI-IS output using the default prompt:

```json
{
  "questionnaire_id": "BPI-IS",
  "persona": {
    "name": "Anxious cervical pain narrator",
    "traits": "Fearful of symptom worsening, experiences sleep disruption, and avoids movements that trigger pain while still attempting exercises."
  },
  "responses": [
    {"code": "BPI_Q1_1", "value": 5},
    {"code": "BPI_Q1_2", "value": 6},
    {"code": "BPI_Q1_3", "value": 3},
    {"code": "BPI_Q1_5", "value": 3},
    {"code": "BPI_Q1_6", "value": 7},
    {"code": "BPI_Q1_7", "value": 5},
    {"code": "BPI_Q2_8", "value": 7},
    {"code": "BPI_Q3_9", "value": 3},
    {"code": "BPI_Q4_10", "value": 5},
    {"code": "BPI_Q5_11", "value": 5}
  ],
  "model_reasoning": "The narrative highlights significant sleep disruption and continuous worry about worsening pain, justifying higher interference scores for mood and sleep. General activity and enjoyment are moderately affected because the person still attempts exercises. Walking ability carries a lower score as cervical pain does not primarily limit ambulation. Worst pain reflects the triggering episodes that cause immediate activity cessation."
}
```

Example TSK-11SV output using the default prompt:

```json
{
  "questionnaire_id": "TSK-11SV",
  "persona": {
    "name": "Cautious pain narrator",
    "traits": "Fearful of pain-related injury and quick to stop activity when symptoms increase."
  },
  "responses": [
    {"code": "TSK_01", "value": 3},
    {"code": "TSK_02", "value": 3},
    {"code": "TSK_03", "value": 3},
    {"code": "TSK_04", "value": 2},
    {"code": "TSK_05", "value": 3},
    {"code": "TSK_06", "value": 3},
    {"code": "TSK_07", "value": 2},
    {"code": "TSK_08", "value": 4},
    {"code": "TSK_09", "value": 2},
    {"code": "TSK_10", "value": 3},
    {"code": "TSK_11", "value": 1}
  ],
  "model_reasoning": "The responses reflect fear of worsening or injury during movement, but not a complete rejection of physical activity because the person still attempts exercises."
}
```

In `simplified_v1`, questionnaire responses omit `persona` and `model_reasoning`
fields, keeping only the answer values. PCS keeps its `scores` dict structure:

```json
{
  "questionnaire_id": "PCS",
  "scores": {
    "1": 3,
    "2": 2,
    "3": 3,
    "4": 2,
    "5": 2,
    "6": 3,
    "7": 2,
    "8": 3,
    "9": 3,
    "10": 2,
    "11": 3,
    "12": 1,
    "13": 3
  }
}
```

BPI-IS and TSK-11SV follow the same reduction, retaining only the `responses`
array. For example, TSK-11SV in `simplified_v1`:

```json
{
  "questionnaire_id": "TSK-11SV",
  "responses": [
    {"code": "TSK_01", "value": 3},
    {"code": "TSK_02", "value": 3},
    {"code": "TSK_03", "value": 3},
    {"code": "TSK_04", "value": 2},
    {"code": "TSK_05", "value": 3},
    {"code": "TSK_06", "value": 3},
    {"code": "TSK_07", "value": 2},
    {"code": "TSK_08", "value": 4},
    {"code": "TSK_09", "value": 2},
    {"code": "TSK_10", "value": 3},
    {"code": "TSK_11", "value": 1}
  ]
}
```

These examples are illustrative only. Actual scores can vary by model,
temperature, prompt version, and the specific evidence present in each
narrative.

## Prompt Library Templates

`default_prompts.yaml` also contains a `prompt_library` section with
pre-configured full prompt templates that can be selected through the UI or
used directly in experiments. The current templates are:

| Template key | Description |
|---|---|
| `chronic_pain_expert_assessment` | Default expert-evaluator prompt (same dimensions as the main default). |
| `chronic_pain_comprehensive` | Extended evaluation with five dimensions: pain intensity, functional impact, emotional impact, descriptive quality, and symptom complexity. Scores use a 1-10 scale. |
| `general_pain_assessment` | General pain assessment with pain severity, functional limitation, temporal pattern, and associated symptoms. Scores use a 1-10 scale. |
| `research_focused` | Research-oriented analysis with six scored dimensions plus pain descriptors and affected functional domains. Scores use a 1-10 scale. |

These templates are self-contained: each one embeds the system role, dimension
definitions, scoring instructions, and the JSON response schema. They are
intended as starting points that researchers can clone and adapt via the UI.
