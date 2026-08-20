# qwen3-coder-30b — Step 4 — derive composition from publishText (has ground truth)

```json
{
  "elapsed_s": 9.3,
  "prompt_tokens": 831,
  "completion_tokens": 358,
  "tok_per_s": 38.4,
  "finish": "stop",
  "reasoning_chars": 0
}
```

```ts
import type { PlatformNativeDraft } from "@azelify/contracts/distribution";
import type { ProposedMove } from "@/domain/distribution/growth-move.validator";
import type { TasteGenerationAgentOutput } from "./taste-generation.agent";

export function mapTasteGeneratedMove(input: {
  output: TasteGenerationAgentOutput;
  playbookVersion: string;
  now: Date;
}): ProposedMove {
  const generated = input.output.move;
  const recommended = new Date(input.now);
  recommended.setUTCHours(generated.timingHourLocal, 40, 0, 0);
  if (recommended <= input.now)
    recommended.setUTCDate(recommended.getUTCDate() + 1);
  const publishText = generated.publishText;
  const draft: PlatformNativeDraft = {
    composition: {
      platform: "tiktok",
      fields: { caption: publishText },
      source: "ai",
    },
    publishText,
    productionBrief: {
      hook: generated.hook,
      angle: generated.angle,
      structure: generated.structure,
      sourceUrl: null,
    },
  };
  return {
    platform: "tiktok",
    type: generated.type,
    urgency: generated.urgency,
    expiresAt: null,
    evidenceSnapshotIds: generated.evidenceSnapshotIds,
    rationale: generated.rationale,
    headline: generated.headline,
    draft,
    visual: null,
    timing: {
      recommendedAt: recommended.toISOString(),
      timezone: "local",
      confidence: generated.timingConfidence,
      rationale: generated.timingRationale,
    },
    playbookVersion: input.playbookVersion,
    topicEntities: generated.topicEntities,
    angle: generated.angle,
  };
}
```
