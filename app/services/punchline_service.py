"""Punchline generation service for creating personalized email opening lines."""

import re
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.lead import Lead
from app.models.task import Task, TaskStatus
from app.services.llm_provider import get_llm_client
from app.schemas.lead import LeadUpdate


# Configuration
MAX_WORDS = 35

PROVENANCE_NATURAL: Dict[str, List[str]] = {
    "home": ["on your homepage", "in your main pitch", "right up front"],
    "about": ["on your About page", "in your story"],
    "services": ["across your services", "in how you position the offer"],
    "cases": ["in your case work", "in your client stories", "across the case studies"],
    "portfolio": ["through the portfolio", "across your work"],
    "clients": ["among your client logos", "in the clientele you show"],
    "blog": ["in a recent post", "on the blog", "in your writing"],
    "news": ["in your latest update", "in the recent press", "in news/press"],
    "generic": ["on your site"]
}

GOOD_EXAMPLES = [
    "Impressed by how you highlight sustainability on your homepage—it's rare to see an agency tie green practices directly into their service offering.",
    "Your case study with Shopify brands stood out—it's clear you've carved a strong niche in eCommerce growth.",
    "Loved your blog on AI in marketing—practical tips like that show how tuned-in you are to what SMBs need today."
]

BAD_EXAMPLES = [
    "I saw your website and it looks great.",
    "You seem like a good company doing nice work.",
    "I noticed you are an agency in New York."
]

BAD_PHRASES = [
    "i saw your website",
    "came across your website",
    "hope this email finds you",
    "you seem like a good company",
    "you are an agency in",
    "i noticed you are an agency",
    "looks great",
    "nice work",
]

BAD_REGEXES = [
    r"\bi noticed\b",
    r"\bi was browsing\b",
    r"\byour website looks\b",
    r"\byou (?:seem|seems)\b",
    r"\bwe (?:can|could|help)\b",
]

SYSTEM_RULES = (
    "You write the opening line for a cold email. Do not use clichés starting like I see, I like, I appreciate something like that.\n"
    f"Write ONE punchy, human line (1–2 sentences, max {MAX_WORDS} words).\n"
    "Be specific, flattering, and focused on THEM (not us). No clichés.\n"
    "Paraphrase; do not copy snippets. Mention WHERE naturally if useful (e.g., on your homepage, in your case study, on your blog).\n"
    "Prefer recency > case/results > awards/clients > hero.\n"
    "Vary style; do not sound templated. Output only the line.\n\n"
    "Good examples to emulate (tone/structure only):\n"
    f"- {GOOD_EXAMPLES[0]}\n- {GOOD_EXAMPLES[1]}\n- {GOOD_EXAMPLES[2]}\n\n"
    "Bad examples to avoid (do not produce anything similar):\n"
    f"- {BAD_EXAMPLES[0]}\n- {BAD_EXAMPLES[1]}\n- {BAD_EXAMPLES[2]}"
)


class PunchlineService:
    """Service for generating personalized email punchlines using LLM."""
    
    @staticmethod
    def _word_count(s: str) -> int:
        """Count words in a string."""
        return len(re.findall(r"\b\w+\b", s))
    
    @staticmethod
    def _ngram_overlap(a: str, b: str, n: int = 4) -> float:
        """Calculate n-gram overlap between two strings."""
        def grams(s):
            toks = re.findall(r"\w+", s.lower())
            return set(tuple(toks[i:i+n]) for i in range(len(toks)-n+1))
        
        A, B = grams(a), grams(b)
        if not A or not B:
            return 0.0
        return len(A & B) / float(len(A))
    
    @staticmethod
    def _normalize(s: str) -> str:
        """Normalize whitespace in string."""
        return re.sub(r"\s+", " ", s).strip()
    
    @staticmethod
    def _passes_qc(line: str, snippets: List[str]) -> bool:
        """
        Quality check for a punchline.
        
        Args:
            line: Generated punchline
            snippets: Source text snippets to check for copying
            
        Returns:
            True if punchline passes quality checks
        """
        if not line or len(line.strip()) < 10:
            return False
        
        words = PunchlineService._word_count(line)
        if words > MAX_WORDS:
            return False
        
        # Check for bad phrases
        lower = line.lower()
        for phrase in BAD_PHRASES:
            if phrase in lower:
                return False
        
        # Check for bad regex patterns
        for pattern in BAD_REGEXES:
            if re.search(pattern, lower):
                return False
        
        # Check for copied snippets
        for snippet in snippets:
            if PunchlineService._ngram_overlap(line, snippet) > 0.3:
                return False
        
        return True
    
    @staticmethod
    def _detect_used_kind(line: str, default: str = "generic") -> str:
        """Detect which provenance kind was used in the line."""
        lower = line.lower()
        for kind, phrases in PROVENANCE_NATURAL.items():
            for phrase in phrases:
                if phrase.lower() in lower:
                    return kind
        return default
    
    @staticmethod
    def _score_line(line: str, used_kind: str) -> float:
        """
        Score a punchline for quality.
        
        Higher score = better quality
        """
        score = 0.5  # Base score
        
        # Prefer shorter lines
        words = PunchlineService._word_count(line)
        if words < 20:
            score += 0.2
        elif words > 30:
            score -= 0.2
        
        # Bonus for non-generic provenance
        if used_kind != "generic":
            score += 0.3
        
        # Bonus for recency indicators
        if any(word in line.lower() for word in ["recent", "latest", "new", "just"]):
            score += 0.2
        
        # Bonus for specificity indicators
        if any(word in line.lower() for word in ["case", "study", "blog", "post", "award"]):
            score += 0.1
        
        return score
    
    @staticmethod
    def _build_prompt(company: str, website_url: str, evidence: List[str]) -> List[Dict[str, str]]:
        """Build messages for LLM."""
        evidence_text = "\n".join([f"- {ev}" for ev in evidence[:5]])  # Limit to top 5
        
        user_prompt = (
            f"Company: {company}\n"
            f"Website: {website_url}\n\n"
            f"Evidence from their site:\n{evidence_text}\n\n"
            "Write ONE compelling opening line for a cold email."
        )
        
        return [
            {"role": "system", "content": SYSTEM_RULES},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    async def generate_punchlines(
        db: AsyncSession,
        lead_id: int,
        k: int = 3
    ) -> Dict[str, Any]:
        """
        Generate k punchlines for a lead.
        
        Args:
            db: Database session
            lead_id: Lead ID to generate punchlines for
            k: Number of punchlines to generate (default 3)
            
        Returns:
            Dict with generated punchlines and metadata
            
        Raises:
            ValueError: If lead not found or missing required data
        """
        # Fetch lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        if not lead.company or not lead.website_url:
            raise ValueError(f"Lead {lead_id} missing company or website_url")
        
        # Build evidence from lead data and optionally scrape website
        evidence = [
            f"Company {lead.company} has a website at {lead.website_url}",
        ]
        
        if lead.website_speed_web:
            evidence.append(f"Desktop PageSpeed score: {lead.website_speed_web}/100")
        
        if lead.website_speed_mobile:
            evidence.append(f"Mobile PageSpeed score: {lead.website_speed_mobile}/100")
        
        if lead.seo_score:
            evidence.append(f"SEO score: {lead.seo_score}/100")
        
        if lead.accessibility_score:
            evidence.append(f"Accessibility score: {lead.accessibility_score}/100")
        
        if lead.best_practices_score:
            evidence.append(f"Best practices score: {lead.best_practices_score}/100")
        
        # Optionally scrape website for additional evidence
        try:
            from app.integrations.firecrawl import firecrawl_client
            scraped = await firecrawl_client.scrape_url(
                str(lead.website_url),
                formats=["markdown"]
            )
            content = scraped.get("data", {}).get("markdown", "")
            if content:
                # Extract key facts from content (first 500 chars)
                evidence.append(f"Website content preview: {content[:500]}")
        except Exception as e:
            print(f"Could not scrape website for evidence: {e}")
        
        # Generate punchlines
        messages = PunchlineService._build_prompt(
            lead.company, 
            lead.website_url, 
            evidence
        )
        
        temps = [0.8, 0.6, 1.0, 0.7, 0.9]
        raw: List[str] = []
        i = 0
        
        while len(raw) < k and i < len(temps) * 2:
            try:
                llm = get_llm_client(temperature=temps[i % len(temps)])
                response = llm.invoke(messages)
                line = PunchlineService._normalize(response.content or "")
                
                # Ensure line ends with punctuation
                if line and not line.endswith((".", "!", "?")):
                    line += "."
                
                # Check quality and uniqueness
                if PunchlineService._passes_qc(line, evidence) and \
                   all(line.lower() != r.lower() for r in raw):
                    raw.append(line)
                    # Wait to avoid rate limits
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"Error generating punchline: {e}")
            
            i += 1
        
        # Fill remaining with placeholder
        while len(raw) < k:
            raw.append("Couldn't access website—manual review needed.")
        
        # Score and sort
        scored = []
        for line in raw:
            used_kind = PunchlineService._detect_used_kind(line)
            scored.append({
                "line": line,
                "used_kind": used_kind,
                "score": round(PunchlineService._score_line(line, used_kind), 3)
            })
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # Update lead with top 3 punchlines
        punchlines_dict = {
            "punchline1": scored[0]["line"] if len(scored) > 0 else None,
            "punchline2": scored[1]["line"] if len(scored) > 1 else None,
            "punchline3": scored[2]["line"] if len(scored) > 2 else None,
        }
        
        # Update lead
        for key, value in punchlines_dict.items():
            setattr(lead, key, value)
        
        await db.commit()
        
        return {
            "lead_id": lead_id,
            "company": lead.company,
            "punchlines": scored,
            "updated": punchlines_dict
        }
    
    @staticmethod
    async def generate_bulk_punchlines(
        db: AsyncSession,
        untested_only: bool = True
    ) -> Dict[str, Any]:
        """
        Generate punchlines for multiple leads.
        
        Args:
            db: Database session
            untested_only: Only process leads without punchlines
            
        Returns:
            Dict with task results
        """
        # Create task record
        task = Task(
            name="bulk_punchline_generation",
            status=TaskStatus.RUNNING,
            metadata={"untested_only": untested_only}
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        try:
            # Query leads
            query = select(Lead).where(
                Lead.company.isnot(None),
                Lead.website_url.isnot(None)
            )
            
            if untested_only:
                query = query.where(Lead.punchline1.is_(None))
            
            result = await db.execute(query)
            leads = result.scalars().all()
            
            processed = 0
            failed = 0
            
            for lead in leads:
                try:
                    await PunchlineService.generate_punchlines(db, lead.id)
                    processed += 1
                except Exception as e:
                    print(f"Failed to generate punchlines for lead {lead.id}: {e}")
                    failed += 1
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.result = {
                "processed": processed,
                "failed": failed,
                "total": len(leads)
            }
            await db.commit()
            
            return {
                "task_id": task.id,
                "status": "completed",
                "processed": processed,
                "failed": failed,
                "total": len(leads)
            }
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await db.commit()
            raise


# Import asyncio for sleep
import asyncio
