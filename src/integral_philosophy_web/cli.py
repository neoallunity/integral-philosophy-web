#!/usr/bin/env python3
"""Integral Philosophy Web CLI - Web Interface Tools"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        prog='integral-web',
        description='🌐 Web interface and API CLI'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start web interface')
    start_parser.add_argument('--port', type=int, default=8000, help='Port')
    
    # API command
    api_parser = subparsers.add_parser('api', help='Start API server')
    api_parser.add_argument('--port', type=int, default=8001, help='Port')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        print(f"Starting web interface on port {args.port}...")
    elif args.command == 'api':
        print(f"Starting API server on port {args.port}...")
    else:
        parser.print_help()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
