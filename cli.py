#!/usr/bin/env python3
"""
Command-line interface for Proxy Service
"""
import sys
import argparse
import json
from src.proxy_manager import ProxyManager
from src.proxy_provider import ProxyProvider
from src.database import ProxyDatabase


def cmd_fetch(args):
    """Fetch and validate proxies"""
    manager = ProxyManager()
    print("Fetching proxies from all sources...")
    result = manager.refresh_proxy_pool()
    
    if result['success']:
        print(f"\n✓ Successfully fetched {result['valid_proxies']} working proxies")
        print(f"  Time taken: {result['elapsed_time']:.2f}s")
        print(f"\nDatabase stats:")
        stats = result['stats']
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print("✗ Failed to fetch proxies")
        sys.exit(1)


def cmd_stats(args):
    """Show proxy statistics"""
    db = ProxyDatabase()
    stats = db.get_stats()
    
    print("\n" + "=" * 60)
    print("PROXY POOL STATISTICS")
    print("=" * 60)
    
    for key, value in stats.items():
        key_formatted = key.replace('_', ' ').title()
        print(f"{key_formatted:.<40} {value}")
    
    print("=" * 60 + "\n")


def cmd_list(args):
    """List active proxies"""
    provider = ProxyProvider()
    limit = args.limit or 20
    output_format = args.format or 'table'
    
    proxies = provider.get_proxies(limit=limit)
    
    if output_format == 'table':
        print(f"\n{'IP':<20} {'Port':<8} {'Protocol':<10} {'Success':<10} {'Speed':<10}")
        print("-" * 70)
        
        for proxy in proxies:
            success_rate = 0
            total = proxy.get('success_count', 0) + proxy.get('fail_count', 0)
            if total > 0:
                success_rate = (proxy.get('success_count', 0) / total) * 100
            
            speed = proxy.get('speed', 0) or 0
            
            print(f"{proxy['ip']:<20} {proxy['port']:<8} {proxy.get('protocol', 'http'):<10} "
                  f"{success_rate:>6.1f}% {speed:>8.2f}s")
        
        print(f"\nShowing {len(proxies)} proxies")
    
    elif output_format in ['text', 'simple']:
        for proxy in proxies:
            print(provider.format_proxy_simple(proxy))
    
    elif output_format == 'url':
        for proxy in proxies:
            print(provider.format_proxy_url(proxy))
    
    elif output_format == 'json':
        print(json.dumps(proxies, indent=2))
    
    elif output_format == 'csv':
        print(provider.export_proxies(proxies, format='csv'))


def cmd_random(args):
    """Get a random proxy"""
    provider = ProxyProvider()
    output_format = args.format or 'simple'
    
    proxy = provider.get_random_proxy()
    
    if not proxy:
        print("✗ No proxies available")
        sys.exit(1)
    
    if output_format == 'simple' or output_format == 'text':
        print(provider.format_proxy_simple(proxy))
    
    elif output_format == 'url':
        print(provider.format_proxy_url(proxy))
    
    elif output_format == 'json':
        print(json.dumps(proxy, indent=2))


def cmd_export(args):
    """Export proxies to file"""
    provider = ProxyProvider()
    limit = args.limit or 100
    output_format = args.format or 'text'
    output_file = args.output or 'proxies.txt'
    
    proxies = provider.get_proxies(limit=limit)
    
    if output_format == 'json':
        content = json.dumps(proxies, indent=2)
    else:
        content = provider.export_proxies(proxies, format=output_format)
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✓ Exported {len(proxies)} proxies to {output_file}")


def cmd_clean(args):
    """Clean up inactive proxies"""
    db = ProxyDatabase()
    days = args.days or 7
    
    print(f"Removing proxies inactive for {days} days...")
    removed = db.remove_inactive_proxies(days=days)
    print(f"✓ Removed {removed} inactive proxies")


def cmd_best(args):
    """Get best performing proxies"""
    provider = ProxyProvider()
    limit = args.limit or 10
    output_format = args.format or 'table'
    
    proxies = provider.get_best_proxies(limit=limit)
    
    if output_format == 'table':
        print(f"\n{'IP':<20} {'Port':<8} {'Success':<10} {'Speed':<10}")
        print("-" * 60)
        
        for proxy in proxies:
            success_rate = 0
            total = proxy.get('success_count', 0) + proxy.get('fail_count', 0)
            if total > 0:
                success_rate = (proxy.get('success_count', 0) / total) * 100
            
            speed = proxy.get('speed', 0) or 0
            
            print(f"{proxy['ip']:<20} {proxy['port']:<8} "
                  f"{success_rate:>6.1f}% {speed:>8.2f}s")
        
        print(f"\nTop {len(proxies)} proxies")
    
    elif output_format in ['text', 'simple']:
        for proxy in proxies:
            print(provider.format_proxy_simple(proxy))
    
    elif output_format == 'json':
        print(json.dumps(proxies, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Proxy Service CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Fetch command
    parser_fetch = subparsers.add_parser('fetch', help='Fetch and validate proxies')
    parser_fetch.set_defaults(func=cmd_fetch)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show proxy statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # List command
    parser_list = subparsers.add_parser('list', help='List active proxies')
    parser_list.add_argument('--limit', type=int, help='Number of proxies to show')
    parser_list.add_argument('--format', choices=['table', 'text', 'simple', 'url', 'json', 'csv'],
                            help='Output format')
    parser_list.set_defaults(func=cmd_list)
    
    # Random command
    parser_random = subparsers.add_parser('random', help='Get a random proxy')
    parser_random.add_argument('--format', choices=['simple', 'url', 'json'],
                              help='Output format (default: simple)')
    parser_random.set_defaults(func=cmd_random)
    
    # Best command
    parser_best = subparsers.add_parser('best', help='Get best performing proxies')
    parser_best.add_argument('--limit', type=int, help='Number of proxies (default: 10)')
    parser_best.add_argument('--format', choices=['table', 'text', 'simple', 'json'],
                            help='Output format')
    parser_best.set_defaults(func=cmd_best)
    
    # Export command
    parser_export = subparsers.add_parser('export', help='Export proxies to file')
    parser_export.add_argument('--limit', type=int, help='Number of proxies (default: 100)')
    parser_export.add_argument('--format', choices=['text', 'url', 'json', 'csv'],
                              help='Output format (default: text)')
    parser_export.add_argument('--output', help='Output file (default: proxies.txt)')
    parser_export.set_defaults(func=cmd_export)
    
    # Clean command
    parser_clean = subparsers.add_parser('clean', help='Remove inactive proxies')
    parser_clean.add_argument('--days', type=int, help='Days of inactivity (default: 7)')
    parser_clean.set_defaults(func=cmd_clean)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()