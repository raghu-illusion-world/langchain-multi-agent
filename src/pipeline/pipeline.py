import re
import time

from groq import RateLimitError

from src.agents.agents import critic_chain, writer_chain
from src.tools.tools import scrape_url, web_search


def _urls_from_search_results(text: str) -> list[str]:
    urls = re.findall(r"URL:\s*(https?://\S+)", text)
    return [url.rstrip(".,)") for url in urls]


def _is_failed_scrape(content: str) -> bool:
    failure_markers = (
        "HTTP error occurred",
        "403 Client Error",
        "Request timed out",
        "Could not scrape URL",
        "Could not extract meaningful content",
    )
    return any(marker in content for marker in failure_markers)


def _invoke_with_rate_limit_retry(chain, payload: dict, attempts: int = 3) -> str:
    for attempt in range(1, attempts + 1):
        try:
            return chain.invoke(payload)
        except RateLimitError:
            if attempt == attempts:
                raise
            wait_seconds = 5 * attempt
            print(f"\nGroq rate limit hit. Retrying in {wait_seconds} seconds...")
            time.sleep(wait_seconds)

    raise RuntimeError("Unable to invoke Groq chain.")


def run_research_pipeline(topic : str) -> dict:

    state = {}

    #search agent working 
    print("\n"+" ="*50)
    print("step 1 - search agent is working ...")
    print("="*50)

    state["search_results"] = web_search.invoke(
        f"Find recent, reliable and detailed information about: {topic}"
    )

    print("\n search result ",state['search_results'])


    #step 2 - reader agent 
    print("\n"+" ="*50)
    print("step 2 - Reader agent is scraping top resources ...")
    print("="*50)

    state["scraped_url"] = None
    state["scrape_errors"] = []

    for url in _urls_from_search_results(state["search_results"]):
        print("\ntrying URL:", url)
        scraped_content = scrape_url.invoke(url)

        if not _is_failed_scrape(scraped_content):
            state["scraped_url"] = url
            state["scraped_content"] = scraped_content
            break

        state["scrape_errors"].append(f"{url} -> {scraped_content}")
        print("blocked or failed, trying next result...")
    else:
        state["scraped_content"] = (
            "Could not scrape the search results directly. "
            "Using the search result snippets as the research source instead."
        )

    print("\nscraped content: \n", state['scraped_content'])


    #step 3 - writer chain 

    print("\n"+" ="*50)
    print("step 3 - Writer is drafting the report ...")
    print("="*50)

    research_combined = (
        f"SEARCH RESULTS : \n {state['search_results'][:2500]} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content'][:2500]}"
    )

    state["report"] = _invoke_with_rate_limit_retry(writer_chain, {
        "topic" : topic,
        "research" : research_combined
    })

    print("\n Final Report\n",state['report'])


    #critic report 

    print("\n"+" ="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    state["feedback"] = _invoke_with_rate_limit_retry(critic_chain, {
        "report": state['report'][:3500]
    })

    print("\n critic report \n", state['feedback'])

    return state
