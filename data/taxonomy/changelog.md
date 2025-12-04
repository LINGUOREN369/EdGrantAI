# Taxonomy Changelog

## 0.0.1
 - Initial taxonomy release
Created MECE lists for mission, population, org types, geography, and red flags.
Cleaned and standardized naming conventions across all files.
## 0.0.2 - Updated taxonomy matching thresholds
- Updated all taxonomy with more broader range 


## 0.0.3 - Updated all taxonomy to better focus on the NSF grants
- Refined mission, population, org types, geography, and red flags to align more closely with NSF grant criteria
- Removed less relevant tags and added more specific ones based on recent grant analyses


## 0.0.4 - Minor adjustments to taxonomy thresholds to tailor towards NSF grants and remove underline issues
- Adjusted mission, population, org types, geography, and red flags thresholds for improved accuracy
- Fixed underline formatting issues in taxonomy files
- Upgrade to embedding model to text-embedding-3-large for better semantic understanding

## 0.0.5 - NSF-focused additions and variants
- Added org types to better reflect NSF collaborator/eligibility language:
  - "local education agency (LEA)", "national laboratory", "industry partner", "international organization", "small business concern"
- Added red-flag/requirement variants commonly seen in NSF solicitations:
  - "data management and sharing plan", "postdoctoral mentoring plan", "letters of collaboration", "human subjects protections", "industry partner required", "multi-institutional collaboration required"
- Added mission refinements to capture NSF-EHR phrasing:
  - "computing education research", "learning technologies", "STEM pathways"
- No removals; semantic embeddings should be rebuilt and validated.

## 0.0.6 - Guardrails and coverage for org profiles
- Added population breadth and instructor roles:
  - "K-12 students", "middle school teachers", "high school teachers", "college instructors"
- Added geography specificity:
  - "Colorado"
- Introduced canonical mapping guardrails (code) to reduce org_type misclassification and spurious red flags.
  - Audience-like phrases no longer map to org_types
  - Red flags require gating terms (e.g., "only", "required", "eligibility", etc.)
  - Computing-related mission tags require explicit computing cues (e.g., "computer science", "coding")

## 0.0.7 - Added NSF programs taxonomy
- New taxonomy file: `nsf_programs.json` capturing NSF directorates, divisions, and offices (BIO, CISE, ENG, GEO, MPS, SBE, EDU, TIP, and associated sub-units).
- Use case: analytics, filtering, or future program‑aware matching.
- To build embeddings only for this taxonomy: `python -m pipeline.build_taxonomy_embeddings --names nsf_programs --force`
## 0.0.8 - Mission taxonomy refinements
- Removed redundancy: dropped "STEM pathways" (keep "STEM career pathways").
- Added cross-cutting education terms:
  - "technology-enhanced learning", "open educational resources (OER)", "digital learning platforms", "simulation-based learning"
- Added policy term:
  - "STEM education policy"
## 0.0.9 - MECE cleanup and NSF alignment
- Mission (MECE):
  - Removed overlap: dropped "computing education" (keep "computer science education" and "computing education research").
  - Replaced generic "education research" with "STEM education research".
  - Removed "education equity and access" and "access to STEM opportunities" (covered by existing equity tags).
  - Removed "informal learning environments" (keep "informal STEM learning").
- Population (MECE):
  - Removed duplicate grade-range variants (K-5, grades 6-8, grades 9-12) and general "postsecondary students"; kept canonical grade bands and undergrad/grad.
  - Kept new breadth tags (K-12 students, college instructors).
- Org types (MECE):
  - Removed "nonprofit organization" (keep "501(c)(3) nonprofit").
  - Consolidated private school tags into "independent private school".
  - Removed "library system"; kept "public library".
  - Added "university-based research center".
  - Removed duplicate "local education agency (LEA)" (kept "public school district").
- Geography (MECE):
  - Removed overlapping synonyms: "international", "national", "statewide programs", "municipal programs", "district-wide programs", and duplicate tribal variants.
## 0.0.10 - Mission/population/org-type coverage for EdTech/AI tutoring orgs
- Mission additions for breadth:
  - "personalized learning", "mastery-based learning", "AI-powered tutoring", "curriculum alignment", "teacher professional learning", "education system partnerships", "early childhood learning"
- Population additions:
  - "all-ages learners", "informal learners", "historically underserved students", "underserved communities", "teachers", "school districts", "state education agencies", "ministries of education", "global learners"
- Org types:
  - Added "education technology organization"; nonprofit enforcement added in org profile builder when "nonprofit" appears.
