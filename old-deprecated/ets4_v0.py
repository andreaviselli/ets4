import feedparser
from openai import OpenAI
import datetime
from dateutil import parser as dateparser
import json
import requests
import os
import re
from bs4 import BeautifulSoup

def get_ets4(
    openai_api_key: str,
    llm_model: str,
    score_threshold: float,
    days_back: int,
    output_dir: str,
    rss_feeds: dict
):
    """
    Executes the ETS4 Monthly newsletter pipeline: fetches RSS feeds, summarizes/scores papers 
    using an LLM, filters based on quality, and generates Markdown reports.

    Args:
        openai_api_key (str): The valid API key for OpenAI.
        llm_model (str): The model name to use (e.g., "gpt-4o-mini").
        score_threshold (float): Papers with a score below this (1-10) are discarded.
        days_back (int): Number of days to look back in the RSS feeds.
        output_dir (str): Directory path to save the generated Markdown files.
        rss_feeds (dict): A dictionary where keys are Source Names and values are RSS URLs.

    Returns:
        Internal and public Markdown files containing processed and shortlisted papers.
    """
    
    # --- Initialize Client ---
    if not openai_api_key:
        raise ValueError("openai_api_key must be provided.")
    
    client = OpenAI(api_key=openai_api_key)

    # --- Helper Functions (Internal) ---

    def _get_authors(entry):
        """Normalizes author information from a feed entry."""
        if hasattr(entry, 'authors') and entry.authors:
            return ', '.join(author['name'] for author in entry.authors if 'name' in author)
        if hasattr(entry, 'author'):
            return entry.author
        return "Unknown"

    def _create_anchor_slug(title):
        """Creates a Markdown-compatible anchor slug from a title."""
        s = title.lower()
        s = re.sub(r'[^\w\s-]', '', s) # Remove non-alphanumeric characters
        s = re.sub(r'[\s_]+', '-', s).strip('-') # Replace spaces with a single hyphen
        return s

    def fetch_recent_papers(feeds, days):
        """Fetch recent papers from RSS feeds."""
        print(f"Fetching papers from {len(feeds)} sources, looking back {days} days...")
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        papers = []

        for source, url in feeds.items():
            print(f"  - Processing {source} from {url}")
            try:
                response = requests.get(url, timeout=15)
                # Fix encoding if necessary
                if "utf-8" in response.text.lower() or "<?xml" in response.text:
                    response.encoding = "utf-8"
                
                feed = feedparser.parse(response.text)
                if feed.bozo:
                    print(f"    Warning: Malformed feed for {source}. Error: {feed.bozo_exception}")

                found_in_feed = 0
                for entry in feed.entries:
                    pub_date_str = getattr(entry, "published", getattr(entry, "updated", None))
                    if not pub_date_str: continue
                    try:
                        pub_date = dateparser.parse(pub_date_str)
                    except dateparser.ParserError:
                        continue
                    
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
                    
                    if pub_date < cutoff_date: continue
                    
                    summary = getattr(entry, "summary", "")
                    if "<" in summary and ">" in summary:
                        summary = BeautifulSoup(summary, "html.parser").get_text(separator=' ', strip=True)
                    
                    papers.append({
                        "title": entry.title, 
                        "link": entry.link, 
                        "summary": summary,
                        "authors": _get_authors(entry), 
                        "source": source, 
                        "date": pub_date.strftime("%Y-%m-%d")
                    })
                    found_in_feed += 1
                print(f"    Found {found_in_feed} recent papers in {source}.")
            except Exception as e:
                print(f"    Error fetching or parsing feed {source}: {e}")
                continue
        return papers

    def score_and_summarize(paper_data):
        """Sends abstract to LLM for summary, scoring, and categorization."""
        prompt = f"""
You are a highly specialized econometrician and economic forecaster curating "ets4 Monthly (Economic Time Series Forecasting Monthly)", a customized newsletter focused **exclusively on impactful forecasting methods suitable for economic time series.** Your role is to identify only the most relevant and innovative work for an audience of researchers and practitioners that includes econometricians, macroeconomists, energy economists, financial economists and all professionals that are interested in innovative forecasting methods.

You will be given a research working paper. Evaluate it strictly through the lens of **forecasting relevance, innovative content, and potential. In particular, **papers that focus on topics** such as structural analysis and/or causal inference (i.e., structural vector autoregressions for dynamic causal analysis, and causal inference with cross-sections), descriptive statistics and/or econometrics, purely theoretical econometrics and applied economics with no clear and unique forecasting objective and components must be classified as **Not Relevant**, even if they appear in economics journals or are effectively innovative.

---

**Paper Information**

Title: {paper_data['title']}
Authors: {paper_data['authors']}
Source: {paper_data['source']}
Date: {paper_data['date']}
Abstract: {paper_data['summary']}

---

### Your Tasks

1. **Summarize (4–5 sentences)**  
   Focus strictly on elements related to **forecasting and predictive modeling** as stated or clearly implied in the abstract. Because you only see the abstract, avoid inventing or assuming forecasting details unless explicitly mentioned.  
   - If forecasting, prediction, or nowcasting is **explicitly mentioned**, summarize only those components (methods, data, evaluation).  
   - If forecasting is **implied but not directly stated**, clearly indicate this uncertainty (e.g., “the abstract suggests but does not confirm a forecasting application”).  
   - If forecasting is **absent**, explicitly state that no forecasting content is presented.  
   Clearly explain **what is technically or conceptually novel**, but only when the abstract provides enough information to support such statements.

2. **Assign a Quality Score (1–10)**  
      Score based on **forecasting methodological or data novelty, empirical rigor, clarity of predictive purpose, and potential impact or interest for the forecasting community**. Since only the abstract is available, be conservative: give higher scores only when forecasting content is unambiguous.
   - **Extra weight should be given** to papers that:
     - Introduce **new modeling/methodological approaches** or **improve existing ones**. Some examples are, in particular, the use of machine learning/deep learning methods, large language models and generative AI methods, Bayesian methods, novel time series models, forecast combination methods (including Bayesian model averaging), advanced econometric techniques specifically designed for forecasting for policy-relevant macro-financial-economic applications, forecast evaluation such as statistical predictive ability tests and scoring rules, and methods for handling real-time data issues (e.g., ragged edges, mixed frequencies, and data revisions), judgemental forecasting methods, human-AI collaboration for forecasting, study of forecast biases, and interpretability/explainability of forecasts, feature engineering, methods to quantify and improve forecast uncertainty.
     - Use **novel datasets** that could meaningfully enhance economic forecasting. Some examples are, in particular, the use of high-frequency data, alternative data sources (e.g., web-scraped data, satellite data, social media data, news sentiment data, mobility data, transaction data), large-scale datasets, real-time datasets, and data from large language models or other generative AI systems.
     - Present **forecasting applications with real-world decision value**. Some examples are, in particular, the forecasting (and nowcasting) of GDP and inflation, energy prices and demand (including gas, oil, commodities, and electricity), asset prices (including stocks, bonds, interest rates, and crypto), and financial risks (including volatility and default risk).

3. **Classify into One Category**  
   Choose exactly one:
   - **Directly Relevant** → The paper is clearly about **forecasting *economic* time series**, has some of the elements presented above, and offers meaningful contributions or applications although the innovation might not be significant (this is to select also papers that are solid and interesting but not necessarily groundbreaking or highly novel).
   - **Paper of Interest** → The paper is *not economic*, but presents **highly innovative forecasting methods or data sources/types** that could be plausibly transferred to the forecasting of economic time series with some adaptation. Explain briefly how this could be done in the `"adaptability_reason"` field of the JSON output.
   - **Not Relevant** → No clear link with forecasting, or relevance is too indirect (e.g., see the list that is made above).

---

### Scoring & Categorization Rules

| Score | Meaning | Default Category |
|--------|---------|------------------|
| **1–3** | Low quality OR no forecasting at all | Not Relevant |
| **4–6** | Little forecasting contribution and low general quality | Not Relevant |
| **7–8** | Solid contribution to forecasting | Directly Relevant *if economic*, otherwise Paper of Interest |
| **9–10** | Novel forecasting contribution with clear future impact | Directly Relevant *if economic*, otherwise Paper of Interest |

---

### JSON Output Format

Return your response strictly in **valid JSON** using the following schema:

{{
"summary": "...",
"score": X,
"category": "Directly Relevant" | "Paper of Interest" | "Not Relevant",
"adaptability_reason": null | "Required only if category is 'Paper of Interest'"
}}

- If you select **Paper of Interest**, you **must** fill in `"adaptability_reason"` with a short statement explaining how the method could be applied to economic forecasting.
- For **Directly Relevant** or **Not Relevant**, set `"adaptability_reason": null`.
"""
        try:
            response = client.chat.completions.create(
                model=llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            required_keys = ["summary", "score", "category", "adaptability_reason"]
            if not all(key in data for key in required_keys):
                raise ValueError(f"LLM response missing one or more required keys: {required_keys}")
            if not isinstance(data["score"], (int, float)):
                raise ValueError("LLM score is not a number.")
            if data["category"] == "Paper of Interest" and not data.get("adaptability_reason"):
                raise ValueError("Category is 'Paper of Interest' but adaptability_reason is missing.")
            data["score"] = float(data["score"])
            return data
        except Exception as e:
            print(f"Error during LLM call for paper '{paper_data['title']}': {e}")
            return {"summary": f"Error: {e}", "score": 0.0, "category": "Not Relevant", "adaptability_reason": None}

    def build_internal_markdown(relevant, interest, out_dir):
        """Creates the internal markdown file WITH scores for review."""
        os.makedirs(out_dir, exist_ok=True)
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        fname = os.path.join(out_dir, f"{today_str}_ets4_monthly_INTERNAL.md")
        
        lines = [f"# ets4 Monthly [INTERNAL] – {today_str}\n", "Internal review copy with quality scores.\n"]
        lines.append("## Directly Relevant Papers\n")
        if not relevant:
            lines.append("No directly relevant papers met the criteria this month.\n")
        else:
            relevant.sort(key=lambda p: p['score'], reverse=True)
            for p in relevant:
                lines.append(f"### [{p['title']}]({p['link']})")
                lines.append(f"- **Authors:** {p['authors']}")
                lines.append(f"- **Source:** {p['source']} ({p['date']})")
                lines.append(f"- **Quality Score:** {p['score']:.1f}/10")
                lines.append(f"- **Summary:** {p['summary']}\n")
        lines.append("\n---\n")
        lines.append("## Papers of Interest\n")
        if not interest:
            lines.append("No papers of interest were identified this month.\n")
        else:
            interest.sort(key=lambda p: p['score'], reverse=True)
            for p in interest:
                lines.append(f"### [{p['title']}]({p['link']})")
                lines.append(f"- **Authors:** {p['authors']}")
                lines.append(f"- **Source:** {p['source']} ({p['date']})")
                lines.append(f"- **Quality Score:** {p['score']:.1f}/10")
                lines.append(f"- **Summary:** {p['summary']}")
                lines.append(f"- **Reason for Interest:** {p.get('adaptability_reason', 'N/A')}\n")
        
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"✅ Internal review file saved: {fname}")

    def build_public_markdown(relevant, interest, out_dir):
        """Creates the public-facing markdown file with the user-specified clean format."""
        os.makedirs(out_dir, exist_ok=True)
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        fname = os.path.join(out_dir, f"{today_str}_ets4_monthly_PUBLIC.md")
        
        # Date formats
        iso_date_str = today.strftime('%Y-%m-%d')
        main_header_date_str = today.strftime('%B %d, %Y') 
        front_matter_date_str = today.strftime('%B %Y')

        # Front matter
        front_matter = f"""---
title: "ets4: {front_matter_date_str} Issue"
date: {iso_date_str}
draft: true
toc: false
---
"""
        lines = [
            front_matter,
            f"# ets4: {main_header_date_str}\n",
            "\n&nbsp;\n"
        ]

        # Deduplicate and Sort
        seen_titles = set()
        unique_relevant = []
        for p in sorted(relevant, key=lambda x: x['score'], reverse=True):
            normalized_title = ' '.join(p['title'].lower().split())
            if normalized_title not in seen_titles:
                unique_relevant.append(p)
                seen_titles.add(normalized_title)

        unique_interest = []
        for p in sorted(interest, key=lambda x: x['score'], reverse=True):
            normalized_title = ' '.join(p['title'].lower().split())
            if normalized_title not in seen_titles:
                unique_interest.append(p)
                seen_titles.add(normalized_title)

        # "Directly Relevant Papers" Section
        if unique_relevant:
            lines.append("## Directly Relevant Papers\n")
            lines.append("A curated list of recent papers on novel methods for forecasting economic time series.\n")
            lines.append("**In this Issue**\n")
            for p in unique_relevant:
                anchor = _create_anchor_slug(p['title'])
                lines.append(f"* [{p['title']}](#{anchor})")
            lines.append("")

        # "Papers of Interest" Section
        if unique_interest:
            lines.append("\n---\n")
            lines.append("## Papers of Interest\n")
            lines.append("_Methodologically novel papers from other fields that could be adapted for economic forecasting._\n")
            lines.append("**In this Issue**\n")
            for p in unique_interest:
                anchor = _create_anchor_slug(p['title'])
                lines.append(f"* [{p['title']}](#{anchor})")
            lines.append("")

        # "Paper Details" for Relevant
        if unique_relevant:
            lines.append("\n&nbsp;\n")
            lines.append("\n---\n")
            for p in unique_relevant:
                lines.append(f"## {p['title']}")
                lines.append(f"[Link to working paper ↗]({p['link']})\n")
                lines.append(f"- **Authors:** {p['authors']}")
                lines.append(f"- **Source:** {p['source']} ({p['date']})")
                lines.append(f"- **Summary:** {p['summary']}")
                lines.append("\n&nbsp;\n")

        # "Paper Details" for Interest
        if unique_interest:
            lines.append("\n---\n")
            lines.append("\n&nbsp;\n")
            for p in unique_interest:
                lines.append(f"## {p['title']}")
                lines.append(f"[Link to working paper ↗]({p['link']})\n")
                lines.append(f"- **Authors:** {p['authors']}")
                lines.append(f"- **Source:** {p['source']} ({p['date']})")
                lines.append(f"- **Summary:** {p['summary']}")
                lines.append(f"- **Reason for Interest:** {p.get('adaptability_reason', 'N/A')}")
                lines.append("\n&nbsp;\n")

        if not unique_relevant and not unique_interest:
            lines.append("## No papers met the criteria this month. Check back soon!\n")
            
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"✅ Public newsletter file saved: {fname}")

    # --- Main Pipeline Logic ---
    
    print("Starting Economic Forecasting Newsletter Pipeline...")
    
    # 1. Fetch
    all_papers = fetch_recent_papers(rss_feeds, days_back)
    print(f"Found {len(all_papers)} total recent papers.")
    
    # 2. Deduplicate (Link-based)
    unique_papers = []
    seen_links = set()
    for paper in all_papers:
        if paper['link'] not in seen_links:
            unique_papers.append(paper)
            seen_links.add(paper['link'])
    
    if len(all_papers) > len(unique_papers):
        print(f"Removed {len(all_papers) - len(unique_papers)} link-based duplicates. Processing {len(unique_papers)} unique papers.")
    
    # 3. Score and Filter
    shortlisted_relevant = []
    shortlisted_interest = []
    
    for i, paper in enumerate(unique_papers, 1):
        print(f"Processing paper {i}/{len(unique_papers)}: '{paper['title'][:70]}...'")
        result = score_and_summarize(paper)
        paper.update(result)
        
        if paper.get("score", 0.0) >= score_threshold:
            if paper.get("category") == "Directly Relevant":
                shortlisted_relevant.append(paper)
                print(f"  -> Shortlisted! (Relevant) Score: {paper['score']:.1f}/10")
            elif paper.get("category") == "Paper of Interest":
                shortlisted_interest.append(paper)
                print(f"  -> Shortlisted! (Interest) Score: {paper['score']:.1f}/10")
            else:
                print(f"  -> Skipped. Category: {paper.get('category', 'Unknown')}, Score: {paper['score']:.1f}/10")
        else:
            print(f"  -> Skipped. Score below threshold: {paper.get('score', 0.0):.1f}/10")
    
    # 4. Build Outputs
    build_internal_markdown(shortlisted_relevant, shortlisted_interest, output_dir)
    build_public_markdown(shortlisted_relevant, shortlisted_interest, output_dir)
    
    print("\n--- Pipeline Finished ---")
    
    return {
        "total_processed": len(unique_papers),
        "shortlisted_relevant": len(shortlisted_relevant),
        "shortlisted_interest": len(shortlisted_interest)
    }