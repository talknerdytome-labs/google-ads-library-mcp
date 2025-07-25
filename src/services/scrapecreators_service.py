import requests
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Google Ads API endpoints
COMPANY_ADS_API_URL = "https://api.scrapecreators.com/v1/google/company/ads"
AD_DETAILS_API_URL = "https://api.scrapecreators.com/v1/google/ad"


SCRAPECREATORS_API_KEY = None

# --- Helper Functions ---

def get_scrapecreators_api_key() -> str:
    """
    Get ScrapeCreators API key from command line arguments or environment variable.
    Caches the key in memory after first read.
    Priority: command line argument > environment variable

    Returns:
        str: The ScrapeCreators API key.

    Raises:
        Exception: If no key is provided in command line arguments or environment.
    """
    global SCRAPECREATORS_API_KEY
    if SCRAPECREATORS_API_KEY is None:
        # Try command line argument first
        if "--scrapecreators-api-key" in sys.argv:
            token_index = sys.argv.index("--scrapecreators-api-key") + 1
            if token_index < len(sys.argv):
                SCRAPECREATORS_API_KEY = sys.argv[token_index]
                logger.info(f"Using ScrapeCreators API key from command line arguments")
            else:
                raise Exception("--scrapecreators-api-key argument provided but no key value followed it")
        # Try environment variable
        elif os.getenv("SCRAPECREATORS_API_KEY"):
            SCRAPECREATORS_API_KEY = os.getenv("SCRAPECREATORS_API_KEY")
            logger.info(f"Using ScrapeCreators API key from environment variable")
        else:
            raise Exception("ScrapeCreators API key must be provided via '--scrapecreators-api-key' command line argument or 'SCRAPECREATORS_API_KEY' environment variable")

    return SCRAPECREATORS_API_KEY


def get_ad_details(ad_url: str) -> Dict[str, Any]:
    """
    Get detailed information for a specific Google ad.
    
    Args:
        ad_url: The URL of the ad from Google Ads Transparency Center.
    
    Returns:
        Dictionary containing ad details including variations, regions, and impressions.
    
    Raises:
        requests.RequestException: If the API request fails.
        Exception: For other errors.
    """
    api_key = get_scrapecreators_api_key()
    
    response = requests.get(
        AD_DETAILS_API_URL,
        headers={"x-api-key": api_key},
        params={
            "url": ad_url,
        },
        timeout=30
    )
    response.raise_for_status()
    content = response.json()
    
    if not content.get('success'):
        raise Exception(f"API returned unsuccessful response: {content}")
    
    logger.info(f"Retrieved ad details for {ad_url}")
    return content


def get_ads(
    domain: Optional[str] = None,
    advertiser_id: Optional[str] = None,
    topic: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get ads for a company from Google Ads Transparency Center.
    
    Args:
        domain: The domain of the company (e.g., "lululemon.com").
        advertiser_id: The advertiser ID of the company.
        topic: The topic to search for (e.g., "political").
        region: The region to search for (required if topic is "political").
        limit: Maximum number of ads to retrieve.
        cursor: Cursor for pagination.
    
    Returns:
        Dictionary containing ads list, cursor, and success status.
    
    Raises:
        requests.RequestException: If the API request fails.
        Exception: For other errors.
    """
    if not domain and not advertiser_id:
        raise ValueError("Either domain or advertiser_id must be provided")
    
    if topic == "political" and not region:
        raise ValueError("Region is required when searching for political ads")
    
    api_key = get_scrapecreators_api_key()
    headers = {"x-api-key": api_key}
    
    params = {}
    if domain:
        params["domain"] = domain
    if advertiser_id:
        params["advertiser_id"] = advertiser_id
    if topic:
        params["topic"] = topic
    if region:
        params["region"] = region
    if cursor:
        params["cursor"] = cursor
    
    try:
        response = requests.get(
            COMPANY_ADS_API_URL,
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        content = response.json()
        
        if not content.get('success'):
            raise Exception(f"API returned unsuccessful response: {content}")
        
        # Process ads to limit results
        ads = content.get('ads', [])
        if len(ads) > limit:
            ads = ads[:limit]
            content['ads'] = ads
        
        logger.info(f"Retrieved {len(ads)} Google ads for {domain or advertiser_id}")
        return content
        
    except requests.RequestException as e:
        logger.error(f"Network error while fetching Google ads: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing Google ads response: {str(e)}")
        raise


def parse_google_ads(ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse Google ads to extract key information.
    
    Args:
        ads: List of ad objects from Google Ads API.
    
    Returns:
        List of parsed ad objects with extracted media URLs.
    """
    parsed_ads = []
    
    for ad in ads:
        try:
            # Google ads structure is already clean, just need to extract media if available
            ad_obj = {
                'advertiser_id': ad.get('advertiserId'),
                'creative_id': ad.get('creativeId'),
                'format': ad.get('format'),
                'ad_url': ad.get('adUrl'),
                'advertiser_name': ad.get('advertiserName'),
                'domain': ad.get('domain'),
                'first_shown': ad.get('firstShown'),
                'last_shown': ad.get('lastShown')
            }
            
            # For detailed analysis, we'll need to call get_ad_details with the ad_url
            parsed_ads.append(ad_obj)
            
        except Exception as e:
            logger.error(f"Error parsing Google ad {ad.get('creativeId', 'unknown')}: {str(e)}")
            continue
    
    return parsed_ads