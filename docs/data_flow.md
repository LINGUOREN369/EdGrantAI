# EdGrantAI — Data Flow

```mermaid
flowchart TD
    A[Grant text (input)] --> B[CKE: Controlled Keyphrase Extractor<br/>(pipeline/cke.py)]
    P[prompts/cke_prompt_v1.txt] --> B
    B -->|OpenAI Chat · settings.OPENAI_CHAT_MODEL| C[Extracted phrases (JSON array)]

    C --> D[Canonical Mapping<br/>(pipeline/canonical_mapper.py)]
    T1[data/taxonomy/*.json] --> D
    T2[data/taxonomy/embeddings/*_embeddings.json] --> D
    D -->|OpenAI Embeddings · settings.OPENAI_EMBEDDING_MODEL| E[Canonical tags + confidence]

    C --> F[Grant Profile Builder<br/>(pipeline/grant_profile_builder.py)]
    E --> F
    V[data/taxonomy/schema_version.json] --> F
    F --> G[Grant profile (dict)]
    G --> H[data/processed_grants/{grant_id}_profile.json]

    subgraph Offline Prep
      O[Embed canonical tags<br/>(embedding_matcher.embed_canonical_tags)] --> T2
    end

    subgraph Config & Env
      S[pipeline/config.py<br/>loads .env, defines paths & models] -.-> B
      S -.-> D
      S -.-> F
    end
```

## Summary
- CKE extracts verbatim phrases using the prompt and OpenAI Chat.
- Canonical mapping embeds phrases and matches against taxonomy embeddings.
- Grant profile builder merges phrases, tags, and taxonomy version and writes JSON to `data/processed_grants/`.
- `pipeline/config.py` centralizes paths, models, and `.env` loading.

