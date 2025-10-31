import requests
from bs4 import BeautifulSoup
import time
import re
import csv
from datetime import datetime
import json

def get_product_bsr(url):
    """
    Fetches the Best Sellers Rank (BSR) from an Amazon product page.
    
    Args:
        url (str): Amazon product URL
    
    Returns:
        dict: Product information including title and BSR
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product title
        title_element = soup.find('span', {'id': 'productTitle'})
        title = title_element.get_text().strip() if title_element else "Title not found"
        
        # Extract ASIN from URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        asin = asin_match.group(1) if asin_match else "N/A"
        
        # Extract Best Sellers Rank
        rankings = []
        
        # Method 1: Product details table
        rank_section = soup.find('th', string=re.compile('Best Sellers Rank', re.IGNORECASE))
        if rank_section:
            rank_data = rank_section.find_next('td')
            if rank_data:
                rank_text = rank_data.get_text()
                rank_matches = re.findall(r'#([\d,]+)\s+in\s+([^\(]+?)(?:\s*\(|$)', rank_text)
                for rank, category in rank_matches:
                    rankings.append({
                        'rank': int(rank.replace(',', '')),
                        'rank_formatted': rank,
                        'category': category.strip()
                    })
        
        # Method 2: Detail bullets section
        if not rankings:
            detail_bullets = soup.find('div', {'id': 'detailBulletsWrapper_feature_div'})
            if detail_bullets:
                bsr_li = detail_bullets.find('li', string=re.compile('Best Sellers Rank', re.IGNORECASE))
                if not bsr_li:
                    # Try finding in spans
                    spans = detail_bullets.find_all('span', string=re.compile('Best Sellers Rank', re.IGNORECASE))
                    for span in spans:
                        parent = span.find_parent('li') or span.find_parent('span')
                        if parent:
                            rank_text = parent.get_text()
                            rank_matches = re.findall(r'#([\d,]+)\s+in\s+([^\(]+?)(?:\s*\(|$)', rank_text)
                            for rank, category in rank_matches:
                                rankings.append({
                                    'rank': int(rank.replace(',', '')),
                                    'rank_formatted': rank,
                                    'category': category.strip()
                                })
                else:
                    rank_text = bsr_li.get_text()
                    rank_matches = re.findall(r'#([\d,]+)\s+in\s+([^\(]+?)(?:\s*\(|$)', rank_text)
                    for rank, category in rank_matches:
                        rankings.append({
                            'rank': int(rank.replace(',', '')),
                            'rank_formatted': rank,
                            'category': category.strip()
                        })
        
        # Method 3: Product details section (newer layout)
        if not rankings:
            detail_section = soup.find('div', {'id': 'detailBullets_feature_div'})
            if detail_section:
                bsr_text = detail_section.get_text()
                if 'Best Sellers Rank' in bsr_text:
                    rank_matches = re.findall(r'#([\d,]+)\s+in\s+([^\(]+?)(?:\s*\(|$)', bsr_text)
                    for rank, category in rank_matches:
                        rankings.append({
                            'rank': int(rank.replace(',', '')),
                            'rank_formatted': rank,
                            'category': category.strip()
                        })
        
        # Get primary rank (first one listed)
        primary_rank = rankings[0] if rankings else None
        
        return {
            'url': url,
            'asin': asin,
            'title': title,
            'primary_rank': primary_rank['rank'] if primary_rank else None,
            'primary_rank_formatted': primary_rank['rank_formatted'] if primary_rank else 'Not found',
            'primary_category': primary_rank['category'] if primary_rank else 'N/A',
            'all_rankings': rankings,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success'
        }
    
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'asin': 'N/A',
            'title': 'Error',
            'primary_rank': None,
            'primary_rank_formatted': 'Error',
            'primary_category': 'N/A',
            'all_rankings': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'error',
            'error': str(e)
        }
    except Exception as e:
        return {
            'url': url,
            'asin': 'N/A',
            'title': 'Error',
            'primary_rank': None,
            'primary_rank_formatted': 'Error',
            'primary_category': 'N/A',
            'all_rankings': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'error',
            'error': f"Parsing error: {str(e)}"
        }

def process_products(urls, delay=3):
    """
    Process multiple Amazon product URLs with progress tracking.
    
    Args:
        urls (list): List of Amazon product URLs
        delay (int): Delay between requests in seconds
    
    Returns:
        list: List of product information dictionaries
    """
    results = []
    total = len(urls)
    
    print(f"\nStarting to process {total} products...")
    print(f"Estimated time: ~{(total * delay) / 60:.1f} minutes\n")
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{total}] Processing: {url[:60]}...")
        result = get_product_bsr(url)
        results.append(result)
        
        if result['status'] == 'success':
            print(f"  ✓ BSR: #{result['primary_rank_formatted']} in {result['primary_category']}")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")
        
        # Add delay between requests
        if i < total:
            time.sleep(delay)
    
    return results

def save_to_csv(results, filename='amazon_bsr_results.csv'):
    """Save results to CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ASIN', 'Product Title', 'Primary BSR', 'Primary Category', 'All Rankings', 'URL', 'Timestamp', 'Status'])
        
        for result in results:
            all_ranks = '; '.join([f"#{r['rank_formatted']} in {r['category']}" for r in result['all_rankings']])
            writer.writerow([
                result['asin'],
                result['title'],
                result['primary_rank_formatted'],
                result['primary_category'],
                all_ranks,
                result['url'],
                result['timestamp'],
                result['status']
            ])
    
    print(f"\n✓ Results saved to {filename}")

def save_to_json(results, filename='amazon_bsr_results.json'):
    """Save results to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to {filename}")

def display_summary(results):
    """Display summary statistics."""
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    successful_results = [r for r in results if r['status'] == 'success' and r['primary_rank']]
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total products processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if successful_results:
        avg_rank = sum(r['primary_rank'] for r in successful_results) / len(successful_results)
        best_rank = min(r['primary_rank'] for r in successful_results)
        worst_rank = max(r['primary_rank'] for r in successful_results)
        
        print(f"\nRanking Statistics:")
        print(f"  Average BSR: #{avg_rank:,.0f}")
        print(f"  Best BSR: #{best_rank:,}")
        print(f"  Worst BSR: #{worst_rank:,}")

# Example usage
if __name__ == "__main__":
    # Load URLs from a text file (one URL per line)
    try:
        with open('amazon_urls.txt', 'r') as f:
            product_urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
        
        if not product_urls:
            print("Error: No valid URLs found in amazon_urls.txt")
            print("Please create amazon_urls.txt with one Amazon URL per line.")
            exit(1)
        
        print(f"Loaded {len(product_urls)} URLs from amazon_urls.txt")
        
    except FileNotFoundError:
        print("Error: amazon_urls.txt not found!")
        print("Please create amazon_urls.txt with one Amazon URL per line.")
        print("\nExample content:")
        print("https://www.amazon.com/dp/B08N5WRWNW")
        print("https://www.amazon.com/dp/B0BSHF7WHW")
        exit(1)
    
    # Process products (3 second delay between requests)
    results = process_products(product_urls, delay=3)
    
    # Save results to CSV
    save_to_csv(results)
    
    # Save results to JSON (optional)
    save_to_json(results)
    
    # Display summary
    display_summary(results)
