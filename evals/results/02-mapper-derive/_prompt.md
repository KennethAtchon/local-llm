## Runbook excerpt — docs/delivery/plans/taste-engine-v2/01-publish-string-and-correctness.md lines 158-188

### Step 3 — Writer emits one string

`backend/src/domain/distribution/taste/generation/taste-generation.agent.ts`

1. Remove `caption` from `outputSchema.move`.
2. Rename `previewText` → `publishText`, keep `min(1).max(2_200)`.
3. Add to the system prompt: `"Return exactly one publish string. It is the text
   the owner will read and the text that will be posted."`
4. Bump `promptVersion: 1` → `2`. A prompt change with an unchanged version is
   how receipts start lying.

### Step 4 — Derive composition, never author it twice

`taste-generation.mapper.ts`:

```ts
const publishText = generated.publishText;
const draft: PlatformNativeDraft = {
  composition: {
    platform: "tiktok",
    fields: { caption: publishText },   // derived, single source
    source: "ai",
  },
  publishText,
  productionBrief: { ... },
};
```

Do the same for the classic mapper (`mapAgentMove`, `growth-move.service.ts:2704-2801`)
so both branches share the invariant before WP07 merges them.


---

## Existing file — backend/src/domain/distribution/taste/generation/taste-generation.mapper.ts

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

---

## Your task

The existing file shown above is the PRE-change version for this exercise. Rewrite backend/src/domain/distribution/taste/generation/taste-generation.mapper.ts so the publish string is authored once and composition.fields.caption is derived from it, per Step 4. Output the complete file.