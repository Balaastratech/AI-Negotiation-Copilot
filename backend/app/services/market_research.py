"""
Market Research Service

This service provides market data research capabilities for the negotiation advisor.
It searches online marketplaces and discussion forums to gather price insights and
comparable listings for items being negotiated.
"""

import logging
import asyncio
from typing import Dict, List, Optional
from statistics import median, mean

logger = logging.getLogger(__name__)


async def search_marketplaces(item: str) -> List[Dict]:
    """
    Search online marketplaces for comparable listings.
    
    Searches platforms like OLX, Facebook Marketplace, and other online
    marketplaces for items similar to the one being negotiated.
    
    Args:
        item: Name/description of item being negotiated
        
    Returns:
        List of marketplace listings, each containing:
        - source: Marketplace name (e.g., "OLX", "Facebook")
        - title: Listing title
        - price: Listed price
        - condition: Item condition (if available)
        - location: Seller location (if available)
        - url: Listing URL
        - posted_date: When posted (if available)
    """
    logger.info(f"Searching marketplaces for: {item}")
    
    try:
        # TODO: Implement actual marketplace search
        # This is a placeholder that will be replaced with real search implementation
        # using web scraping or marketplace APIs
        
        # For now, return empty list
        # Real implementation would search OLX, Facebook Marketplace, etc.
        results = []
        
        logger.info(f"Found {len(results)} marketplace listings for: {item}")
        return results
        
    except Exception as e:
        logger.error(f"Marketplace search failed for '{item}': {e}", exc_info=True)
        # Return empty list on error (graceful degradation)
        return []


async def search_forums(item: str) -> List[Dict]:
    """
    Search discussion forums for price insights and discussions.
    
    Searches platforms like Reddit and other forums for discussions about
    the item being negotiated, including price mentions and buying advice.
    
    Args:
        item: Name/description of item being negotiated
        
    Returns:
        List of forum discussions, each containing:
        - source: Forum name (e.g., "Reddit")
        - title: Thread title
        - summary: Key points from discussion
        - price_mentioned: Price if mentioned in discussion
        - url: Thread URL
        - date: Post date (if available)
    """
    logger.info(f"Searching forums for: {item}")
    
    try:
        # TODO: Implement actual forum search
        # This is a placeholder that will be replaced with real search implementation
        # using Reddit API, forum scraping, etc.
        
        # For now, return empty list
        # Real implementation would search Reddit, specialized forums, etc.
        results = []
        
        logger.info(f"Found {len(results)} forum discussions for: {item}")
        return results
        
    except Exception as e:
        logger.error(f"Forum search failed for '{item}': {e}", exc_info=True)
        # Return empty list on error (graceful degradation)
        return []


def calculate_price_range(results: Dict[str, List[Dict]]) -> Dict:
    """
    Calculate price statistics from search results.
    
    Computes minimum, maximum, average, and median prices from marketplace
    listings and forum discussions.
    
    Args:
        results: Dictionary containing:
            - marketplace_listings: List of marketplace results
            - forum_discussions: List of forum results
            
    Returns:
        Dictionary containing:
        - min: Minimum price found
        - max: Maximum price found
        - average: Average price
        - median: Median price
        - sample_size: Number of listings with prices
    """
    logger.info("Calculating price range from search results")
    
    prices = []
    
    # Extract prices from marketplace listings
    marketplace_listings = results.get("marketplace_listings", [])
    for listing in marketplace_listings:
        price = listing.get("price")
        if price is not None and isinstance(price, (int, float)) and price > 0:
            prices.append(float(price))
    
    # Extract prices from forum discussions
    forum_discussions = results.get("forum_discussions", [])
    for discussion in forum_discussions:
        price = discussion.get("price_mentioned")
        if price is not None and isinstance(price, (int, float)) and price > 0:
            prices.append(float(price))
    
    # Calculate statistics
    if not prices:
        logger.warning("No valid prices found in search results")
        return {
            "min": None,
            "max": None,
            "average": None,
            "median": None,
            "sample_size": 0
        }
    
    price_range = {
        "min": min(prices),
        "max": max(prices),
        "average": mean(prices),
        "median": median(prices),
        "sample_size": len(prices)
    }
    
    logger.info(f"Price range calculated: {price_range}")
    return price_range


async def search_market_data(
    item: str,
    user_price: Optional[float] = None,
    counterparty_price: Optional[float] = None
) -> Dict:
    """
    Search for market data on marketplaces and forums.
    
    Coordinates parallel searches across marketplaces and forums, then
    calculates price statistics from the combined results.
    
    Args:
        item: Name/description of item being negotiated
        user_price: User's asking price (optional, for context)
        counterparty_price: Counterparty's offer (optional, for context)
        
    Returns:
        Dictionary containing:
        - marketplace_listings: List of comparable listings
        - forum_discussions: List of relevant forum posts
        - price_range: Calculated min/max/avg/median prices
        - search_errors: List of any errors encountered (for debugging)
    """
    logger.info(f"Starting market research for: {item}")
    if user_price:
        logger.info(f"  User price: {user_price}")
    if counterparty_price:
        logger.info(f"  Counterparty price: {counterparty_price}")
    
    search_errors = []
    
    # Execute searches in parallel for better performance
    try:
        marketplace_task = search_marketplaces(item)
        forum_task = search_forums(item)
        
        # Wait for both searches to complete
        marketplace_listings, forum_discussions = await asyncio.gather(
            marketplace_task,
            forum_task,
            return_exceptions=True
        )
        
        # Handle exceptions from gather
        if isinstance(marketplace_listings, Exception):
            logger.error(f"Marketplace search raised exception: {marketplace_listings}")
            search_errors.append(f"Marketplace search failed: {str(marketplace_listings)}")
            marketplace_listings = []
        
        if isinstance(forum_discussions, Exception):
            logger.error(f"Forum search raised exception: {forum_discussions}")
            search_errors.append(f"Forum search failed: {str(forum_discussions)}")
            forum_discussions = []
        
    except Exception as e:
        logger.error(f"Market research coordination failed: {e}", exc_info=True)
        search_errors.append(f"Search coordination failed: {str(e)}")
        marketplace_listings = []
        forum_discussions = []
    
    # Combine results
    combined_results = {
        "marketplace_listings": marketplace_listings,
        "forum_discussions": forum_discussions
    }
    
    # Calculate price range from combined results
    try:
        price_range = calculate_price_range(combined_results)
    except Exception as e:
        logger.error(f"Price range calculation failed: {e}", exc_info=True)
        search_errors.append(f"Price calculation failed: {str(e)}")
        price_range = {
            "min": None,
            "max": None,
            "average": None,
            "median": None,
            "sample_size": 0
        }
    
    # Build final result
    result = {
        "marketplace_listings": marketplace_listings,
        "forum_discussions": forum_discussions,
        "price_range": price_range
    }
    
    # Include errors if any occurred (for debugging and graceful degradation)
    if search_errors:
        result["search_errors"] = search_errors
        logger.warning(f"Market research completed with {len(search_errors)} errors")
    else:
        logger.info(f"Market research completed successfully: "
                   f"{len(marketplace_listings)} marketplace listings, "
                   f"{len(forum_discussions)} forum discussions")
    
    return result
